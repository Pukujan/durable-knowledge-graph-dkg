from __future__ import annotations

import hmac
import ipaddress
import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fossil_core.adapters.mcp import ThinMCPAdapter
from fossil_core.agent import AgentContext, AgentProvenanceError
from fossil_core.domain.pack import PackBoundaryError
from fossil_core.ports.capability import CapabilityError

from .node import FilesystemFossilNode


_ACTION_PATHS = {
    "/actions/search": "fossil.search",
    "/actions/read": "fossil.read",
}
_ACTION_ROUTE_ALLOWLIST = frozenset(
    {"/openapi.json", *_ACTION_PATHS, "/actions/capabilities"}
)
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_MAX_QUERY_CHARS = 8192


def _error(code: str, detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "detail": detail}}, status_code=status_code
    )


def _map_action_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, PackBoundaryError):
        return _error("unauthorized_pack", "requested knowledge is not readable", 403)
    if isinstance(exc, (CapabilityError, AgentProvenanceError)):
        return _error("capability_denied", "requested capability is not permitted", 403)
    if isinstance(exc, (FileNotFoundError, KeyError)):
        return _error("not_found", "requested resource was not found", 404)
    if isinstance(exc, (TypeError, ValueError)):
        return _error("invalid_request", "request was rejected", 400)
    if isinstance(exc, OSError):
        return _error("canonical_store_unavailable", "canonical store unavailable", 503)
    return _error("internal_error", "FOSSIL Action execution failed", 500)


def _object_schema(*, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _json_response(schema: dict[str, Any], description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": schema}},
    }


def _ref(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def _identifier_schema(description: str) -> dict[str, Any]:
    return {
        "type": "string",
        "minLength": 1,
        "maxLength": 256,
        "pattern": _OPAQUE_ID.pattern,
        "description": description,
    }


def chatgpt_action_openapi_schema(*, server_url: str | None = None) -> dict[str, Any]:
    """Return the bounded OpenAPI 3.1 contract for a private GPT Action."""

    common_responses = {
        "400": _json_response(_ref("ErrorEnvelope"), "Invalid request"),
        "401": _json_response(_ref("ErrorEnvelope"), "Missing or invalid bearer token"),
        "403": _json_response(_ref("ErrorEnvelope"), "Pack or capability denied"),
        "404": _json_response(_ref("ErrorEnvelope"), "Resource not found"),
        "405": _json_response(_ref("ErrorEnvelope"), "HTTP method not allowed"),
        "413": _json_response(_ref("ErrorEnvelope"), "Request body too large"),
        "500": _json_response(_ref("ErrorEnvelope"), "Internal server error"),
        "503": _json_response(
            _ref("ErrorEnvelope"), "Canonical store or HTTPS origin unavailable"
        ),
    }

    schemas: dict[str, Any] = {
        "ErrorDetail": {
            "type": "object",
            "additionalProperties": False,
            "required": ["code", "detail"],
            "properties": {
                "code": {"type": "string"},
                "detail": {"type": "string"},
            },
        },
        "ErrorEnvelope": {
            "type": "object",
            "additionalProperties": False,
            "required": ["error"],
            "properties": {"error": _ref("ErrorDetail")},
        },
        "Actor": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "actor_type": {"type": "string"},
                "actor_id": {"type": "string"},
                "model_id": {"type": "string"},
                "harness_version": {"type": "string"},
                "skill_id": {"type": "string"},
                "skill_version": {"type": "string"},
            },
        },
        "SearchRequest": _object_schema(
            required=["query"],
            properties={
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": _MAX_QUERY_CHARS,
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                },
            },
        ),
        "ReadRequest": _object_schema(
            required=["event_id"],
            properties={
                "event_id": _identifier_schema("Opaque durable event identifier")
            },
        ),
        "SearchResult": {
            "type": "object",
            "additionalProperties": True,
            "required": ["event_id", "event_type", "pack_id", "recorded_at"],
            "properties": {
                "event_id": {"type": "string"},
                "event_type": {"type": "string"},
                "pack_id": {"type": "string"},
                "recorded_at": {"type": "string"},
                "subject_refs": {"type": "array", "items": {"type": "string"}},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "source_snapshot_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "score": {"type": "number"},
            },
        },
        "FossilEvent": {
            "type": "object",
            "additionalProperties": True,
            "required": [
                "event_id",
                "event_type",
                "pack_id",
                "occurred_at",
                "recorded_at",
            ],
            "properties": {
                "schema_version": {"type": "string"},
                "event_id": {"type": "string"},
                "event_type": {"type": "string"},
                "occurred_at": {"type": "string"},
                "recorded_at": {"type": "string"},
                "pack_id": {"type": "string"},
                "actor": _ref("Actor"),
                "subject_refs": {"type": "array", "items": {"type": "string"}},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "source_snapshot_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "caused_by_event_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "correlation_id": {"type": ["string", "null"]},
                "idempotency_key": {"type": "string"},
                "payload": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Event-type-specific canonical payload.",
                },
                "provenance": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Canonical event provenance when present.",
                },
            },
        },
        "CapabilitiesResponse": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "service_version",
                "action_capabilities",
                "durable_writes_exposed",
                "ingestion_exposed",
                "mcp_exposed",
                "arbitrary_graph_mutation",
            ],
            "properties": {
                "service_version": {"type": "string"},
                "action_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "const": ["search", "read"],
                },
                "durable_writes_exposed": {"type": "boolean", "const": False},
                "ingestion_exposed": {"type": "boolean", "const": False},
                "mcp_exposed": {"type": "boolean", "const": False},
                "arbitrary_graph_mutation": {"type": "boolean", "const": False},
            },
        },
    }

    schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "FOSSIL read-only ChatGPT Action API",
            "version": "1.0.0",
            "description": (
                "Private read-only compatibility surface over canonical FOSSIL data. "
                "Only search, durable-event read, and capability metadata are Action "
                "operations. Lineage remains a FOSSIL domain/MCP capability but is not "
                "advertised by the standalone Action until a durable read-only lineage "
                "provider is configured. MCP, ingestion, proposal, validation, commit, "
                "graph mutation, arbitrary filesystem access, and secret disclosure are "
                "prohibited."
            ),
        },
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "opaque",
                }
            },
        },
        "security": [{"BearerAuth": []}],
        "paths": {
            "/actions/search": {
                "post": {
                    "operationId": "fossilSearch",
                    "summary": "Search readable FOSSIL knowledge",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {"schema": _ref("SearchRequest")}
                        },
                    },
                    "responses": {
                        "200": _json_response(
                            {"type": "array", "items": _ref("SearchResult")},
                            "Authorized search results",
                        ),
                        **common_responses,
                    },
                }
            },
            "/actions/read": {
                "post": {
                    "operationId": "fossilRead",
                    "summary": "Read one durable FOSSIL event",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {"schema": _ref("ReadRequest")}
                        },
                    },
                    "responses": {
                        "200": _json_response(
                            _ref("FossilEvent"), "Authorized durable event"
                        ),
                        **common_responses,
                    },
                }
            },
            "/actions/capabilities": {
                "get": {
                    "operationId": "fossilActionCapabilities",
                    "summary": "Describe the bounded read-only Action surface",
                    "responses": {
                        "200": _json_response(
                            _ref("CapabilitiesResponse"),
                            "Read-only Action capabilities",
                        ),
                        "401": common_responses["401"],
                        "405": common_responses["405"],
                    },
                }
            },
        },
    }
    if server_url:
        schema["servers"] = [{"url": server_url.rstrip("/")}]
    return schema


def _safe_identifier(value: Any) -> str | None:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        return None
    return value


def _has_only_keys(payload: Mapping[str, Any], allowed: set[str]) -> bool:
    return set(payload).issubset(allowed)


class ChatGPTActionMiddleware(BaseHTTPMiddleware):
    """Serve only the bounded authenticated REST compatibility surface."""

    def __init__(
        self,
        app: Any,
        *,
        adapter: ThinMCPAdapter,
        bearer_token: str,
        max_request_body_size: int = 64 * 1024,
        public_base_url: str | None = None,
        trusted_proxy_cidrs: tuple[str, ...] = (),
    ) -> None:
        super().__init__(app)
        if not bearer_token or bearer_token != bearer_token.strip():
            raise ValueError(
                "ChatGPT Action bearer token must be a non-empty trimmed string"
            )
        if max_request_body_size < 1:
            raise ValueError("ChatGPT Action request body limit must be positive")
        if public_base_url is not None and not public_base_url.startswith("https://"):
            raise ValueError("public ChatGPT Action base URL must use https://")
        self.adapter = adapter
        self.bearer_token = bearer_token
        self.max_request_body_size = max_request_body_size
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self.trusted_proxy_networks = tuple(
            ipaddress.ip_network(cidr, strict=False) for cidr in trusted_proxy_cidrs
        )

    def _authorized(self, request: Request) -> bool:
        values = request.headers.getlist("authorization")
        if len(values) != 1:
            return False
        value = values[0]
        scheme, separator, supplied = value.partition(" ")
        if (
            separator != " "
            or scheme.lower() != "bearer"
            or not supplied
            or supplied != supplied.strip()
            or any(character.isspace() for character in supplied)
        ):
            return False
        return hmac.compare_digest(supplied, self.bearer_token)

    def _trusted_proxy_origin(self, request: Request) -> str | None:
        if not self.trusted_proxy_networks or request.client is None:
            return None
        try:
            peer = ipaddress.ip_address(request.client.host)
        except ValueError:
            return None
        if not any(peer in network for network in self.trusted_proxy_networks):
            return None

        proto_values = request.headers.getlist("x-forwarded-proto")
        host_values = request.headers.getlist("x-forwarded-host")
        if len(proto_values) != 1 or len(host_values) != 1:
            return None
        proto = proto_values[0]
        host = host_values[0]
        if (
            proto.lower() != "https"
            or not host
            or "," in proto
            or "," in host
            or len(host) > 255
            or any(character.isspace() for character in host)
            or any(character in host for character in "/\\@?#")
        ):
            return None
        try:
            parsed = urlsplit(f"https://{host}")
            _ = parsed.port
        except ValueError:
            return None
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            return None
        return f"https://{host}"

    def _schema_origin(self, request: Request) -> str | None:
        if self.public_base_url:
            return self.public_base_url
        # A caller-controlled direct HTTPS Host is not an authority signal. Without
        # a fixed public origin, only forwarded HTTPS metadata from an explicitly
        # trusted proxy peer may define the server URL advertised to a Custom GPT.
        return self._trusted_proxy_origin(request)

    async def _read_json(self, request: Request) -> Mapping[str, Any] | JSONResponse:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                return _error("invalid_request", "invalid Content-Length header", 400)
            if declared < 0:
                return _error("invalid_request", "invalid Content-Length header", 400)
            if declared > self.max_request_body_size:
                return _error(
                    "request_too_large",
                    f"request exceeds {self.max_request_body_size} byte Action limit",
                    413,
                )

        raw = bytearray()
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > self.max_request_body_size:
                return _error(
                    "request_too_large",
                    f"request exceeds {self.max_request_body_size} byte Action limit",
                    413,
                )
            raw.extend(chunk)

        try:
            payload = json.loads(bytes(raw).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error("invalid_json", "request body must be valid UTF-8 JSON", 400)
        if not isinstance(payload, Mapping):
            return _error("invalid_request", "request body must be a JSON object", 400)
        return payload

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        if path not in _ACTION_ROUTE_ALLOWLIST:
            return _error("not_found", "route not found", 404)

        if path == "/openapi.json":
            if request.method != "GET":
                return _error(
                    "method_not_allowed", "OpenAPI discovery requires GET", 405
                )
            server_url = self._schema_origin(request)
            if server_url is None:
                return _error(
                    "https_origin_required",
                    "OpenAPI discovery requires a trusted public HTTPS origin",
                    503,
                )
            return JSONResponse(chatgpt_action_openapi_schema(server_url=server_url))

        if not self._authorized(request):
            response = _error("unauthorized", "valid bearer token required", 401)
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        if path == "/actions/capabilities":
            if request.method != "GET":
                return _error(
                    "method_not_allowed", "capabilities requires GET", 405
                )
            service = getattr(self.adapter, "service", None)
            return JSONResponse(
                {
                    "service_version": getattr(service, "service_version", "unknown"),
                    "action_capabilities": ["search", "read"],
                    "durable_writes_exposed": False,
                    "ingestion_exposed": False,
                    "mcp_exposed": False,
                    "arbitrary_graph_mutation": False,
                }
            )

        tool_name = _ACTION_PATHS[path]
        if request.method != "POST":
            return _error(
                "method_not_allowed", "Action operation requires POST", 405
            )

        parsed = await self._read_json(request)
        if isinstance(parsed, JSONResponse):
            return parsed

        if tool_name == "fossil.search":
            if not _has_only_keys(parsed, {"query", "limit"}):
                return _error("invalid_request", "unexpected request field", 400)
            query = parsed.get("query")
            if (
                not isinstance(query, str)
                or not query.strip()
                or len(query) > _MAX_QUERY_CHARS
            ):
                return _error(
                    "invalid_request", "query must be a bounded non-empty string", 400
                )
            arguments: dict[str, Any] = {"query": query}
            if "limit" in parsed:
                limit = parsed["limit"]
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or limit < 1
                    or limit > 100
                ):
                    return _error(
                        "invalid_request",
                        "limit must be an integer from 1 through 100",
                        400,
                    )
                arguments["limit"] = limit
        else:
            if not _has_only_keys(parsed, {"event_id"}):
                return _error("invalid_request", "unexpected request field", 400)
            event_id = _safe_identifier(parsed.get("event_id"))
            if event_id is None:
                return _error(
                    "invalid_request", "event_id must be an opaque identifier", 400
                )
            arguments = {"event_id": event_id}

        try:
            result = self.adapter.invoke(tool_name, arguments)
        except Exception as exc:
            return _map_action_error(exc)
        return JSONResponse(result)


def add_chatgpt_action_api(
    app: Starlette,
    *,
    adapter: ThinMCPAdapter,
    bearer_token: str,
    max_request_body_size: int = 64 * 1024,
    public_base_url: str | None = None,
    trusted_proxy_cidrs: tuple[str, ...] = (),
) -> Starlette:
    app.add_middleware(
        ChatGPTActionMiddleware,
        adapter=adapter,
        bearer_token=bearer_token,
        max_request_body_size=max_request_body_size,
        public_base_url=public_base_url,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )
    app.state.chatgpt_action_enabled = True
    return app


def create_chatgpt_action_app(
    node: FilesystemFossilNode,
    *,
    context: AgentContext,
    bearer_token: str,
    max_request_body_size: int = 64 * 1024,
    public_base_url: str | None = None,
    trusted_proxy_cidrs: tuple[str, ...] = (),
) -> Starlette:
    """Create the public-facing read-only GPT Action ASGI app."""

    adapter = ThinMCPAdapter(
        service=node.corpus_service,
        access=node.pack_access,
        context=context,
    )
    return add_chatgpt_action_api(
        Starlette(),
        adapter=adapter,
        bearer_token=bearer_token,
        max_request_body_size=max_request_body_size,
        public_base_url=public_base_url,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )


__all__ = [
    "ChatGPTActionMiddleware",
    "add_chatgpt_action_api",
    "chatgpt_action_openapi_schema",
    "create_chatgpt_action_app",
]
