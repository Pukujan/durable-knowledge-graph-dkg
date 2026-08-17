from __future__ import annotations

import copy
from typing import Any, Mapping

import pytest

from fossil_core.adapters.litellm import (
    GEMINI_EMBEDDING_2_CANONICAL_MODEL,
    GEMINI_EMBEDDING_2_DIMENSION,
    GEMINI_EMBEDDING_2_REQUESTED_MODEL,
    GeminiEmbedding2IdentityError,
    GeminiEmbedding2ProtocolError,
    GeminiEmbedding2Provider,
    GeminiEmbedding2TransportError,
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


def _vector(seed: float = 0.0) -> list[float]:
    return [seed + (index / 10_000.0) for index in range(GEMINI_EMBEDDING_2_DIMENSION)]


def _provider(
    transport: RecordingTransport,
    *,
    require_reported_actual_model: bool = True,
    timeout_seconds: float = 12.0,
    max_batch_size: int = 8,
    max_chars_per_text: int = 100,
    max_total_chars: int = 400,
) -> GeminiEmbedding2Provider:
    return GeminiEmbedding2Provider(
        base_url="https://gateway.example/v1/",
        api_key="unit-test-secret",
        gateway_id="ckff-production",
        provider_version="proxy-contract-v1",
        projection_id="projection_gemini2_test_v1",
        timeout_seconds=timeout_seconds,
        max_batch_size=max_batch_size,
        max_chars_per_text=max_chars_per_text,
        max_total_chars=max_total_chars,
        transport=transport,
        implementation_version="workstream-d",
        require_reported_actual_model=require_reported_actual_model,
        estimated_cost_per_call_usd=0.001,
    )


def test_gemini_embedding2_makes_one_bounded_non_streaming_request_and_pins_projection_space():
    first = _vector(1.0)
    second = _vector(2.0)
    transport = RecordingTransport(
        {
            "model": GEMINI_EMBEDDING_2_CANONICAL_MODEL,
            "provider": "google",
            "data": [
                {"index": 1, "embedding": second},
                {"index": 0, "embedding": first},
            ],
            "usage": {"prompt_tokens": 7, "total_tokens": 7},
        }
    )
    provider = _provider(transport)

    vectors = provider.embed(["alpha", "beta"])

    assert vectors == [first, second]
    assert len(transport.calls) == 1
    url, headers, payload, timeout_seconds = transport.calls[0]
    assert url == "https://gateway.example/v1/embeddings"
    assert headers == {
        "Authorization": "Bearer unit-test-secret",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    assert payload == {
        "model": GEMINI_EMBEDDING_2_REQUESTED_MODEL,
        "input": ["alpha", "beta"],
    }
    assert "stream" not in payload
    assert timeout_seconds == 12.0

    assert provider.model_id == GEMINI_EMBEDDING_2_REQUESTED_MODEL
    assert provider.embedding_space_id == (
        "projection_gemini2_test_v1:google/gemini-embedding-2:3072"
    )

    metadata = provider.metadata()
    assert metadata["kind"] == "embedding"
    assert metadata["provider"] == "litellm"
    assert metadata["provider_version"] == "proxy-contract-v1"
    assert metadata["implementation"] == "litellm-gemini-embedding-2"
    assert metadata["implementation_version"] == "workstream-d"
    assert metadata["model_id"] == GEMINI_EMBEDDING_2_CANONICAL_MODEL
    assert metadata["local"] is False
    assert metadata["estimated_cost_per_call_usd"] == 0.001
    runtime = metadata["runtime"]
    assert runtime["gateway_id"] == "ckff-production"
    assert runtime["requested_model_id"] == GEMINI_EMBEDDING_2_REQUESTED_MODEL
    assert runtime["actual_model_id"] == GEMINI_EMBEDDING_2_CANONICAL_MODEL
    assert runtime["actual_provider"] == "google"
    assert runtime["actual_model_verified"] == "true"
    assert runtime["projection_id"] == "projection_gemini2_test_v1"
    assert runtime["embedding_space_id"] == provider.embedding_space_id
    assert runtime["output_dimension"] == "3072"
    assert runtime["timeout_seconds"] == "12.0"
    assert runtime["max_batch_size"] == "8"
    assert runtime["max_chars_per_text"] == "100"
    assert runtime["max_total_chars"] == "400"
    assert runtime["automatic_retries"] == "0"
    assert runtime["fallback"] == "disabled"
    assert runtime["dynamic_model_switching"] == "disabled"
    assert runtime["projection_switching"] == "disabled"
    assert runtime["request_granularity"] == "one-bounded-embedding-request-per-call"
    assert runtime["batching_mode"] == "single-request-explicit-batch"
    assert runtime["streaming_supported"] == "false"
    assert runtime["streaming_required"] == "false"
    assert runtime["response_mode"] == "buffered-json"
    assert runtime["task_type"] == "not-exposed-by-openai-compatible-route"
    assert runtime["last_usage"] == '{"prompt_tokens":7,"total_tokens":7}'
    assert "unit-test-secret" not in repr(metadata)


def test_gemini_embedding2_requires_reported_actual_identity_by_default():
    transport = RecordingTransport(
        {"data": [{"index": 0, "embedding": _vector()}]}
    )
    provider = _provider(transport)

    with pytest.raises(
        GeminiEmbedding2IdentityError,
        match="did not report actual model identity",
    ):
        provider.embed(["alpha"])

    assert len(transport.calls) == 1


def test_gemini_embedding2_rejects_unaccepted_model_identity_without_fallback():
    transport = RecordingTransport(
        {
            "model": "some-other-embedding-model",
            "data": [{"index": 0, "embedding": _vector()}],
        }
    )
    provider = _provider(transport)

    with pytest.raises(
        GeminiEmbedding2IdentityError,
        match="unaccepted actual model identity",
    ):
        provider.embed(["alpha"])

    assert len(transport.calls) == 1


def test_gemini_embedding2_accepts_only_known_aliases_for_the_same_canonical_space():
    responses = [
        {
            "model": GEMINI_EMBEDDING_2_REQUESTED_MODEL,
            "data": [{"index": 0, "embedding": _vector(1.0)}],
        },
        {
            "model": GEMINI_EMBEDDING_2_CANONICAL_MODEL,
            "data": [{"index": 0, "embedding": _vector(2.0)}],
        },
    ]

    class SequenceTransport(RecordingTransport):
        def __call__(self, url, headers, payload, timeout_seconds):
            self.response = responses[len(self.calls)]
            return super().__call__(url, headers, payload, timeout_seconds)

    transport = SequenceTransport()
    provider = _provider(transport)

    provider.embed(["document"])
    provider.embed(["query"])

    assert len(transport.calls) == 2
    assert provider.metadata()["runtime"]["actual_model_id"] == (
        GEMINI_EMBEDDING_2_CANONICAL_MODEL
    )


def test_gemini_embedding2_has_no_hidden_retry_on_transport_failure():
    transport = RecordingTransport(error=TimeoutError("simulated"))
    provider = _provider(transport, timeout_seconds=4.0)

    with pytest.raises(GeminiEmbedding2TransportError, match="transport failed"):
        provider.embed(["alpha"])

    assert len(transport.calls) == 1
    assert transport.calls[0][3] == 4.0


def test_gemini_embedding2_enforces_batch_and_input_bounds_before_execution():
    transport = RecordingTransport(
        {
            "model": GEMINI_EMBEDDING_2_CANONICAL_MODEL,
            "data": [{"index": 0, "embedding": _vector()}],
        }
    )
    provider = _provider(
        transport,
        max_batch_size=2,
        max_chars_per_text=5,
        max_total_chars=8,
    )

    with pytest.raises(ValueError, match="max_batch_size"):
        provider.embed(["a", "b", "c"])
    with pytest.raises(ValueError, match="max_chars_per_text"):
        provider.embed(["123456"])
    with pytest.raises(ValueError, match="max_total_chars"):
        provider.embed(["12345", "6789"])
    assert transport.calls == []

    with pytest.raises(ValueError, match="timeout_seconds"):
        _provider(transport, timeout_seconds=0.0)
    with pytest.raises(ValueError, match="max_batch_size"):
        _provider(transport, max_batch_size=65)


def test_gemini_embedding2_rejects_wrong_dimension_duplicate_index_and_nonfinite_values():
    wrong_dimension = RecordingTransport(
        {
            "model": GEMINI_EMBEDDING_2_CANONICAL_MODEL,
            "data": [{"index": 0, "embedding": [0.0, 1.0]}],
        }
    )
    with pytest.raises(GeminiEmbedding2ProtocolError, match="dimension"):
        _provider(wrong_dimension).embed(["alpha"])

    duplicate = RecordingTransport(
        {
            "model": GEMINI_EMBEDDING_2_CANONICAL_MODEL,
            "data": [
                {"index": 0, "embedding": _vector()},
                {"index": 0, "embedding": _vector(1.0)},
            ],
        }
    )
    with pytest.raises(GeminiEmbedding2ProtocolError, match="duplicate or outside"):
        _provider(duplicate).embed(["alpha", "beta"])

    nonfinite = _vector()
    nonfinite[42] = float("nan")
    invalid = RecordingTransport(
        {
            "model": GEMINI_EMBEDDING_2_CANONICAL_MODEL,
            "data": [{"index": 0, "embedding": nonfinite}],
        }
    )
    with pytest.raises(GeminiEmbedding2ProtocolError, match="non-finite"):
        _provider(invalid).embed(["alpha"])


def test_gemini_embedding2_empty_batch_is_local_noop_with_no_network_request():
    transport = RecordingTransport()
    provider = _provider(transport)

    assert provider.embed([]) == []
    assert transport.calls == []
