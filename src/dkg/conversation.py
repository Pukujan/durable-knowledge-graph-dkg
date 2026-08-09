from __future__ import annotations

import copy
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from dkg.artifact_store import ArtifactStore
from dkg.io import publish_immutable


class ConversationConflict(RuntimeError):
    pass


class ConversationProvenanceError(ValueError):
    pass


def _canonical(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _stable_id(prefix: str, *parts: str, length: int = 20) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:length]}"


class ConversationStore:
    """Immutable conversation envelopes over content-addressed source evidence.

    Source bytes live in :class:`ArtifactStore`. Conversation envelopes preserve
    message ordering, actor metadata, parent/reply relationships, and byte spans
    into those immutable source artifacts. `evidence_status` is semantic: a span
    can be byte-exact within a recovery checkpoint while still being explicitly
    `reconstructed` because the checkpoint itself is not a verbatim transcript.
    """

    def __init__(self, root: Path, artifact_store: ArtifactStore, schema_path: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifact_store = artifact_store
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def _path(self, conversation_id: str) -> Path:
        suffix = conversation_id.removeprefix("conv_")
        return self.root / suffix[:2] / f"{conversation_id}.json"

    def add_source(
        self,
        data: bytes,
        *,
        evidence_status: str,
        media_type: str = "text/plain",
        label: str = "",
        external_ref: str | None = None,
    ) -> dict[str, Any]:
        if evidence_status not in {"verbatim", "reconstructed"}:
            raise ValueError("source evidence_status must be verbatim or reconstructed")
        manifest = self.artifact_store.put_bytes(data, media_type=media_type)
        source_id = _stable_id(
            "src", manifest["artifact_id"], evidence_status, label, external_ref or ""
        )
        return {
            "source_id": source_id,
            "artifact_id": manifest["artifact_id"],
            "evidence_status": evidence_status,
            "label": label,
            "media_type": media_type,
            "external_ref": external_ref,
        }

    def span_for_text(
        self,
        source: Mapping[str, Any],
        needle: str,
        *,
        occurrence: int = 0,
        evidence_status: str | None = None,
    ) -> dict[str, Any]:
        if occurrence < 0:
            raise ValueError("occurrence must be non-negative")
        data = self.artifact_store.read_bytes(str(source["artifact_id"]))
        target = needle.encode("utf-8")
        start = -1
        cursor = 0
        for _ in range(occurrence + 1):
            start = data.find(target, cursor)
            if start < 0:
                raise ValueError(f"source text not found: {needle!r}")
            cursor = start + len(target)
        end = start + len(target)
        status = evidence_status or str(source["evidence_status"])
        span_id = _stable_id(
            "span", str(source["source_id"]), str(start), str(end), status
        )
        return {
            "span_id": span_id,
            "source_id": source["source_id"],
            "byte_start": start,
            "byte_end": end,
            "evidence_status": status,
        }

    def resolve_span_bytes(
        self, envelope: Mapping[str, Any], span_id: str
    ) -> bytes:
        span = next(
            (item for item in envelope["spans"] if item["span_id"] == span_id), None
        )
        if span is None:
            raise KeyError(span_id)
        source = next(
            (
                item
                for item in envelope["sources"]
                if item["source_id"] == span["source_id"]
            ),
            None,
        )
        if source is None:
            raise ConversationProvenanceError(
                f"span {span_id} references missing source {span['source_id']}"
            )
        data = self.artifact_store.read_bytes(source["artifact_id"])
        start = int(span["byte_start"])
        end = int(span["byte_end"])
        if start < 0 or end <= start or end > len(data):
            raise ConversationProvenanceError(
                f"span {span_id} is outside immutable source artifact bounds"
            )
        return data[start:end]

    def resolve_span_text(self, envelope: Mapping[str, Any], span_id: str) -> str:
        try:
            return self.resolve_span_bytes(envelope, span_id).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ConversationProvenanceError(
                f"span {span_id} is not valid UTF-8 text"
            ) from exc

    def _validate_provenance(self, envelope: Mapping[str, Any]) -> None:
        sources = {source["source_id"]: source for source in envelope["sources"]}
        if len(sources) != len(envelope["sources"]):
            raise ConversationProvenanceError("duplicate source_id")

        for source in sources.values():
            self.artifact_store.verify(source["artifact_id"])

        spans = {span["span_id"]: span for span in envelope["spans"]}
        if len(spans) != len(envelope["spans"]):
            raise ConversationProvenanceError("duplicate span_id")
        for span in spans.values():
            source = sources.get(span["source_id"])
            if source is None:
                raise ConversationProvenanceError(
                    f"span {span['span_id']} references unknown source"
                )
            if (
                source["evidence_status"] == "reconstructed"
                and span["evidence_status"] == "verbatim"
            ):
                raise ConversationProvenanceError(
                    "a reconstructed source cannot silently yield a verbatim span"
                )
            self.resolve_span_bytes(envelope, span["span_id"])

        messages = {message["message_id"]: message for message in envelope["messages"]}
        if len(messages) != len(envelope["messages"]):
            raise ConversationProvenanceError("duplicate message_id")
        sequences = [int(message["sequence"]) for message in envelope["messages"]]
        if len(set(sequences)) != len(sequences):
            raise ConversationProvenanceError("message sequence values must be unique")

        for message in envelope["messages"]:
            parent_id = message["parent_message_id"]
            if parent_id is not None:
                parent = messages.get(parent_id)
                if parent is None:
                    raise ConversationProvenanceError(
                        f"message {message['message_id']} references missing parent"
                    )
                if int(parent["sequence"]) >= int(message["sequence"]):
                    raise ConversationProvenanceError(
                        "message parent must occur before the child message"
                    )

            refs = message["source_span_refs"]
            referenced_spans = []
            for span_id in refs:
                if span_id not in spans:
                    raise ConversationProvenanceError(
                        f"message {message['message_id']} references missing span {span_id}"
                    )
                referenced_spans.append(spans[span_id])

            if message["evidence_status"] == "verbatim":
                if any(span["evidence_status"] != "verbatim" for span in referenced_spans):
                    raise ConversationProvenanceError(
                        "verbatim message cannot depend on reconstructed source spans"
                    )
                exact_text = "".join(
                    self.resolve_span_text(envelope, span_id) for span_id in refs
                )
                if exact_text != message["text"]:
                    raise ConversationProvenanceError(
                        "verbatim message text must exactly equal its immutable source span(s)"
                    )

        source_status = envelope["source_status"]
        statuses = {message["evidence_status"] for message in envelope["messages"]}
        if source_status == "verbatim" and statuses != {"verbatim"}:
            raise ConversationProvenanceError(
                "verbatim conversation cannot contain reconstructed messages"
            )
        if source_status == "reconstructed" and "verbatim" in statuses:
            raise ConversationProvenanceError(
                "reconstructed conversation cannot silently contain verbatim messages; use mixed"
            )

    def commit(self, envelope: dict[str, Any]) -> dict[str, Any]:
        candidate = copy.deepcopy(envelope)
        self.validator.validate(candidate)
        self._validate_provenance(candidate)
        path = self._path(candidate["conversation_id"])
        data = _canonical(candidate)
        if publish_immutable(path, data):
            return candidate
        existing = json.loads(path.read_text(encoding="utf-8"))
        if _canonical(existing) == data:
            return existing
        raise ConversationConflict(
            f"conversation {candidate['conversation_id']} already exists with different content"
        )

    def get(self, conversation_id: str) -> dict[str, Any]:
        return json.loads(self._path(conversation_id).read_text(encoding="utf-8"))

    @staticmethod
    def ordered_messages(envelope: Mapping[str, Any]) -> list[dict[str, Any]]:
        return sorted(envelope["messages"], key=lambda message: int(message["sequence"]))

    @staticmethod
    def build_ingested_event(
        envelope: Mapping[str, Any],
        *,
        pack_id: str,
        actor_id: str,
        occurred_at: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        artifact_ids = [source["artifact_id"] for source in envelope["sources"]]
        return {
            "schema_version": "dkg.event.v1",
            "event_type": "conversation.ingested",
            "occurred_at": occurred_at,
            "recorded_at": recorded_at,
            "pack_id": pack_id,
            "actor": {"actor_type": "importer", "actor_id": actor_id},
            "subject_refs": [envelope["conversation_id"]],
            "evidence_refs": artifact_ids,
            "idempotency_key": f"conversation-ingested:{envelope['conversation_id']}",
            "payload": {
                "conversation_id": envelope["conversation_id"],
                "source_status": envelope["source_status"],
                "source_artifact_ids": artifact_ids,
                "message_ids": [
                    message["message_id"]
                    for message in ConversationStore.ordered_messages(envelope)
                ],
            },
        }


class ConversationLineage:
    """Deterministic query layer over derived conversation intellectual lineage."""

    OPPOSITION_RELATIONS = {"challenges", "rebuts"}
    PATH_RELATIONS = {
        "leads_to",
        "supports",
        "reframes",
        "supersedes",
        "depends_on",
    }

    def __init__(
        self,
        lineage: dict[str, Any],
        *,
        schema_path: Path,
        conversation_store: ConversationStore,
        envelope: Mapping[str, Any],
    ):
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.validator.validate(lineage)
        if lineage["conversation_id"] != envelope["conversation_id"]:
            raise ConversationProvenanceError(
                "lineage conversation_id does not match conversation envelope"
            )
        self.lineage = copy.deepcopy(lineage)
        self.conversation_store = conversation_store
        self.envelope = envelope
        self.nodes = {node["node_id"]: node for node in lineage["nodes"]}
        self.edges = list(lineage["edges"])
        self._validate_references()

    def _validate_references(self) -> None:
        if len(self.nodes) != len(self.lineage["nodes"]):
            raise ConversationProvenanceError("duplicate lineage node_id")
        message_map = {
            message["message_id"]: message for message in self.envelope["messages"]
        }
        span_ids = {span["span_id"] for span in self.envelope["spans"]}

        edge_ids: set[str] = set()
        for edge in self.edges:
            if edge["edge_id"] in edge_ids:
                raise ConversationProvenanceError("duplicate lineage edge_id")
            edge_ids.add(edge["edge_id"])
            if edge["source_node_id"] not in self.nodes or edge["target_node_id"] not in self.nodes:
                raise ConversationProvenanceError("lineage edge references missing node")

        for node in self.nodes.values():
            source_messages = []
            for message_id in node["source_message_refs"]:
                message = message_map.get(message_id)
                if message is None:
                    raise ConversationProvenanceError(
                        f"lineage node {node['node_id']} references missing message"
                    )
                source_messages.append(message)
            for span_id in node["source_span_refs"]:
                if span_id not in span_ids:
                    raise ConversationProvenanceError(
                        f"lineage node {node['node_id']} references missing span"
                    )
                self.conversation_store.resolve_span_bytes(self.envelope, span_id)
            if node["evidence_status"] == "verbatim" and any(
                message["evidence_status"] != "verbatim" for message in source_messages
            ):
                raise ConversationProvenanceError(
                    "verbatim-derived lineage node cannot depend on reconstructed messages"
                )

        for node_id in self.lineage["current_conclusion_refs"]:
            node = self.nodes.get(node_id)
            if node is None:
                raise ConversationProvenanceError(
                    f"current conclusion references missing node {node_id}"
                )
            if node["kind"] not in {"conclusion", "decision"}:
                raise ConversationProvenanceError(
                    "current conclusion ref must point to a conclusion or decision"
                )
            if node["position_state"] != "current":
                raise ConversationProvenanceError(
                    "current conclusion ref must point to current position state"
                )

    def node(self, node_id: str) -> dict[str, Any]:
        return copy.deepcopy(self.nodes[node_id])

    def current_conclusions(self) -> list[dict[str, Any]]:
        return [self.node(node_id) for node_id in self.lineage["current_conclusion_refs"]]

    def historical_nodes(self) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(node)
            for node in self.lineage["nodes"]
            if node["position_state"] == "historical"
        ]

    def path(
        self,
        start_node_id: str,
        end_node_id: str,
        *,
        relation_types: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        allowed = relation_types or self.PATH_RELATIONS
        adjacency: dict[str, list[tuple[str, str]]] = {}
        for edge in sorted(self.edges, key=lambda item: item["edge_id"]):
            if edge["relation_type"] not in allowed:
                continue
            adjacency.setdefault(edge["source_node_id"], []).append(
                (edge["edge_id"], edge["target_node_id"])
            )

        queue: deque[tuple[str, list[str]]] = deque([(start_node_id, [start_node_id])])
        visited = {start_node_id}
        while queue:
            current, current_path = queue.popleft()
            if current == end_node_id:
                return [self.node(node_id) for node_id in current_path]
            for _, target in adjacency.get(current, []):
                if target in visited:
                    continue
                visited.add(target)
                queue.append((target, [*current_path, target]))
        return []

    def opposing_positions(self, node_id: str) -> list[dict[str, Any]]:
        opponents: set[str] = set()
        for edge in self.edges:
            if edge["relation_type"] not in self.OPPOSITION_RELATIONS:
                continue
            if edge["source_node_id"] == node_id:
                opponents.add(edge["target_node_id"])
            elif edge["target_node_id"] == node_id:
                opponents.add(edge["source_node_id"])
        return [self.node(opponent) for opponent in sorted(opponents)]

    def citations(self, node_id: str) -> list[dict[str, Any]]:
        node = self.nodes[node_id]
        span_map = {span["span_id"]: span for span in self.envelope["spans"]}
        source_map = {
            source["source_id"]: source for source in self.envelope["sources"]
        }
        citations = []
        for span_id in node["source_span_refs"]:
            span = span_map[span_id]
            source = source_map[span["source_id"]]
            citations.append(
                {
                    "span_id": span_id,
                    "artifact_id": source["artifact_id"],
                    "evidence_status": span["evidence_status"],
                    "byte_start": span["byte_start"],
                    "byte_end": span["byte_end"],
                    "text": self.conversation_store.resolve_span_text(
                        self.envelope, span_id
                    ),
                }
            )
        return citations

    def benchmark(
        self,
        *,
        required_path: Sequence[str],
        current_conclusion_ref: str,
        opposing_pairs: Iterable[tuple[str, str]],
    ) -> dict[str, Any]:
        if not required_path:
            raise ValueError("required_path cannot be empty")
        reconstructed = self.path(required_path[0], required_path[-1])
        actual_path = [node["node_id"] for node in reconstructed]
        path_matches = actual_path == list(required_path)
        citation_nodes = set(required_path) | {current_conclusion_ref}
        for left, right in opposing_pairs:
            citation_nodes.update({left, right})
        citations_resolve = all(self.citations(node_id) for node_id in citation_nodes)
        current_queryable = current_conclusion_ref in {
            node["node_id"] for node in self.current_conclusions()
        }
        opposing_results: dict[str, bool] = {}
        for left, right in opposing_pairs:
            opposing_results[f"{left}<->{right}"] = right in {
                node["node_id"] for node in self.opposing_positions(left)
            }
        historical_queryable = bool(self.historical_nodes()) and bool(reconstructed)
        passed = (
            path_matches
            and citations_resolve
            and current_queryable
            and historical_queryable
            and all(opposing_results.values())
        )
        return {
            "passed": passed,
            "required_path": list(required_path),
            "actual_path": actual_path,
            "path_matches": path_matches,
            "citations_resolve": citations_resolve,
            "current_conclusion_queryable": current_queryable,
            "historical_path_queryable": historical_queryable,
            "opposing_positions_queryable": opposing_results,
        }
