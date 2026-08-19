from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from ...domain.pack import PackBoundaryError
from ...domain.packset import (
    build_packset_lock as build_validated_packset_lock,
    validate_pack_dependency_graph,
    validate_packset_lock as validate_existing_packset_lock,
)


class KnowledgePackValidator:
    def __init__(self, schema_path: Path):
        self.schema_path = Path(schema_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema, format_checker=FormatChecker())

    def validate(self, manifest: dict[str, Any]) -> None:
        self.validator.validate(manifest)
        pack_id = manifest["pack_id"]
        if pack_id not in manifest["read_mounts"]:
            raise PackBoundaryError("a pack must be able to read itself")
        for target in manifest["write_targets"]:
            if target not in manifest["read_mounts"]:
                raise PackBoundaryError("every write target must also be readable")
        for dependency in manifest.get("dependencies", []):
            if dependency["required"] and dependency["pack_id"] not in manifest["read_mounts"]:
                raise PackBoundaryError("every required dependency must be in read_mounts")

    def _validate_catalog(self, manifests: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for manifest in manifests:
            self.validate(manifest)
            pack_id = manifest["pack_id"]
            if pack_id in by_id:
                raise PackBoundaryError(f"duplicate pack_id: {pack_id}")
            by_id[pack_id] = manifest
        return by_id

    def validate_set(self, manifests: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        by_id = self._validate_catalog(manifests)
        for manifest in by_id.values():
            for dependency in manifest.get("dependencies", []):
                if dependency["required"] and dependency["pack_id"] not in by_id:
                    raise PackBoundaryError(
                        f"required dependency {dependency['pack_id']} is unavailable"
                    )
        validate_pack_dependency_graph(by_id)
        return by_id

    def build_packset_lock(
        self,
        manifests: Iterable[dict[str, Any]],
        revisions: Mapping[str, str],
    ) -> dict[str, Any]:
        """Validate a mounted manifest set, then freeze its exact revisions."""

        by_id = self.validate_set(manifests)
        return build_validated_packset_lock(by_id, revisions)

    def validate_packset_lock(
        self,
        lock: Mapping[str, Any],
        manifests: Iterable[dict[str, Any]],
    ) -> None:
        """Validate replay lock content against an available manifest catalog.

        The catalog may contain packs that are not mounted by this lock. Those
        unrelated packs are schema/boundary checked but do not participate in
        this lock's dependency graph.
        """

        by_id = self._validate_catalog(manifests)
        validate_existing_packset_lock(lock, by_id)

    def load_and_validate(self, path: Path) -> dict[str, Any]:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        self.validate(manifest)
        return manifest
