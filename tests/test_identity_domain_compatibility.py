from __future__ import annotations

import string

import fossil_core.ids as legacy_ids
from fossil_core.domain.identity import deterministic_event_id, new_id


def test_legacy_identity_module_preserves_canonical_function_identity():
    assert legacy_ids.new_id is new_id
    assert legacy_ids.deterministic_event_id is deterministic_event_id


def test_deterministic_event_id_regression_vector_is_unchanged():
    assert (
        deterministic_event_id("pack-a", "retry-1")
        == "evt_d45980b2e134f30d603bb913ff0b9005"
    )


def test_new_id_keeps_corpus_prefix_and_uuid_hex_shape():
    value = new_id("claim")

    assert value.startswith("claim_")
    suffix = value.removeprefix("claim_")
    assert len(suffix) == 32
    assert set(suffix) <= set(string.hexdigits.lower())
    assert suffix == suffix.lower()


def test_legacy_ids_preserves_historical_implicit_star_surface():
    assert not hasattr(legacy_ids, "__all__")
    public_names = sorted(name for name in vars(legacy_ids) if not name.startswith("_"))
    assert public_names == ["deterministic_event_id", "hashlib", "new_id", "uuid"]
