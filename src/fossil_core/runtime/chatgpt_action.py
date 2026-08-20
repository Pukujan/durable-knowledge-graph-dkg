from __future__ import annotations

import hmac
import json
from collections.abc import Mapping
from typing import Any

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fossil_core.adapters.mcp import ThinMCPAdapter
from fossil_core.agent import AgentContext, AgentProvenanceError
from fossil_core.domain.pack import PackBoundaryError
from fossil_core.ports.capability import CapabilityError

from .network import create_node_network_app
from .node import FilesystemFossilNode


_ACTION_PATHS = {
    "/actions/search": "fossil.search",
    "/actions/read": "fossil.read",
    "/actions/lineage": "fossil.lineage",
}


def _error(code: str, detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "detail": detail}}, status_code=status_code
    )


def _map_action_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, PackBoundaryError):
        return _error("unauthorized_pack", str(exc), 403)
    if isinstance(exc, (CapabilityError, AgentProvenanceError)):
        return _error("capability_denied", str(exc), 403)
    if isinstance(exc, FileNotFoundError):
        return _error("not_found", str(exc), 404)
    if isinstance(exc, KeyError):
        detail = str(exc.args[0]) if exc.args else "resource not found"
        return _error("not_found", detail, 404)
    if isinstance(exc, (TypeError, ValueError)):
        return _error("invalid_request", str(exc), 400)
    if isinstance(exc, OSError):
        return _error("canonical_store_unavailable", str(exc), 503)
    return _error("internal_error", "FOSSIL Action execution failed", 500)


def _object_schema(*, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def chatgpt_action_openapi_schema(*, server_url: str | None = None) -> dict[str, Any]:
    """Return the read-only OpenAPI contract intended for a ChatGPT GPT Action."""

    error_schema = {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "detail"],
                "properties": {
                    "code": {"type": "string"},
                    "detail": {"type": "string"},
                },
            }
        },
    }
    common_responses = {
        "400": {"description": "Invalid request", "content": {"application/json": {"schema": error_schema}}},
        "401": {"description": "Missing or invalid bearer token", "content": {"application/json": {"schema": error_schema}}},
        "403": {"description": "Pack or capability denied", "content": {"application/json": {"schema": error_schema}}},
        "404": {"description": "Resource not found", "content": {"application/json": {"schema": error_schema}}},
        "503": {"description": "Canonical store unavailable", "content": {"application/json": {"schema": error_schema}}},
    }

    schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "FOSSIL read-only ChatGPT Action API",
            "version": "1.0.0",
            "description": (
                "Read-only compatibility surface over the canonical FOSSIL corpus. "
                "It exposes search, durable-event read, lineage, and adapter capability metadata; "
                "durable proposal/validation/commit are intentionally not exposed."
            ),
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "opaque",
                }
            }
        },
        "security": [{"BearerAuth": []}],
        "paths": {
            "/actions/search": {
                "post": {
                    "operationId": "fossilSearch",
                    "summary": "Search readable FOSSIL knowledge",
                    "description": "Search only the packs mounted as readable for the configured node context.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": _object_schema(
                                    required=["query"],
                                    properties={
                                        "query": {"type": "string", "minLength": 1},
                                        "limit": {
                                            "type": "integer",
                                            "minimum": 1,
                                            "maximum": 100,
                                            "default": 20,
                                        },
                                    },
                                )
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Authorized search results",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object", "additionalProperties": True},
                                    }
                                }
                            },
                        },
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
                            "application/json": {
                                "schema": _object_schema(
                                    required=["event_id"],
                                    properties={"event_id": {"type": "string", "minLength": 1}},
                                )
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Authorized durable event",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "additionalProperties": True}
                                }
                            },
                        },
                        **common_responses,
                    },
                }
            },
            "/actions/lineage": {
                "post": {
                    "operationId": "fossilLineage",
                    "summary": "Read conversation intellectual lineage",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": _object_schema(
                                    required=["conversation_id"],
                                    properties={
                                        "conversation_id": {"type": "string", "minLength": 1},
                                        "node_id": {"type": "string", "minLength": 1},
                                    },
                                )
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Authorized lineage view",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "additionalProperties": True}
                                }
                            },
                        },
                        **common_responses,
                    },
                }
            },
            "/actions/capabilities": {
                "get": {
                    "operationId": "fossilActionCapabilities",
                    "summary": "Describe the bounded ChatGPT Action surface",
                    "responses": {
                        "200": {
                            "description": "Read-only Action capabilities",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "additionalProperties": True}
                                }
                            },
                        },
                        "401": common_responses["401"],
                    },
                }
            },
        },
    }
    if server_url:
        schema["servers"] = [{"url": server_url.rstrip("/")}]
    return schema


class ChatGPTActionMiddleware(BaseHTTPMiddleware):
    """Intercept a small authenticated REST surface before the node's MCP mount."""

    def __init__(
        self,
        app: Any,
        *,
        adapter: ThinMCPAdapter,
        bearer_token: str,
        max_request_body_size: int = 64 * 1024,
    ) -> None:
        super().__init__(app)
        if not bearer_token or bearer_token != bearer_token.strip():
            raise ValueError("ChatGPT Action bearer token must be a non-empty trimmed string")
        if max_request_body_size < 1:
            raise ValueError("ChatGPT Action request body limit must be positive")
        self.adapter = adapter
        self.bearer_token = bearer_token
        self.max_request_body_size = max_request_body_size

    def _authorized(self, request: Request) -> bool:
        value = request.headers.get("authorization", "")
        scheme, separator, supplied = value.partition(" ")
        if not separator or scheme.lower() != "bearer" or not supplied:
            return False
        return hmac.compare_digest(supplied, self.bearer_token)

    async def _read_json(self, request: Request) -> Mapping[str, Any] | JSONResponse:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_request_body_size:
                    return _error(
                        "request_too_large",
                        f"request exceeds {self.max_request_body_size} byte Action limit",
                        413,
                    )
            except ValueError:
                return _error("invalid_request", "invalid Content-Length header", 400)

        raw = await request.body()
        if len(raw) > self.max_request_body_size:
            return _error(
                "request_too_large",
                f"request exceeds {self.max_request_body_size} byte Action limit",
                413,
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error("invalid_json", "request body must be valid UTF-8 JSON", 400)
        if not isinstance(payload, Mapping):
            return _error("invalid_request", "request body must be a JSON object", 400)
        return payload

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        if path == "/openapi.json" and request.method == "GET":
            return JSONResponse(
                chatgpt_action_openapi_schema(server_url=str(request.base_url))
            )

        if path not in {*_ACTION_PATHS, "/actions/capabilities"}:
            return await call_next(request)

        if not self._authorized(request):
            response = _error("unauthorized", "valid bearer token required", 401)
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        if path == "/actions/capabilities" and request.method == "GET":
            service = getattr(self.adapter, "service", None)
            return JSONResponse(
                {
                    "service_version": getattr(service, "service_version", "unknown"),
                    "action_capabilities": ["search", "read", "lineage"],
                    "durable_writes_exposed": False,
                    "arbitrary_graph_mutation": False,
                }
            )

        tool_name = _ACTION_PATHS.get(path)
        if tool_name is None or request.method != "POST":
            return _error("method_not_allowed", "unsupported Action method", 405)

        parsed = await self._read_json(request)
        if isinstance(parsed, JSONResponse):
            return parsed

        arguments = dict(parsed)
        if tool_name == "fossil.search":
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                return _error("invalid_request", "query must be a non-empty string", 400)
            arguments["query"] = query
            if "limit" in arguments:
                try:
                    arguments["limit"] = int(arguments["limit"])
                except (TypeError, ValueError):
                    return _error("invalid_request", "limit must be an integer", 400)
        elif tool_name == "fossil.read":
            event_id = arguments.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                return _error("invalid_request", "event_id must be a non-empty string", 400)
            arguments = {"event_id": event_id}
        elif tool_name == "fossil.lineage":
            conversation_id = arguments.get("conversation_id")
            if not isinstance(conversation_id, str) or not conversation_id:
                return _error(
                    "invalid_request", "conversation_id must be a non-empty string", 400
                )
            clean_arguments: dict[str, Any] = {"conversation_id": conversation_id}
            if arguments.get("node_id") is not None:
                node_id = arguments["node_id"]
                if not isinstance(node_id, str) or not node_id:
                    return _error("invalid_request", "node_id must be a non-empty string", 400)
                clean_arguments["node_id"] = node_id
            arguments = clean_arguments

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
) -> Starlette:
    """Attach the read-only GPT Action compatibility surface to a Starlette node app."""

    app.add_middleware(
        ChatGPTActionMiddleware,
        adapter=adapter,
        bearer_token=bearer_token,
        max_request_body_size=max_request_body_size,
    )
    app.state.chatgpt_action_enabled = True
    return app


def create_chatgpt_action_network_app(
    node: FilesystemFossilNode,
    *,
    context: AgentContext,
    bearer_token: str,
    max_action_request_body_size: int = 64 * 1024,
    **network_kwargs: Any,
) -> Starlette:
    """Compose the existing FOSSIL node network app plus read-only GPT Actions.

    The same ``ThinMCPAdapter``/``CorpusService`` boundary is used by MCP and the
    Action surface. The Action API deliberately exposes no proposal, validation,
    commit, ingestion, or arbitrary graph mutation operation.
    """

    app = create_node_network_app(node, context=context, **network_kwargs)
    adapter = ThinMCPAdapter(
        service=node.corpus_service,
        access=node.pack_access,
        context=context,
    )
    return add_chatgpt_action_api(
        app,
        adapter=adapter,
        bearer_token=bearer_token,
        max_request_body_size=max_action_request_body_size,
    )


__all__ = [
    "ChatGPTActionMiddleware",
    "add_chatgpt_action_api",
    "chatgpt_action_openapi_schema",
    "create_chatgpt_action_network_app",
]
