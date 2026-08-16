from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/object-store-live.yml"
SCRIPT = ROOT / "scripts/live_object_store_proof.py"
REBUILD_SCRIPT = ROOT / "scripts/live_object_store_rebuild_proof.py"


def test_object_store_live_workflow_is_manual_exact_head_and_credential_scoped() -> None:
    assert WORKFLOW.exists(), "OBJECT_STORE_LIVE workflow is required"
    workflow = WORKFLOW.read_text(encoding="utf-8")

    required = [
        "workflow_dispatch:",
        "environment: r2-proof",
        "ref: ${{ inputs.ref }}",
        "git rev-parse HEAD",
        "vars.R2_ENDPOINT",
        "vars.FOSSIL_R2_ENDPOINT",
        "vars.R2_BUCKET",
        "vars.FOSSIL_R2_BUCKET",
        "secrets.R2_ACCESS_KEY_ID",
        "secrets.FOSSIL_R2_ACCESS_KEY_ID",
        "secrets.R2_SECRET_ACCESS_KEY",
        "secrets.FOSSIL_R2_SECRET_ACCESS_KEY",
        "AWS_EC2_METADATA_DISABLED: \"true\"",
        "fossil-live-proof/${{ github.run_id }}/${{ github.run_attempt }}",
        "python scripts/live_object_store_proof.py write",
        "python scripts/live_object_store_rebuild_proof.py",
        'FOSSIL_PROOF_RECEIPT_PATH=$RUNNER_TEMP/writer-receipt.json',
        'FOSSIL_PROOF_RECEIPT_PATH=$RUNNER_TEMP/rebuild-receipt.json',
    ]
    for needle in required:
        assert needle in workflow, f"missing live object-store safety contract: {needle}"

    assert "environment: object-store-live" not in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    # The runner context is not valid in jobs.<job_id>.env. Resolve temporary
    # paths only after the hosted runner has started.
    assert "FOSSIL_PROOF_RECEIPT_PATH: ${{ runner.temp }}" not in workflow


def test_writer_hands_runner_b_only_prefix_and_deterministic_fixture_identity() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    writer_block, rebuild_block = workflow.split("\n  rebuild:\n", 1)

    for needle in [
        "outputs:",
        "proof_prefix: ${{ steps.proof_outputs.outputs.proof_prefix }}",
        "fixture_identity: ${{ steps.proof_outputs.outputs.fixture_identity }}",
        "id: proof_outputs",
        "printf 'proof_prefix=%s\\n' \"$FOSSIL_PROOF_PREFIX\" >> \"$GITHUB_OUTPUT\"",
        "printf 'fixture_identity=%s\\n' \"$fixture_identity\" >> \"$GITHUB_OUTPUT\"",
    ]:
        assert needle in writer_block, f"missing writer handoff contract: {needle}"

    assert "FOSSIL_PROOF_PREFIX: ${{ needs.writer.outputs.proof_prefix }}" in rebuild_block
    assert "FOSSIL_FIXTURE_IDENTITY: ${{ needs.writer.outputs.fixture_identity }}" in rebuild_block
    assert "FOSSIL_PROOF_PREFIX: fossil-live-proof/${{ github.run_id }}/${{ github.run_attempt }}" not in rebuild_block


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
        "list_objects_v2",
        "Prefix=f\"{prefix.strip('/')}/\"",
    ]:
        assert needle in source, f"missing live proof semantic: {needle}"

    # Object-scoped R2 credentials may list objects in the proof bucket but
    # reject the bucket-level HeadBucket probe.  Keep preflight scoped to the
    # unique run prefix and never regress to that broader bucket operation.
    assert "head_bucket" not in source

    # Provider-specific secret names belong at the workflow boundary, not in the
    # provider-neutral proof implementation or receipts.
    assert "R2_SECRET_ACCESS_KEY" not in source
    assert "R2_ACCESS_KEY_ID" not in source


def test_fresh_runner_reopens_artifact_and_proves_redaction_non_resurrection() -> None:
    assert REBUILD_SCRIPT.exists(), "fresh-runner artifact verification wrapper is required"
    source = REBUILD_SCRIPT.read_text(encoding="utf-8")

    for needle in [
        "S3ArtifactStore",
        "artifacts.get_manifest(artifact_id)",
        "artifacts.read_bytes(artifact_id)",
        "artifacts.verify(artifact_id)",
        "artifacts.is_redacted(redacted_artifact_id)",
        "artifacts.get_redaction(redacted_artifact_id)",
        "artifacts.backend.exists(artifacts._blob_key(redacted_digest))",
        "ArtifactRedactedError",
        "base._rebuild_once()",
        '"artifact_exact_bytes_hash_identity": "PASS"',
        '"artifact_rebuild_verification": "PASS"',
        '"redaction_non_resurrection": "PASS"',
    ]:
        assert needle in source, f"missing fresh-runner acceptance proof: {needle}"

    assert source.count("base._rebuild_once()") == 2
    assert "R2_SECRET_ACCESS_KEY" not in source
    assert "R2_ACCESS_KEY_ID" not in source
