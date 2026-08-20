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

from .node import FilesystemFossilNode


_ACTION_PATHS = {
    "/actions/search": "fossil.search",
    "/actions/read": "fossil.read",
    "/actions/lineage": "fossil.lineage",
}
_ACTION_ROUTE_ALLOWLIST = frozenset({"/openapi.json", *_ACTION_PATHS, "/actions/capabilities"})


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


def chatgpt_action_openapi_schema(*, server_url: str | None = None) -> dict[str, Any]:
    """Return the bounded read-only OpenAPI contract for a ChatGPT GPT Action."""

    error_ref = {"$ref": "#/components/schemas/ErrorEnvelope"}
    common_responses = {
        "400": _json_response(error_ref, "Invalid request"),
        "401": _json_response(error_ref, "Missing or invalid bearer token"),
        "403": _json_response(error_ref, "Pack or capability denied"),
        "404": _json_response(error_ref, "Resource not found"),
        "413": _json_response(error_ref, "Request body too large"),
        "503": _json_response(error_ref, "Canonical store unavailable"),
    }

    record_properties = {
        "event_id": {"type": "string"},
        "pack_id": {"type": "string"},
        "event_type": {"type": "string"},
        "occurred_at": {"type": "string"},
        "recorded_at": {"type": "string"},
        "subject_refs": {"type": "array", "items": {"type": "string"}},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "payload": {"type": "object", "additionalProperties": True},
    }

    schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "FOSSIL read-only ChatGPT Action API",
            "version": "1.0.0",
            "description": (
                "Read-only compatibility surface over the canonical FOSSIL corpus. "
                "Only OpenAPI discovery, search, durable-event read, lineage, and "
                "capability metadata are exposed. MCP, ingestion, proposal, validation, "
                "commit, graph mutation, and arbitrary filesystem access are prohibited."
            ),
        },
        "components": {
            "schemas": {
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
                    "properties": {
                        "error": {"$ref": "#/components/schemas/ErrorDetail"}
                    },
                },
                "FossilRecord": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": record_properties,
                },
                "LineageResponse": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["conversation_id"],
                    "properties": {
                        "conversation_id": {"type": "string"},
                        "current_conclusions": {"type": "array", "items": {"type": "object"}},
                        "historical_nodes": {"type": "array", "items": {"type": "object"}},
                        "node": {"type": ["object", "null"]},
                        "citations": {"type": "array", "items": {"type": "object"}},
                        "opposing_positions": {"type": "array", "items": {"type": "object"}},
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
                        "action_capabilities": {"type": "array", "items": {"type": "string"}},
                        "durable_writes_exposed": {"type": "boolean", "const": False},
                        "ingestion_exposed": {"type": "boolean", "const": False},
                        "mcp_exposed": {"type": "boolean", "const": False},
                        "arbitrary_graph_mutation": {"type": "boolean", "const": False},
                    },
                },
            },
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
                        "content": {"application/json": {"schema": _object_schema(
                            required=["query"],
                            properties={
                                "query": {"type": "string", "minLength": 1},
                                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                            },
                        )}},
                    },
                    "responses": {
                        "200": _json_response(
                            {"type": "array", "items": {"$ref": "#/components/schemas/FossilRecord"}},
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
                        "content": {"application/json": {"schema": _object_schema(
                            required=["event_id"],
                            properties={"event_id": {"type": "string", "minLength": 1}},
                        )}},
                    },
                    "responses": {
                        "200": _json_response({"$ref": "#/components/schemas/FossilRecord"}, "Authorized durable event"),
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
                        "content": {"application/json": {"schema": _object_schema(
                            required=["conversation_id"],
                            properties={
                                "conversation_id": {"type": "string", "minLength": 1},
                                "node_id": {"type": "string", "minLength": 1},
                            },
                        )}},
                    },
                    "responses": {
                        "200": _json_response({"$ref": "#/components/schemas/LineageResponse"}, "Authorized lineage view"),
                        **common_responses,
                    },
                }
            },
            "/actions/capabilities": {
                "get": {
                    "operationId": "fossilActionCapabilities",
                    "summary": "Describe the bounded ChatGPT Action surface",
                    "responses": {
                        "200": _json_response({"$ref": "#/components/schemas/CapabilitiesResponse"}, "Read-only Action capabilities"),
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
    """Serve only the bounded authenticated REST compatibility surface."""

    def __init__(
        self,
        app: Any,
        *,
        adapter: ThinMCPAdapter,
        bearer_token: str,
        max_request_body_size: int = 64 * 1024,
        public_base_url: str | None = None,
    ) -> None:
        super().__init__(app)
        if not bearer_token or bearer_token != bearer_token.strip():
            raise ValueError("ChatGPT Action bearer token must be a non-empty trimmed string")
        if max_request_body_size < 1:
            raise ValueError("ChatGPT Action request body limit must be positive")
        if public_base_url is not None and not public_base_url.startswith("https://"):
            raise ValueError("public ChatGPT Action base URL must use https://")
        self.adapter = adapter
        self.bearer_token = bearer_token
        self.max_request_body_size = max_request_body_size
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None

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
                    return _error("request_too_large", f"request exceeds {self.max_request_body_size} byte Action limit", 413)
            except ValueError:
                return _error("invalid_request", "invalid Content-Length header", 400)
        raw = await request.body()
        if len(raw) > self.max_request_body_size:
            return _error("request_too_large", f"request exceeds {self.max_request_body_size} byte Action limit", 413)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error("invalid_json", "request body must be valid UTF-8 JSON", 400)
        if not isinstance(payload, Mapping):
            return _error("invalid_request", "request body must be a JSON object", 400)
        return payload

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        if path == "/openapi.json":
            if request.method != "GET":
                return _error("method_not_allowed", "OpenAPI discovery requires GET", 405)
            server_url = self.public_base_url or str(request.base_url)
            return JSONResponse(chatgpt_action_openapi_schema(server_url=server_url))

        if path not in {*_ACTION_PATHS, "/actions/capabilities"}:
            return await call_next(request)

        if not self._authorized(request):
            response = _error("unauthorized", "valid bearer token required", 401)
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        if path == "/actions/capabilities":
            if request.method != "GET":
                return _error("method_not_allowed", "capabilities requires GET", 405)
            service = getattr(self.adapter, "service", None)
            return JSONResponse({
                "service_version": getattr(service, "service_version", "unknown"),
                "action_capabilities": ["search", "read", "lineage"],
                "durable_writes_exposed": False,
                "ingestion_exposed": False,
                "mcp_exposed": False,
                "arbitrary_graph_mutation": False,
            })

        tool_name = _ACTION_PATHS.get(path)
        if tool_name is None or request.method != "POST":
            return _error("method_not_allowed", "Action operation requires POST", 405)

        parsed = await self._read_json(request)
        if isinstance(parsed, JSONResponse):
            return parsed

        if tool_name == "fossil.search":
            query = parsed.get("query")
            if not isinstance(query, str) or not query.strip():
                return _error("invalid_request", "query must be a non-empty string", 400)
            arguments: dict[str, Any] = {"query": query}
            if "limit" in parsed:
                limit = parsed["limit"]
                if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 100:
                    return _error("invalid_request", "limit must be an integer from 1 through 100", 400)
                arguments["limit"] = limit
        elif tool_name == "fossil.read":
            event_id = parsed.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                return _error("invalid_request", "event_id must be a non-empty string", 400)
            arguments = {"event_id": event_id}
        else:
            conversation_id = parsed.get("conversation_id")
            if not isinstance(conversation_id, str) or not conversation_id:
                return _error("invalid_request", "conversation_id must be a non-empty string", 400)
            arguments = {"conversation_id": conversation_id}
            if parsed.get("node_id") is not None:
                node_id = parsed["node_id"]
                if not isinstance(node_id, str) or not node_id:
                    return _error("invalid_request", "node_id must be a non-empty string", 400)
                arguments["node_id"] = node_id

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
) -> Starlette:
    app.add_middleware(
        ChatGPTActionMiddleware,
        adapter=adapter,
        bearer_token=bearer_token,
        max_request_body_size=max_request_body_size,
        public_base_url=public_base_url,
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
) -> Starlette:
    adapter = ThinMCPAdapter(service=node.corpus_service, access=node.pack_access, context=context)
    return add_chatgpt_action_api(
        Starlette(),
        adapter=adapter,
        bearer_token=bearer_token,
        max_request_body_size=max_request_body_size,
        public_base_url=public_base_url,
    )


__all__ = [
    "ChatGPTActionMiddleware",
    "add_chatgpt_action_api",
    "chatgpt_action_openapi_schema",
    "create_chatgpt_action_app",
]
