from __future__ import annotations

import string

from hypothesis import given, settings, strategies as st

from fossil_core.domain.identity import deterministic_event_id, new_id


TEXT = st.text(max_size=96)
PREFIX = st.text(
    alphabet=string.ascii_letters + string.digits + "_-",
    min_size=1,
    max_size=24,
)
HEX = set(string.hexdigits.lower())


@settings(max_examples=200, derandomize=True)
@given(pack_id=TEXT, idempotency_key=TEXT)
def test_deterministic_event_id_replays_identically(
    pack_id: str, idempotency_key: str
) -> None:
    first = deterministic_event_id(pack_id, idempotency_key)
    second = deterministic_event_id(pack_id, idempotency_key)

    assert first == second


@settings(max_examples=200, derandomize=True)
@given(
    pack_id=TEXT,
    other_pack_id=TEXT,
    idempotency_key=TEXT,
    other_idempotency_key=TEXT,
)
def test_deterministic_event_id_separates_changed_pack_or_key(
    pack_id: str,
    other_pack_id: str,
    idempotency_key: str,
    other_idempotency_key: str,
) -> None:
    baseline = deterministic_event_id(pack_id, idempotency_key)

    if other_pack_id != pack_id:
        assert deterministic_event_id(other_pack_id, idempotency_key) != baseline
    if other_idempotency_key != idempotency_key:
        assert deterministic_event_id(pack_id, other_idempotency_key) != baseline


@settings(max_examples=200, derandomize=True)
@given(pack_id=TEXT, idempotency_key=TEXT)
def test_deterministic_event_id_has_stable_prefix_length_and_hex_body(
    pack_id: str, idempotency_key: str
) -> None:
    event_id = deterministic_event_id(pack_id, idempotency_key)
    prefix, digest = event_id.split("_", 1)

    assert prefix == "evt"
    assert len(digest) == 32
    assert set(digest) <= HEX


@settings(max_examples=100, derandomize=True)
@given(prefix=PREFIX)
def test_new_id_preserves_prefix_and_uuid_hex_shape(prefix: str) -> None:
    generated = new_id(prefix)
    actual_prefix, suffix = generated.rsplit("_", 1)

    assert actual_prefix == prefix
    assert len(suffix) == 32
    assert set(suffix) <= HEX


@settings(max_examples=200, derandomize=True)
@given(pack_id=st.text(max_size=64), idempotency_key=st.text(max_size=64))
def test_deterministic_event_id_accepts_unicode_inputs(
    pack_id: str, idempotency_key: str
) -> None:
    event_id = deterministic_event_id(pack_id, idempotency_key)

    assert event_id == deterministic_event_id(pack_id, idempotency_key)
    assert event_id.startswith("evt_")
