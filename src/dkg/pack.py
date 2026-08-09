from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


class KnowledgePackValidator:
    def __init__(self, schema_path: Path):
        self.schema_path = Path(schema_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema, format_checker=FormatChecker())

    def validate(self, manifest: dict[str, Any]) -> None:
        self.validator.validate(manifest)
        pack_id = manifest["pack_id"]
        if pack_id not in manifest["read_mounts"]:
            raise ValueError("a pack must be able to read itself")
        for target in manifest["write_targets"]:
            if target not in manifest["read_mounts"]:
                raise ValueError("every write target must also be readable")

    def load_and_validate(self, path: Path) -> dict[str, Any]:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        self.validate(manifest)
        return manifest
