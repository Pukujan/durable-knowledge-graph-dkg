from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from private_probe import ProbeError, probe_url, safe_url  # noqa: E402
from probe_inference import _extract_text  # noqa: E402


def test_control_plane_contract_is_github_hosted_and_scoped():
    contract = json.loads(
        (ROOT / "config/integrations/github-control-plane.json").read_text(encoding="utf-8")
    )
    assert contract["control_plane"] == "github-hosted-actions"
    assert contract["runner"] == "github-hosted-ubuntu-latest"
    assert contract["private_network"] == "tailscale"
    assert contract["runner_identity"]["mode"] == "ephemeral-workload-identity"
    assert contract["routine_health_checks_mutate_knowledge_graph"] is False
    assert "ssc-runtime" in contract["forbidden_dependencies"]
    assert "kubernetes" in contract["forbidden_dependencies"]


@pytest.mark.parametrize(
    "workflow",
    [
        "fossil-private-health.yml",
        "gravebuster-private-health.yml",
    ],
)
def test_private_health_workflows_use_ephemeral_oidc_tailnet_access(workflow: str):
    text = (ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" in text
    assert "tailscale/github-action@v4" in text
    assert "oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}" in text
    assert "audience: ${{ secrets.TS_AUDIENCE }}" in text
    assert "tags: tag:ci" in text
    assert "id-token: write" in text
    assert "self-hosted" not in text
    assert "tailscale up" not in text
    assert "authkey:" not in text


def test_probe_scripts_fail_closed_and_never_echo_response_body():
    fossil = (ROOT / "scripts/probe-fossil.sh").read_text(encoding="utf-8")
    gravebuster = (ROOT / "scripts/probe-gravebuster.sh").read_text(encoding="utf-8")
    for script in (fossil, gravebuster):
        assert "set -euo pipefail" in script
        assert "private_probe.py" in script
        assert "--require-json-key" in script
    probe = (ROOT / "scripts/private_probe.py").read_text(encoding="utf-8")
    assert "response.read()" in probe
    assert "print(rendered" in probe
    assert "raw" not in probe.split("print(rendered", 1)[1]


class _Handler(BaseHTTPRequestHandler):
    body = b"{}"
    status = 200

    def do_GET(self):  # noqa: N802
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        return


def _server(body: bytes, status: int = 200):
    handler = type("Handler", (_Handler,), {"body": body, "status": status})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_private_probe_accepts_required_json_and_redacts_url():
    server, thread = _server(b'{"status":"ok"}')
    try:
        url = f"http://127.0.0.1:{server.server_port}/health?token=secret#fragment"
        result = probe_url(name="fixture", url=url, required_keys=("status",))
        assert result["ok"] is True
        assert result["url"].endswith("/health")
        assert "secret" not in result["url"]
    finally:
        server.shutdown()
        thread.join(timeout=2)


@pytest.mark.parametrize("body", [b"", b"not-json", b"[]"])
def test_private_probe_rejects_empty_malformed_or_non_object_success(body: bytes):
    server, thread = _server(body)
    try:
        with pytest.raises(ProbeError):
            probe_url(name="fixture", url=f"http://127.0.0.1:{server.server_port}/health")
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_inference_probe_rejects_zero_payload_shapes():
    assert _extract_text({"choices": [{"message": {"content": "ok"}}]}) == "ok"
    assert _extract_text({"choices": [{"message": {"content": ""}}]}) == ""
    assert _extract_text({"choices": [{"text": "ok"}]}) == "ok"
    assert _extract_text({"choices": [{"tool_calls": [{"id": "tool"}]}]}) == "[tool_call]"
    assert _extract_text({"choices": []}) == ""
    assert _extract_text({}) == ""


def test_workflows_do_not_put_private_credentials_in_urls_or_logs():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "?token=" not in text
        assert "Authorization: Bearer" not in text


def test_synthetic_trace_workflow_uses_tailnet_and_sanitized_evidence():
    text = (ROOT / ".github/workflows/langfuse-synthetic-trace.yml").read_text(
        encoding="utf-8"
    )
    assert "tailscale/github-action@v4" in text
    assert "opentelemetry-exporter-otlp-proto-http" in text
    assert "emit_langfuse_trace.py" in text
    assert "id-token: write" in text
    assert "self-hosted" not in text


def test_langfuse_trace_report_contains_no_payload_or_credentials():
    text = (ROOT / "scripts/emit_langfuse_trace.py").read_text(encoding="utf-8")
    assert "non-sensitive-health-check" in text
    assert "response.read()" in text
    assert "secret_key" not in text.split("print(json.dumps(report", 1)[-1]
