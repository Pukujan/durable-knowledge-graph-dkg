from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence


QUERY_EXECUTION_RECEIPT_SCHEMA = "fossil.query-execution-receipt.v1"
QUERY_EXECUTION_RECEIPT_AUTHORITY = "execution_observability_only"

_SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)
_ABSTENTION_OUTCOMES = frozenset(
    {"insufficient_evidence", "conflicting_evidence", "current_state_unresolved"}
)


def normalize_query(query: str) -> str:
    """Normalize representation noise without changing query wording or case."""

    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(query)).strip())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SECRET_KEY_PARTS)


def sanitize_diagnostics(value: Any) -> Any:
    """Return JSON-safe bounded diagnostics while dropping credential-shaped fields."""

    if isinstance(value, Mapping):
        return {
            str(key): sanitize_diagnostics(item)
            for key, item in value.items()
            if not _is_secret_key(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_diagnostics(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _service_identity(metadata: Mapping[str, Any]) -> dict[str, Any]:
    value = sanitize_diagnostics(dict(metadata))
    runtime = value.get("runtime", {})
    if not isinstance(runtime, Mapping):
        runtime = {"value": str(runtime)}
    return {
        "kind": str(value.get("kind", "unknown")),
        "provider": str(value.get("provider", "unknown")),
        "provider_version": str(value.get("provider_version", "unknown")),
        "implementation": str(value.get("implementation", "unknown")),
        "implementation_version": str(value.get("implementation_version", "unknown")),
        "model_id": (
            str(value["model_id"]) if value.get("model_id") is not None else None
        ),
        "local": bool(value.get("local", False)),
        "runtime": sanitize_diagnostics(dict(runtime)),
    }


def build_service_invocation(
    role: str,
    actual_metadata: Mapping[str, Any],
    *,
    requested: Mapping[str, Any] | None = None,
    attempts: Iterable[Mapping[str, Any]] = (),
    latency_ms: float | None = None,
    cost_usd: float | None = None,
) -> dict[str, Any]:
    """Build a compact requested-vs-actual service record without raw telemetry."""

    actual = _service_identity(actual_metadata)
    requested_value = sanitize_diagnostics(dict(requested or {}))
    requested_identity = {
        "provider": str(requested_value.get("provider", actual["provider"])),
        "model_id": (
            str(requested_value["model_id"])
            if requested_value.get("model_id") is not None
            else actual["model_id"]
        ),
        "implementation": str(
            requested_value.get("implementation", actual["implementation"])
        ),
    }
    safe_attempts: list[dict[str, Any]] = []
    for attempt in attempts:
        item = sanitize_diagnostics(dict(attempt))
        safe_attempts.append(
            {
                key: item[key]
                for key in (
                    "provider",
                    "model_id",
                    "implementation",
                    "outcome",
                    "error_type",
                    "fallback_reason",
                )
                if key in item
            }
        )

    if cost_usd is None:
        cost_usd = float(actual_metadata.get("estimated_cost_per_call_usd", 0.0))
    return {
        "role": str(role),
        "requested": requested_identity,
        "actual": actual,
        "fallback_used": bool(
            requested_identity.get("provider") != actual.get("provider")
            or requested_identity.get("model_id") != actual.get("model_id")
            or any(str(item.get("outcome", "")) not in {"", "success"} for item in safe_attempts)
        ),
        "attempts": safe_attempts,
        "latency_ms": float(latency_ms) if latency_ms is not None else None,
        "cost_usd": float(cost_usd) if cost_usd is not None else None,
    }


def normalize_pack_mounts(
    pack_mounts: Mapping[str, str] | Iterable[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(pack_mounts, Mapping):
        mounts = [
            {"pack_id": str(pack_id), "revision": str(revision)}
            for pack_id, revision in pack_mounts.items()
        ]
    else:
        mounts = [
            {
                "pack_id": str(item.get("pack_id", "")),
                "revision": str(item.get("revision", "")),
            }
            for item in pack_mounts
        ]
    if not mounts or any(not item["pack_id"] or not item["revision"] for item in mounts):
        raise ValueError("query receipt requires non-empty pack_id and exact revision")
    by_pack: dict[str, str] = {}
    for item in mounts:
        existing = by_pack.get(item["pack_id"])
        if existing is not None and existing != item["revision"]:
            raise ValueError("query receipt cannot mount one pack_id at multiple revisions")
        by_pack[item["pack_id"]] = item["revision"]
    return [
        {"pack_id": pack_id, "revision": by_pack[pack_id]}
        for pack_id in sorted(by_pack)
    ]


def _retrieval_candidate(candidate: Mapping[str, Any], fallback_rank: int) -> dict[str, Any]:
    retrieval = dict(candidate.get("retrieval", {}))
    result: dict[str, Any] = {
        "id": str(candidate.get("id", "")),
        "pack_id": str(candidate.get("pack_id", "")),
        "rank": int(retrieval.get("rank", fallback_rank)),
        "score": (
            float(retrieval["score"]) if retrieval.get("score") is not None else None
        ),
    }
    base = candidate.get("base_retrieval")
    if isinstance(base, Mapping):
        result["base_rank"] = int(base.get("rank", fallback_rank))
        result["base_score"] = (
            float(base["score"]) if base.get("score") is not None else None
        )
    rerank = candidate.get("rerank")
    if isinstance(rerank, Mapping):
        result["rerank_score"] = (
            float(rerank["score"]) if rerank.get("score") is not None else None
        )
    return result


def _reranker_metadata(candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for candidate in candidates:
        rerank = candidate.get("rerank")
        if isinstance(rerank, Mapping) and isinstance(rerank.get("service"), Mapping):
            return rerank["service"]
    return None


def _citation_ids(output: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for claim in output.get("claims", []):
        if not isinstance(claim, Mapping):
            continue
        citation = claim.get("citation")
        if not isinstance(citation, Mapping):
            continue
        citation_id = str(citation.get("citation_id", ""))
        if citation_id and citation_id not in values:
            values.append(citation_id)
    return values


def _claim_ids(output: Mapping[str, Any]) -> list[str]:
    return [
        str(claim.get("claim_id"))
        for claim in output.get("claims", [])
        if isinstance(claim, Mapping) and claim.get("claim_id")
    ]


def _resolver_records(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    security = response.get("context_security")
    if isinstance(security, Mapping):
        records.append(
            {
                "resolver": str(security.get("resolver", "unknown")),
                "resolved_ids": [str(item) for item in security.get("canonicalized_ids", [])],
                "added_ids": [str(item) for item in security.get("demoted_untrusted_ids", [])],
                "removed_ids": [
                    str(item)
                    for item in [
                        *security.get("dropped_out_of_scope_ids", []),
                        *security.get("deduplicated_ids", []),
                    ]
                ],
                "final_context_ids": [
                    str(item) for item in security.get("forwarded_item_ids", [])
                ],
                "diagnostics": sanitize_diagnostics(
                    {
                        key: security[key]
                        for key in (
                            "source_text_trust",
                            "retrieved_payload_mismatch_ids",
                            "blocked_response_fields",
                            "blocked_output_fields",
                            "invalid_output_claim_ids",
                        )
                        if key in security
                    }
                ),
            }
        )
    lineage = response.get("lineage_resolution")
    if isinstance(lineage, Mapping):
        records.append(
            {
                "resolver": str(lineage.get("resolver", "unknown")),
                "resolved_ids": [str(item) for item in lineage.get("expanded_ids", [])],
                "added_ids": [str(item) for item in lineage.get("expanded_ids", [])],
                "removed_ids": [],
                "final_context_ids": [
                    str(item) for item in lineage.get("final_context_ids", [])
                ],
                "diagnostics": {
                    "max_expansions": int(lineage.get("max_expansions", 0)),
                },
            }
        )
    return records


def _final_context_ids(
    candidates: Sequence[Mapping[str, Any]],
    resolver_records: Sequence[Mapping[str, Any]],
) -> list[str]:
    for record in reversed(resolver_records):
        values = [str(item) for item in record.get("final_context_ids", [])]
        if values:
            return values
    return [str(item.get("id", "")) for item in candidates if item.get("id")]


def _execution_identity_payload(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "query_sha256": receipt["query"]["sha256"],
        "packs": receipt["packs"],
        "projection": receipt["projection"],
        "policy": receipt["policy"],
        "services": [
            {
                "role": item["role"],
                "requested": item["requested"],
                "actual": item["actual"],
                "fallback_used": item["fallback_used"],
                "attempts": item["attempts"],
            }
            for item in receipt["services"]
        ],
        "resolvers": [item["resolver"] for item in receipt["resolvers"]],
    }


def _result_identity_payload(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "retrieval": receipt["retrieval"],
        "resolvers": receipt["resolvers"],
        "context": receipt["context"],
        "result": receipt["result"],
    }


def build_query_execution_receipt(
    *,
    query: str,
    pack_mounts: Mapping[str, str] | Iterable[Mapping[str, Any]],
    projection: Mapping[str, Any],
    policy: Mapping[str, Any],
    services: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    response: Mapping[str, Any],
    trace_ref: str,
    run_ref: str | None = None,
    query_id: str | None = None,
    recorded_at: str | None = None,
    latency_ms: float = 0.0,
    cost_usd: float = 0.0,
) -> dict[str, Any]:
    normalized = normalize_query(query)
    if not normalized:
        raise ValueError("query receipt requires a non-empty query")
    query_hash = _sha256_text(normalized)
    mounts = normalize_pack_mounts(pack_mounts)
    projection_value = sanitize_diagnostics(dict(projection))
    if not all(str(projection_value.get(key, "")) for key in ("name", "version", "build_id")):
        raise ValueError("query receipt requires projection name, version, and build_id")
    policy_value = sanitize_diagnostics(dict(policy))
    if not str(policy_value.get("route_id", "")) or not str(
        policy_value.get("retrieval_policy_id", "")
    ):
        raise ValueError("query receipt requires route_id and retrieval_policy_id")
    if not trace_ref:
        raise ValueError("query receipt requires trace_ref")

    output_value = response.get("output", {})
    output = dict(output_value) if isinstance(output_value, Mapping) else {}
    resolver_records = _resolver_records(response)
    citation_ids = _citation_ids(output)
    candidate_records = [
        _retrieval_candidate(candidate, rank)
        for rank, candidate in enumerate(candidates, start=1)
    ]
    result = {
        "outcome": str(output.get("outcome", "unknown")),
        "abstained": str(output.get("outcome", "")) in _ABSTENTION_OUTCOMES,
        "claim_ids": _claim_ids(output),
        "citation_ids": citation_ids,
        "confidence": (
            float(output["confidence"]) if output.get("confidence") is not None else None
        ),
        "authority": str(response.get("authority", "unknown")),
    }
    context_ids = _final_context_ids(candidates, resolver_records)
    receipt: dict[str, Any] = {
        "schema_version": QUERY_EXECUTION_RECEIPT_SCHEMA,
        "receipt_id": "pending",
        "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
        "authority": QUERY_EXECUTION_RECEIPT_AUTHORITY,
        "query": {
            "query_id": query_id or f"qry_{query_hash[:24]}",
            "text": str(query),
            "normalized": normalized,
            "sha256": query_hash,
        },
        "packs": mounts,
        "projection": {
            "name": str(projection_value["name"]),
            "version": str(projection_value["version"]),
            "build_id": str(projection_value["build_id"]),
        },
        "policy": {
            "route_id": str(policy_value["route_id"]),
            "retrieval_policy_id": str(policy_value["retrieval_policy_id"]),
            "mode": str(policy_value.get("mode", "unspecified")),
        },
        "services": [copy.deepcopy(dict(item)) for item in services],
        "retrieval": {
            "candidates": candidate_records,
            "candidate_count": len(candidate_records),
        },
        "resolvers": resolver_records,
        "context": {
            "item_ids": context_ids,
            "citation_ids": citation_ids,
        },
        "result": result,
        "telemetry": {
            "latency_ms": float(latency_ms),
            "cost_usd": float(cost_usd),
            "trace_ref": str(trace_ref),
            "run_ref": str(run_ref) if run_ref is not None else None,
        },
    }
    receipt["execution_identity_sha256"] = _sha256_json(
        _execution_identity_payload(receipt)
    )
    receipt["result_sha256"] = _sha256_json(_result_identity_payload(receipt))
    receipt_without_id = copy.deepcopy(receipt)
    receipt_without_id["receipt_id"] = ""
    receipt_hash = _sha256_json(receipt_without_id)
    receipt["receipt_id"] = f"qrx_{receipt_hash[:24]}"
    return receipt


def compare_query_execution_receipts(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare replay receipts while separating corpus drift from execution changes."""

    dimensions = {
        "query": before.get("query", {}).get("sha256") != after.get("query", {}).get("sha256"),
        "corpus": before.get("packs") != after.get("packs"),
        "projection": before.get("projection") != after.get("projection"),
        "policy": before.get("policy") != after.get("policy"),
        "services": [
            {
                "role": item.get("role"),
                "requested": item.get("requested"),
                "actual": item.get("actual"),
                "fallback_used": item.get("fallback_used"),
                "attempts": item.get("attempts"),
            }
            for item in before.get("services", [])
        ]
        != [
            {
                "role": item.get("role"),
                "requested": item.get("requested"),
                "actual": item.get("actual"),
                "fallback_used": item.get("fallback_used"),
                "attempts": item.get("attempts"),
            }
            for item in after.get("services", [])
        ],
        "retrieval_candidates": before.get("retrieval") != after.get("retrieval"),
        "resolvers": before.get("resolvers") != after.get("resolvers"),
        "context": before.get("context") != after.get("context"),
        "result": before.get("result") != after.get("result"),
    }
    changed = [name for name, did_change in dimensions.items() if did_change]
    before_pack_ids = [item.get("pack_id") for item in before.get("packs", [])]
    after_pack_ids = [item.get("pack_id") for item in after.get("packs", [])]
    same_pack_ids = before_pack_ids == after_pack_ids
    return {
        "schema_version": "fossil.query-execution-replay-comparison.v1",
        "before_receipt_id": str(before.get("receipt_id", "")),
        "after_receipt_id": str(after.get("receipt_id", "")),
        "same_logical_query": not dimensions["query"],
        "same_pack_ids": same_pack_ids,
        "same_corpus_revision": not dimensions["corpus"],
        "corpus_revision_changed": same_pack_ids and dimensions["corpus"],
        "execution_identity_match": (
            before.get("execution_identity_sha256")
            == after.get("execution_identity_sha256")
        ),
        "result_identity_match": before.get("result_sha256") == after.get("result_sha256"),
        "changed_dimensions": changed,
        "telemetry_changed": before.get("telemetry") != after.get("telemetry"),
        "replay_comparable": not dimensions["query"],
    }


def execute_query_with_receipt(
    *,
    query: str,
    pack_mounts: Mapping[str, str] | Iterable[Mapping[str, Any]],
    query_pack_ids: Sequence[str],
    projection: Mapping[str, Any],
    policy: Mapping[str, Any],
    retriever: Any,
    model_service: Any,
    limit: int,
    trace_ref: str,
    run_ref: str | None = None,
    query_id: str | None = None,
    requested_model: Mapping[str, Any] | None = None,
    model_attempts: Iterable[Mapping[str, Any]] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute one query and emit a compact replayable receipt around existing services."""

    if limit < 1:
        raise ValueError("query receipt execution limit must be positive")
    mounts = normalize_pack_mounts(pack_mounts)
    mounted_ids = {item["pack_id"] for item in mounts}
    requested_pack_ids = [str(item) for item in query_pack_ids]
    if not set(requested_pack_ids) <= mounted_ids:
        raise ValueError("query_pack_ids must be mounted at exact revisions")

    started = time.perf_counter()
    retrieval_started = time.perf_counter()
    candidates = retriever.search(query, pack_ids=requested_pack_ids, limit=limit)
    retrieval_latency_ms = (time.perf_counter() - retrieval_started) * 1000.0

    model_started = time.perf_counter()
    response = copy.deepcopy(
        dict(
            model_service.run(
                {
                    "query": query,
                    "pack_ids": requested_pack_ids,
                    "context_items": candidates,
                    "response_contract": {
                        "outcomes": [
                            "answer",
                            "conflicting_evidence",
                            "current_state_unresolved",
                            "insufficient_evidence",
                        ],
                        "authority": "candidate_only",
                    },
                }
            )
        )
    )
    model_latency_ms = (time.perf_counter() - model_started) * 1000.0
    total_latency_ms = (time.perf_counter() - started) * 1000.0

    retriever_metadata = dict(retriever.metadata())
    model_metadata = dict(response.get("service", model_service.metadata()))
    retriever_cost = float(retriever_metadata.get("estimated_cost_per_call_usd", 0.0))
    model_cost = float(response.get("cost_usd", model_metadata.get("estimated_cost_per_call_usd", 0.0)))
    services = [
        build_service_invocation(
            "retriever",
            retriever_metadata,
            latency_ms=retrieval_latency_ms,
            cost_usd=retriever_cost,
        )
    ]
    reranker_metadata = _reranker_metadata(candidates)
    if reranker_metadata is not None:
        services.append(
            build_service_invocation(
                "reranker",
                reranker_metadata,
                latency_ms=None,
                cost_usd=None,
            )
        )
    services.append(
        build_service_invocation(
            "model",
            model_metadata,
            requested=requested_model,
            attempts=model_attempts,
            latency_ms=model_latency_ms,
            cost_usd=model_cost,
        )
    )

    receipt = build_query_execution_receipt(
        query=query,
        pack_mounts=mounts,
        projection=projection,
        policy=policy,
        services=services,
        candidates=candidates,
        response=response,
        trace_ref=trace_ref,
        run_ref=run_ref,
        query_id=query_id,
        latency_ms=total_latency_ms,
        cost_usd=retriever_cost + model_cost,
    )
    return response, receipt
