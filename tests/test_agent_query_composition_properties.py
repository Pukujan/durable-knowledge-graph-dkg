from __future__ import annotations

import string

import pytest
from hypothesis import given, settings, strategies as st

from fossil_core.agent import AgentContext, CorpusService
from fossil_core.pack import PackAccess, PackBoundaryError


PACK_ID = st.text(
    alphabet=string.ascii_lowercase + string.digits,
    min_size=16,
    max_size=24,
).map(lambda suffix: f"pack_{suffix}")


class AllowingSkills:
    def require_capability(self, skill_id: str, capability: str) -> dict[str, str]:
        assert skill_id == "skill_corpus-search"
        assert capability in {"search", "context"}
        return {"version": "1.0.0"}


class RecordingRetriever:
    def __init__(self, *, leak_pack_id: str | None = None):
        self.leak_pack_id = leak_pack_id
        self.seen_pack_ids: list[str] | None = None

    def search(self, query: str, *, pack_ids: list[str], limit: int = 20):
        del query, limit
        self.seen_pack_ids = list(pack_ids)
        results = [
            {"id": f"doc_{index}", "pack_id": pack_id, "text": "generated scoped result"}
            for index, pack_id in enumerate(pack_ids)
        ]
        if self.leak_pack_id is not None:
            results.append(
                {
                    "id": "doc_leaked",
                    "pack_id": self.leak_pack_id,
                    "text": "generated leaked result",
                }
            )
        return results


class RecordingContextProvider:
    def __init__(self, *, leak_pack_id: str | None = None):
        self.leak_pack_id = leak_pack_id
        self.requests: list[dict] = []

    def build_context(self, request: dict):
        self.requests.append(dict(request))
        pack_ids = list(request["pack_ids"])
        items = [
            {"id": f"ctx_{index}", "pack_id": pack_id, "text": "generated scoped context"}
            for index, pack_id in enumerate(pack_ids)
        ]
        if self.leak_pack_id is not None:
            items.append(
                {
                    "id": "ctx_leaked",
                    "pack_id": self.leak_pack_id,
                    "text": "generated leaked context",
                }
            )
        return {
            "query": request.get("query", ""),
            "items": items,
            "context_text": "generated context",
        }


def agent_context() -> AgentContext:
    return AgentContext(
        actor_id="property-agent",
        model_id="property-model",
        harness_version="property-harness",
        skill_id="skill_corpus-search",
        skill_version="1.0.0",
    )


@st.composite
def access_cases(draw):
    mounts = draw(st.lists(PACK_ID, min_size=1, max_size=5, unique=True))
    mounted = frozenset(mounts)
    unmounted = draw(PACK_ID.filter(lambda pack_id: pack_id not in mounted))
    requested = draw(
        st.sets(st.sampled_from(mounts), min_size=1, max_size=len(mounts))
    )
    return mounted, unmounted, frozenset(requested)


def service(*, retriever=None, context_provider=None) -> CorpusService:
    return CorpusService(
        event_store=object(),
        skills=AllowingSkills(),
        retriever=retriever,
        context_provider=context_provider,
    )


@settings(max_examples=150, derandomize=True)
@given(case=access_cases())
def test_rich_search_scope_is_exactly_the_read_mount_set(case) -> None:
    mounts, unmounted, _requested = case
    access = PackAccess(
        pack_id=sorted(mounts)[0],
        read_mounts=mounts,
        write_targets=frozenset(),
    )
    retriever = RecordingRetriever()

    results = service(retriever=retriever).search(
        "generated query",
        access=access,
        context=agent_context(),
        limit=100,
    )

    assert retriever.seen_pack_ids == sorted(mounts)
    assert {item["pack_id"] for item in results} == set(mounts)

    leaky = RecordingRetriever(leak_pack_id=unmounted)
    with pytest.raises(PackBoundaryError, match="crossed query boundary"):
        service(retriever=leaky).search(
            "generated query",
            access=access,
            context=agent_context(),
            limit=100,
        )


@settings(max_examples=150, derandomize=True)
@given(case=access_cases())
def test_context_scope_can_narrow_but_never_widen(case) -> None:
    mounts, unmounted, requested = case
    access = PackAccess(
        pack_id=sorted(mounts)[0],
        read_mounts=mounts,
        write_targets=frozenset(),
    )
    provider = RecordingContextProvider()
    requested_list = sorted(requested)

    result = service(context_provider=provider).context(
        {"query": "generated query", "pack_ids": requested_list},
        access=access,
        context=agent_context(),
    )

    assert provider.requests[-1]["pack_ids"] == requested_list
    assert result["pack_ids"] == requested_list
    assert {item["pack_id"] for item in result["items"]} == set(requested)
    assert set(result["pack_ids"]) <= set(mounts)

    before = len(provider.requests)
    with pytest.raises(PackBoundaryError, match="not mounted for reading"):
        service(context_provider=provider).context(
            {"query": "generated query", "pack_ids": [unmounted]},
            access=access,
            context=agent_context(),
        )
    assert len(provider.requests) == before

    leaky = RecordingContextProvider(leak_pack_id=unmounted)
    with pytest.raises(PackBoundaryError, match="crossed query boundary"):
        service(context_provider=leaky).context(
            {"query": "generated query", "pack_ids": requested_list},
            access=access,
            context=agent_context(),
        )


@settings(max_examples=100, derandomize=True)
@given(case=access_cases())
def test_context_defaults_to_all_read_mounts_without_explicit_scope(case) -> None:
    mounts, _unmounted, _requested = case
    access = PackAccess(
        pack_id=sorted(mounts)[0],
        read_mounts=mounts,
        write_targets=frozenset(),
    )
    provider = RecordingContextProvider()

    result = service(context_provider=provider).context(
        {"query": "generated query"},
        access=access,
        context=agent_context(),
    )

    assert provider.requests[-1]["pack_ids"] == sorted(mounts)
    assert result["pack_ids"] == sorted(mounts)
    assert {item["pack_id"] for item in result["items"]} == set(mounts)
