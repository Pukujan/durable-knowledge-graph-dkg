from pathlib import Path

from dkg.benchmark_cases import load_benchmark_case_set, retrieval_cases_from_case_set


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"
COMMON_COMMIT = "d583005dce06dbb499c3c0de5c22b899655eb8d2"
AI_COMMIT = "fd64992d4011eb55609396f6b8b194a8c679b4bd"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_gate2_real_case_set_is_valid_and_pins_merged_pack_commits():
    root = repo_root()
    case_set = load_benchmark_case_set(
        root / "benchmarks" / "gate2" / "real-corpus-seed-v1.json",
        root / "schemas" / "benchmark" / "case-set-v1.schema.json",
    )

    corpus = {entry["pack_id"]: entry for entry in case_set["corpus"]}
    assert corpus[COMMON]["repository"] == "Pukujan/fossil-common"
    assert corpus[COMMON]["commit_sha"] == COMMON_COMMIT
    assert corpus[AI]["repository"] == "Pukujan/fossil-ai-systems"
    assert corpus[AI]["commit_sha"] == AI_COMMIT

    cases = retrieval_cases_from_case_set(case_set)
    assert len(cases) >= 8
    assert {case.category for case in cases} >= {
        "source-citation-recovery",
        "evidence-authority",
        "insufficient-evidence",
        "benchmark-control-status",
        "projection-rebuild",
        "temporal-ordering",
        "cross-pack-lineage",
    }


def test_gate2_real_case_set_declares_uncovered_history_categories_in_scope_note():
    root = repo_root()
    case_set = load_benchmark_case_set(
        root / "benchmarks" / "gate2" / "real-corpus-seed-v1.json",
        root / "schemas" / "benchmark" / "case-set-v1.schema.json",
    )

    description = case_set["description"].lower()
    for missing in ("supersession", "disagreement", "staleness", "conversation-lineage"):
        assert missing in description
