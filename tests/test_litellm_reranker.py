from __future__ import annotations

import copy
from typing import Any, Mapping

import pytest

from fossil_core.adapters.litellm import (
    LiteLLMReranker,
    LiteLLMRerankerIdentityError,
    LiteLLMRerankerProtocolError,
    LiteLLMRerankerTransportError,
)


class RecordingTransport:
    def __init__(
        self,
        response: Mapping[str, Any] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = dict(response or {})
        self.error = error
        self.calls: list[tuple[str, dict[str, str], dict[str, Any], float]] = []

    def __call__(
        self,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        self.calls.append(
            (
                str(url),
                dict(headers),
                copy.deepcopy(dict(payload)),
                float(timeout_seconds),
            )
        )
        if self.error is not None:
            raise self.error
        return copy.deepcopy(self.response)


def _reranker(
    transport: RecordingTransport,
    *,
    accepted_actual_models: tuple[str, ...] = (),
    require_reported_actual_model: bool = False,
    timeout_seconds: float = 7.5,
    max_candidates: int = 8,
) -> LiteLLMReranker:
    return LiteLLMReranker(
        base_url="https://gateway.example/v1/",
        api_key="unit-test-secret",
        model="rerank-v4-pro",
        gateway_id="ckff-production",
        provider_version="proxy-contract-v1",
        timeout_seconds=timeout_seconds,
        max_candidates=max_candidates,
        accepted_actual_models=accepted_actual_models,
        require_reported_actual_model=require_reported_actual_model,
        transport=transport,
        implementation_version="workstream-d",
    )


def _candidates() -> list[dict[str, Any]]:
    return [
        {
            "id": "claim_alpha",
            "pack_id": "pack_test",
            "text": "alpha evidence",
            "retrieval": {"rank": 1, "score": 0.7},
            "extra": ("preserve", "tuple"),
        },
        {
            "id": "claim_beta",
            "pack_id": "pack_test",
            "text": "beta evidence",
            "retrieval": {"rank": 2, "score": 0.6},
        },
        {
            "id": "claim_gamma",
            "pack_id": "pack_test",
            "text": "gamma evidence",
            "retrieval": {"rank": 3, "score": 0.5},
        },
    ]


def test_hosted_reranker_makes_one_bounded_non_streaming_request_and_preserves_candidates():
    transport = RecordingTransport(
        {
            "model": "rerank-v4-pro",
            "provider": "cohere",
            "results": [
                {"index": 1, "relevance_score": 0.99},
                {"index": 0, "relevance_score": 0.75},
            ],
        }
    )
    reranker = _reranker(transport)
    candidates = _candidates()
    original = copy.deepcopy(candidates)

    results = reranker.rerank("which evidence is strongest?", candidates, limit=2)

    assert [item["id"] for item in results] == ["claim_beta", "claim_alpha"]
    assert results[0]["rerank"]["base_rank"] == 2
    assert results[0]["rerank"]["api_rank"] == 1
    assert results[0]["rerank"]["score"] == 0.99
    assert results[1]["extra"] == ("preserve", "tuple")
    assert candidates == original

    assert len(transport.calls) == 1
    url, headers, payload, timeout_seconds = transport.calls[0]
    assert url == "https://gateway.example/v1/rerank"
    assert headers == {
        "Authorization": "Bearer unit-test-secret",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    assert payload == {
        "model": "rerank-v4-pro",
        "query": "which evidence is strongest?",
        "documents": ["alpha evidence", "beta evidence", "gamma evidence"],
        "top_n": 2,
    }
    assert "stream" not in payload
    assert timeout_seconds == 7.5

    metadata = results[0]["rerank"]["service"]
    assert metadata["kind"] == "reranker"
    assert metadata["provider"] == "litellm"
    assert metadata["provider_version"] == "proxy-contract-v1"
    assert metadata["implementation"] == "litellm-rerank-api"
    assert metadata["implementation_version"] == "workstream-d"
    assert metadata["model_id"] == "rerank-v4-pro"
    assert metadata["local"] is False
    assert metadata["runtime"]["gateway_id"] == "ckff-production"
    assert metadata["runtime"]["requested_model_id"] == "rerank-v4-pro"
    assert metadata["runtime"]["actual_model_id"] == "rerank-v4-pro"
    assert metadata["runtime"]["actual_provider"] == "cohere"
    assert metadata["runtime"]["actual_model_verified"] == "true"
    assert metadata["runtime"]["timeout_seconds"] == "7.5"
    assert metadata["runtime"]["max_candidates"] == "8"
    assert metadata["runtime"]["automatic_retries"] == "0"
    assert metadata["runtime"]["fallback"] == "disabled"
    assert metadata["runtime"]["request_granularity"] == (
        "one-bounded-rerank-request-per-call"
    )
    assert metadata["runtime"]["streaming_supported"] == "false"
    assert metadata["runtime"]["streaming_required"] == "false"
    assert metadata["runtime"]["response_mode"] == "buffered-json"
    assert metadata["runtime"]["score_authority"] == "candidate-ordering-only"
    assert "unit-test-secret" not in repr(metadata)


def test_hosted_reranker_records_unreported_actual_identity_without_inventing_it():
    transport = RecordingTransport(
        {
            "results": [
                {"index": 0, "relevance_score": 0.9},
            ]
        }
    )
    reranker = _reranker(transport)

    results = reranker.rerank("alpha?", _candidates(), limit=1)
    metadata = results[0]["rerank"]["service"]

    assert metadata["model_id"] is None
    assert metadata["runtime"]["requested_model_id"] == "rerank-v4-pro"
    assert metadata["runtime"]["actual_model_id"] == "unreported"
    assert metadata["runtime"]["actual_provider"] == "unreported"
    assert metadata["runtime"]["actual_model_verified"] == "false"


def test_hosted_reranker_can_require_reported_actual_identity_for_promotion_grade_runs():
    transport = RecordingTransport(
        {
            "results": [
                {"index": 0, "relevance_score": 0.9},
            ]
        }
    )
    reranker = _reranker(transport, require_reported_actual_model=True)

    with pytest.raises(
        LiteLLMRerankerIdentityError,
        match="did not report actual model identity",
    ):
        reranker.rerank("alpha?", _candidates(), limit=1)

    assert len(transport.calls) == 1


def test_hosted_reranker_accepts_only_explicitly_allowlisted_actual_model_aliases():
    accepted = RecordingTransport(
        {
            "metadata": {
                "bridge_actual_model": "cohere/rerank-v4-pro",
                "bridge_actual_provider": "cohere",
            },
            "results": [
                {"index": 2, "relevance_score": 0.93},
            ],
        }
    )
    reranker = _reranker(
        accepted,
        accepted_actual_models=("cohere/rerank-v4-pro",),
        require_reported_actual_model=True,
    )

    result = reranker.rerank("gamma?", _candidates(), limit=1)[0]

    assert result["id"] == "claim_gamma"
    assert result["rerank"]["service"]["model_id"] == "cohere/rerank-v4-pro"
    assert result["rerank"]["service"]["runtime"]["actual_provider"] == "cohere"

    rejected = RecordingTransport(
        {
            "model": "unexpected-reranker",
            "results": [
                {"index": 0, "relevance_score": 0.8},
            ],
        }
    )
    reranker = _reranker(rejected)
    with pytest.raises(
        LiteLLMRerankerIdentityError,
        match="unaccepted actual model identity",
    ):
        reranker.rerank("alpha?", _candidates(), limit=1)
    assert len(rejected.calls) == 1


def test_hosted_reranker_has_no_hidden_retry_or_fallback_on_transport_failure():
    transport = RecordingTransport(error=TimeoutError("simulated"))
    reranker = _reranker(transport, timeout_seconds=3.0)

    with pytest.raises(LiteLLMRerankerTransportError, match="transport failed"):
        reranker.rerank("alpha?", _candidates(), limit=1)

    assert len(transport.calls) == 1
    assert transport.calls[0][3] == 3.0


def test_hosted_reranker_enforces_candidate_and_timeout_bounds_before_execution():
    transport = RecordingTransport(
        {"results": [{"index": 0, "relevance_score": 1.0}]}
    )
    reranker = _reranker(transport, max_candidates=2)

    with pytest.raises(ValueError, match="max_candidates"):
        reranker.rerank("query", _candidates(), limit=1)
    assert transport.calls == []

    with pytest.raises(ValueError, match="timeout_seconds"):
        _reranker(transport, timeout_seconds=0.0)
    with pytest.raises(ValueError, match="timeout_seconds"):
        _reranker(transport, timeout_seconds=121.0)


def test_hosted_reranker_rejects_malformed_or_overbroad_ranking_rows():
    duplicate = RecordingTransport(
        {
            "results": [
                {"index": 0, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.8},
            ]
        }
    )
    with pytest.raises(LiteLLMRerankerProtocolError, match="duplicate or outside"):
        _reranker(duplicate).rerank("query", _candidates(), limit=2)

    non_numeric = RecordingTransport(
        {
            "results": [
                {"index": 0, "relevance_score": "high"},
            ]
        }
    )
    with pytest.raises(LiteLLMRerankerProtocolError, match="numeric"):
        _reranker(non_numeric).rerank("query", _candidates(), limit=1)

    too_many = RecordingTransport(
        {
            "results": [
                {"index": 0, "relevance_score": 0.9},
                {"index": 1, "relevance_score": 0.8},
            ]
        }
    )
    with pytest.raises(LiteLLMRerankerProtocolError, match="top_n"):
        _reranker(too_many).rerank("query", _candidates(), limit=1)
