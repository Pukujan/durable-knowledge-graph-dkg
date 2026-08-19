from __future__ import annotations

import importlib.util
from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "reviewed_ingest_fixture_module",
    ROOT / "tests" / "test_reviewed_evidence_ingest.py",
)
assert SPEC is not None and SPEC.loader is not None
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


@settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    source_kind=st.sampled_from(
        [
            "RAW_CI_LOG",
            " raw_ci_log ",
            "Raw_Build_Log",
            " raw_runtime_log ",
        ]
    )
)
def test_raw_log_policy_cannot_be_bypassed_by_case_or_whitespace(
    tmp_path: Path,
    source_kind: str,
):
    service = FIXTURE._service(tmp_path)
    receipt = service.ingest(
        pack_manifest=FIXTURE._manifest(),
        source=FIXTURE._source(source_kind=source_kind),
        claims=[FIXTURE._draft()],
        review_ref="review:noise-normalization",
        actor={"actor_type": "importer", "actor_id": "noise-filter"},
        occurred_at="2026-08-19T19:46:00Z",
        recorded_at="2026-08-19T19:46:01Z",
        correlation_id=f"noise:{source_kind.strip().lower()}",
    )

    assert receipt["status"] == "rejected"
    assert receipt["source"]["preserved"] is False
    assert list(service.source_store.iter_snapshots()) == []
    assert list(service.event_store.iter_events()) == []


def test_reviewed_ingest_retry_is_idempotent_for_source_proposals_and_receipt(tmp_path: Path):
    service = FIXTURE._service(tmp_path)
    kwargs = {
        "pack_manifest": FIXTURE._manifest(),
        "source": FIXTURE._source(),
        "claims": [FIXTURE._draft()],
        "review_ref": "review:idempotent-retry",
        "actor": {"actor_type": "importer", "actor_id": "reviewed-evidence-ingest"},
        "occurred_at": "2026-08-19T19:47:00Z",
        "recorded_at": "2026-08-19T19:47:01Z",
        "correlation_id": "reviewed-ingest-idempotent",
    }

    first = service.ingest(**kwargs)
    second = service.ingest(**kwargs)

    assert first == second
    assert len(list(service.source_store.iter_snapshots())) == 1
    assert len(list(service.event_store.iter_events())) == 1
