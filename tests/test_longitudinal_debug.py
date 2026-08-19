from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from fossil_core.temporal_benchmark import run_longitudinal_epistemic_benchmark


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "longitudinal_fixture_module",
    ROOT / "tests" / "test_longitudinal_epistemic_benchmark.py",
)
assert SPEC is not None and SPEC.loader is not None
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


def test_diagnostic_longitudinal_report(tmp_path: Path, monkeypatch):
    events = FIXTURE._evolution_events()
    root = FIXTURE._write_fixture(tmp_path / "pack", events)
    monkeypatch.setattr(
        "fossil_core.application.rebuild.pack_corpus.validate_pack_fixtures",
        lambda *args, **kwargs: None,
    )
    report = run_longitudinal_epistemic_benchmark(
        [root],
        schemas_root=tmp_path / "schemas",
        phases=FIXTURE._phases(events),
        benchmark_id="diagnostic",
    )
    assert report["passed"], json.dumps(report, indent=2, sort_keys=True)
