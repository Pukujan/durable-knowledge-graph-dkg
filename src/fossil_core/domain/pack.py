from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PackBoundaryError(ValueError):
    pass


@dataclass(frozen=True)
class PackAccess:
    pack_id: str
    read_mounts: frozenset[str]
    write_targets: frozenset[str]

    @classmethod
    def from_manifest(cls, manifest: dict[str, Any]) -> "PackAccess":
        return cls(
            pack_id=manifest["pack_id"],
            read_mounts=frozenset(manifest["read_mounts"]),
            write_targets=frozenset(manifest["write_targets"]),
        )

    def require_read(self, pack_id: str) -> None:
        if pack_id not in self.read_mounts:
            raise PackBoundaryError(f"pack {pack_id} is not mounted for reading")

    def require_write(self, pack_id: str) -> None:
        if pack_id not in self.write_targets:
            raise PackBoundaryError(f"pack {pack_id} is not an allowed write target")


__all__ = ["PackBoundaryError", "PackAccess"]
