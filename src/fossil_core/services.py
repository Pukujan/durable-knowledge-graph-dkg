from __future__ import annotations

import copy
import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class ServiceMetadata:
    """Version/provenance metadata shared by replaceable cognitive services."""

    kind: str
    provider: str
    provider_version: str
    implementation: str
    implementation_version: str
    model_id: str | None = None
    local: bool = True
    estimated_cost_per_call_usd: float = 0.0
    runtime: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "provider": self.provider,
            "provider_version": self.provider_version,
            "implementation": self.implementation,
            "implementation_version": self.implementation_version,
            "model_id": self.model_id,
            "local": self.local,
            "estimated_cost_per_call_usd": self.estimated_cost_per_call_usd,
            "runtime": dict(self.runtime),
        }


class BM25Retriever:
    """Small dependency-free lexical baseline used to make retrieval measurable."""

    def __init__(
        self,
        documents: Iterable[Mapping[str, Any]],
        *,
        k1: float = 1.5,
        b: float = 0.75,
        version: str = "1",
    ) -> None:
        self.documents = [copy.deepcopy(dict(document)) for document in documents]
        self.k1 = float(k1)
        self.b = float(b)
        self.version = version
        if self.k1 <= 0 or not 0 <= self.b <= 1:
            raise ValueError("BM25 requires k1 > 0 and 0 <= b <= 1")
        for document in self.documents:
            if not document.get("id") or not document.get("pack_id"):
                raise ValueError("retrieval documents require id and pack_id")
            if not isinstance(document.get("text"), str):
                raise ValueError("retrieval documents require string text")

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="retriever",
            provider="fossil",
            provider_version="1",
            implementation="bm25",
            implementation_version=self.version,
            model_id=None,
            local=True,
            estimated_cost_per_call_usd=0.0,
        ).as_dict()

    def search(
        self,
        query: str,
        *,
        pack_ids: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_terms = tokenize(query)
        if not query_terms:
            return []
        allowed = set(pack_ids)
        eligible = [doc for doc in self.documents if doc["pack_id"] in allowed]
        if not eligible:
            return []

        tokenized = {doc["id"]: tokenize(doc["text"]) for doc in eligible}
        lengths = [len(tokens) for tokens in tokenized.values()]
        avgdl = sum(lengths) / len(lengths) if lengths else 1.0
        avgdl = avgdl or 1.0
        document_count = len(eligible)
        scores: list[tuple[float, dict[str, Any]]] = []

        for document in eligible:
            tokens = tokenized[document["id"]]
            term_counts: dict[str, int] = {}
            for token in tokens:
                term_counts[token] = term_counts.get(token, 0) + 1
            score = 0.0
            for term in query_terms:
                df = sum(1 for values in tokenized.values() if term in values)
                if df == 0:
                    continue
                idf = math.log(1.0 + (document_count - df + 0.5) / (df + 0.5))
                tf = term_counts.get(term, 0)
                if tf == 0:
                    continue
                denominator = tf + self.k1 * (
                    1.0 - self.b + self.b * len(tokens) / avgdl
                )
                score += idf * (tf * (self.k1 + 1.0)) / denominator
            if score > 0:
                scores.append((score, document))

        scores.sort(key=lambda item: (-item[0], str(item[1]["id"])))
        results: list[dict[str, Any]] = []
        for rank, (score, document) in enumerate(scores[:limit], start=1):
            result = copy.deepcopy(document)
            result["retrieval"] = {
                "score": score,
                "rank": rank,
                "service": self.metadata(),
            }
            results.append(result)
        return results


class HashEmbeddingProvider:
    """Deterministic local hashing baseline; useful as a control, not semantic truth."""

    def __init__(self, *, dimension: int = 128, version: str = "1") -> None:
        if dimension < 8:
            raise ValueError("embedding dimension must be at least 8")
        self.dimension = int(dimension)
        self.version = version

    @property
    def model_id(self) -> str:
        return f"fossil-hash-embedding-{self.dimension}-v{self.version}"

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="embedding",
            provider="fossil",
            provider_version="1",
            implementation="signed-token-hash",
            implementation_version=self.version,
            model_id=self.model_id,
            local=True,
            estimated_cost_per_call_usd=0.0,
        ).as_dict()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            for token in tokenize(text):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:8], "big") % self.dimension
                sign = 1.0 if digest[8] & 1 else -1.0
                vector[index] += sign
            norm = math.sqrt(sum(value * value for value in vector))
            if norm:
                vector = [value / norm for value in vector]
            vectors.append(vector)
        return vectors


class EmbeddingRetriever:
    """In-memory cosine baseline over any `EmbeddingProvider` implementation."""

    def __init__(
        self,
        documents: Iterable[Mapping[str, Any]],
        embedder: Any,
        *,
        version: str = "1",
    ) -> None:
        self.documents = [copy.deepcopy(dict(document)) for document in documents]
        self.embedder = embedder
        self.version = version
        for document in self.documents:
            if not document.get("id") or not document.get("pack_id"):
                raise ValueError("retrieval documents require id and pack_id")
            if not isinstance(document.get("text"), str):
                raise ValueError("retrieval documents require string text")
        self._vectors = self.embedder.embed([doc["text"] for doc in self.documents])

    def metadata(self) -> dict[str, Any]:
        embedder_metadata = self.embedder.metadata()
        return ServiceMetadata(
            kind="retriever",
            provider="fossil",
            provider_version="1",
            implementation="in-memory-cosine",
            implementation_version=self.version,
            model_id=str(embedder_metadata.get("model_id")),
            local=bool(embedder_metadata.get("local", True)),
            estimated_cost_per_call_usd=float(
                embedder_metadata.get("estimated_cost_per_call_usd", 0.0)
            ),
            runtime={"embedding_provider": str(embedder_metadata.get("provider"))},
        ).as_dict()

    def search(
        self,
        query: str,
        *,
        pack_ids: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_vector = self.embedder.embed([query])[0]
        if not any(query_vector):
            return []
        allowed = set(pack_ids)
        scored: list[tuple[float, dict[str, Any]]] = []
        for document, vector in zip(self.documents, self._vectors, strict=True):
            if document["pack_id"] not in allowed:
                continue
            score = sum(left * right for left, right in zip(query_vector, vector, strict=True))
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], str(item[1]["id"])))
        results: list[dict[str, Any]] = []
        for rank, (score, document) in enumerate(scored[:limit], start=1):
            result = copy.deepcopy(document)
            result["retrieval"] = {
                "score": score,
                "rank": rank,
                "service": self.metadata(),
            }
            results.append(result)
        return results


class TokenOverlapReranker:
    def __init__(self, *, version: str = "1") -> None:
        self.version = version

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="reranker",
            provider="fossil",
            provider_version="1",
            implementation="token-overlap",
            implementation_version=self.version,
            local=True,
            estimated_cost_per_call_usd=0.0,
        ).as_dict()

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_terms = set(tokenize(query))
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for candidate in candidates:
            terms = set(tokenize(str(candidate.get("text", ""))))
            overlap = len(query_terms & terms) / max(len(query_terms), 1)
            result = copy.deepcopy(candidate)
            result["rerank"] = {
                "score": overlap,
                "service": self.metadata(),
            }
            scored.append((overlap, str(candidate.get("id", "")), result))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:limit]]


class BudgetedContextProvider:
    """Retrieval + optional reranking with an explicit character budget."""

    def __init__(
        self,
        retriever: Any,
        *,
        reranker: Any | None = None,
        max_chars: int = 8_000,
        version: str = "1",
    ) -> None:
        if max_chars < 1:
            raise ValueError("max_chars must be positive")
        self.retriever = retriever
        self.reranker = reranker
        self.max_chars = int(max_chars)
        self.version = version

    def metadata(self) -> dict[str, Any]:
        runtime = {"retriever": str(self.retriever.metadata().get("implementation"))}
        if self.reranker is not None:
            runtime["reranker"] = str(self.reranker.metadata().get("implementation"))
        return ServiceMetadata(
            kind="context",
            provider="fossil",
            provider_version="1",
            implementation="budgeted-retrieval-context",
            implementation_version=self.version,
            local=bool(self.retriever.metadata().get("local", True)),
            estimated_cost_per_call_usd=float(
                self.retriever.metadata().get("estimated_cost_per_call_usd", 0.0)
            ),
            runtime=runtime,
        ).as_dict()

    def build_context(self, request: dict[str, Any]) -> dict[str, Any]:
        query = str(request["query"])
        pack_ids = [str(item) for item in request["pack_ids"]]
        limit = int(request.get("limit", 8))
        candidates = self.retriever.search(
            query,
            pack_ids=pack_ids,
            limit=max(limit * 3, limit),
        )
        if self.reranker is not None and candidates:
            candidates = self.reranker.rerank(query, candidates, limit=limit)
        else:
            candidates = candidates[:limit]

        selected: list[dict[str, Any]] = []
        used = 0
        chunks: list[str] = []
        for candidate in candidates:
            text = str(candidate.get("text", ""))
            separator = "\n\n" if chunks else ""
            remaining = self.max_chars - used - len(separator)
            if remaining <= 0:
                break
            included = text[:remaining]
            if not included:
                break
            result = copy.deepcopy(candidate)
            result["context_text"] = included
            result["context_truncated"] = len(included) < len(text)
            selected.append(result)
            chunks.append(separator + included)
            used += len(separator) + len(included)
            if used >= self.max_chars:
                break

        return {
            "query": query,
            "pack_ids": pack_ids,
            "items": selected,
            "context_text": "".join(chunks),
            "chars_used": used,
            "max_chars": self.max_chars,
            "service": self.metadata(),
        }


class CallableCandidateModelService:
    """Provider adapter that deliberately emits candidate-only model output."""

    def __init__(
        self,
        runner: Callable[[dict[str, Any]], Mapping[str, Any]],
        *,
        provider: str,
        provider_version: str,
        model_id: str,
        implementation_version: str = "1",
        local: bool = True,
        estimated_cost_per_call_usd: float = 0.0,
        runtime: Mapping[str, str] | None = None,
    ) -> None:
        self.runner = runner
        self._metadata = ServiceMetadata(
            kind="model",
            provider=provider,
            provider_version=provider_version,
            implementation="callable-candidate-model",
            implementation_version=implementation_version,
            model_id=model_id,
            local=local,
            estimated_cost_per_call_usd=estimated_cost_per_call_usd,
            runtime=dict(runtime or {}),
        )

    def metadata(self) -> dict[str, Any]:
        return self._metadata.as_dict()

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        output = dict(self.runner(copy.deepcopy(task)))
        return {
            "output": output,
            "authority": "candidate_only",
            "service": self.metadata(),
        }


@dataclass(frozen=True)
class RiskEscalationPolicy:
    """Representable authority boundary for candidate model proposals."""

    policy_id: str = "fossil-risk-escalation-v1"
    uncertainty_threshold: float = 0.35
    min_independent_evidence_for_truth_change: int = 1
    high_risk_levels: frozenset[str] = frozenset({"high", "critical"})

    def assess(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        requested_action = str(proposal.get("requested_action", "propose"))
        truth_change = bool(proposal.get("truth_change", False))
        risk = str(proposal.get("risk", "low"))
        uncertainty = float(proposal.get("uncertainty", 1.0))
        authority = str(proposal.get("authority", "candidate_only"))
        evidence = [str(ref) for ref in proposal.get("independent_evidence_refs", [])]

        reasons: list[str] = []
        if risk in self.high_risk_levels:
            reasons.append("high_risk")
        if uncertainty > self.uncertainty_threshold:
            reasons.append("uncertainty_above_threshold")
        if truth_change and len(evidence) < self.min_independent_evidence_for_truth_change:
            reasons.append("insufficient_independent_evidence")

        if requested_action != "commit":
            decision = "allow_proposal"
        elif reasons:
            decision = "escalate"
        elif truth_change and authority == "candidate_only":
            # Authority comes from this independent evidence/policy gate, not model consensus.
            decision = "allow_commit_after_verification"
        else:
            decision = "allow_commit"

        return {
            "decision": decision,
            "policy_id": self.policy_id,
            "reasons": reasons,
            "risk": risk,
            "uncertainty": uncertainty,
            "truth_change": truth_change,
            "source_authority": authority,
            "independent_evidence_refs": evidence,
        }


class PolicyVerificationService:
    def __init__(
        self,
        policy: RiskEscalationPolicy | None = None,
        *,
        version: str = "1",
    ) -> None:
        self.policy = policy or RiskEscalationPolicy()
        self.version = version

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="verification",
            provider="fossil",
            provider_version="1",
            implementation="risk-escalation-policy",
            implementation_version=self.version,
            model_id=None,
            local=True,
            estimated_cost_per_call_usd=0.0,
            runtime={"policy_id": self.policy.policy_id},
        ).as_dict()

    def verify(self, proposal: dict[str, Any]) -> dict[str, Any]:
        result = self.policy.assess(proposal)
        result["service"] = self.metadata()
        return result
