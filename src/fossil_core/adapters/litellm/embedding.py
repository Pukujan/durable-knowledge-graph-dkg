from __future__ import annotations

import json
import math
import socket
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ...services import ServiceMetadata


GEMINI_EMBEDDING_2_REQUESTED_MODEL = "gemini-embedding-2"
GEMINI_EMBEDDING_2_CANONICAL_MODEL = "google/gemini-embedding-2"
GEMINI_EMBEDDING_2_DIMENSION = 3072
GEMINI_EMBEDDING_2_ACCEPTED_ACTUAL_MODELS = frozenset(
    {
        GEMINI_EMBEDDING_2_REQUESTED_MODEL,
        GEMINI_EMBEDDING_2_CANONICAL_MODEL,
    }
)

JsonTransport = Callable[
    [str, Mapping[str, str], Mapping[str, Any], float],
    Mapping[str, Any],
]


class GeminiEmbedding2TransportError(RuntimeError):
    """Raised when the bounded embedding request cannot be completed."""


class GeminiEmbedding2ProtocolError(RuntimeError):
    """Raised when the embedding response violates the expected response contract."""


class GeminiEmbedding2IdentityError(GeminiEmbedding2ProtocolError):
    """Raised when reported model identity is missing or contradicts Gemini Embedding 2."""


def _post_json(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(16_000_001)
    except HTTPError as exc:
        raise GeminiEmbedding2TransportError(
            f"Gemini Embedding 2 request failed with HTTP status {exc.code}"
        ) from None
    except (URLError, TimeoutError, socket.timeout):
        raise GeminiEmbedding2TransportError("Gemini Embedding 2 request failed") from None

    if len(raw) > 16_000_000:
        raise GeminiEmbedding2ProtocolError(
            "Gemini Embedding 2 response exceeded the 16 MB bound"
        )
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise GeminiEmbedding2ProtocolError(
            "Gemini Embedding 2 response was not valid JSON"
        ) from None
    if not isinstance(decoded, Mapping):
        raise GeminiEmbedding2ProtocolError(
            "Gemini Embedding 2 response must be a JSON object"
        )
    return decoded


def _reported_model(payload: Mapping[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    values = [
        payload.get("model"),
        metadata.get("bridge_actual_model") if isinstance(metadata, Mapping) else None,
        metadata.get("actual_model") if isinstance(metadata, Mapping) else None,
    ]
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return None


def _reported_provider(payload: Mapping[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    values = [
        payload.get("provider"),
        metadata.get("bridge_actual_provider") if isinstance(metadata, Mapping) else None,
        metadata.get("actual_provider") if isinstance(metadata, Mapping) else None,
    ]
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return None


def _canonical_model(model: str) -> str:
    if model in GEMINI_EMBEDDING_2_ACCEPTED_ACTUAL_MODELS:
        return GEMINI_EMBEDDING_2_CANONICAL_MODEL
    return model


class GeminiEmbedding2Provider:
    """Bounded LiteLLM adapter for the approved Gemini Embedding 2 candidate lane.

    Each :meth:`embed` call is exactly one buffered `/v1/embeddings` request.
    The adapter never splits batches, retries, falls back, or switches models.
    An embedding-space identity must be tied to a caller-supplied projection ID,
    so a promoted model cannot silently reuse an incompatible vector projection.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        gateway_id: str,
        provider_version: str,
        projection_id: str,
        timeout_seconds: float,
        max_batch_size: int,
        max_chars_per_text: int,
        max_total_chars: int,
        transport: JsonTransport | None = None,
        implementation_version: str = "1",
        require_reported_actual_model: bool = True,
        estimated_cost_per_call_usd: float = 0.0,
    ) -> None:
        values = {
            "base_url": base_url,
            "api_key": api_key,
            "gateway_id": gateway_id,
            "provider_version": provider_version,
            "projection_id": projection_id,
            "implementation_version": implementation_version,
        }
        if any(not str(value).strip() for value in values.values()):
            raise ValueError(
                "Gemini Embedding 2 requires non-empty connection, identity, and projection values"
            )
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("Gemini Embedding 2 timeout_seconds must be in (0, 120]")
        if max_batch_size < 1 or max_batch_size > 64:
            raise ValueError("Gemini Embedding 2 max_batch_size must be in [1, 64]")
        if max_chars_per_text < 1 or max_chars_per_text > 100_000:
            raise ValueError(
                "Gemini Embedding 2 max_chars_per_text must be in [1, 100000]"
            )
        if max_total_chars < max_chars_per_text or max_total_chars > 1_000_000:
            raise ValueError(
                "Gemini Embedding 2 max_total_chars must be >= max_chars_per_text and <= 1000000"
            )
        if estimated_cost_per_call_usd < 0:
            raise ValueError("estimated_cost_per_call_usd must be non-negative")

        self.base_url = str(base_url).rstrip("/")
        self.api_key = str(api_key)
        self.gateway_id = str(gateway_id)
        self.provider_version = str(provider_version)
        self.projection_id = str(projection_id)
        self.timeout_seconds = float(timeout_seconds)
        self.max_batch_size = int(max_batch_size)
        self.max_chars_per_text = int(max_chars_per_text)
        self.max_total_chars = int(max_total_chars)
        self.transport = transport or _post_json
        self.implementation_version = str(implementation_version)
        self.require_reported_actual_model = bool(require_reported_actual_model)
        self.estimated_cost_per_call_usd = float(estimated_cost_per_call_usd)
        self._last_actual_model: str | None = None
        self._last_actual_provider: str | None = None
        self._last_usage: Mapping[str, Any] = {}

    @property
    def model_id(self) -> str:
        """Pinned requested model identity used to define the embedding space."""
        return GEMINI_EMBEDDING_2_REQUESTED_MODEL

    @property
    def embedding_space_id(self) -> str:
        return (
            f"{self.projection_id}:{GEMINI_EMBEDDING_2_CANONICAL_MODEL}:"
            f"{GEMINI_EMBEDDING_2_DIMENSION}"
        )

    @property
    def identity_verified(self) -> bool:
        return self._last_actual_model is not None

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="embedding",
            provider="litellm",
            provider_version=self.provider_version,
            implementation="litellm-gemini-embedding-2",
            implementation_version=self.implementation_version,
            model_id=self._last_actual_model or self.model_id,
            local=False,
            estimated_cost_per_call_usd=self.estimated_cost_per_call_usd,
            runtime={
                "gateway_id": self.gateway_id,
                "requested_model_id": self.model_id,
                "actual_model_id": self._last_actual_model or "unreported",
                "actual_provider": self._last_actual_provider or "unreported",
                "actual_model_verified": str(self.identity_verified).lower(),
                "require_reported_actual_model": str(
                    self.require_reported_actual_model
                ).lower(),
                "projection_id": self.projection_id,
                "embedding_space_id": self.embedding_space_id,
                "output_dimension": str(GEMINI_EMBEDDING_2_DIMENSION),
                "timeout_seconds": str(self.timeout_seconds),
                "max_batch_size": str(self.max_batch_size),
                "max_chars_per_text": str(self.max_chars_per_text),
                "max_total_chars": str(self.max_total_chars),
                "automatic_retries": "0",
                "fallback": "disabled",
                "dynamic_model_switching": "disabled",
                "projection_switching": "disabled",
                "request_granularity": "one-bounded-embedding-request-per-call",
                "batching_mode": "single-request-explicit-batch",
                "streaming_supported": "false",
                "streaming_required": "false",
                "response_mode": "buffered-json",
                "task_type": "not-exposed-by-openai-compatible-route",
                "last_usage": json.dumps(
                    dict(self._last_usage), sort_keys=True, separators=(",", ":")
                ),
            },
        ).as_dict()

    def _verify_identity(self, payload: Mapping[str, Any]) -> None:
        actual_model = _reported_model(payload)
        actual_provider = _reported_provider(payload)
        if actual_model is None:
            self._last_actual_model = None
            self._last_actual_provider = actual_provider
            if self.require_reported_actual_model:
                raise GeminiEmbedding2IdentityError(
                    "Gemini Embedding 2 response did not report actual model identity"
                )
            return
        if actual_model not in GEMINI_EMBEDDING_2_ACCEPTED_ACTUAL_MODELS:
            raise GeminiEmbedding2IdentityError(
                "Gemini Embedding 2 response reported an unaccepted actual model identity"
            )
        if (
            self._last_actual_model is not None
            and _canonical_model(self._last_actual_model) != _canonical_model(actual_model)
        ):
            raise GeminiEmbedding2IdentityError(
                "Gemini Embedding 2 actual model changed within one projection-bound provider"
            )
        self._last_actual_model = actual_model
        self._last_actual_provider = actual_provider

    def _validate_inputs(self, texts: list[str]) -> None:
        if len(texts) > self.max_batch_size:
            raise ValueError(
                "Gemini Embedding 2 batch exceeds the explicit max_batch_size request bound"
            )
        total_chars = 0
        for text in texts:
            if not isinstance(text, str) or not text:
                raise ValueError("Gemini Embedding 2 inputs must be non-empty strings")
            if len(text) > self.max_chars_per_text:
                raise ValueError(
                    "Gemini Embedding 2 input exceeds the explicit max_chars_per_text bound"
                )
            total_chars += len(text)
        if total_chars > self.max_total_chars:
            raise ValueError(
                "Gemini Embedding 2 batch exceeds the explicit max_total_chars bound"
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._validate_inputs(texts)
        payload = {
            "model": self.model_id,
            "input": list(texts),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = self.transport(
                f"{self.base_url}/embeddings",
                headers,
                payload,
                self.timeout_seconds,
            )
        except (GeminiEmbedding2TransportError, GeminiEmbedding2ProtocolError):
            raise
        except Exception:
            raise GeminiEmbedding2TransportError(
                "Gemini Embedding 2 transport failed"
            ) from None
        if not isinstance(response, Mapping):
            raise GeminiEmbedding2ProtocolError(
                "Gemini Embedding 2 response must be a mapping"
            )

        self._verify_identity(response)
        raw_data = response.get("data")
        if not isinstance(raw_data, list) or len(raw_data) != len(texts):
            raise GeminiEmbedding2ProtocolError(
                "Gemini Embedding 2 response count did not match the input count"
            )

        indexed: dict[int, list[float]] = {}
        for item in raw_data:
            if not isinstance(item, Mapping):
                raise GeminiEmbedding2ProtocolError(
                    "Gemini Embedding 2 response item must be a mapping"
                )
            index = item.get("index")
            if isinstance(index, bool) or not isinstance(index, int):
                raise GeminiEmbedding2ProtocolError(
                    "Gemini Embedding 2 response item index must be an integer"
                )
            if index < 0 or index >= len(texts) or index in indexed:
                raise GeminiEmbedding2ProtocolError(
                    "Gemini Embedding 2 response index was duplicate or outside input bounds"
                )
            raw_vector = item.get("embedding")
            if not isinstance(raw_vector, list) or len(raw_vector) != GEMINI_EMBEDDING_2_DIMENSION:
                raise GeminiEmbedding2ProtocolError(
                    "Gemini Embedding 2 response vector dimension was not 3072"
                )
            vector: list[float] = []
            for value in raw_vector:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise GeminiEmbedding2ProtocolError(
                        "Gemini Embedding 2 response vector contained a non-numeric value"
                    )
                converted = float(value)
                if not math.isfinite(converted):
                    raise GeminiEmbedding2ProtocolError(
                        "Gemini Embedding 2 response vector contained a non-finite value"
                    )
                vector.append(converted)
            indexed[index] = vector

        if set(indexed) != set(range(len(texts))):
            raise GeminiEmbedding2ProtocolError(
                "Gemini Embedding 2 response did not cover every input index exactly once"
            )

        usage = response.get("usage")
        self._last_usage = dict(usage) if isinstance(usage, Mapping) else {}
        return [indexed[index] for index in range(len(texts))]


__all__ = [
    "GEMINI_EMBEDDING_2_ACCEPTED_ACTUAL_MODELS",
    "GEMINI_EMBEDDING_2_CANONICAL_MODEL",
    "GEMINI_EMBEDDING_2_DIMENSION",
    "GEMINI_EMBEDDING_2_REQUESTED_MODEL",
    "GeminiEmbedding2IdentityError",
    "GeminiEmbedding2ProtocolError",
    "GeminiEmbedding2Provider",
    "GeminiEmbedding2TransportError",
]
