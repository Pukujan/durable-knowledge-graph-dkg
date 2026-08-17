from __future__ import annotations

import inspect

import fossil_core.answer_pipeline as legacy_answer_pipeline
import fossil_core.application.query as canonical_query
import fossil_core.application.query.lineage as lineage_impl


def _assert_lineage_function_signature(function, *, diagnostics: bool = False) -> None:
    signature = inspect.signature(function)
    parameters = list(signature.parameters.values())

    assert [parameter.name for parameter in parameters] == [
        "context_items",
        "documents",
        "pack_ids",
        "max_expansions",
    ]
    assert [parameter.kind for parameter in parameters] == [
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
    ]
    assert parameters[0].default is inspect.Parameter.empty
    assert parameters[1].default is inspect.Parameter.empty
    assert parameters[2].default is inspect.Parameter.empty
    assert parameters[3].default == 24
    expected_return = (
        "tuple[list[dict[str, Any]], dict[str, Any]]"
        if diagnostics
        else "list[dict[str, Any]]"
    )
    assert signature.return_annotation == expected_return


def test_answer_pipeline_legacy_namespace_and_object_identity_are_frozen():
    assert not hasattr(legacy_answer_pipeline, "__all__")
    assert sorted(
        name for name in vars(legacy_answer_pipeline) if not name.startswith("_")
    ) == [
        "Any",
        "Iterable",
        "LINEAGE_CONTEXT_RESOLVER",
        "LineageResolvedModelService",
        "Mapping",
        "annotations",
        "copy",
        "expand_context_with_lineage",
        "expand_context_with_lineage_diagnostics",
    ]

    assert canonical_query.__all__ == [
        "LINEAGE_CONTEXT_RESOLVER",
        "expand_context_with_lineage",
        "expand_context_with_lineage_diagnostics",
        "LineageResolvedModelService",
    ]
    for symbol in canonical_query.__all__:
        assert getattr(legacy_answer_pipeline, symbol) is getattr(canonical_query, symbol)
        assert getattr(canonical_query, symbol) is getattr(lineage_impl, symbol)


def test_answer_pipeline_public_call_signatures_are_unchanged():
    _assert_lineage_function_signature(canonical_query.expand_context_with_lineage)
    _assert_lineage_function_signature(
        canonical_query.expand_context_with_lineage_diagnostics,
        diagnostics=True,
    )

    init_signature = inspect.signature(canonical_query.LineageResolvedModelService.__init__)
    parameters = list(init_signature.parameters.values())
    assert [parameter.name for parameter in parameters] == [
        "self",
        "service",
        "documents",
        "max_expansions",
    ]
    assert [parameter.kind for parameter in parameters] == [
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.KEYWORD_ONLY,
    ]
    assert parameters[1].default is inspect.Parameter.empty
    assert parameters[2].default is inspect.Parameter.empty
    assert parameters[3].default == 24


def test_canonical_and_legacy_lineage_behavior_match_historical_shape():
    relation = {
        "id": "rel_1",
        "pack_id": "pack_1",
        "document_type": "relation",
        "source_ref": "claim_source",
        "target_ref": "claim_target",
    }
    source = {
        "id": "claim_source",
        "pack_id": "pack_1",
        "document_type": "claim",
        "text": "source",
    }
    target = {
        "id": "claim_target",
        "pack_id": "pack_1",
        "document_type": "claim",
        "text": "target",
    }

    legacy_result = legacy_answer_pipeline.expand_context_with_lineage(
        [relation],
        documents=[relation, source, target],
        pack_ids=["pack_1"],
    )
    canonical_result, diagnostics = canonical_query.expand_context_with_lineage_diagnostics(
        [relation],
        documents=[relation, source, target],
        pack_ids=["pack_1"],
    )

    assert legacy_result == canonical_result == [
        relation,
        {
            **source,
            "context_expansion": {
                "reason": "durable_relation_endpoint",
                "resolver": "fossil-lineage-context-v1",
            },
        },
        {
            **target,
            "context_expansion": {
                "reason": "durable_relation_endpoint",
                "resolver": "fossil-lineage-context-v1",
            },
        },
    ]
    assert diagnostics == {
        "resolver": "fossil-lineage-context-v1",
        "allowed_pack_ids": ["pack_1"],
        "input_context_ids": ["rel_1"],
        "expanded_ids": ["claim_source", "claim_target"],
        "final_context_ids": ["rel_1", "claim_source", "claim_target"],
        "max_expansions": 24,
    }
