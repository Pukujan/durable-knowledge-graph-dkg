from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from fossil_core.artifact_store import ArtifactStore
from fossil_core.source import SourceSnapshotStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCHEMA = ROOT / "schemas" / "source-snapshot" / "v1.schema.json"
CITATION_SCHEMA = ROOT / "schemas" / "citation" / "v1.schema.json"
LOCATOR_KEYS = ("url", "identifier", "repository_ref")
SOURCE_ROLES_WITHOUT_DERIVATION = ("primary", "secondary", "local")
DERIVED_SOURCE_ROLES = ("derived", "reconstructed")


NONBLANK_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=64,
).filter(lambda value: bool(value.strip()))


def source_store(tmp_path: Path) -> SourceSnapshotStore:
    return SourceSnapshotStore(
        tmp_path / "sources",
        ArtifactStore(tmp_path / "artifacts"),
        SOURCE_SCHEMA,
        CITATION_SCHEMA,
    )


def quality() -> dict:
    return {
        "authority": 0.9,
        "directness": 1.0,
        "independence": 0.8,
        "reproducibility": 0.7,
        "timeliness": 0.95,
        "notes": "generated public property fixture",
    }


def put_local_snapshot(
    store: SourceSnapshotStore,
    payload: bytes,
    *,
    locator: dict | None = None,
    retrieved_at: str = "2026-08-19T01:55:00Z",
) -> dict:
    return store.put_snapshot(
        payload,
        locator=locator or {"identifier": "property:source"},
        retrieved_at=retrieved_at,
        source_role="local",
        quality=quality(),
        media_type="application/octet-stream",
    )


@settings(max_examples=160, derandomize=True)
@given(key=st.sampled_from(LOCATOR_KEYS), value=NONBLANK_TEXT)
def test_source_identity_is_deterministic_for_normalized_locator(key: str, value: str) -> None:
    locator = {key: value}

    first = SourceSnapshotStore.source_id_for_locator(locator)
    second = SourceSnapshotStore.source_id_for_locator(dict(locator))

    assert first == second
    assert first.startswith("source_")
    assert len(first.removeprefix("source_")) == 20


@settings(max_examples=80, derandomize=True)
@given(payload=st.binary(min_size=0, max_size=128), locator_value=NONBLANK_TEXT)
def test_identical_snapshot_publish_is_idempotent(
    tmp_path: Path,
    payload: bytes,
    locator_value: str,
) -> None:
    store = source_store(tmp_path)
    kwargs = {
        "locator": {"identifier": locator_value},
        "retrieved_at": "2026-08-19T01:55:00Z",
        "source_role": "local",
        "quality": quality(),
        "media_type": "application/octet-stream",
    }

    first = store.put_snapshot(payload, **kwargs)
    second = store.put_snapshot(payload, **kwargs)

    assert first == second
    assert first["snapshot_id"] == second["snapshot_id"]
    assert first["source_id"] == second["source_id"]
    assert first["content_hash"]["digest"] == hashlib.sha256(payload).hexdigest()


@settings(max_examples=80, derandomize=True)
@given(payload=st.binary(min_size=0, max_size=128), locator_value=NONBLANK_TEXT)
def test_distinct_versions_coexist_under_one_source_identity(
    tmp_path: Path,
    payload: bytes,
    locator_value: str,
) -> None:
    store = source_store(tmp_path)
    locator = {"repository_ref": locator_value}
    first = put_local_snapshot(
        store,
        payload,
        locator=locator,
        retrieved_at="2026-08-19T01:55:00Z",
    )
    second = put_local_snapshot(
        store,
        payload + b"\x00",
        locator=locator,
        retrieved_at="2026-08-19T01:56:00Z",
    )

    assert first["source_id"] == second["source_id"]
    assert first["snapshot_id"] != second["snapshot_id"]
    assert [item["snapshot_id"] for item in store.versions(first["source_id"])] == [
        first["snapshot_id"],
        second["snapshot_id"],
    ]


@settings(max_examples=120, derandomize=True)
@given(payload=st.binary(min_size=1, max_size=128), draw=st.data())
def test_bounded_citation_resolves_exact_bytes_and_hash(
    tmp_path: Path,
    payload: bytes,
    draw: st.DataObject,
) -> None:
    store = source_store(tmp_path)
    snapshot = put_local_snapshot(store, payload)
    start = draw.draw(st.integers(min_value=0, max_value=len(payload) - 1), label="byte_start")
    end = draw.draw(st.integers(min_value=start + 1, max_value=len(payload)), label="byte_end")

    citation = store.create_citation(snapshot["snapshot_id"], byte_start=start, byte_end=end)
    resolved = store.resolve_citation(citation)
    expected = payload[start:end]

    assert resolved["bytes"] == expected
    assert citation["snapshot_id"] == snapshot["snapshot_id"]
    assert citation["artifact_id"] == snapshot["artifact_id"]
    assert citation["passage_hash"] == {
        "algorithm": "sha256",
        "digest": hashlib.sha256(expected).hexdigest(),
    }


@settings(max_examples=80, derandomize=True)
@given(payload=st.binary(min_size=1, max_size=128))
def test_invalid_citation_spans_fail_closed(tmp_path: Path, payload: bytes) -> None:
    store = source_store(tmp_path)
    snapshot = put_local_snapshot(store, payload)
    snapshot_id = snapshot["snapshot_id"]

    invalid_spans = [
        (-1, 1),
        (0, 0),
        (len(payload), len(payload)),
        (0, len(payload) + 1),
    ]
    for start, end in invalid_spans:
        with pytest.raises(ValueError, match="outside source artifact bounds"):
            store.create_citation(snapshot_id, byte_start=start, byte_end=end)

    with pytest.raises(ValueError, match="supplied together"):
        store.create_citation(snapshot_id, byte_start=0)
    with pytest.raises(ValueError, match="supplied together"):
        store.create_citation(snapshot_id, byte_end=1)


@settings(max_examples=60, derandomize=True)
@given(role=st.sampled_from(SOURCE_ROLES_WITHOUT_DERIVATION), payload=st.binary(max_size=96))
def test_primary_secondary_and_local_snapshots_cannot_claim_derivation(
    tmp_path: Path,
    role: str,
    payload: bytes,
) -> None:
    store = source_store(tmp_path)

    with pytest.raises(ValueError, match="must not claim derivation"):
        store.put_snapshot(
            payload,
            locator={"identifier": f"property:{role}"},
            retrieved_at="2026-08-19T01:55:00Z",
            source_role=role,
            quality=quality(),
            derivation={
                "method": "invalid generated derivation",
                "parent_snapshot_refs": ["snap_missing_parent_0001"],
            },
        )


@settings(max_examples=60, derandomize=True)
@given(role=st.sampled_from(DERIVED_SOURCE_ROLES), payload=st.binary(max_size=96))
def test_derived_and_reconstructed_snapshots_require_resolvable_parent(
    tmp_path: Path,
    role: str,
    payload: bytes,
) -> None:
    store = source_store(tmp_path)

    with pytest.raises(ValueError, match="requires explicit parent_snapshot_refs"):
        store.put_snapshot(
            payload,
            locator={"identifier": f"property:{role}:missing-parent"},
            retrieved_at="2026-08-19T01:55:00Z",
            source_role=role,
            quality=quality(),
        )

    parent = put_local_snapshot(store, b"parent evidence")
    child = store.put_snapshot(
        payload,
        locator={"identifier": f"property:{role}:child"},
        retrieved_at="2026-08-19T01:56:00Z",
        source_role=role,
        quality=quality(),
        derivation={
            "method": "generated derivation",
            "parent_snapshot_refs": [parent["snapshot_id"]],
        },
    )

    assert child["derivation"]["parent_snapshot_refs"] == [parent["snapshot_id"]]
