from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from ...domain.pack import PackAccess, PackBoundaryError


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

    def validate_set(self, manifests: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for manifest in manifests:
            self.validate(manifest)
            pack_id = manifest["pack_id"]
            if pack_id in by_id:
                raise PackBoundaryError(f"duplicate pack_id: {pack_id}")
            by_id[pack_id] = manifest
        for manifest in by_id.values():
            for dependency in manifest.get("dependencies", []):
                if dependency["required"] and dependency["pack_id"] not in by_id:
                    raise PackBoundaryError(
                        f"required dependency {dependency['pack_id']} is unavailable"
                    )
        return by_id

    def load_and_validate(self, path: Path) -> dict[str, Any]:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        self.validate(manifest)
        return manifest
