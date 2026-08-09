from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

import pytest

from dkg.event_store import DurableEventStore
from dkg.projection.graphiti import GraphitiProjectionAdapter
from dkg.projection.ledger import ProjectionLedger
from dkg.projection.migration import (
    ProjectionMigrationHarness,
    ProjectionSwitchLedger,
    SemanticSnapshot,
)


PACK_ID = "pack_269099f7b2ba43b7a99b9427d64092de"
BLUE = "fossil-issue5-blue"
GREEN = "fossil-issue5-green"
OLLAMA = "fossil-issue5-ollama"
PASSWORD = "fossil-issue5-pass"
MODEL = "qwen2.5:3b"
EMBEDDING_MODEL = "nomic-embed-text"


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


def _event(commit: str) -> dict:
    timestamp = "2026-08-09T22:40:00Z"
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": timestamp,
        "recorded_at": timestamp,
        "pack_id": PACK_ID,
        "actor": {"actor_type": "system", "actor_id": "issue5-live-rebuild"},
        "subject_refs": ["clm_issue5_rebuild_survives_graph_loss"],
        "idempotency_key": "issue5-live-rebuild-v1",
        "payload": {
            "claim_text": (
                "FOSSIL durable events can rebuild a replaceable Neo4j Graphiti "
                "projection after graph storage is destroyed."
            )
        },
        "provenance": {
            "method": "issue5-live-blue-green-proof",
            "software_commit": commit,
            "ontology_version": "1.0.0",
        },
    }


def _start_neo4j(name: str, host_port: int) -> None:
    _run(
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "-p",
        f"{host_port}:7687",
        "-e",
        f"NEO4J_AUTH=neo4j/{PASSWORD}",
        "-e",
        "NEO4J_server_memory_heap_initial__size=128m",
        "-e",
        "NEO4J_server_memory_heap_max__size=256m",
        "-e",
        "NEO4J_server_memory_pagecache_size=128m",
        "neo4j:5.26",
        timeout=300,
    )


def _start_ollama() -> None:
    _run(
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        OLLAMA,
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


@pytest.mark.skipif(not os.environ.get("CI"), reason="one-time GitHub-hosted Issue #5 live probe")
def test_issue5_live_destructive_rebuild_and_blue_green(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Real two-projection proof. This disposable branch must not be merged."""

    assert shutil.which("docker"), "GitHub runner must provide Docker"
    repo_root = Path(__file__).resolve().parents[1]
    containers = (BLUE, GREEN, OLLAMA)
    proof: dict = {"status": "starting"}

    for name in containers:
        subprocess.run(
            ["docker", "rm", "-f", name],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    blue_graphiti = None
    green_graphiti = None
    try:
        _start_neo4j(BLUE, 7687)
        _start_neo4j(GREEN, 7688)
        _start_ollama()

        # The repository's normal CI installs only fast test dependencies. Add the
        # exact optional projection dependency at runtime for this disposable proof.
        _run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "graphiti-core==0.29.3",
            timeout=300,
        )
        _run("docker", "exec", OLLAMA, "ollama", "pull", MODEL, timeout=900)
        _run("docker", "exec", OLLAMA, "ollama", "pull", EMBEDDING_MODEL, timeout=600)

        from graphiti_core import Graphiti
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
        from graphiti_core.nodes import EpisodeType
        from neo4j import AsyncGraphDatabase

        async def wait_neo4j(uri: str) -> str:
            driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", PASSWORD))
            try:
                for attempt in range(90):
                    try:
                        await driver.verify_connectivity()
                        records, _, _ = await driver.execute_query(
                            "CALL dbms.components() YIELD versions RETURN versions[0] AS version LIMIT 1",
                            database_="neo4j",
                        )
                        return str(records[0]["version"])
                    except Exception:
                        if attempt == 89:
                            raise
                        await asyncio.sleep(2)
            finally:
                await driver.close()
            raise AssertionError("Neo4j did not become ready")

        def make_graphiti(uri: str):
            config = LLMConfig(
                api_key="ollama",
                model=MODEL,
                small_model=MODEL,
                base_url="http://127.0.0.1:11434/v1",
            )
            llm = OpenAIGenericClient(config=config, structured_output_mode="json_schema")
            embedder = OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="ollama",
                    embedding_model=EMBEDDING_MODEL,
                    embedding_dim=768,
                    base_url="http://127.0.0.1:11434/v1",
                )
            )
            return Graphiti(
                uri,
                "neo4j",
                PASSWORD,
                llm_client=llm,
                embedder=embedder,
                cross_encoder=OpenAIRerankerClient(client=llm, config=config),
                max_coroutines=1,
            )

        async def projected_events(uri: str) -> list[dict]:
            driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", PASSWORD))
            try:
                records, _, _ = await driver.execute_query(
                    "MATCH (e:Episodic {group_id: $group_id}) "
                    "RETURN e.content AS content ORDER BY e.valid_at, e.uuid",
                    group_id=PACK_ID,
                    database_="neo4j",
                )
                return [json.loads(record["content"]) for record in records]
            finally:
                await driver.close()

        async def graph_node_count(uri: str) -> int:
            driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", PASSWORD))
            try:
                records, _, _ = await driver.execute_query(
                    "MATCH (n) RETURN count(n) AS count", database_="neo4j"
                )
                return int(records[0]["count"])
            finally:
                await driver.close()

        async def seed_and_destroy_green(uri: str) -> tuple[int, int]:
            driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", PASSWORD))
            try:
                await driver.execute_query(
                    "CREATE (:FossilMigrationSentinel {id: 'must-disappear'})",
                    database_="neo4j",
                )
                before_records, _, _ = await driver.execute_query(
                    "MATCH (n) RETURN count(n) AS count", database_="neo4j"
                )
                await driver.execute_query("MATCH (n) DETACH DELETE n", database_="neo4j")
                after_records, _, _ = await driver.execute_query(
                    "MATCH (n) RETURN count(n) AS count", database_="neo4j"
                )
                return int(before_records[0]["count"]), int(after_records[0]["count"])
            finally:
                await driver.close()

        async def live() -> dict:
            nonlocal blue_graphiti, green_graphiti
            blue_uri = "bolt://127.0.0.1:7687"
            green_uri = "bolt://127.0.0.1:7688"
            blue_version, green_version = await asyncio.gather(
                wait_neo4j(blue_uri), wait_neo4j(green_uri)
            )

            commit = os.environ.get("GITHUB_SHA", "issue5-live-probe")
            store = DurableEventStore(
                tmp_path / "events", repo_root / "schemas" / "events" / "v1.schema.json"
            )
            accepted = store.commit(_event(commit))
            event_id = accepted["event_id"]
            expected = SemanticSnapshot.from_events(store.iter_events())
            durable_event_file = next((tmp_path / "events").rglob(f"{event_id}.json"))
            assert durable_event_file.exists()

            common_manifest = {
                "graphiti_version": importlib.metadata.version("graphiti-core"),
                "neo4j_version": blue_version,
                "llm_provider": "ollama-openai-compatible",
                "model_id": MODEL,
                "embedding_model_id": EMBEDDING_MODEL,
                "embedding_dim": 768,
                "structured_output_mode": "json_schema",
                "ontology_version": "1.0.0",
                "software_commit": commit,
            }

            # BLUE: current projection A remains live throughout GREEN rebuild.
            blue_graphiti = make_graphiti(blue_uri)
            blue_adapter = GraphitiProjectionAdapter(
                client=blue_graphiti,
                ledger=ProjectionLedger(
                    tmp_path / "projection-ledger",
                    GraphitiProjectionAdapter.name,
                    build_id="blue-build-1",
                ),
                build_manifest={**common_manifest, "projection_build_id": "blue-build-1"},
                episode_type_json=EpisodeType.json,
            )
            await blue_adapter.initialize_async()
            blue_receipt = await blue_adapter.apply_event_async(accepted)
            assert blue_receipt.status == "applied"
            blue_snapshot = SemanticSnapshot.from_events(await projected_events(blue_uri))
            assert blue_snapshot.digest() == expected.digest()
            blue_nodes_before_green_rebuild = await graph_node_count(blue_uri)
            assert blue_nodes_before_green_rebuild > 0

            # GREEN: explicit destructive reset followed by replay from the SAME
            # immutable event store, using a fresh build-scoped projection ledger.
            green_graphiti = make_graphiti(green_uri)
            green_adapter = GraphitiProjectionAdapter(
                client=green_graphiti,
                ledger=ProjectionLedger(
                    tmp_path / "projection-ledger",
                    GraphitiProjectionAdapter.name,
                    build_id="green-rebuild-1",
                ),
                build_manifest={
                    **common_manifest,
                    "neo4j_version": green_version,
                    "projection_build_id": "green-rebuild-1",
                },
                episode_type_json=EpisodeType.json,
            )
            switch_ledger = ProjectionSwitchLedger(tmp_path / "active-projection")
            harness = ProjectionMigrationHarness(switch_ledger)
            sentinel_before = 0
            sentinel_after_destroy = -1

            async def destroy_green():
                nonlocal sentinel_before, sentinel_after_destroy
                sentinel_before, sentinel_after_destroy = await seed_and_destroy_green(green_uri)
                assert sentinel_before >= 1
                assert sentinel_after_destroy == 0
                # Destruction of replaceable graph storage must not touch durable data.
                assert store.get(event_id) == accepted
                assert durable_event_file.exists()

            async def rebuild_green():
                await green_adapter.initialize_async()
                return await green_adapter.rebuild_async(events_root=store.root)

            green_receipts = await harness.destructive_rebuild(
                destroy=destroy_green,
                rebuild=rebuild_green,
            )
            assert [receipt.status for receipt in green_receipts] == ["applied"]
            green_snapshot = SemanticSnapshot.from_events(await projected_events(green_uri))

            # BLUE is still present beside rebuilt GREEN: actual blue/green overlap.
            blue_nodes_after_green_rebuild = await graph_node_count(blue_uri)
            assert blue_nodes_after_green_rebuild == blue_nodes_before_green_rebuild

            report, switch = harness.compare_and_switch(
                expected=expected,
                current=blue_snapshot,
                current_slot="blue",
                candidate=green_snapshot,
                candidate_slot="green",
                benchmarks={
                    "blue_matches_durable": blue_snapshot.digest() == expected.digest(),
                    "green_matches_durable": green_snapshot.digest() == expected.digest(),
                    "green_destroyed_before_rebuild": sentinel_after_destroy == 0,
                    "durable_event_survived_graph_destruction": store.get(event_id) == accepted,
                    "namespace_preserved": dict(green_snapshot.pack_event_ids).get(PACK_ID)
                    == (event_id,),
                },
                build_manifest={
                    **common_manifest,
                    "neo4j_version": green_version,
                    "projection_build_id": "green-rebuild-1",
                },
                switched_at="2026-08-09T22:55:00+00:00",
            )
            assert report.passed
            assert switch_ledger.active_slot() == "green"
            assert switch["from_slot"] == "blue"
            assert switch["to_slot"] == "green"

            return {
                "status": "passed",
                "event_id": event_id,
                "pack_id": PACK_ID,
                "durable_event_survived_graph_destruction": True,
                "blue": {
                    "projection_build_id": "blue-build-1",
                    "semantic_digest": blue_snapshot.digest(),
                    "node_count": blue_nodes_after_green_rebuild,
                    "neo4j_version": blue_version,
                },
                "green": {
                    "projection_build_id": "green-rebuild-1",
                    "semantic_digest": green_snapshot.digest(),
                    "sentinel_count_before_destroy": sentinel_before,
                    "node_count_after_destroy": sentinel_after_destroy,
                    "node_count_after_rebuild": await graph_node_count(green_uri),
                    "neo4j_version": green_version,
                    "rebuild_receipts": [receipt.status for receipt in green_receipts],
                },
                "comparison": {
                    "passed": report.passed,
                    "mismatches": list(report.mismatches),
                    "benchmarks": dict(report.benchmark_results),
                    "expected_digest": report.expected_digest,
                    "candidate_digest": report.candidate_digest,
                },
                "switch": switch,
                "build": {
                    "graphiti_version": importlib.metadata.version("graphiti-core"),
                    "model_id": MODEL,
                    "embedding_model_id": EMBEDDING_MODEL,
                    "structured_output_mode": "json_schema",
                    "software_commit": commit,
                },
            }

        proof = asyncio.run(live())
        with capsys.disabled():
            print("\nFOSSIL_ISSUE5_LIVE_PROOF_BEGIN")
            print(json.dumps(proof, indent=2, sort_keys=True))
            print("FOSSIL_ISSUE5_LIVE_PROOF_END\n")
        assert proof["status"] == "passed"
    finally:
        for graphiti in (green_graphiti, blue_graphiti):
            if graphiti is not None:
                try:
                    asyncio.run(graphiti.close())
                except Exception:
                    pass
        for name in containers:
            subprocess.run(
                ["docker", "rm", "-f", name],
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
