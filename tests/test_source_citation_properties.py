from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st
from jsonschema import ValidationError

from fossil_core.artifact_store import ArtifactStore
from fossil_core.source import (
    RedactionPolicy,
    SourceSnapshotConflict,
    SourceSnapshotStore,
)

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


def source_store(root: Path) -> SourceSnapshotStore:
    return SourceSnapshotStore(
        root / "sources",
        ArtifactStore(root / "artifacts"),
        SOURCE_SCHEMA,
        CITATION_SCHEMA,
    )


def isolated_source_store() -> tuple[tempfile.TemporaryDirectory, SourceSnapshotStore]:
    temporary = tempfile.TemporaryDirectory()
    return temporary, source_store(Path(temporary.name))


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


def expected_stable_id(prefix: str, *parts: str, length: int = 24) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:length]}"


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
def test_identical_snapshot_publish_is_idempotent(payload: bytes, locator_value: str) -> None:
    temporary, store = isolated_source_store()
    try:
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
    finally:
        temporary.cleanup()


@settings(max_examples=80, derandomize=True)
@given(payload=st.binary(min_size=0, max_size=128), locator_value=NONBLANK_TEXT)
def test_distinct_versions_coexist_under_one_source_identity(
    payload: bytes,
    locator_value: str,
) -> None:
    temporary, store = isolated_source_store()
    try:
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
    finally:
        temporary.cleanup()


@settings(max_examples=120, derandomize=True)
@given(payload=st.binary(min_size=1, max_size=128), draw=st.data())
def test_bounded_citation_resolves_exact_bytes_and_hash(payload: bytes, draw) -> None:
    temporary, store = isolated_source_store()
    try:
        snapshot = put_local_snapshot(store, payload)
        start = draw.draw(
            st.integers(min_value=0, max_value=len(payload) - 1), label="byte_start"
        )
        end = draw.draw(
            st.integers(min_value=start + 1, max_value=len(payload)), label="byte_end"
        )

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
    finally:
        temporary.cleanup()


@settings(max_examples=80, derandomize=True)
@given(payload=st.binary(min_size=1, max_size=128))
def test_invalid_citation_spans_fail_closed(payload: bytes) -> None:
    temporary, store = isolated_source_store()
    try:
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
    finally:
        temporary.cleanup()


@settings(max_examples=60, derandomize=True)
@given(role=st.sampled_from(SOURCE_ROLES_WITHOUT_DERIVATION), payload=st.binary(max_size=96))
def test_primary_secondary_and_local_snapshots_cannot_claim_derivation(
    role: str,
    payload: bytes,
) -> None:
    temporary, store = isolated_source_store()
    try:
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
    finally:
        temporary.cleanup()


@settings(max_examples=60, derandomize=True)
@given(role=st.sampled_from(DERIVED_SOURCE_ROLES), payload=st.binary(max_size=96))
def test_derived_and_reconstructed_snapshots_require_resolvable_parent(
    role: str,
    payload: bytes,
) -> None:
    temporary, store = isolated_source_store()
    try:
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
    finally:
        temporary.cleanup()


def test_source_store_initialization_is_idempotent_for_nested_root(tmp_path: Path) -> None:
    nested_root = tmp_path / "deep" / "nested" / "sources"
    artifacts = ArtifactStore(tmp_path / "artifacts")

    first = SourceSnapshotStore(nested_root, artifacts, SOURCE_SCHEMA, CITATION_SCHEMA)
    second = SourceSnapshotStore(nested_root, artifacts, SOURCE_SCHEMA, CITATION_SCHEMA)

    assert first.root == nested_root
    assert second.root == nested_root
    assert nested_root.is_dir()


def test_source_snapshot_persistence_and_ids_are_canonical(tmp_path: Path) -> None:
    store = source_store(tmp_path)
    payload = "π evidence with stable bytes".encode("utf-8")
    locator = {"identifier": "urn:fossil:π"}
    retrieved_at = "2026-08-19T02:10:00Z"
    version_metadata = {"etag": '"π-v1"', "version_id": "revision-7"}

    snapshot = store.put_snapshot(
        payload,
        locator=locator,
        retrieved_at=retrieved_at,
        source_role="local",
        quality=quality(),
        version_metadata=version_metadata,
        media_type="text/plain",
    )

    normalized_locator = {
        "url": None,
        "identifier": "urn:fossil:π",
        "repository_ref": None,
    }
    expected_source_id = expected_stable_id(
        "source",
        json.dumps(
            normalized_locator,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        length=20,
    )
    version = {
        "etag": '"π-v1"',
        "last_modified": None,
        "version_id": "revision-7",
        "commit_sha": None,
    }
    expected_snapshot_id = expected_stable_id(
        "snap",
        expected_source_id,
        hashlib.sha256(payload).hexdigest(),
        retrieved_at,
        json.dumps(version, sort_keys=True, separators=(",", ":")),
    )

    assert snapshot["source_id"] == expected_source_id
    assert snapshot["snapshot_id"] == expected_snapshot_id
    assert len(snapshot["snapshot_id"].removeprefix("snap_")) == 24
    assert store.artifact_store.get_manifest(snapshot["artifact_id"])["media_type"] == "text/plain"

    persisted = next((store.root / "snapshots").glob("*/*.json"))
    expected_bytes = (
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    assert persisted.read_bytes() == expected_bytes


def test_source_snapshot_validation_enforces_date_time_formats(tmp_path: Path) -> None:
    store = source_store(tmp_path)

    with pytest.raises(ValidationError):
        store.put_snapshot(
            b"invalid retrieval time",
            locator={"identifier": "property:invalid-date"},
            retrieved_at="not-a-date-time",
            source_role="local",
            quality=quality(),
        )


def test_default_snapshot_media_type_is_preserved_in_artifact_manifest(tmp_path: Path) -> None:
    store = source_store(tmp_path)
    snapshot = store.put_snapshot(
        b"default media type",
        locator={"identifier": "property:default-media"},
        retrieved_at="2026-08-19T02:11:00Z",
        source_role="local",
        quality=quality(),
    )

    manifest = store.artifact_store.get_manifest(snapshot["artifact_id"])
    assert manifest["media_type"] == "application/octet-stream"


def test_snapshot_republish_detects_tampered_durable_record(tmp_path: Path) -> None:
    store = source_store(tmp_path)
    kwargs = {
        "locator": {"identifier": "property:immutable-conflict"},
        "retrieved_at": "2026-08-19T02:12:00Z",
        "source_role": "local",
        "quality": quality(),
        "media_type": "text/plain",
    }
    snapshot = store.put_snapshot(b"immutable snapshot bytes", **kwargs)
    path = next((store.root / "snapshots").glob(f"*/{snapshot['snapshot_id']}.json"))
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["published_at"] = "2026-08-18T00:00:00Z"
    path.write_text(
        json.dumps(tampered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SourceSnapshotConflict):
        store.put_snapshot(b"immutable snapshot bytes", **kwargs)


def test_citation_identity_resolution_shape_and_copy_are_stable(tmp_path: Path) -> None:
    store = source_store(tmp_path)
    payload = b"alpha beta gamma"
    snapshot = put_local_snapshot(store, payload)
    start, end = 6, 10
    passage = payload[start:end]
    passage_digest = hashlib.sha256(passage).hexdigest()

    bounded = store.create_citation(
        snapshot["snapshot_id"],
        byte_start=start,
        byte_end=end,
    )
    expected_bounded_id = expected_stable_id(
        "cite",
        snapshot["snapshot_id"],
        snapshot["artifact_id"],
        str(start),
        str(end),
        passage_digest,
    )
    assert bounded["citation_id"] == expected_bounded_id
    assert len(bounded["citation_id"].removeprefix("cite_")) == 24

    resolved = store.resolve_citation(bounded)
    assert set(resolved) == {"citation", "snapshot", "bytes", "text"}
    assert resolved["citation"] == bounded
    assert resolved["snapshot"] == snapshot
    assert resolved["bytes"] == passage
    assert resolved["text"] == "beta"

    original_digest = bounded["passage_hash"]["digest"]
    bounded["passage_hash"]["digest"] = "0" * 64
    assert resolved["citation"]["passage_hash"]["digest"] == original_digest

    whole = store.create_citation(snapshot["snapshot_id"])
    expected_whole_id = expected_stable_id(
        "cite",
        snapshot["snapshot_id"],
        snapshot["artifact_id"],
        "None",
        "None",
        "whole-artifact",
    )
    assert whole["citation_id"] == expected_whole_id
    assert whole["passage_hash"] is None
    assert whole["citation_id"] != expected_bounded_id
    assert store.resolve_citation(whole)["bytes"] == payload


def test_derived_snapshot_detaches_caller_owned_derivation(tmp_path: Path) -> None:
    store = source_store(tmp_path)
    parent = put_local_snapshot(store, b"parent")
    parent_refs = [parent["snapshot_id"]]
    derivation = {
        "method": "generated derivation",
        "parent_snapshot_refs": parent_refs,
    }
    child = store.put_snapshot(
        b"child",
        locator={"identifier": "property:derived-copy"},
        retrieved_at="2026-08-19T02:13:00Z",
        source_role="derived",
        quality=quality(),
        derivation=derivation,
    )

    parent_refs.append("snap_external_mutation_0001")

    assert child["derivation"]["parent_snapshot_refs"] == [parent["snapshot_id"]]
    assert store.get_snapshot(child["snapshot_id"])["derivation"]["parent_snapshot_refs"] == [
        parent["snapshot_id"]
    ]


def test_snapshot_exports_preserve_shape_before_and_after_redaction(tmp_path: Path) -> None:
    store = source_store(tmp_path)
    payload = b"exported source bytes"
    snapshot = put_local_snapshot(store, payload)

    assert store.artifact_for_snapshot(snapshot["snapshot_id"]) == snapshot["artifact_id"]
    assert store.export_snapshot(snapshot["snapshot_id"]) == {
        "snapshot": snapshot,
        "content": payload,
        "redacted": False,
        "redaction": None,
    }

    tombstone = store.artifact_store.redact(
        snapshot["artifact_id"],
        reason="property redaction",
        authority="property-test",
        redacted_at="2026-08-19T02:14:00Z",
        request_ref="property-redaction-1",
    )
    assert store.export_snapshot(snapshot["snapshot_id"]) == {
        "snapshot": snapshot,
        "content": None,
        "redacted": True,
        "redaction": tombstone,
    }


def test_redaction_policy_filters_visible_events_and_defensively_exports(tmp_path: Path) -> None:
    store = source_store(tmp_path)
    visible_snapshot = put_local_snapshot(
        store,
        b"visible evidence",
        locator={"identifier": "property:visible"},
        retrieved_at="2026-08-19T02:15:00Z",
    )
    hidden_snapshot = put_local_snapshot(
        store,
        b"hidden evidence",
        locator={"identifier": "property:hidden"},
        retrieved_at="2026-08-19T02:16:00Z",
    )
    store.artifact_store.redact(
        hidden_snapshot["artifact_id"],
        reason="property redaction",
        authority="property-test",
        redacted_at="2026-08-19T02:17:00Z",
        request_ref="property-redaction-2",
    )
    policy = RedactionPolicy(store)

    visible_event = {
        "event_id": "evt_visible_property",
        "evidence_refs": [visible_snapshot["artifact_id"]],
        "source_snapshot_refs": [visible_snapshot["snapshot_id"]],
        "payload": {"nested": {"value": 1}},
    }
    hidden_by_artifact = {
        "event_id": "evt_hidden_artifact",
        "evidence_refs": [hidden_snapshot["artifact_id"]],
        "source_snapshot_refs": [],
        "payload": {},
    }
    hidden_by_snapshot = {
        "event_id": "evt_hidden_snapshot",
        "evidence_refs": [],
        "source_snapshot_refs": [hidden_snapshot["snapshot_id"]],
        "payload": {},
    }
    unknown_then_hidden = {
        "event_id": "evt_unknown_then_hidden",
        "evidence_refs": [],
        "source_snapshot_refs": [
            "snap_missing_property_0001",
            hidden_snapshot["snapshot_id"],
        ],
        "payload": {},
    }

    assert policy.event_visible(visible_event) is True
    assert policy.event_visible(hidden_by_artifact) is False
    assert policy.event_visible(hidden_by_snapshot) is False
    assert policy.event_visible(unknown_then_hidden) is False
    assert policy.visible_events(
        [visible_event, hidden_by_artifact, hidden_by_snapshot, unknown_then_hidden]
    ) == [visible_event]

    exported = policy.export_event(visible_event)
    assert exported == visible_event
    visible_event["payload"]["nested"]["value"] = 2
    assert exported is not None
    assert exported["payload"]["nested"]["value"] == 1
