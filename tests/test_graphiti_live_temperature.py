from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _llm_config_keyword_sets(source: str) -> list[set[str]]:
    tree = ast.parse(source)
    found: list[set[str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "LLMConfig":
            continue
        found.append({keyword.arg for keyword in node.keywords if keyword.arg})
    return found


def _manifest_records_temperature(source: str) -> bool:
    return re.search(r"""["']temperature["']\s*:""", source) is not None


def test_workflow_pins_explicit_zero_llm_temperature() -> None:
    workflow = _source(".github/workflows/graphiti-live.yml")
    assert re.search(
        r'(?m)^\s*GRAPHITI_LLM_TEMPERATURE:\s*"0"\s*$',
        workflow,
    ), "Graphiti live workflow must pin GRAPHITI_LLM_TEMPERATURE to 0"


def test_workflow_pins_bounded_model_compatibility_candidate() -> None:
    workflow = _source(".github/workflows/graphiti-live.yml")
    assert re.search(r"(?m)^\s*GRAPHITI_LLM_MODEL:\s*gemma3:4b\s*$", workflow)
    assert re.search(r"(?m)^\s*GRAPHITI_SMALL_MODEL:\s*gemma3:4b\s*$", workflow)
    assert re.search(
        r"(?m)^\s*GRAPHITI_STRUCTURED_OUTPUT_MODE:\s*json_schema\s*$",
        workflow,
    )
    assert re.search(r"(?m)^\s*ollama pull gemma3:4b\s*$", workflow)
    assert not re.search(r"(?m)^\s*ollama pull deepseek-r1:7b\s*$", workflow)


def test_workflow_checks_out_and_records_exact_pr_head_sha() -> None:
    workflow = _source(".github/workflows/graphiti-live.yml")
    target = "${{ github.event.pull_request.head.sha || github.sha }}"
    assert f"FOSSIL_SOFTWARE_COMMIT: {target}" in workflow
    assert f"ref: {target}" in workflow
    assert "FOSSIL_SOFTWARE_COMMIT: ${{ github.sha }}" not in workflow


def test_live_graphiti_smoke_passes_and_records_temperature() -> None:
    source = _source("scripts/live_graphiti_smoke.py")
    assert "GRAPHITI_LLM_TEMPERATURE" in source
    configs = _llm_config_keyword_sets(source)
    assert configs, "live_graphiti_smoke.py must construct LLMConfig"
    assert all("temperature" in keys for keys in configs)
    assert _manifest_records_temperature(source)


def test_live_redaction_smoke_passes_and_records_temperature() -> None:
    source = _source("scripts/live_redaction_smoke.py")
    assert "llm_temperature" in source
    configs = _llm_config_keyword_sets(source)
    assert configs, "live_redaction_smoke.py must construct LLMConfig"
    assert all("temperature" in keys for keys in configs)
    assert _manifest_records_temperature(source)
