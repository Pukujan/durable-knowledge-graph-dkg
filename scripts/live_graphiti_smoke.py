from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from graphiti_core import Graphiti
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.nodes import EpisodeType
from neo4j import AsyncGraphDatabase

from fossil_core.event_store import DurableEventStore
from fossil_core.projection.graphiti import GraphitiProjectionAdapter
from fossil_core.projection.ledger import ProjectionLedger
from fossil_core.runtime import ProjectorWorker


PACK_ID = "pack_269099f7b2ba43b7a99b9427d64092de"
IDEMPOTENCY_KEY = "gate1-live-graphiti-materialization-v1"


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def llm_temperature() -> float:
    raw = os.environ.get("GRAPHITI_LLM_TEMPERATURE", "0")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("GRAPHITI_LLM_TEMPERATURE must be a number") from exc
    if value < 0:
        raise ValueError("GRAPHITI_LLM_TEMPERATURE must be >= 0")
    return value


def software_commit() -> str:
    configured = os.environ.get("FOSSIL_SOFTWARE_COMMIT")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


async def wait_for_neo4j(
    uri: str, user: str, password: str, *, attempts: int = 60
) -> str:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        for attempt in range(1, attempts + 1):
            try:
                await driver.verify_connectivity()
                records, _, _ = await driver.execute_query(
                    "CALL dbms.components() "
                    "YIELD name, versions "
                    "RETURN name, versions[0] AS version "
                    "ORDER BY name LIMIT 1",
                    database_="neo4j",
                )
                if not records:
                    raise RuntimeError("Neo4j returned no component version")
                return str(records[0]["version"])
            except Exception:
                if attempt == attempts:
                    raise
                await asyncio.sleep(2)
    finally:
        await driver.close()
    raise RuntimeError("Neo4j did not become ready")


async def observe_projection(
    uri: str,
    user: str,
    password: str,
    *,
    group_id: str,
    episode_name: str,
) -> dict[str, Any]:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        records, _, _ = await driver.execute_query(
            """
            MATCH (e:Episodic {group_id: $group_id, name: $episode_name})
            OPTIONAL MATCH (e)-[:MENTIONS]->(entity:Entity)
            WITH e, count(DISTINCT entity) AS mentioned_entity_count
            OPTIONAL MATCH (left:Entity {group_id: $group_id})
              -[fact:RELATES_TO]->
              (right:Entity {group_id: $group_id})
            RETURN
                count(DISTINCT e) AS episode_count,
                max(mentioned_entity_count) AS mentioned_entity_count,
                count(DISTINCT fact) AS fact_edge_count,
                collect(DISTINCT e.uuid) AS episode_uuids,
                collect(DISTINCT e.content) AS episode_contents
            """,
            group_id=group_id,
            episode_name=episode_name,
            database_="neo4j",
        )
        if not records:
            return {
                "episode_count": 0,
                "mentioned_entity_count": 0,
                "fact_edge_count": 0,
                "episode_uuids": [],
                "episode_contents": [],
            }
        record = records[0]
        return {
            "episode_count": int(record["episode_count"] or 0),
            "mentioned_entity_count": int(record["mentioned_entity_count"] or 0),
            "fact_edge_count": int(record["fact_edge_count"] or 0),
            "episode_uuids": list(record["episode_uuids"] or []),
            "episode_contents": list(record["episode_contents"] or []),
        }
    finally:
        await driver.close()


def build_event(commit: str) -> dict[str, Any]:
    timestamp = "2026-08-09T19:20:00Z"
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": timestamp,
        "recorded_at": timestamp,
        "pack_id": PACK_ID,
        "actor": {
            "actor_type": "system",
            "actor_id": "fossil-gate1-live-smoke",
        },
        "subject_refs": ["clm_gate1_live_graphiti_projection"],
        "idempotency_key": IDEMPOTENCY_KEY,
        "payload": {
            "claim_text": (
                "FOSSIL Core uses Graphiti with Neo4j as a rebuildable knowledge "
                "projection. Durable FOSSIL events remain the canonical record."
            )
        },
        "provenance": {
            "method": "gate1-live-graphiti-smoke",
            "software_commit": commit,
            "ontology_version": os.environ.get("FOSSIL_ONTOLOGY_VERSION", "1.0.0"),
        },
    }


async def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    root = Path(
        os.environ.get(
            "FOSSIL_SMOKE_ROOT",
            tempfile.mkdtemp(prefix="fossil-graphiti-smoke-"),
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    proof_path = Path(
        os.environ.get(
            "FOSSIL_PROOF_PATH",
            str(root / "live-graphiti-proof.json"),
        )
    )
    proof: dict[str, Any] = {"status": "starting", "pack_id": PACK_ID}
    graphiti: Graphiti | None = None

    try:
        commit = software_commit()
        event_store = DurableEventStore(
            root / "events",
            repo_root / "schemas" / "events" / "v1.schema.json",
        )
        accepted_event = event_store.commit(build_event(commit))
        event_id = accepted_event["event_id"]
        durable_event_path = next((root / "events").rglob(f"{event_id}.json"))
        if event_store.get(event_id) != accepted_event:
            raise AssertionError("durable event was not readable before graph projection")

        proof.update(
            {
                "status": "durable_event_committed",
                "event_id": event_id,
                "episode_name": f"dkg-event:{event_id}",
                "durable_event_path": str(durable_event_path),
                "durable_event_path_exists_before_projection": durable_event_path.exists(),
            }
        )
        if not proof["durable_event_path_exists_before_projection"]:
            raise AssertionError("durable event file does not exist before projection")

        neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = required_env("NEO4J_PASSWORD")
        llm_base_url = os.environ.get(
            "GRAPHITI_LLM_BASE_URL", "http://127.0.0.1:11434/v1"
        )
        llm_api_key = os.environ.get("GRAPHITI_LLM_API_KEY", "ollama")
        llm_model = os.environ.get("GRAPHITI_LLM_MODEL", "deepseek-r1:7b")
        small_model = os.environ.get("GRAPHITI_SMALL_MODEL", llm_model)
        embedding_model = os.environ.get(
            "GRAPHITI_EMBEDDING_MODEL", "nomic-embed-text"
        )
        embedding_dim = int(os.environ.get("GRAPHITI_EMBEDDING_DIM", "768"))
        structured_output_mode = os.environ.get(
            "GRAPHITI_STRUCTURED_OUTPUT_MODE", "json_schema"
        )
        if structured_output_mode not in {"json_schema", "json_object"}:
            raise ValueError(
                "GRAPHITI_STRUCTURED_OUTPUT_MODE must be json_schema or json_object"
            )
        temperature = llm_temperature()

        neo4j_version = await wait_for_neo4j(
            neo4j_uri, neo4j_user, neo4j_password
        )
        llm_config = LLMConfig(
            api_key=llm_api_key,
            model=llm_model,
            small_model=small_model,
            base_url=llm_base_url,
            temperature=temperature,
        )
        llm_client = OpenAIGenericClient(
            config=llm_config,
            structured_output_mode=structured_output_mode,
        )
        embedder = OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key=llm_api_key,
                embedding_model=embedding_model,
                embedding_dim=embedding_dim,
                base_url=llm_base_url,
            )
        )
        graphiti = Graphiti(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=OpenAIRerankerClient(
                client=llm_client,
                config=llm_config,
            ),
            max_coroutines=1,
        )
        build_manifest = {
            "graphiti_version": importlib.metadata.version("graphiti-core"),
            "neo4j_version": neo4j_version,
            "llm_provider": "ollama-openai-compatible",
            "llm_base_url": llm_base_url,
            "model_id": llm_model,
            "small_model_id": small_model,
            "embedding_model_id": embedding_model,
            "embedding_dim": embedding_dim,
            "structured_output_mode": structured_output_mode,
            "temperature": temperature,
            "ontology_version": os.environ.get("FOSSIL_ONTOLOGY_VERSION", "1.0.0"),
            "software_commit": commit,
        }
        proof["build_manifest"] = build_manifest
        projection = GraphitiProjectionAdapter(
            client=graphiti,
            ledger=ProjectionLedger(
                root / "projection-ledger",
                GraphitiProjectionAdapter.name,
                build_id="node-01-live-smoke-v1",
            ),
            build_manifest=build_manifest,
            episode_type_json=EpisodeType.json,
        )
        projector = ProjectorWorker(
            event_store=event_store,
            projection=projection,
            ledger=projection.ledger,
            poll_interval_seconds=1.0,
        )

        await projection.initialize_async()
        proof["status"] = "graphiti_initialized"

        first_cycle = await projector.run_once_async()
        proof["first_projector_cycle"] = {
            "scanned": first_cycle.scanned,
            "applied": first_cycle.applied,
            "skipped": first_cycle.skipped,
            "failed": first_cycle.failed,
        }
        if first_cycle.applied != 1 or first_cycle.failed != 0:
            raise AssertionError(
                f"first projector cycle did not apply exactly one event: {first_cycle}"
            )
        first = next(
            receipt for receipt in first_cycle.receipts if receipt.event_id == event_id
        )
        proof["first_receipt"] = {
            "status": first.status,
            "detail": first.detail,
        }
        if first.status != "applied":
            raise AssertionError(f"first projection did not apply: {first}")

        episode_name = proof["episode_name"]
        after_first = await observe_projection(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            group_id=PACK_ID,
            episode_name=episode_name,
        )
        proof["after_first_projection"] = after_first
        if after_first["episode_count"] != 1:
            raise AssertionError(
                "expected exactly one real Graphiti Episodic node after projection"
            )
        if not any(event_id in content for content in after_first["episode_contents"]):
            raise AssertionError(
                "projected Graphiti episode does not contain the durable event id"
            )
        if after_first["mentioned_entity_count"] < 1:
            raise AssertionError(
                "Graphiti materialized the episode but extracted no mentioned entities"
            )

        second_cycle = await projector.run_once_async()
        proof["second_projector_cycle"] = {
            "scanned": second_cycle.scanned,
            "applied": second_cycle.applied,
            "skipped": second_cycle.skipped,
            "failed": second_cycle.failed,
        }
        second = next(
            receipt for receipt in second_cycle.receipts if receipt.event_id == event_id
        )
        proof["second_receipt"] = {
            "status": second.status,
            "detail": second.detail,
        }
        if second.status != "skipped" or second_cycle.skipped != 1:
            raise AssertionError(
                f"replay should be skipped by projection ledger: {second_cycle}"
            )

        after_retry = await observe_projection(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            group_id=PACK_ID,
            episode_name=episode_name,
        )
        proof["after_idempotent_retry"] = after_retry
        if after_retry["episode_count"] != 1:
            raise AssertionError(
                "idempotent retry changed the Graphiti episode count"
            )

        applied_record = projection.ledger.get_applied(event_id)
        proof["projection_ledger"] = applied_record
        if applied_record["group_id"] != PACK_ID:
            raise AssertionError("projection ledger did not preserve pack namespace")

        proof["status"] = "passed"
    except Exception as exc:
        proof["status"] = "failed"
        proof["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        raise
    finally:
        if graphiti is not None:
            try:
                await graphiti.close()
            except Exception as exc:
                proof["close_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
        proof_path.parent.mkdir(parents=True, exist_ok=True)
        proof_path.write_text(
            json.dumps(proof, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(proof, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
