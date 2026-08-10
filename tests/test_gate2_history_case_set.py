from pathlib import Path

from dkg.benchmark_cases import load_benchmark_case_set, retrieval_cases_from_case_set


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"
COMMON_COMMIT = "d583005dce06dbb499c3c0de5c22b899655eb8d2"
AI_COMMIT = "cf7cf4087bde543cb247a978de2a7252b1b8e4de"
REQUIRED_CATEGORIES = {
    "exact-factual-lookup",
    "source-citation-recovery",
    "decision-lineage",
    "current-vs-historical",
    "contradiction-disagreement",
    "stale-superseded",
    "cross-pack-isolation",
    "obscure-deep-evidence",
    "conversation-lineage",
    "insufficient-evidence",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_history_case_set():
    root = repo_root()
    return load_benchmark_case_set(
        root / "benchmarks" / "gate2" / "real-corpus-history-v2.json",
        root / "schemas" / "benchmark" / "case-set-v1.schema.json",
    )


def test_history_case_set_pins_validated_pack_merges_and_covers_gate2a_families():
    case_set = load_history_case_set()
    corpus = {entry["pack_id"]: entry for entry in case_set["corpus"]}

    assert corpus[COMMON]["commit_sha"] == COMMON_COMMIT
    assert corpus[AI]["commit_sha"] == AI_COMMIT

    cases = retrieval_cases_from_case_set(case_set)
    assert len(cases) == 21
    assert {case.category for case in cases} == REQUIRED_CATEGORIES


def test_history_case_set_contains_real_supersession_disagreement_and_recovery_targets():
    case_set = load_history_case_set()
    by_id = {case["case_id"]: case for case in case_set["cases"]}

    assert by_id["sqlite_dependent_staleness"]["relevant_ids"] == [
        "clm_a047d79b8604fadbd44efdf4"
    ]
    assert by_id["sqlite_supersession_lineage"]["relevant_ids"] == [
        "rel_e0102ade0b5fad5cc2668ccd"
    ]
    assert by_id["graph_disagreement_relation"]["relevant_ids"] == [
        "rel_c0e74317e7ff1ee59461b036"
    ]
    assert set(by_id["false_premise_quote_missing_chat"]["relevant_ids"]) == {
        "clm_1f4c5f053bd7dccac79c301c",
        "clm_841df02f01de69cafeb9c084",
    }


def test_history_case_set_reconstructed_chat_gold_never_claims_verbatim_recovery():
    case_set = load_history_case_set()
    conversation = [
        case for case in case_set["cases"] if case["category"] == "conversation-lineage"
    ]

    assert conversation
    answers = " ".join(str(case["gold"].get("expected_answer", "")) for case in conversation)
    assert "not verbatim" in answers or "not recoverable" in answers
    assert "not invented" in answers
