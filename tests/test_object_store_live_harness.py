from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/object-store-live.yml"
SCRIPT = ROOT / "scripts/live_object_store_proof.py"


def test_object_store_live_workflow_is_manual_exact_head_and_credential_scoped() -> None:
    assert WORKFLOW.exists(), "OBJECT_STORE_LIVE workflow is required"
    workflow = WORKFLOW.read_text(encoding="utf-8")

    required = [
        "workflow_dispatch:",
        "environment: object-store-live",
        "ref: ${{ inputs.ref }}",
        "git rev-parse HEAD",
        "vars.R2_ENDPOINT",
        "vars.R2_BUCKET",
        "secrets.R2_ACCESS_KEY_ID",
        "secrets.R2_SECRET_ACCESS_KEY",
        "AWS_EC2_METADATA_DISABLED: \"true\"",
        "fossil-live-proof/${{ github.run_id }}/${{ github.run_attempt }}",
        "python scripts/live_object_store_proof.py write",
        "python scripts/live_object_store_proof.py rebuild",
    ]
    for needle in required:
        assert needle in workflow, f"missing live object-store safety contract: {needle}"

    assert "pull_request:" not in workflow
    assert "push:" not in workflow


def test_object_store_live_script_is_provider_neutral_and_fail_closed() -> None:
    assert SCRIPT.exists(), "OBJECT_STORE_LIVE proof script is required"
    source = SCRIPT.read_text(encoding="utf-8")

    for needle in [
        "S3ArtifactStore",
        "S3DurableEventStore",
        "SemanticSnapshot",
        "RemoteStoreUnavailable",
        "ArtifactRedactedError",
        "IdempotencyConflict",
        "OBJECT_STORE_ENDPOINT",
        "OBJECT_STORE_BUCKET",
        "FOSSIL_PROOF_PREFIX",
        "writer-receipt.json",
        "rebuild-receipt.json",
    ]:
        assert needle in source, f"missing live proof semantic: {needle}"

    # Provider-specific secret names belong at the workflow boundary, not in the
    # provider-neutral proof implementation or receipts.
    assert "R2_SECRET_ACCESS_KEY" not in source
    assert "R2_ACCESS_KEY_ID" not in source
