# Production RAG Hardening Research Trace

**Date:** 2026-08-10  
**Campaign:** #48 — Post-Gate-2 production RAG hardening  
**State:** `accepted_for_campaign_planning`  
**Evidence posture:** external research/production documentation + FOSSIL-specific synthesis. The synthesis below is **derived analysis**, not a substitute for the original external sources.

## Research question

After Gate 2 established FOSSIL's durable knowledge contracts and an evidence-backed default retriever, what failure modes and design tradeoffs from current production RAG systems and 2025–2026 research should influence the next hardening campaign?

## FOSSIL baseline being evaluated

FOSSIL already treats the following as durable/canonical:

- immutable original evidence;
- corpus-owned stable identities;
- append-only validated knowledge-changing events;
- versioned ontology/contracts;
- explicit provenance;
- explicit history of disagreement, revision, supersession, retraction, and unresolved claims;
- pack-scoped read/write boundaries.

Graphiti/Neo4j, lexical/vector retrieval, embedding models, rerankers, context builders, model services, planners, Skills/MCP, and future databases remain replaceable projections/services.

Gate 2 decision D021 currently routes normal semantic retrieval through revision-pinned BGE dense retrieval with explicit degraded BM25 availability fallback. Current/latest/accepted questions must resolve lifecycle/provenance; lineage/history questions must use durable lineage/read operations; retrieval rank is not truth.

## External evidence reviewed

### 1. VersionRAG — version-aware retrieval over evolving documents

**Source:** Daniel Huwiler, Kurt Stockinger, Jonathan Fürst, *VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents* (2025).  
**URL:** https://arxiv.org/abs/2510.08109

Reported benchmark result on VersionQA:

- naive RAG: 58% accuracy on version-sensitive questions;
- GraphRAG: 64%;
- VersionRAG: 90%;
- VersionRAG reports 60% on implicit change detection where compared baselines reached 0–10%;
- the paper reports substantially lower indexing-token use than its GraphRAG comparison.

**FOSSIL implication:** this supports keeping version/history/lifecycle state outside retrieval rank. It also motivates an **evolving-corpus benchmark** that measures correctness before and after knowledge changes rather than only testing a frozen final corpus.

**Limit:** this is one framework and one purpose-built benchmark. Its exact graph design is not automatically a better implementation for FOSSIL.

### 2. TG-RAG — temporal graphs and incremental updates

**Source:** Jiale Han et al., *RAG Meets Temporal Graphs: Time-Sensitive Modeling and Retrieval for Evolving Knowledge* (2025).  
**URL:** https://arxiv.org/abs/2510.13590

The paper argues two recurring blind spots in conventional RAG:

1. same or similar facts valid at different times are difficult to distinguish with ordinary embeddings or conventional static graphs;
2. most RAG evaluation assumes a static corpus and therefore misses incremental-update cost and retrieval stability as knowledge evolves.

TG-RAG explicitly represents temporal facts and evaluates incremental updates.

**FOSSIL implication:** the canonical lifecycle/event model is aligned with the problem statement. The missing piece is a benchmark that exercises **incremental change, rebuild, and historical reconstruction** as a sequence.

**Limit:** temporal graph machinery is one possible projection strategy. FOSSIL should benchmark it behind replaceable interfaces rather than adopt it as canonical storage.

### 3. CReSt — practical RAG requires more than retrieval metrics

**Source:** Minsoo Khang, Sangjun Park, Teakgyu Hong, Dawoon Jung, *CReSt: A Comprehensive Benchmark for Retrieval-Augmented Generation with Complex Reasoning over Structured Documents* (2025).  
**URL:** https://arxiv.org/abs/2505.17503

CReSt contains 2,245 human-annotated English/Korean examples and evaluates dimensions including:

- complex reasoning;
- appropriate refusal when an answer should not be produced;
- precise citations;
- document-layout/structure understanding.

The authors report that advanced LLMs still struggle to perform consistently across these dimensions.

**FOSSIL implication:** Gate 2 retrieval metrics are necessary but insufficient. The next benchmark layer should measure **final answer correctness, citation correctness, unsupported claims, completeness, contradiction handling, and appropriate abstention**.

**Limit:** CReSt targets structured-document QA and two languages. FOSSIL should borrow evaluation dimensions, not assume benchmark scores transfer to its corpus.

### 4. URAG — retrieval noise can create confident errors

**Source:** Vinh Nguyen et al., *URAG: A Benchmark for Uncertainty Quantification in Retrieval-Augmented Large Language Models* (2026).  
**URL:** https://arxiv.org/abs/2603.19281

URAG evaluates eight standard RAG methods across multiple domains and reports:

- accuracy improvement often correlates with lower uncertainty, but the relationship breaks under retrieval noise;
- simpler modular RAG methods can offer better accuracy–uncertainty tradeoffs than more complex reasoning pipelines;
- no single RAG approach is universally reliable across domains;
- deeper retrieval, dependence on parametric knowledge, and exposure to confidence cues can amplify confident errors/hallucinations.

**FOSSIL implication:** uncertainty should be an output state, not merely an internal model score. Important answer paths should support explicit outcomes such as `insufficient evidence`, `conflicting evidence`, and `current state unresolved` rather than rewarding confident completion.

**Limit:** the benchmark reformulates tasks for principled uncertainty measurement; its exact metrics do not need to become FOSSIL's universal calibration method.

### 5. RAGRouter-Bench — no single retrieval paradigm wins everywhere

**Source:** Ziqi Wang et al., *RAGRouter-Bench: A Dataset and Benchmark for Adaptive RAG Routing* (2026).  
**URL:** https://arxiv.org/abs/2602.00296

RAGRouter-Bench standardizes five RAG paradigms across 7,727 queries and 21,460 documents and evaluates generation quality plus resource use. The paper reports that:

- no single RAG paradigm is universally optimal;
- applicability depends strongly on query–corpus interaction;
- adding more advanced mechanisms does not necessarily improve the effectiveness/efficiency tradeoff.

**FOSSIL implication:** routing is worth testing, but should start with **interpretable query classes** and a simple fixed baseline. LLM-planned retrieval should earn its additional latency, cost, and failure surface.

### 6. Text-and-table retrieval benchmark — hybrid + reranking can win, BM25 can still matter

**Source:** Meftun Akarsu, Recep Kaan Karaman, Christopher Mierbach, *From BM25 to Corrective RAG: Benchmarking Retrieval Strategies for Text-and-Table Documents* (2026).  
**URL:** https://arxiv.org/abs/2604.01733

The study compares ten retrieval strategies over 23,088 financial QA queries and 7,318 mixed text/table documents. It reports:

- two-stage hybrid retrieval + neural reranking: Recall@5 0.816 and MRR@3 0.605, best among its compared single/two-stage strategies;
- BM25 outperforms the tested state-of-the-art dense retrieval on this financial corpus;
- query expansion/adaptive retrieval provides limited benefit for precise numerical questions;
- contextual retrieval provides consistent gains in that evaluation.

**FOSSIL implication:** D021 should remain corpus-specific rather than being generalized into “dense is always better.” #47 should include real reranking and retain BM25/hybrid controls. Exact/identifier/numeric-style questions may deserve a lexical or hybrid route if FOSSIL's own benchmark proves it.

**Limit:** financial text/table QA differs materially from FOSSIL's current history-rich technical corpus.

### 7. Poisoning benchmark — advanced RAG does not remove ingestion/retrieval security risk

**Source:** Baolei Zhang et al., *Benchmarking Poisoning Attacks against Retrieval-Augmented Generation* (2025).  
**URL:** https://arxiv.org/abs/2505.18543

The benchmark covers 13 poisoning attacks and seven defenses across standard and expanded QA settings. The authors report that multiple advanced RAG architectures—including sequential, branching, conditional, looping, conversational, multimodal, and agentic RAG—remain susceptible, and that the evaluated defenses do not provide robust general protection.

**FOSSIL implication:** retrieved content must be treated as **untrusted data**, never executable system/policy instructions. FOSSIL needs adversarial cases for malicious documents, authority spoofing, fake supersession, duplicated poisoned passages, and conflicting evidence. Proposal-before-commit, pack boundaries, source identity, and evidence authority should be exercised under attack.

**Limit:** no single defense should be represented as solving poisoning. Residual risk must remain explicit.

### 8. Stronger long-context baselines — complexity needs to earn itself

**Source:** Alex Laitenberger, Christopher D. Manning, Nelson F. Liu, *Stronger Baselines for Retrieval-Augmented Generation with Long-Context Language Models* (2025; EMNLP 2025).  
**URL:** https://arxiv.org/abs/2506.03989

The paper compares multi-stage systems with simpler baselines under scaled token budgets. Its DOS RAG baseline preserves original document structure/order and consistently matches or outperforms the more intricate compared methods on multiple long-context QA benchmarks.

**FOSSIL implication:** every future graph/planner/query-expansion layer should be compared against strong **simple retrieve-then-read and direct-source-read baselines under matched context budgets**. Complexity is not a goal.

### 9. Anthropic Contextual Retrieval — contextual hybrid + reranking as a production pattern

**Source:** Anthropic, *Contextual Retrieval in AI Systems*.  
**URL:** https://www.anthropic.com/engineering/contextual-retrieval

Anthropic reports on its evaluated domains/configurations that:

- contextual embeddings reduced top-20 retrieval failure from 5.7% to 3.7%;
- contextual embeddings + contextual BM25 reduced it to 2.9% (49% relative reduction from the baseline);
- adding reranking reduced it to 1.9% (67% relative reduction from the baseline).

The article also explicitly notes the latency/cost tradeoff from reranking more candidates and recommends corpus-specific experimentation.

**FOSSIL implication:** a real contextualization/reranking bakeoff is justified, but it should remain a replaceable retrieval policy experiment. The existing `Reranker` interface means this does not require a canonical-storage redesign.

**Limit:** vendor-reported experiments are useful production evidence but are not independent proof that the same gains occur on FOSSIL.

### 10. Azure AI Search agentic retrieval — observable multi-query production orchestration

**Source:** Microsoft, *Agentic Retrieval Overview — Azure AI Search* and related 2026 documentation.  
**URLs:**

- https://learn.microsoft.com/en-us/azure/search/search-agentic-retrieval-concept
- https://learn.microsoft.com/en-us/azure/search/search-features-list

Current documented production pattern includes:

- conversation-aware query planning;
- decomposition into focused subqueries;
- parallel execution across knowledge sources;
- keyword, vector, and hybrid retrieval;
- semantic reranking;
- source references for citations;
- optional execution/activity details exposing the retrieval plan and runtime use.

**FOSSIL implication:** the useful architectural idea is not “let an agent search however it wants”; it is **observable routing with a reproducible execution record**. FOSSIL should retain a compact receipt for important queries containing service identities, candidate stable IDs, lifecycle/lineage resolution, context/citations, and outcome while leaving verbose telemetry outside canonical knowledge.

**Limit:** Azure's managed pipeline has different security, cost, and operational assumptions; it is an implementation reference, not a target architecture.

### 11. GraphRAG-Bench — evaluate the whole graph pipeline, not graph novelty

**Source:** Yilin Xiao et al., *GraphRAG-Bench: Challenging Domain-Specific Reasoning for Evaluating Graph Retrieval-Augmented Generation* (2025).  
**URL:** https://arxiv.org/abs/2506.02404

GraphRAG-Bench evaluates nine GraphRAG methods and explicitly separates graph construction, retrieval, answer generation, and reasoning quality across multi-hop domain questions.

**FOSSIL implication:** if a graph retrieval strategy is introduced, measure **construction cost, retrieval quality, answer quality, and reasoning behavior separately**. Graph-based retrieval remains a projection/service choice, not evidence that the graph should become canonical truth.

## Cross-source synthesis

### Findings that reinforce the existing architecture

1. **Temporal/version state must not be inferred from semantic similarity alone.**
   - Strong agreement with FOSSIL's explicit lifecycle/supersession/provenance design.
2. **No retriever, graph, planner, or model should become canonical truth.**
   - The research shows significant domain/query dependence and failure variation.
3. **Simple baselines must remain in every bakeoff.**
   - BM25 and straightforward long-context strategies continue to win in some settings.
4. **Reranking is worth serious evaluation.**
   - Multiple external sources show gains, but cost/latency and first-stage recall remain limiting factors.
5. **Final-answer reliability must be evaluated independently from retrieval.**
   - Retrieval can succeed while generation/citation/refusal fails.
6. **Uncertainty and abstention are product behavior, not model decoration.**
   - Noisy retrieval can increase confident error.
7. **Security does not disappear with more elaborate RAG.**
   - Poisoning remains a distinct ingestion/retrieval threat model.

### Gaps in current FOSSIL evidence

1. Gate 2 uses a history-rich corpus but does not yet execute a full **evolving-corpus sequence benchmark**.
2. Current benchmark contracts emphasize retrieval quality/resource metrics more than **end-to-end answer faithfulness/citation/abstention**.
3. Poisoning/untrusted-context behavior is not yet represented by a dedicated adversarial suite.
4. The `Reranker` interface exists, but Gate 2 did not benchmark a strong real neural/API reranker.
5. D021 routes lifecycle/lineage-sensitive questions explicitly, but broader **adaptive query routing** has not been benchmarked.
6. Important queries do not yet have a standardized **replayable execution receipt** covering route → candidates → rerank → lifecycle/lineage → context/citations → outcome.
7. Permission/redaction contracts exist conceptually, but shared/cloud deployment should wait for route-level ACL/redaction propagation tests.

## Recommended campaign order

1. **Evolving-corpus benchmark** — prove current/history correctness through actual knowledge changes.
2. **End-to-end answer/citation/abstention benchmark** — detect failures retrieval metrics cannot see.
3. **Poisoning/untrusted-context suite** — harden before broad automatic ingestion.
4. **Query execution receipt + replay proof** — make failures diagnosable and future model changes comparable.
5. **#47 embedding/reranker bakeoff** — BGE/BM25/hybrid plus current embedding candidates and a real reranker.
6. **Conservative adaptive routing** — only after the above evidence reveals stable query classes worth routing.
7. **ACL/redaction readiness** — required before multi-user/shared/cloud ingestion becomes a production goal.

## Explicit non-recommendations

Do **not**:

- replace the durable event/evidence model with a graph database;
- adopt a large GraphRAG pipeline merely because it is graph-based;
- equate top retrieval/reranker score with current truth;
- replace D021 based on a public leaderboard or aggregate embedding score;
- let retrieved text issue system/tool instructions;
- treat model consensus as evidence;
- hide provider/model/runtime substitution;
- allow a complex adaptive planner to become default without a matched simple-baseline win.

## Decision status

The research supports **hardening the existing architecture rather than redesigning its durable core**.

Campaign #48 should treat every proposed retrieval/planning/security technique as an evidence-driven competitor behind current contracts. Architectural invariants remain unchanged unless a later explicit decision with committed evidence supersedes them.

## Provenance / reconstruction note

This document is a 2026-08-10 FOSSIL-specific synthesis produced from the external sources listed above and the committed FOSSIL architecture/D021 state. It is intentionally suitable for later ingestion as a **local derived research artifact**. The original external papers/pages should be captured as their own source snapshots when the campaign implements full research-trace ingestion; this synthesis must not be misrepresented as verbatim source evidence.
