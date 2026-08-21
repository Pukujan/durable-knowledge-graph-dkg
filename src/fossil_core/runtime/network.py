from __future__ import annotations

import base64
import binascii
import hmac
import inspect
import json
import os
from collections.abc import Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from fossil_core.adapters.mcp import ThinMCPAdapter
from fossil_core.adapters.mcp.server import build_mcp_server
from fossil_core.agent import AgentContext
from fossil_core.application.ingest.reviewed_evidence import (
    ReviewedClaimDraft,
    ReviewedEvidenceIngestError,
    ReviewedSource,
)
from fossil_core.domain.pack import PackBoundaryError

from .node import FilesystemFossilNode


Probe = Callable[[], Any | Awaitable[Any]]
MCP_BEARER_TOKEN_ENV = "FOSSIL_MCP_BEARER_TOKEN"


class BearerAuthMiddleware:
    """Fail-closed bearer authentication for the public FOSSIL HTTP edge."""

    def __init__(self, app: Any, token: str, *, public_paths: frozenset[str]):
        if not token or any(character.isspace() for character in token):
            raise ValueError("FOSSIL MCP bearer token must be non-empty and whitespace-free")
        self.app = app
        self.token = token
        self.public_paths = public_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self.public_paths:
            await self.app(scope, receive, send)
            return

        authorization_values = [
            value.decode("latin-1")
            for name, value in scope.get("headers", [])
            if name.lower() == b"authorization"
        ]
        valid = False
        if len(authorization_values) == 1:
            scheme, separator, presented = authorization_values[0].partition(" ")
            valid = (
                separator == " "
                and scheme.lower() == "bearer"
                and bool(presented)
                and not any(character.isspace() for character in presented)
                and hmac.compare_digest(presented, self.token)
            )

        if not valid:
            response = JSONResponse(
                {
                    "error": {
                        "code": "authentication_required",
                        "detail": "Bearer authentication required",
                    }
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


async def _await_if_needed(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _json_error(code: str, detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "detail": detail}}, status_code=status_code
    )


@dataclass
class NodeReadinessProbe:
    """Machine-readable readiness for canonical truth and its projection.

    Liveness is intentionally separate. A graph outage can make the node not
    ready for semantic retrieval while the canonical evidence/event substrate is
    still healthy and authoritative.
    """

    node: FilesystemFossilNode
    projection_check: Probe | None = None
    max_projection_lag_events: int = 0

    def __post_init__(self) -> None:
        if self.max_projection_lag_events < 0:
            raise ValueError("max_projection_lag_events must be non-negative")

    def _canonical_status(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        roots = {
            "artifacts": self.node.paths.artifacts_root,
            "sources": self.node.paths.sources_root,
            "events": self.node.paths.events_root,
        }
        try:
            for name, root in roots.items():
                if not root.is_dir():
                    raise OSError(f"canonical {name} root is unavailable: {root}")
                if not os.access(root, os.R_OK | os.W_OK):
                    raise OSError(f"canonical {name} root is not readable/writable: {root}")
            events = list(self.node.event_store.iter_events())
        except Exception as exc:
            return (
                {
                    "status": "unavailable",
                    "reason": "canonical_store_unavailable",
                    "detail": str(exc),
                },
                [],
            )
        return (
            {
                "status": "available",
                "event_count": len(events),
            },
            events,
        )

    async def _probe_projection(self) -> Any:
        if self.projection_check is not None:
            return await _await_if_needed(self.projection_check())

        driver = getattr(self.node.projection.client, "driver", None)
        execute_query = getattr(driver, "execute_query", None)
        if callable(execute_query):
            return await _await_if_needed(
                execute_query("RETURN 1 AS fossil_ready", routing_="r")
            )

        # Test/dummy projection clients may not expose a database driver. The
        # adapter health contract still establishes that the projection is wired;
        # production Graphiti exposes ``driver.execute_query`` and is probed above.
        return self.node.projection.health()

    async def check(self) -> dict[str, Any]:
        canonical, events = self._canonical_status()
        durable_truth = (
            "available" if canonical["status"] == "available" else "unavailable"
        )

        try:
            projection_probe = await self._probe_projection()
            if projection_probe is False:
                raise RuntimeError("projection readiness probe returned false")
        except Exception as exc:
            projection = {
                "status": "unavailable",
                "reason": "projection_unavailable",
                "detail": str(exc),
            }
            return {
                "status": "not_ready",
                "durable_truth": durable_truth,
                "canonical": canonical,
                "projection": projection,
            }

        pending_event_ids = [
            str(event["event_id"])
            for event in events
            if not self.node.projection.ledger.is_applied(str(event["event_id"]))
            and not self.node.projection.ledger.is_redacted(str(event["event_id"]))
        ]
        if len(pending_event_ids) > self.max_projection_lag_events:
            projection = {
                "status": "lagging",
                "reason": "projection_lag",
                "pending_events": len(pending_event_ids),
                "max_pending_events": self.max_projection_lag_events,
            }
        else:
            projection = {
                "status": "available",
                "pending_events": len(pending_event_ids),
                "max_pending_events": self.max_projection_lag_events,
            }

        ready = canonical["status"] == "available" and projection["status"] == "available"
        return {
            "status": "ready" if ready else "not_ready",
            "durable_truth": durable_truth,
            "canonical": canonical,
            "projection": projection,
        }


def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be an object")
    return value


def _required_text(mapping: Mapping[str, Any], field: str) -> str:
    value = mapping[field]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _decode_source(source: Mapping[str, Any]) -> ReviewedSource:
    encoded = _required_text(source, "data_b64")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("source.data_b64 must be valid base64") from exc

    return ReviewedSource(
        data=data,
        source_kind=_required_text(source, "source_kind"),
        source_role=_required_text(source, "source_role"),
        locator=dict(_required_mapping(source["locator"], "source.locator")),
        retrieved_at=_required_text(source, "retrieved_at"),
        quality=dict(_required_mapping(source["quality"], "source.quality")),
        published_at=source.get("published_at"),
        version_metadata=(
            dict(_required_mapping(source["version_metadata"], "source.version_metadata"))
            if source.get("version_metadata") is not None
            else None
        ),
        derivation=(
            dict(_required_mapping(source["derivation"], "source.derivation"))
            if source.get("derivation") is not None
            else None
        ),
        media_type=str(source.get("media_type") or "application/octet-stream"),
    )


def _decode_claims(value: Any) -> list[ReviewedClaimDraft]:
    if not isinstance(value, list):
        raise TypeError("claims must be an array")
    claims: list[ReviewedClaimDraft] = []
    for index, raw_claim in enumerate(value):
        claim = _required_mapping(raw_claim, f"claims[{index}]")
        claims.append(
            ReviewedClaimDraft(
                subject_ref=_required_text(claim, "subject_ref"),
                claim_text=_required_text(claim, "claim_text"),
                reason=_required_text(claim, "reason"),
            )
        )
    return claims


async def _read_json(request: Request, *, max_bytes: int) -> Mapping[str, Any] | JSONResponse:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                return _json_error(
                    "request_too_large",
                    f"request exceeds {max_bytes} byte ingest limit",
                    413,
                )
        except ValueError:
            return _json_error("invalid_request", "invalid Content-Length header", 400)

    raw = await request.body()
    if len(raw) > max_bytes:
        return _json_error(
            "request_too_large",
            f"request exceeds {max_bytes} byte ingest limit",
            413,
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _json_error("invalid_json", "request body must be valid UTF-8 JSON", 400)
    if not isinstance(payload, Mapping):
        return _json_error("invalid_request", "request body must be a JSON object", 400)
    return payload


def create_node_network_app(
    node: FilesystemFossilNode,
    *,
    context: AgentContext,
    readiness_probe: NodeReadinessProbe | None = None,
    transport_security: TransportSecuritySettings | None = None,
    bearer_token: str | None = None,
    host: str = "127.0.0.1",
    max_ingest_bytes: int = 16 * 1024 * 1024,
    max_mcp_request_body_size: int = 1024 * 1024,
) -> Starlette:
    """Compose MCP Streamable HTTP and operational HTTP routes for one node.

    The configured ``AgentContext`` is node-owned authority. HTTP request bodies
    cannot supply a durable actor or a pack manifest, preventing remote callers
    from manufacturing provenance or widening the pack boundary.
    """

    if max_ingest_bytes < 1 or max_mcp_request_body_size < 1:
        raise ValueError("request body limits must be positive")

    resolved_bearer_token = (
        bearer_token if bearer_token is not None else os.environ.get(MCP_BEARER_TOKEN_ENV)
    )
    if not resolved_bearer_token:
        raise ValueError(
            "FOSSIL MCP bearer token is required; pass bearer_token or set "
            f"{MCP_BEARER_TOKEN_ENV}"
        )

    mcp_adapter = ThinMCPAdapter(
        service=node.corpus_service,
        access=node.pack_access,
        context=context,
    )
    mcp = build_mcp_server(mcp_adapter)
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        max_request_body_size=max_mcp_request_body_size,
        transport_security=transport_security,
        host=host,
    )
    readiness = readiness_probe or NodeReadinessProbe(node)

    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "fossil-core",
                "service_version": node.corpus_service.service_version,
            }
        )

    async def readyz(request: Request) -> JSONResponse:
        snapshot = await readiness.check()
        return JSONResponse(
            snapshot,
            status_code=200 if snapshot["status"] == "ready" else 503,
        )

    async def ingest(request: Request) -> JSONResponse:
        parsed = await _read_json(request, max_bytes=max_ingest_bytes)
        if isinstance(parsed, JSONResponse):
            return parsed

        try:
            expected_pack_id = str(node.pack_manifest["pack_id"])
            requested_pack_id = str(parsed.get("pack_id") or expected_pack_id)
            if requested_pack_id != expected_pack_id:
                raise PackBoundaryError(
                    f"ingest pack {requested_pack_id} does not match mounted pack {expected_pack_id}"
                )
            node.pack_access.require_write(expected_pack_id)

            source = _decode_source(_required_mapping(parsed["source"], "source"))
            claims = _decode_claims(parsed["claims"])
            receipt = node.reviewed_ingest.ingest(
                pack_manifest=node.pack_manifest,
                source=source,
                claims=claims,
                review_ref=_required_text(parsed, "review_ref"),
                actor=context.durable_actor(),
                occurred_at=_required_text(parsed, "occurred_at"),
                recorded_at=_required_text(parsed, "recorded_at"),
                correlation_id=_required_text(parsed, "correlation_id"),
                requested_outcome="proposed",
            )
        except PackBoundaryError as exc:
            return _json_error("unauthorized_pack", str(exc), 403)
        except OSError as exc:
            return _json_error("canonical_store_unavailable", str(exc), 503)
        except (
            KeyError,
            TypeError,
            ValueError,
            ValidationError,
            ReviewedEvidenceIngestError,
        ) as exc:
            return _json_error("invalid_ingest", str(exc), 422)
        except Exception:
            return _json_error("internal_error", "reviewed ingest failed", 500)

        if receipt.get("status") == "rejected":
            return JSONResponse(receipt, status_code=422)
        return JSONResponse(receipt, status_code=201)

    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[
            Route("/healthz", healthz, methods=["GET"]),
            Route("/readyz", readyz, methods=["GET"]),
            Route("/ingest", ingest, methods=["POST"]),
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(
        BearerAuthMiddleware,
        token=resolved_bearer_token,
        public_paths=frozenset({"/healthz", "/readyz"}),
    )
    app.state.fossil_node = node
    app.state.mcp_server = mcp
    app.state.readiness_probe = readiness
    return app


__all__ = ["NodeReadinessProbe", "create_node_network_app"]
