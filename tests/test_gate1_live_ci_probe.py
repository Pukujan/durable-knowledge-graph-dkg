from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

import pytest


NEO4J_CONTAINER = "fossil-gate1-neo4j-probe"
OLLAMA_CONTAINER = "fossil-gate1-ollama-probe"


def _run(*args: str, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def _wait_http(url: str, *, attempts: int = 90) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as exc:  # pragma: no cover - live CI probe only
            last_error = exc
        time.sleep(2)
    raise AssertionError(f"service did not become ready at {url}: {last_error}")


@pytest.mark.skipif(not os.environ.get("CI"), reason="one-time GitHub-hosted live integration probe")
def test_gate1_live_graphiti_neo4j(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Execute the real Gate 1 proof through the repository's already-trusted CI job.

    This file is intentionally kept on a disposable PR branch and must not be merged.
    It avoids changing workflow definitions while still exercising real Neo4j, Graphiti,
    Ollama inference/embeddings, FOSSIL durable commit ordering, namespace materialization,
    and idempotent replay.
    """

    assert shutil.which("docker"), "GitHub runner must provide Docker"
    proof_path = tmp_path / "fossil-live-graphiti-proof.json"

    for name in (NEO4J_CONTAINER, OLLAMA_CONTAINER):
        subprocess.run(
            ["docker", "rm", "-f", name],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    try:
        _run(
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            NEO4J_CONTAINER,
            "-p",
            "7687:7687",
            "-e",
            "NEO4J_AUTH=neo4j/fossil-gate1-pass",
            "-e",
            "NEO4J_server_memory_heap_initial__size=256m",
            "-e",
            "NEO4J_server_memory_heap_max__size=512m",
            "-e",
            "NEO4J_server_memory_pagecache_size=256m",
            "neo4j:5.26",
            timeout=300,
        )
        _run(
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            OLLAMA_CONTAINER,
            "-p",
            "11434:11434",
            "-e",
            "OLLAMA_NUM_PARALLEL=1",
            "-e",
            "OLLAMA_MAX_LOADED_MODELS=1",
            "ollama/ollama:latest",
            timeout=300,
        )
        _wait_http("http://127.0.0.1:11434/api/tags")

        # Install exactly the projection dependency pinned by fossil-core. The ordinary
        # CI job intentionally installs only the fast test extra before pytest starts.
        _run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "graphiti-core==0.29.3",
            timeout=300,
        )

        # Use Graphiti's documented Ollama-compatible models for this real gate.
        _run("docker", "exec", OLLAMA_CONTAINER, "ollama", "pull", "deepseek-r1:7b", timeout=900)
        _run("docker", "exec", OLLAMA_CONTAINER, "ollama", "pull", "nomic-embed-text", timeout=600)

        env = os.environ.copy()
        env.update(
            {
                "NEO4J_URI": "bolt://127.0.0.1:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "fossil-gate1-pass",
                "GRAPHITI_LLM_BASE_URL": "http://127.0.0.1:11434/v1",
                "GRAPHITI_LLM_API_KEY": "ollama",
                "GRAPHITI_LLM_MODEL": "deepseek-r1:7b",
                "GRAPHITI_SMALL_MODEL": "deepseek-r1:7b",
                "GRAPHITI_EMBEDDING_MODEL": "nomic-embed-text",
                "GRAPHITI_EMBEDDING_DIM": "768",
                "GRAPHITI_STRUCTURED_OUTPUT_MODE": "json_object",
                "GRAPHITI_TELEMETRY_ENABLED": "false",
                "SEMAPHORE_LIMIT": "1",
                "FOSSIL_ONTOLOGY_VERSION": "1.0.0",
                "FOSSIL_SOFTWARE_COMMIT": os.environ.get("GITHUB_SHA", "ci-probe"),
                "FOSSIL_PROOF_PATH": str(proof_path),
            }
        )
        smoke = subprocess.run(
            [sys.executable, "scripts/live_graphiti_smoke.py"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            timeout=1200,
            check=False,
        )

        # Bypass pytest capture so the connected GitHub tooling can recover durable
        # runtime evidence from an otherwise successful `pytest -q` job.
        with capsys.disabled():
            print("\nFOSSIL_GATE1_LIVE_PROOF_BEGIN")
            if proof_path.exists():
                print(proof_path.read_text(encoding="utf-8"))
            else:
                print(smoke.stdout[-12000:])
            print("FOSSIL_GATE1_LIVE_PROOF_END\n")

        assert smoke.returncode == 0, smoke.stdout[-16000:]
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        assert proof["status"] == "passed"
        assert proof["durable_event_path_exists_before_projection"] is True
        assert proof["after_first_projection"]["episode_count"] == 1
        assert proof["after_first_projection"]["mentioned_entity_count"] >= 1
        assert proof["second_receipt"]["status"] == "skipped"
        assert proof["after_idempotent_retry"]["episode_count"] == 1
    finally:
        for name in (NEO4J_CONTAINER, OLLAMA_CONTAINER):
            subprocess.run(
                ["docker", "rm", "-f", name],
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
