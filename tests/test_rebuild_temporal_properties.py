from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings, strategies as st

from fossil_core.application.rebuild import retrieval_documents_from_pack_fixtures
from fossil_core.domain.lifecycle import CLAIM_STATES


PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
CLAIM = "clm_rebuild_temporal_property_000001"
DEPENDENT = "clm_rebuild_temporal_property_000002"
RELATION = "rel_rebuild_temporal_property_000001"
TEXT = st.text(max_size=96)


def _timestamp(index: int) -> str:
    return f"2026-08-10T05:26:{index:02d}Z"


def _event_id(index: int) -> str:
    # Deliberately reverse lexical event-id order relative to recorded time so
    # the rebuild must use its explicit (recorded_at, event_id) ordering rule.
    return f"evt_{999999 - index:024d}"


def _event(
    *,
    index: int,
    event_type: str,
    subject_refs: list[str],
    payload: dict,
) -> dict:
    recorded_at = _timestamp(index)
    return {
        "schema_version": "dkg.event.v1",
        "event_id": _event_id(index),
        "event_type": event_type,
        "occurred_at": recorded_at,
        "recorded_at": recorded_at,
        "pack_id": PACK,
        "actor": {"actor_type": "importer", "actor_id": "rebuild-temporal-property"},
        "subject_refs": subject_refs,
        "payload": payload,
    }


def _write_fixture(root: Path, events: list[dict]) -> Path:
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(
        json.dumps({"pack_id": PACK, "event_roots": ["events"]}),
        encoding="utf-8",
    )
    for event in events:
        event_id = str(event["event_id"])
        suffix = event_id.removeprefix("evt_")
        path = root / "events" / suffix[:2] / f"{event_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(event), encoding="utf-8")
    return root


def _claim_history_events(claim_text: str, targets: list[str]) -> list[dict]:
    events = [
        _event(
            index=0,
            event_type="claim.proposed",
            subject_refs=[CLAIM],
            payload={"claim_text": claim_text},
        )
    ]
    current = "proposed"
    for index, target in enumerate(targets, start=1):
        events.append(
            _event(
                index=index,
                event_type="claim.state_changed",
                subject_refs=[CLAIM],
                payload={"from_state": current, "to_state": target},
            )
        )
        current = target
    return events


def _documents(root: Path, *, cutoff: str | None = None) -> list[dict]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "fossil_core.application.rebuild.pack_corpus.validate_pack_fixtures",
            lambda *args, **kwargs: None,
        )
        return retrieval_documents_from_pack_fixtures(
            [root],
            schemas_root=root.parent / "schemas",
            as_of_recorded_at=cutoff,
        )


@settings(max_examples=75, derandomize=True)
@given(
    claim_text=TEXT,
    targets=st.lists(st.sampled_from(sorted(CLAIM_STATES)), min_size=1, max_size=6),
)
def test_rebuild_is_deterministic_despite_hostile_file_write_order(
    claim_text: str,
    targets: list[str],
) -> None:
    events = _claim_history_events(claim_text, targets)
    with TemporaryDirectory() as directory:
        base = Path(directory)
        forward = _write_fixture(base / "forward", events)
        reverse = _write_fixture(base / "reverse", list(reversed(events)))

        forward_documents = _documents(forward)
        reverse_documents = _documents(reverse)

        assert forward_documents == reverse_documents
        claim = forward_documents[0]
        assert claim["id"] == CLAIM
        assert claim["current_state"] == targets[-1]
        assert claim["state_history"] == ["proposed", *targets]


@st.composite
def _cutoff_cases(draw):
    targets = draw(
        st.lists(st.sampled_from(sorted(CLAIM_STATES)), min_size=1, max_size=6)
    )
    cutoff_index = draw(st.integers(min_value=0, max_value=len(targets)))
    claim_text = draw(TEXT)
    return claim_text, targets, cutoff_index


@settings(max_examples=100, derandomize=True)
@given(case=_cutoff_cases())
def test_rebuild_cutoff_includes_exactly_the_then_recorded_claim_history(case) -> None:
    claim_text, targets, cutoff_index = case
    events = _claim_history_events(claim_text, targets)

    with TemporaryDirectory() as directory:
        root = _write_fixture(Path(directory) / "pack", list(reversed(events)))
        cutoff = _timestamp(cutoff_index)

        first = _documents(root, cutoff=cutoff)
        second = _documents(root, cutoff=cutoff)
        assert first == second

        claim = first[0]
        expected_history = ["proposed", *targets[:cutoff_index]]
        assert claim["state_history"] == expected_history
        assert claim["current_state"] == expected_history[-1]
        assert claim["text"] == claim_text


@settings(max_examples=75, derandomize=True)
@given(premise_text=TEXT, dependent_text=TEXT)
def test_future_supersession_does_not_leak_into_historical_rebuild(
    premise_text: str,
    dependent_text: str,
) -> None:
    events = [
        _event(
            index=0,
            event_type="claim.proposed",
            subject_refs=[CLAIM],
            payload={"claim_text": premise_text},
        ),
        _event(
            index=1,
            event_type="claim.state_changed",
            subject_refs=[CLAIM],
            payload={"from_state": "proposed", "to_state": "supported"},
        ),
        _event(
            index=2,
            event_type="claim.proposed",
            subject_refs=[DEPENDENT],
            payload={"claim_text": dependent_text},
        ),
        _event(
            index=3,
            event_type="claim.state_changed",
            subject_refs=[DEPENDENT],
            payload={"from_state": "proposed", "to_state": "supported"},
        ),
        _event(
            index=4,
            event_type="relation.proposed",
            subject_refs=[RELATION, DEPENDENT, CLAIM],
            payload={
                "relation_id": RELATION,
                "relation_type": "DEPENDS_ON",
                "source_ref": DEPENDENT,
                "target_ref": CLAIM,
                "state": "active",
            },
        ),
        _event(
            index=5,
            event_type="claim.superseded",
            subject_refs=[CLAIM],
            payload={"from_state": "supported"},
        ),
    ]

    with TemporaryDirectory() as directory:
        root = _write_fixture(Path(directory) / "pack", list(reversed(events)))
        historical = _documents(root, cutoff=_timestamp(4))
        current = _documents(root)

        historical_by_id = {item["id"]: item for item in historical}
        current_by_id = {item["id"]: item for item in current}

        assert historical_by_id[CLAIM]["current_state"] == "supported"
        assert historical_by_id[DEPENDENT]["current_state"] == "supported"
        assert historical_by_id[RELATION]["current_state"] == "active"
        assert historical_by_id[CLAIM]["state_history"] == ["proposed", "supported"]
        assert historical_by_id[DEPENDENT]["state_history"] == ["proposed", "supported"]

        assert current_by_id[CLAIM]["current_state"] == "superseded"
        assert current_by_id[DEPENDENT]["current_state"] == "stale_pending_review"
        assert current_by_id[CLAIM]["state_history"] == [
            "proposed",
            "supported",
            "superseded",
        ]
        assert current_by_id[DEPENDENT]["state_history"] == [
            "proposed",
            "supported",
            "stale_pending_review",
        ]
