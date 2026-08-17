from __future__ import annotations

import inspect

from fossil_core.application.evaluation.context_probe import classify_context_probe as canonical_classify_context_probe
from fossil_core.benchmark_compare import classify_context_probe as legacy_classify_context_probe


def test_context_probe_legacy_symbol_is_canonical_function():
    assert legacy_classify_context_probe is canonical_classify_context_probe
    parameters = list(inspect.signature(canonical_classify_context_probe).parameters.values())
    assert [parameter.name for parameter in parameters] == ["probe"]
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[0].default is inspect.Parameter.empty


def test_context_probe_classification_behavior_is_frozen():
    clean = {
        "chars_used": 120,
        "max_chars": 4000,
        "items": [
            {"id": "former", "context_truncated": False},
            {"id": "stale", "context_truncated": False},
        ],
    }
    saturated = {
        "chars_used": 4000,
        "max_chars": 4000,
        "items": [{"id": "current", "context_truncated": False}],
    }
    truncated = {
        "chars_used": 100,
        "max_chars": 4000,
        "items": [{"id": "current", "context_truncated": True}],
    }

    assert canonical_classify_context_probe(clean) == {
        "chars_used": 120,
        "max_chars": 4000,
        "item_ids": ["former", "stale"],
        "truncated_ids": [],
        "context_truncation_or_overload": False,
    }
    assert canonical_classify_context_probe(saturated) == {
        "chars_used": 4000,
        "max_chars": 4000,
        "item_ids": ["current"],
        "truncated_ids": [],
        "context_truncation_or_overload": True,
    }
    assert canonical_classify_context_probe(truncated) == {
        "chars_used": 100,
        "max_chars": 4000,
        "item_ids": ["current"],
        "truncated_ids": ["current"],
        "context_truncation_or_overload": True,
    }

    assert legacy_classify_context_probe(clean) == canonical_classify_context_probe(clean)
