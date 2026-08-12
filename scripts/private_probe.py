"""Fail-closed, non-destructive HTTP probe for private services.

The probe deliberately records only response metadata. It never prints response
bodies or credentials, and treats an empty or malformed successful response as
a failure rather than a healthy service.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


class ProbeError(RuntimeError):
    pass


def safe_url(value: str) -> str:
    """Return a display-safe URL with query and fragment removed."""
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _validate_url(value: str) -> None:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ProbeError("URL must include an http(s) scheme and host")
    if parts.username or parts.password:
        raise ProbeError("credentials in URLs are not allowed")


def probe_url(
    *,
    name: str,
    url: str,
    timeout: float = 15.0,
    required_keys: tuple[str, ...] = (),
    bearer_env: str | None = None,
) -> dict:
    _validate_url(url)
    headers = {"Accept": "application/json", "User-Agent": "fossil-private-probe/1"}
    if bearer_env:
        token = os.environ.get(bearer_env)
        if token:
            headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            raw = response.read()
    except HTTPError as exc:
        raise ProbeError(f"{name}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise ProbeError(f"{name}: network failure ({exc.reason})") from exc
    except TimeoutError as exc:
        raise ProbeError(f"{name}: timeout") from exc

    if not 200 <= status < 300:
        raise ProbeError(f"{name}: HTTP {status}")
    if not raw.strip():
        raise ProbeError(f"{name}: 2xx response had an empty body")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"{name}: 2xx response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ProbeError(f"{name}: JSON response was not an object")
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ProbeError(f"{name}: JSON response missing required keys: {', '.join(missing)}")

    return {
        "name": name,
        "url": safe_url(url),
        "status_code": status,
        "json_object": True,
        "json_keys": sorted(str(key) for key in payload),
        "ok": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--require-json-key", action="append", default=[])
    parser.add_argument("--bearer-env")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = probe_url(
            name=args.name,
            url=args.url,
            timeout=args.timeout,
            required_keys=tuple(args.require_json_key),
            bearer_env=args.bearer_env,
        )
    except ProbeError as exc:
        report = {
            "name": args.name,
            "url": safe_url(args.url),
            "ok": False,
            "failure": str(exc),
        }

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="", file=sys.stdout if report["ok"] else sys.stderr)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
