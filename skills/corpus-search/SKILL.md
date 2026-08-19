# Corpus Search

Load this methodology only when the task requires finding or reconstructing corpus knowledge.

1. Search and build context only from packs mounted for the caller; an explicit context request may narrow that scope but may never widen it.
2. Return stable FOSSIL IDs, pack IDs, event types, dates, and evidence/source refs before projection-native details.
3. Prefer durable source evidence and lineage over generated summaries when answering historical questions.
4. Distinguish current state from historical state and preserve disagreement.
5. Follow lineage/citations back to immutable evidence when a conclusion matters.
6. Never treat a graph-native node/edge UUID, retrieval/reranker score, or model consensus as canonical evidence.
