from __future__ import annotations

import inspect

import fossil_core.application.query.receipt as canonical_receipt
import fossil_core.execution_receipt as legacy_receipt


def test_execution_receipt_legacy_namespace_and_object_identity_are_frozen():
    assert not hasattr(legacy_receipt, "__all__")
    assert {
        name for name in vars(legacy_receipt) if not name.startswith("_")
    } == {
        "Any",
        "Iterable",
        "Mapping",
        "QUERY_EXECUTION_RECEIPT_AUTHORITY",
        "QUERY_EXECUTION_RECEIPT_SCHEMA",
        "Sequence",
        "annotations",
        "build_query_execution_receipt",
        "build_service_invocation",
        "compare_query_execution_receipts",
        "copy",
        "datetime",
        "execute_query_with_receipt",
        "hashlib",
        "json",
        "normalize_pack_mounts",
        "normalize_query",
        "re",
        "sanitize_diagnostics",
        "time",
        "timezone",
        "unicodedata",
    }

    for symbol in (
        "normalize_query",
        "sanitize_diagnostics",
        "build_service_invocation",
        "normalize_pack_mounts",
        "build_query_execution_receipt",
        "compare_query_execution_receipts",
        "execute_query_with_receipt",
    ):
        assert getattr(legacy_receipt, symbol) is getattr(canonical_receipt, symbol)


def test_execution_receipt_public_call_signatures_are_unchanged():
    build_signature = inspect.signature(canonical_receipt.build_query_execution_receipt)
    build_parameters = list(build_signature.parameters.values())
    assert [parameter.name for parameter in build_parameters] == [
        "query",
        "pack_mounts",
        "pack_scope_ids",
        "projection",
        "policy",
        "services",
        "candidates",
        "response",
        "trace_ref",
        "run_ref",
        "query_id",
        "recorded_at",
        "latency_ms",
        "cost_usd",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in build_parameters
    )
    assert [parameter.name for parameter in build_parameters if parameter.default is inspect.Parameter.empty] == [
        "query",
        "pack_mounts",
        "projection",
        "policy",
        "services",
        "candidates",
        "response",
        "trace_ref",
    ]

    execute_signature = inspect.signature(canonical_receipt.execute_query_with_receipt)
    execute_parameters = list(execute_signature.parameters.values())
    assert [parameter.name for parameter in execute_parameters] == [
        "query",
        "pack_mounts",
        "query_pack_ids",
        "projection",
        "policy",
        "retriever",
        "model_service",
        "limit",
        "trace_ref",
        "run_ref",
        "query_id",
        "requested_model",
        "model_attempts",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in execute_parameters
    )
    assert [parameter.name for parameter in execute_parameters if parameter.default is inspect.Parameter.empty] == [
        "query",
        "pack_mounts",
        "query_pack_ids",
        "projection",
        "policy",
        "retriever",
        "model_service",
        "limit",
        "trace_ref",
    ]


def test_canonical_and_legacy_receipt_behavior_match_historical_shape():
    kwargs = {
        "query": "  Café   status?  ",
        "pack_mounts": {"pack_b": "rev_b", "pack_a": "rev_a"},
        "pack_scope_ids": ["pack_a"],
        "projection": {"name": "fixture", "version": "1", "build_id": "build_1"},
        "policy": {
            "route_id": "route_1",
            "retrieval_policy_id": "policy_1",
            "mode": "compatibility-test",
        },
        "services": [],
        "candidates": [],
        "response": {
            "authority": "candidate_only",
            "output": {
                "outcome": "insufficient_evidence",
                "answer_text": "Insufficient evidence.",
                "claims": [],
                "confidence": 1.0,
            },
        },
        "trace_ref": "trace://compatibility",
        "run_ref": "run_1",
        "query_id": "query_1",
        "recorded_at": "2026-08-17T00:00:00+00:00",
        "latency_ms": 12.5,
        "cost_usd": 0.0,
    }

    legacy = legacy_receipt.build_query_execution_receipt(**kwargs)
    canonical = canonical_receipt.build_query_execution_receipt(**kwargs)

    assert canonical == legacy
    assert canonical["schema_version"] == "fossil.query-execution-receipt.v1"
    assert canonical["authority"] == "execution_observability_only"
    assert canonical["query"]["normalized"] == "Café status?"
    assert canonical["packs"] == [
        {"pack_id": "pack_a", "revision": "rev_a"},
        {"pack_id": "pack_b", "revision": "rev_b"},
    ]
    assert canonical["result"]["outcome"] == "insufficient_evidence"
    assert canonical["result"]["abstained"] is True


def test_receipt_diagnostic_sanitization_and_mount_order_are_preserved():
    assert canonical_receipt.sanitize_diagnostics(
        {
            "provider": "fixture",
            "api_key": "must-disappear",
            "nested": {"Authorization": "must-disappear", "safe": 7},
        }
    ) == {"provider": "fixture", "nested": {"safe": 7}}
    assert canonical_receipt.normalize_pack_mounts(
        {"pack_z": "rev_z", "pack_a": "rev_a"}
    ) == [
        {"pack_id": "pack_a", "revision": "rev_a"},
        {"pack_id": "pack_z", "revision": "rev_z"},
    ]
