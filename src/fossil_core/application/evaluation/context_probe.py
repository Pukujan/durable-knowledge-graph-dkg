from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def classify_context_probe(probe: Mapping[str, Any]) -> dict[str, Any]:
    items = [dict(item) for item in probe.get("items", [])]
    truncated_ids = [
        str(item.get("id"))
        for item in items
        if bool(item.get("context_truncated", False))
    ]
    chars_used = int(probe.get("chars_used", 0))
    max_chars = int(probe.get("max_chars", 0))
    return {
        "chars_used": chars_used,
        "max_chars": max_chars,
        "item_ids": [str(item.get("id")) for item in items],
        "truncated_ids": truncated_ids,
        "context_truncation_or_overload": bool(truncated_ids) or (
            max_chars > 0 and chars_used >= max_chars
        ),
    }
