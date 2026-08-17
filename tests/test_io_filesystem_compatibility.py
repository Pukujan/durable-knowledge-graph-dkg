from __future__ import annotations

import inspect

import fossil_core.adapters.filesystem.io as canonical_io
import fossil_core.io as legacy_io


def test_io_legacy_namespace_and_object_identity_are_frozen():
    assert not hasattr(legacy_io, "__all__")
    assert {name for name in vars(legacy_io) if not name.startswith("_")} == {
        "Path",
        "annotations",
        "fsync_directory",
        "os",
        "publish_immutable",
        "uuid",
    }
    assert legacy_io.fsync_directory is canonical_io.fsync_directory
    assert legacy_io.publish_immutable is canonical_io.publish_immutable


def test_io_signatures_are_unchanged():
    fsync_signature = inspect.signature(canonical_io.fsync_directory)
    assert list(fsync_signature.parameters) == ["path"]
    assert fsync_signature.return_annotation == "None"

    publish_signature = inspect.signature(canonical_io.publish_immutable)
    assert list(publish_signature.parameters) == ["path", "data"]
    assert publish_signature.return_annotation == "bool"


def test_canonical_and_legacy_immutable_publish_behavior_match(tmp_path):
    canonical_path = tmp_path / "canonical" / "item.bin"
    legacy_path = tmp_path / "legacy" / "item.bin"

    for publish, path in (
        (canonical_io.publish_immutable, canonical_path),
        (legacy_io.publish_immutable, legacy_path),
    ):
        assert publish(path, b"first") is True
        assert path.read_bytes() == b"first"
        assert publish(path, b"first") is False
        assert publish(path, b"different") is False
        assert path.read_bytes() == b"first"
