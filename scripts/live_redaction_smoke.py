from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
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

from dkg.event_store import DurableEventStore, EventRedactedError
from dkg.projection.graphiti import GraphitiProjectionAdapter
from dkg.projection.ledger import ProjectionLedger
from live_graphiti_smoke import required_env, software_commit, wait_for_neo4j


PACK_ID = "pack_f024177f89a5442db84171c3dd7f58e5"
IDEMPOTENCY_KEY = "gate1-live-event-redaction-v1"


def build_event(commit: str) -> dict[str, Any]:
    timestamp = "2026-08-10T00:50:00Z"
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": timestamp,
        "recorded_at": timestamp,
        "pack_id": PACK_ID,
        "actor": {
            "actor_type": "system",
            "actor_id": "fossil-gate1-live-redaction",
        },
        "subject_refs": ["clm_gate1_live_redaction_fixture"],
        "idempotency_key": IDEMPOTENCY_KEY,
        "payload": {
            "claim_text": (
                "FOSSIL live redaction fixture contains deliberately erasable "
                "sensitive projection text unique to this test."
            )
        },
        "provenance": {
            "method": "gate1-live-redaction-smoke",
            "software_commit": commit,
            "ontology_version": os.environ.get("FOSSIL_ONTOLOGY_VERSION", "1.0.0"),
        },
    }


async def observe_pack(
    uri: str,
    user: str,
    password: str,
    *,
    group_id: str,
    episode_name: str,
) -> dict[str, int | list[str]]:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        records, _, _ = await driver.execute_query(
            """
            OPTIONAL MATCH (episode:Episodic {group_id: $group_id, name: $episode_name})
            WITH count(DISTINCT episode) AS episode_count,
                 collect(DISTINCT episode.uuid) AS episode_uuids
            OPTIONAL MATCH (entity:Entity {group_id: $group_id})
            WITH episode_count, episode_uuids, count(DISTINCT entity) AS entity_count
            OPTIONAL MATCH ()-[fact:RELATES_TO]->()
            WHERE fact.group_id = $group_id
            RETURN episode_count, episode_uuids, entity_count,
                   count(DISTINCT fact) AS fact_edge_count
            """,
            group_id=group_id,
            episode_name=episode_name,
            database_="neo4j",
        )
        record = records[0]
        return {
            "episode_count": int(record["episode_count"] or 0),
            "episode_uuids": list(record["episode_uuids"] or []),
            "entity_count": int(record["entity_count"] or 0),
            "fact_edge_count": int(record["fact_edge_count"] or 0),
        }
    finally:
        await driver.close()


async def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    root = Path(
        os.environ.get(
            "FOSSIL_REDACTION_SMOKE_ROOT",
            tempfile.mkdtemp(prefix="fossil-redaction-smoke-"),
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    proof_path = Path(
        os.environ.get(
            "FOSSIL_REDACTION_PROOF_PATH",
            str(root / "live-redaction-proof.json"),
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
        original_event = build_event(commit)
        accepted_event = event_store.commit(original_event)
        event_id = accepted_event["event_id"]
        episode_name = f"dkg-event:{event_id}"
        event_path = next(event_store.root.rglob(f"{event_id}.json"))
        if not event_path.exists():
            raise AssertionError("canonical event must exist before projection")

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
        neo4j_version = await wait_for_neo4j(
            neo4j_uri, neo4j_user, neo4j_password
        )

        llm_config = LLMConfig(
            api_key=llm_api_key,
            model=llm_model,
            small_model=small_model,
            base_url=llm_base_url,
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
            cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
            max_coroutines=1,
        )
        build_manifest = {
            "graphiti_version": importlib.metadata.version("graphiti-core"),
            "neo4j_version": neo4j_version,
            "llm_provider": "ollama-openai-compatible",
            "model_id": llm_model,
            "embedding_model_id": embedding_model,
            "structured_output_mode": structured_output_mode,
            "software_commit": commit,
            "proof": "event-redaction-active-purge-non-resurrection",
        }
        projection = GraphitiProjectionAdapter(
            client=graphiti,
            ledger=ProjectionLedger(
                root / "projection-ledger",
                GraphitiProjectionAdapter.name,
                build_id="redaction-active-1",
            ),
            build_manifest=build_manifest,
            episode_type_json=EpisodeType.json,
        )
        await projection.initialize_async()

        first = await projection.apply_event_async(accepted_event)
        if first.status != "applied":
            raise AssertionError(f"sensitive fixture failed to materialize: {first}")
        applied = projection.ledger.get_applied(event_id)
        episode_uuid = applied.get("episode_uuid") if applied else None
        if not episode_uuid:
            raise AssertionError("applied projection receipt did not retain Graphiti episode UUID")

        before = await observe_pack(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            group_id=PACK_ID,
            episode_name=episode_name,
        )
        if before["episode_count"] != 1:
            raise AssertionError("expected exactly one sensitive episode before redaction")
        if before["entity_count"] < 1:
            raise AssertionError("live fixture extracted no pack-local entities before redaction")

        tombstone = event_store.redact(
            event_id,
            reason="live privacy erasure proof",
            authority="fossil-gate1-live-redaction",
            redacted_at="2026-08-10T00:51:00Z",
            request_ref="gate1-live-redaction-proof",
        )
        if event_path.exists():
            raise AssertionError("sensitive canonical event bytes still exist after redaction")
        if list(event_store.iter_events()):
            raise AssertionError("redacted event still appears in canonical replay source")
        serialized_tombstone = json.dumps(tombstone, sort_keys=True)
        if "sensitive projection text" in serialized_tombstone:
            raise AssertionError("redaction tombstone copied sensitive payload text")
        try:
            event_store.commit(original_event)
        except EventRedactedError:
            pass
        else:
            raise AssertionError("redacted durable event identity was allowed to resurrect")

        purge = await projection.purge_event_redactions_async(event_store=event_store)
        if len(purge) != 1 or purge[0].status != "redacted":
            raise AssertionError(f"active projection purge failed: {purge}")
        if not projection.ledger.is_redacted(event_id):
            raise AssertionError("projection redaction ledger was not recorded")

        after_purge = await observe_pack(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            group_id=PACK_ID,
            episode_name=episode_name,
        )
        if after_purge["episode_count"] != 0:
            raise AssertionError("redacted Graphiti episode remains active")
        if after_purge["entity_count"] != 0:
            raise AssertionError("entities solely mentioned by redacted episode remain active")
        if after_purge["fact_edge_count"] != 0:
            raise AssertionError("facts created by redacted episode remain active")

        fresh = GraphitiProjectionAdapter(
            client=graphiti,
            ledger=ProjectionLedger(
                root / "projection-ledger",
                GraphitiProjectionAdapter.name,
                build_id="redaction-fresh-rebuild-1",
            ),
            build_manifest={**build_manifest, "projection_build_id": "redaction-fresh-rebuild-1"},
            episode_type_json=EpisodeType.json,
        )
        rebuild_receipts = await fresh.rebuild_async(events_root=event_store.root)
        if rebuild_receipts:
            raise AssertionError(
                f"fresh rebuild attempted to replay redacted event: {rebuild_receipts}"
            )
        after_rebuild = await observe_pack(
            neo4j_uri,
            neo4j_user,
            neo4j_password,
            group_id=PACK_ID,
            episode_name=episode_name,
        )
        if after_rebuild != after_purge:
            raise AssertionError("fresh rebuild changed redacted pack materialization")

        proof.update(
            {
                "status": "passed",
                "event_id": event_id,
                "episode_name": episode_name,
                "episode_uuid": str(episode_uuid),
                "build_manifest": build_manifest,
                "before_redaction": before,
                "event_tombstone": tombstone,
                "purge_receipt": {
                    "status": purge[0].status,
                    "detail": purge[0].detail,
                },
                "after_active_purge": after_purge,
                "fresh_rebuild_receipts": [],
                "after_fresh_rebuild": after_rebuild,
                "canonical_event_bytes_deleted": True,
                "same_event_identity_republication_blocked": True,
            }
        )
    except Exception as exc:
        proof["status"] = "failed"
        proof["error"] = {"type": type(exc).__name__, "message": str(exc)}
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
