from __future__ import annotations

import os
import uuid
from pathlib import Path


def fsync_directory(path: Path) -> None:
    """Best-effort directory fsync after publishing a durable file."""
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_immutable(path: Path, data: bytes) -> bool:
    """Atomically publish bytes without replacing an existing path.

    Returns True when this call published the file, False when another writer
    already published the target. The caller decides whether the existing
    content is an idempotent retry or a conflict.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            temp.unlink(missing_ok=True)
            raise

        try:
            os.link(temp, path)
            published = True
        except FileExistsError:
            published = False
        if published:
            fsync_directory(path.parent)
        return published
    finally:
        temp.unlink(missing_ok=True)
