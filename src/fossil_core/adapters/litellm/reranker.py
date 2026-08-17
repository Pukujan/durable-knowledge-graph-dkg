from __future__ import annotations

import copy
import json
import socket
from collections.abc import Callable, Iterable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ...services import ServiceMetadata


JsonTransport = Callable[
    [str, Mapping[str, str], Mapping[str, Any], float],
    Mapping[str, Any],
]


class LiteLLMRerankerTransportError(RuntimeError):
    """Raised when the bounded rerank request cannot be completed."""


class LiteLLMRerankerProtocolError(RuntimeError):
    """Raised when the rerank response cannot be mapped to candidate ordering."""


class LiteLLMRerankerIdentityError(LiteLLMRerankerProtocolError):
    """Raised when a reported actual model contradicts the requested route identity."""


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
            raw = response.read(2_000_001)
    except HTTPError as exc:
        raise LiteLLMRerankerTransportError(
            f"LiteLLM rerank request failed with HTTP status {exc.code}"
        ) from None
    except (URLError, TimeoutError, socket.timeout):
        raise LiteLLMRerankerTransportError("LiteLLM rerank request failed") from None

    if len(raw) > 2_000_000:
        raise LiteLLMRerankerProtocolError("LiteLLM rerank response exceeded the 2 MB bound")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise LiteLLMRerankerProtocolError("LiteLLM rerank response was not valid JSON") from None
    if not isinstance(decoded, Mapping):
        raise LiteLLMRerankerProtocolError("LiteLLM rerank response must be a JSON object")
    return decoded


def _reported_model(payload: Mapping[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    meta = payload.get("meta")
    values = [
        payload.get("model"),
        metadata.get("bridge_actual_model") if isinstance(metadata, Mapping) else None,
        metadata.get("actual_model") if isinstance(metadata, Mapping) else None,
        meta.get("model") if isinstance(meta, Mapping) else None,
        meta.get("actual_model") if isinstance(meta, Mapping) else None,
    ]
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return None


def _reported_provider(payload: Mapping[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    meta = payload.get("meta")
    values = [
        payload.get("provider"),
        metadata.get("bridge_actual_provider") if isinstance(metadata, Mapping) else None,
        metadata.get("actual_provider") if isinstance(metadata, Mapping) else None,
        meta.get("provider") if isinstance(meta, Mapping) else None,
    ]
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return None


class LiteLLMReranker:
    """One-request, bounded adapter for LiteLLM's non-streaming ``/v1/rerank`` lane.

    Rerank scores are candidate-ordering evidence only. The adapter performs no
    retries, fallback, model substitution, truth mutation, or tool execution.
    The rerank endpoint used by the currently verified gateway is a buffered
    JSON API rather than a streaming model surface; that is recorded explicitly
    in service metadata instead of being left as an implicit transport default.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        gateway_id: str,
        provider_version: str,
        timeout_seconds: float,
        max_candidates: int,
        accepted_actual_models: Iterable[str] = (),
        require_reported_actual_model: bool = False,
        transport: JsonTransport | None = None,
        implementation_version: str = "1",
    ) -> None:
        values = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "gateway_id": gateway_id,
            "provider_version": provider_version,
            "implementation_version": implementation_version,
        }
        if any(not str(value).strip() for value in values.values()):
            raise ValueError("LiteLLM reranker requires non-empty connection and identity values")
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValueError("LiteLLM reranker timeout_seconds must be in (0, 120]")
        if max_candidates < 1 or max_candidates > 256:
            raise ValueError("LiteLLM reranker max_candidates must be in [1, 256]")

        self.base_url = str(base_url).rstrip("/")
        self.api_key = str(api_key)
        self.model = str(model)
        self.gateway_id = str(gateway_id)
        self.provider_version = str(provider_version)
        self.timeout_seconds = float(timeout_seconds)
        self.max_candidates = int(max_candidates)
        self.require_reported_actual_model = bool(require_reported_actual_model)
        self.implementation_version = str(implementation_version)
        self.transport = transport or _post_json
        self.accepted_actual_models = {self.model, *[str(item) for item in accepted_actual_models]}
        self._last_actual_model: str | None = None
        self._last_actual_provider: str | None = None

    @property
    def identity_verified(self) -> bool:
        return self._last_actual_model is not None

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="reranker",
            provider="litellm",
            provider_version=self.provider_version,
            implementation="litellm-rerank-api",
            implementation_version=self.implementation_version,
            model_id=self._last_actual_model,
            local=False,
            estimated_cost_per_call_usd=0.0,
            runtime={
                "gateway_id": self.gateway_id,
                "requested_model_id": self.model,
                "actual_model_id": self._last_actual_model or "unreported",
                "actual_provider": self._last_actual_provider or "unreported",
                "actual_model_verified": str(self.identity_verified).lower(),
                "require_reported_actual_model": str(
                    self.require_reported_actual_model
                ).lower(),
                "timeout_seconds": str(self.timeout_seconds),
                "max_candidates": str(self.max_candidates),
                "automatic_retries": "0",
                "fallback": "disabled",
                "request_granularity": "one-bounded-rerank-request-per-call",
                "streaming_supported": "false",
                "streaming_required": "false",
                "response_mode": "buffered-json",
                "score_authority": "candidate-ordering-only",
            },
        ).as_dict()

    def _response_identity(self, payload: Mapping[str, Any]) -> None:
        actual_model = _reported_model(payload)
        actual_provider = _reported_provider(payload)
        if actual_model is None:
            self._last_actual_model = None
            self._last_actual_provider = actual_provider
            if self.require_reported_actual_model:
                raise LiteLLMRerankerIdentityError(
                    "LiteLLM rerank response did not report actual model identity"
                )
            return
        if actual_model not in self.accepted_actual_models:
            raise LiteLLMRerankerIdentityError(
                "LiteLLM rerank response reported an unaccepted actual model identity"
            )
        self._last_actual_model = actual_model
        self._last_actual_provider = actual_provider

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if not str(query).strip():
            raise ValueError("rerank query must be non-empty")
        if not candidates:
            return []
        if len(candidates) > self.max_candidates:
            raise ValueError(
                "rerank candidate count exceeds the explicit max_candidates request bound"
            )

        documents: list[str] = []
        for candidate in candidates:
            if not candidate.get("id"):
                raise ValueError("rerank candidates require stable id")
            if not isinstance(candidate.get("text"), str):
                raise ValueError("rerank candidates require string text")
            documents.append(str(candidate["text"]))

        top_n = min(int(limit), len(candidates))
        payload = {
            "model": self.model,
            "query": str(query),
            "documents": documents,
            "top_n": top_n,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = self.transport(
                f"{self.base_url}/rerank",
                headers,
                payload,
                self.timeout_seconds,
            )
        except (LiteLLMRerankerTransportError, LiteLLMRerankerProtocolError):
            raise
        except Exception:
            raise LiteLLMRerankerTransportError("LiteLLM rerank transport failed") from None
        if not isinstance(response, Mapping):
            raise LiteLLMRerankerProtocolError("LiteLLM rerank response must be a mapping")

        self._response_identity(response)
        rows = response.get("results") or response.get("data")
        if not isinstance(rows, list) or not rows:
            raise LiteLLMRerankerProtocolError("LiteLLM rerank response contained no ranking rows")
        if len(rows) > top_n:
            raise LiteLLMRerankerProtocolError(
                "LiteLLM rerank response exceeded the requested top_n bound"
            )

        seen_indices: set[int] = set()
        parsed: list[tuple[int, float]] = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise LiteLLMRerankerProtocolError("LiteLLM rerank row must be a mapping")
            index = row.get("index")
            if isinstance(index, bool) or not isinstance(index, int):
                raise LiteLLMRerankerProtocolError("LiteLLM rerank row index must be an integer")
            if index < 0 or index >= len(candidates) or index in seen_indices:
                raise LiteLLMRerankerProtocolError(
                    "LiteLLM rerank row index was duplicate or outside candidate bounds"
                )
            raw_score = row.get("relevance_score", row.get("score"))
            if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
                raise LiteLLMRerankerProtocolError(
                    "LiteLLM rerank row requires numeric relevance_score or score"
                )
            seen_indices.add(index)
            parsed.append((index, float(raw_score)))

        service = self.metadata()
        reranked: list[dict[str, Any]] = []
        for api_rank, (index, score) in enumerate(parsed, start=1):
            candidate = candidates[index]
            retrieval = candidate.get("retrieval")
            retrieval_mapping = dict(retrieval) if isinstance(retrieval, Mapping) else {}
            base_rank = int(retrieval_mapping.get("rank", index + 1))
            result = copy.deepcopy(candidate)
            result["rerank"] = {
                "base_rank": base_rank,
                "score": score,
                "api_rank": api_rank,
                "service": service,
            }
            reranked.append(result)
        return reranked


__all__ = [
    "LiteLLMReranker",
    "LiteLLMRerankerIdentityError",
    "LiteLLMRerankerProtocolError",
    "LiteLLMRerankerTransportError",
]
