from __future__ import annotations

from fossil_core.application.query.security import _canonical_citation


def test_canonical_citation_deeply_detaches_nested_hash_data() -> None:
    original = {
        "schema_version": "fossil.citation.v1",
        "citation_id": "cite_defensive_copy_0001",
        "snapshot_id": "snap_defensive_copy_0001",
        "artifact_id": "art_defensive_copy_0001",
        "byte_start": 0,
        "byte_end": 4,
        "passage_hash": {"algorithm": "sha256", "digest": "b" * 64},
        "ignored_extra": {"nested": [1]},
    }

    canonical = _canonical_citation(original)

    assert canonical is not None
    assert set(canonical) == {
        "schema_version",
        "citation_id",
        "snapshot_id",
        "artifact_id",
        "byte_start",
        "byte_end",
        "passage_hash",
    }
    assert canonical["passage_hash"] == original["passage_hash"]
    canonical["passage_hash"]["digest"] = "0" * 64
    assert original["passage_hash"]["digest"] == "b" * 64
