"""Probe a model gateway and reject transport-level false successes."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


class InferenceProbeError(RuntimeError):
    pass


def safe_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _extract_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"].strip()
            if isinstance(first.get("text"), str):
                return first["text"].strip()
            if first.get("tool_calls"):
                return "[tool_call]"
    output = payload.get("output")
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict):
                for content in item.get("content", []):
                    if isinstance(content, dict) and isinstance(content.get("text"), str):
                        return content["text"].strip()
    return ""


def probe(
    *,
    name: str,
    base_url: str,
    path: str,
    model: str,
    api_key_env: str | None,
    timeout: float,
) -> dict:
    if not model.strip():
        raise InferenceProbeError(f"{name}: requested model is empty")
    endpoint = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    parts = urlsplit(endpoint)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise InferenceProbeError(f"{name}: invalid gateway URL")
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key_env and os.environ.get(api_key_env):
        headers["Authorization"] = f"Bearer {os.environ[api_key_env]}"
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with the word ok."}],
            "max_tokens": 16,
            "stream": False,
        }
    ).encode("utf-8")
    request = Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            raw = response.read()
    except HTTPError as exc:
        raise InferenceProbeError(f"{name}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise InferenceProbeError(f"{name}: network failure ({exc.reason})") from exc
    except TimeoutError as exc:
        raise InferenceProbeError(f"{name}: timeout") from exc
    if not 200 <= status < 300:
        raise InferenceProbeError(f"{name}: HTTP {status}")
    if not raw.strip():
        raise InferenceProbeError(f"{name}: 2xx response had an empty body")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InferenceProbeError(f"{name}: 2xx response was not valid JSON") from exc
    text = _extract_text(payload)
    if not text:
        raise InferenceProbeError(f"{name}: 2xx response had zero usable output")
    actual_model = payload.get("model") if isinstance(payload, dict) else None
    return {
        "name": name,
        "endpoint": safe_url(endpoint),
        "requested_model": model,
        "actual_model": actual_model if isinstance(actual_model, str) else None,
        "status_code": status,
        "usable_output": True,
        "output_length": len(text),
        "ok": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", default="/v1/chat/completions")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = probe(
            name=args.name,
            base_url=args.base_url,
            path=args.path,
            model=args.model,
            api_key_env=args.api_key_env,
            timeout=args.timeout,
        )
    except InferenceProbeError as exc:
        report = {"name": args.name, "ok": False, "failure": str(exc)}
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="", file=sys.stdout if report["ok"] else sys.stderr)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
