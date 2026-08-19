from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st

from fossil_core.temporal_benchmark import run_longitudinal_epistemic_benchmark


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "longitudinal_fixture_module",
    ROOT / "tests" / "test_longitudinal_epistemic_benchmark.py",
)
assert SPEC is not None and SPEC.loader is not None
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


@settings(
    max_examples=12,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(later_relation_count=st.integers(min_value=0, max_value=24))
def test_historical_answer_survives_generated_later_relation_and_ontology_noise(
    tmp_path: Path,
    monkeypatch,
    later_relation_count: int,
):
    events = FIXTURE._evolution_events()
    for offset in range(later_relation_count):
        index = 12 + offset
        relation_id = f"rel_generated_later_{offset:06d}"
        events.append(
            FIXTURE._event(
                index,
                "relation.proposed",
                [relation_id, FIXTURE.REPLACEMENT, FIXTURE.DEPENDENT],
                {
                    "relation_id": relation_id,
                    "relation_type": "RELATED_TO",
                    "source_ref": FIXTURE.REPLACEMENT,
                    "source_type": "Claim",
                    "target_ref": FIXTURE.DEPENDENT,
                    "target_type": "Claim",
                    "ontology_ref": f"dkg.core@{2 + (offset % 3)}.0.0",
                    "state": "active",
                },
            )
        )

    root = tmp_path / f"generated-{later_relation_count}"
    if root.exists():
        shutil.rmtree(root)
    FIXTURE._write_fixture(root, events)
    monkeypatch.setattr(
        "fossil_core.application.rebuild.pack_corpus.validate_pack_fixtures",
        lambda *args, **kwargs: None,
    )

    report = run_longitudinal_epistemic_benchmark(
        [root],
        schemas_root=tmp_path / "schemas",
        phases=FIXTURE._phases(events[:12]),
        benchmark_id="generated-longitudinal-stability-v1",
    )

    assert report["passed"] is True
    assert all(phase["rebuild_equivalent"] for phase in report["phases"])
    assert report["historical_answer_stability"]["historical-sqlite"] == {
        "observations": 3,
        "all_full_recall": True,
        "no_current_state_leakage": True,
    }
    assert report["phases"][-1]["beliefs"][FIXTURE.ASSUMPTION]["state"] == "superseded"
