"""Send and verify one non-sensitive OpenTelemetry span in Langfuse."""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def _safe_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _basic_auth(public_key: str, secret_key: str) -> str:
    raw = f"{public_key}:{secret_key}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _verify(url: str, auth: str, trace_id: str) -> bool:
    query = urlencode({"traceId": trace_id})
    request = Request(
        f"{url}?{query}",
        headers={"Accept": "application/json", "Authorization": auth},
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        if not 200 <= int(response.status) < 300:
            return False
        payload = json.loads(response.read())
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return any(
                isinstance(item, dict)
                and (item.get("traceId") == trace_id or item.get("trace_id") == trace_id)
                for item in data
            )
        return bool(payload.get("traceId") == trace_id or payload.get("trace_id") == trace_id)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--otel-path", default="/api/public/otel")
    parser.add_argument("--observations-path", default="/api/public/observations")
    parser.add_argument("--public-key-env", default="LANGFUSE_PUBLIC_KEY")
    parser.add_argument("--secret-key-env", default="LANGFUSE_SECRET_KEY")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    public_key = os.environ.get(args.public_key_env, "")
    secret_key = os.environ.get(args.secret_key_env, "")
    if not public_key or not secret_key:
        raise SystemExit("Langfuse public/secret credentials are required")

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    base_url = args.base_url.rstrip("/") + "/"
    otel_url = urljoin(base_url, args.otel_path.lstrip("/"))
    auth = _basic_auth(public_key, secret_key)
    exporter = OTLPSpanExporter(
        endpoint=otel_url,
        headers={"Authorization": auth, "x-langfuse-ingestion-version": "4"},
    )
    provider = TracerProvider(
        resource=Resource.create({"service.name": "fossil-github-control-plane"})
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("fossil.github.control_plane", "1")
    with tracer.start_as_current_span("fossil-control-plane.synthetic") as span:
        span.set_attribute("fossil.synthetic", True)
        span.set_attribute("fossil.source", "github-actions")
        span.set_attribute("fossil.payload", "non-sensitive-health-check")
        trace_id = f"{span.get_span_context().trace_id:032x}"
    provider.force_flush()
    provider.shutdown()

    verify_url = urljoin(base_url, args.observations_path.lstrip("/"))
    verified = False
    for _ in range(12):
        try:
            if _verify(verify_url, auth, trace_id):
                verified = True
                break
        except Exception:
            pass
        time.sleep(5)
    report = {
        "ok": verified,
        "trace_id": trace_id,
        "ingest_endpoint": _safe_url(otel_url),
        "verification_endpoint": _safe_url(verify_url),
        "synthetic_payload": "non-sensitive-health-check",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
