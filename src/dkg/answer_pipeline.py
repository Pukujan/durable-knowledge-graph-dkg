from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping


def expand_context_with_lineage(
    context_items: Iterable[Mapping[str, Any]],
    *,
    documents: Iterable[Mapping[str, Any]],
    pack_ids: Iterable[str],
    max_expansions: int = 24,
) -> list[dict[str, Any]]:
    """Expand retrieved relation endpoints from the durable corpus before answering.

    Retrieval rank remains candidate ordering. When retrieval returns a durable relation,
    its stable source/target references are resolved from the mounted packs so top-k absence
    cannot erase lineage needed for a current/history answer.
    """

    if max_expansions < 0:
        raise ValueError("max_expansions must be non-negative")
    allowed = {str(pack_id) for pack_id in pack_ids}
    document_by_id = {
        str(document["id"]): copy.deepcopy(dict(document))
        for document in documents
        if str(document.get("pack_id", "")) in allowed
    }
    selected = [copy.deepcopy(dict(item)) for item in context_items]
    selected_ids = {str(item.get("id", "")) for item in selected}
    expansion_ids: list[str] = []

    for item in selected:
        if str(item.get("document_type", "")) != "relation":
            continue
        for key in ("source_ref", "target_ref"):
            identifier = str(item.get(key, ""))
            if identifier and identifier not in selected_ids and identifier in document_by_id:
                expansion_ids.append(identifier)
                selected_ids.add(identifier)
                if len(expansion_ids) >= max_expansions:
                    break
        if len(expansion_ids) >= max_expansions:
            break

    for identifier in expansion_ids:
        item = document_by_id[identifier]
        item["context_expansion"] = {
            "reason": "durable_relation_endpoint",
            "resolver": "fossil-lineage-context-v1",
        }
        selected.append(item)
    return selected


class LineageResolvedModelService:
    """Wrap any ModelService with deterministic durable-lineage context resolution."""

    def __init__(
        self,
        service: Any,
        *,
        documents: Iterable[Mapping[str, Any]],
        max_expansions: int = 24,
    ) -> None:
        self.service = service
        self.documents = [copy.deepcopy(dict(document)) for document in documents]
        self.max_expansions = int(max_expansions)
        if self.max_expansions < 0:
            raise ValueError("max_expansions must be non-negative")

    def metadata(self) -> dict[str, Any]:
        metadata = copy.deepcopy(dict(self.service.metadata()))
        runtime = dict(metadata.get("runtime", {}))
        runtime["lineage_context_resolver"] = "fossil-lineage-context-v1"
        runtime["lineage_max_expansions"] = str(self.max_expansions)
        metadata["runtime"] = runtime
        return metadata

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        request = copy.deepcopy(task)
        request["context_items"] = expand_context_with_lineage(
            request.get("context_items", []),
            documents=self.documents,
            pack_ids=request.get("pack_ids", []),
            max_expansions=self.max_expansions,
        )
        response = copy.deepcopy(dict(self.service.run(request)))
        response["service"] = self.metadata()
        return response
