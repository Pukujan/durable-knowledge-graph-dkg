from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PROTOCOL_VERSION = "2026-07-28"
TOKEN_ENV = "FOSSIL_MCP_BEARER_TOKEN"
EXPECTED_TOOLS = (
    "fossil.search",
    "fossil.read",
    "fossil.lineage",
    "fossil.propose",
    "fossil.validate",
    "fossil.commit",
    "fossil.manage",
)


def _request(
    url: str,
    *,
    token: str | None = None,
    method: str = "tools/list",
    name: str | None = None,
    timeout: float = 10.0,
) -> tuple[int, bytes, dict[str, str]]:
    params: dict[str, Any] = {
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientInfo": {
                "name": "fossil-public-edge-verifier",
                "version": "1",
            },
            "io.modelcontextprotocol/clientCapabilities": {},
        }
    }
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if name is not None:
        headers["Mcp-Name"] = name
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())


def _probe_private_route(url: str, timeout: float) -> int:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _fail(message: str) -> int:
    print(json.dumps({"status": "FAIL", "reason": message}, sort_keys=True))
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the externally reachable generic FOSSIL MCP edge without printing secrets."
    )
    parser.add_argument(
        "--url",
        default="https://fossil.design-bakery.com/mcp",
        help="Public MCP URL; must use HTTPS.",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    parsed = urllib.parse.urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path != "/mcp":
        return _fail("expected an HTTPS URL with path /mcp")

    token = os.environ.get(TOKEN_ENV)
    if not token:
        return _fail(f"{TOKEN_ENV} is not set")
    if any(character.isspace() for character in token):
        return _fail(f"{TOKEN_ENV} contains whitespace")

    unauth_status, unauth_body, unauth_headers = _request(
        args.url,
        timeout=args.timeout,
    )
    if unauth_status != 401:
        return _fail(f"missing-token request returned HTTP {unauth_status}, expected 401")
    if unauth_headers.get("WWW-Authenticate", "").lower() != "bearer":
        return _fail("missing-token response did not advertise Bearer authentication")
    if token.encode() in unauth_body:
        return _fail("token appeared in an unauthenticated response body")

    wrong_status, wrong_body, _ = _request(
        args.url,
        token="fossil-public-edge-deliberately-wrong-token",
        timeout=args.timeout,
    )
    if wrong_status != 401:
        return _fail(f"wrong-token request returned HTTP {wrong_status}, expected 401")
    if token.encode() in wrong_body:
        return _fail("token appeared in a wrong-token response body")

    valid_status, valid_body, _ = _request(
        args.url,
        token=token,
        timeout=args.timeout,
    )
    if valid_status != 200:
        return _fail(f"valid-token tools/list returned HTTP {valid_status}, expected 200")
    if token.encode() in valid_body:
        return _fail("token appeared in a valid response body")
    try:
        payload = json.loads(valid_body)
        tool_names = tuple(tool["name"] for tool in payload["result"]["tools"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return _fail(f"tools/list response was not the expected MCP JSON shape: {type(exc).__name__}")
    if tool_names != EXPECTED_TOOLS:
        return _fail(f"unexpected MCP tool surface: {tool_names!r}")

    public_root = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    exposed: dict[str, int] = {}
    for path in ("/healthz", "/readyz", "/ingest", "/openapi.json", "/admin"):
        status = _probe_private_route(public_root + path, args.timeout)
        if status not in (403, 404):
            exposed[path] = status
    if exposed:
        return _fail(f"non-MCP routes are publicly reachable: {exposed}")

    receipt = {
        "status": "PASS",
        "endpoint": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        "protocol_version": PROTOCOL_VERSION,
        "missing_token_http": unauth_status,
        "wrong_token_http": wrong_status,
        "valid_token_http": valid_status,
        "tools": list(tool_names),
        "public_non_mcp_routes": "blocked",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
