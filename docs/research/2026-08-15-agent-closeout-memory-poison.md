# Agent Closeouts as Context Poison

**Date:** 2026-08-15  
**State:** `provisional`  
**Evidence posture:** external papers/product docs + FOSSIL/Cortex synthesis. This note is **derived analysis**. Original URLs remain the primary sources. Model recap of those papers is not evidence.

## Research question

Agent closeouts / session handoffs are meant to stop later agents from looping on already-solved work. In practice they produce false positives, false negatives, stale claims, and context poison. How should Cortex V5 + FOSSIL encode “don’t redo this” **without ingesting closeout prose as truth**?

## FOSSIL / Cortex baseline being evaluated

Already accepted:

- D007 — model agreement is not evidence.
- D016 / ownership boundary — Cortex owns execution; FOSSIL owns knowledge.
- Closeouts, research recaps, and compressed context remain **candidates** until they pass snapshot + propose + validate + commit.
- Cortex V5 journal is a 24-hour TTL scratch pad (`journal.sqlite3`). That expiry is intentional. It is not Brain and not FOSSIL.

The remaining hole: later agents still want a “already done?” signal. If that signal is a closeout paragraph, the journal/handoff becomes a second, rotting memory system.

## External evidence reviewed

### 1. Context Rot — length alone degrades recall

**Source:** Kelly Hong, Anton Troynikov, Jeff Huber, *Context Rot: How Increasing Input Tokens Impacts LLM Performance* (Chroma, July 2025).  
**URL:** https://research.trychroma.com/context-rot

Eighteen models. Task difficulty held constant; only input length varied. Performance degrades non-uniformly. Needle-in-a-haystack is a false comfort (lexical retrieval). Focused LongMemEval (~300 tokens) beats the full ~113k history. Distractors and low lexical similarity accelerate collapse.

**FOSSIL implication:** dumping prior closeouts into the next prompt is the failure mode this paper measures. Retrieve a receipt + issue state, not a 12k-token recap.

**Limit:** controlled tasks, not Cortex specifically. Worse in real agent loops, not better.

### 2. Effective context engineering — compaction is lossy

**Source:** Anthropic, *Effective context engineering for AI agents* (September 2025).  
**URL:** https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

Context is a finite attention budget. “Overly aggressive compaction can result in the loss of subtle but critical context whose importance only becomes apparent later.” Compaction is a first lever, not a source of truth.

**FOSSIL implication:** persist pointers (receipt id, issue, SHA). Do not persist the compaction as durable state.

### 3. Lost in the Middle — recency/primacy

**Source:** Nelson F. Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* (2023).  
**URL:** https://arxiv.org/abs/2307.03172

U-shaped use of long context. Middle facts vanish. Latest closeout in a journal dump dominates.

**FOSSIL implication:** “don’t redo this” must not live as prose in the middle of a long journal.

### 4. AgentPoison — unverified memory is an attack surface

**Source:** Zhaorun Chen et al., *AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases* (2024).  
**URL:** https://arxiv.org/abs/2407.12784

&lt;0.1% poison in memory/RAG → high attack success with little benign drop. Retrieval-as-memory is not a ledger.

**FOSSIL implication:** do not embed-retrieve over past closeouts to decide skip/retry.

### 5. TMA-NM — summaries launder origin

**Source:** Yedidya Louck, *Trust Must Be Assigned, Not Measured* (2026).  
**URL:** https://arxiv.org/abs/2606.24322

Content scoring and lineage are malleable. Laundering channels include the agent’s own summarization, trusted-tool echo, and manufactured corroboration. Authority must be bound at **write time** to origin class.

**FOSSIL implication:** a closeout cannot upgrade `origin=model` to trusted policy. Summarization cannot raise authority.

### 6. MutMem — signed mutation ≠ truth

**Source:** Saidi, *MutMem* (2026).  
**URL:** https://arxiv.org/abs/2608.02843

Integrity and authorization prove the write happened and was allowed. They do **not** establish content truth.

**FOSSIL implication:** a hashed closeout file is still a model recap. Hash the **world** (inputs/outputs/tests), not the paragraph.

### 7. Provenance-capped belief memory

**Source:** Singh (2026).  
**URL:** https://arxiv.org/abs/2606.22030

Content-derived “reliability” is attackable. Large gap between token-F1 and LLM-as-judge on the same outputs. Trust must be capped by provenance, not by how confident the prose sounds.

**FOSSIL implication:** LLM-as-judge cannot certify “done.” Model-written reliability scores cannot promote a claim.

### 8. SafeClawBench — semantic pass ≠ state change

**Source:** Tian et al., *SafeClawBench* (2026).  
**URL:** https://arxiv.org/abs/2606.18356

Split semantic agreement, audit evidence, and sandbox state. 291/347 sandbox harms occurred on rows that passed the semantic check.

**FOSSIL implication:** “the model said done” and “the checker passed” are different objects. Only the latter (plus hashes) may skip work.

### 9. LongMemEval — assistants drop knowledge across sessions

**Source:** Di Wu et al., *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory* (ICLR 2025).  
**URL:** https://arxiv.org/abs/2410.10813

Knowledge-update and abstention are first-class memory skills. Commercial assistants drop substantially across sessions.

**FOSSIL implication:** “remember we finished X” is exactly the knowledge-update task they fail. Use a ledger, not chat memory.

### 10. Product retreat from auto-memories

**Sources:**

- LangChain, *Memory for agents*: https://blog.langchain.dev/memory-for-agents/
- LangGraph memory: https://docs.langchain.com/oss/python/langgraph/memory
- Windsurf/Devin Cascade memories: https://docs.devin.ai/desktop/cascade/memories

Industry split: thread/scratch vs store. Cursor/Windsurf moved durable knowledge toward versioned Rules / AGENTS.md and away from auto-memories. Checkpointers replay; recaps do not.

**FOSSIL implication:** auto-closeout-as-memory is the pattern vendors are abandoning.

## Competing theories

1. **Better closeouts.** Write shorter, rubric-shaped, citation-heavy recaps. Rejected as the primary fix: TMA-NM and MutMem say the object is still model prose.
2. **Retrieve closeouts with RAG.** Rejected: AgentPoison.
3. **Keep closeouts forever in SQLite.** Rejected: that recreates SSC Brain; TTL exists to kill hypotheses.
4. **No memory at all.** Incomplete: agents will loop. Need a non-prose skip signal.
5. **Receipt + live issue + hash match (recommended).** Fail closed if any clause is missing.

## Recommended mechanism (provisional)

Skip work **without an LLM** iff:

- a receipt exists for the idempotency key;
- live input/output (or declared tests) still hash-match;
- the linked issue is closed;
- no tombstone / supersession exists.

Otherwise treat as open (occasional redo is cheaper than poisoned skip).

Layering:

| Layer | What | Authority |
|---|---|---|
| V5 journal (24h) | hypotheses, draft closeout prose | none |
| Receipt | key, hashes, tests, git SHA, issue | skip/retry |
| FOSSIL | snapshots + `proposed` claims citing receipts | never policy until a non-model gate |
| GitHub issue state | open / closed / blocked | what work is owed |

A closeout may **point** at a receipt id. The next agent follows the pointer. It does not believe the sentence.

## Claims (proposed, not accepted)

- `claim:closeout-prose-is-not-skip-authority`
- `claim:fail-closed-hash-receipt-prevents-false-done`
- `claim:journal-ttl-must-not-be-bypassed-by-jsonl`
- `claim:fossil-must-not-ingest-closeouts-as-evidence`

## Unresolved

- Exact receipt schema version and where it lives before FOSSIL local `serve` exists (V5-local append-only files vs FOSSIL event).
- Who may close the GitHub issue (human only vs gated bot that checks the receipt).
- Whether a passing V5 verification gate is sufficient `outputs_hash` or whether CI on the exact SHA is required.

## Architecture impact

Does **not** change D007, pack identity, or FOSSIL commit gates.

Refines the Cortex↔FOSSIL ownership note: Cortex closeouts stay execution packaging. They are not FOSSIL ingest. “Don’t redo this” is a receipt/issue predicate, not a memory write.
