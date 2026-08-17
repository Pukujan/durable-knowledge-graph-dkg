from __future__ import annotations

import inspect

import fossil_core.application.rebuild.pack_corpus as canonical_pack_corpus
import fossil_core.pack_corpus as legacy_pack_corpus
from fossil_core.domain.lifecycle import KnowledgeState


def test_pack_corpus_legacy_namespace_and_object_identity_are_frozen():
    assert not hasattr(legacy_pack_corpus, "__all__")
    assert {
        name for name in vars(legacy_pack_corpus) if not name.startswith("_")
    } == {
        "Any",
        "Iterable",
        "KnowledgeState",
        "Path",
        "annotations",
        "copy",
        "json",
        "retrieval_documents_from_pack_fixtures",
        "validate_pack_fixtures",
    }

    assert legacy_pack_corpus.KnowledgeState is KnowledgeState
    assert legacy_pack_corpus.validate_pack_fixtures is canonical_pack_corpus.validate_pack_fixtures
    assert (
        legacy_pack_corpus.retrieval_documents_from_pack_fixtures
        is canonical_pack_corpus.retrieval_documents_from_pack_fixtures
    )
    assert legacy_pack_corpus._load_json is canonical_pack_corpus._load_json
    assert legacy_pack_corpus._events_for_pack is canonical_pack_corpus._events_for_pack


def test_pack_corpus_rebuild_signature_is_unchanged():
    signature = inspect.signature(
        canonical_pack_corpus.retrieval_documents_from_pack_fixtures
    )
    parameters = list(signature.parameters.values())

    assert [parameter.name for parameter in parameters] == [
        "pack_roots",
        "schemas_root",
        "as_of_recorded_at",
    ]
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[0].default is inspect.Parameter.empty
    assert parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters[1].default is inspect.Parameter.empty
    assert parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters[2].default is None
