# Gate 1 Conversation Ingestion + Intellectual-Lineage Proof

Date: 2026-08-09  
Issue: #9 — Conversation ingestion + intellectual-lineage reconstruction benchmark

This checkpoint proves that FOSSIL can preserve conversation evidence without laundering reconstruction into verbatim history, derive intellectual lineage with exact source-span provenance, and query both the current conclusion and the historical path that led to it.

## Result

**PASS.** The recovered DKG conversation lineage benchmark reconstructs the required conceptual path, preserves opposing positions, resolves every benchmark citation to immutable artifact byte spans, and keeps the recovery corpus explicitly labeled `reconstructed`.

The original missing chat is **still not claimed to be recovered verbatim**. The benchmark uses a durable reconstructed source whose status is explicit and whose basis is the surviving recovery checkpoint, research-trace seed, and Issue #9 requirement. If a real transcript/export appears later, it must be ingested separately as primary `verbatim` evidence rather than overwriting this reconstruction.

## Durable implementation

### Conversation evidence contract

`schemas/conversation/v1.schema.json` defines:

- stable conversation/message/source/span identities;
- conversation-level source status: `verbatim`, `reconstructed`, or `mixed`;
- source-level and span-level evidence status;
- byte-addressable spans into immutable content-addressed artifacts;
- message sequence and parent/reply relationships;
- actor role/ID plus optional provider/model/run/tool metadata;
- explicit reconstruction-basis references.

`src/dkg/conversation.py` adds `ConversationStore`:

- source bytes are stored in `ArtifactStore` and verified by content hash;
- conversation envelopes are immutable/idempotent;
- source spans resolve by exact UTF-8 byte offsets;
- parent messages must precede children;
- a reconstructed source cannot silently yield a `verbatim` span;
- a `verbatim` message must equal the exact concatenated immutable source span bytes after UTF-8 decoding;
- a reconstructed conversation cannot silently contain verbatim messages; mixed evidence must be labeled `mixed`;
- ingestion can emit a durable `conversation.ingested` knowledge event whose `evidence_refs` point to the source artifacts.

This makes evidence status a durable semantic property rather than a UI convention.

### Derived lineage contract

`schemas/conversation-lineage/v1.schema.json` defines lineage nodes for:

- observation;
- question;
- claim;
- challenge;
- rebuttal;
- assumption;
- conclusion;
- position change;
- decision.

Lineage edges include:

- `leads_to`;
- `supports`;
- `challenges`;
- `rebuts`;
- `reframes`;
- `supersedes`;
- `depends_on`.

Every lineage node must retain both source message refs and source span refs. A lineage node cannot be labeled verbatim-derived if its source messages are reconstructed.

`ConversationLineage` provides deterministic queries for:

- historical path reconstruction;
- current conclusions;
- historical nodes;
- opposing positions;
- source citations with artifact ID + byte range + exact text;
- a benchmark combining path, citation, opposition, current-state, and historical-state checks.

## Recovered benchmark source

The committed source is:

`docs/recovery/2026-08-09-conversation-lineage-benchmark-source.md`

It begins by declaring:

`Evidence status: reconstructed — not a verbatim transcript of the missing chat.`

Its reconstruction basis is explicitly recorded as:

- `docs/recovery/2026-08-09-chat-recovery-checkpoint.md`;
- `docs/research/2026-08-09-dkg-project-research-trace-seed.md`;
- GitHub Issue #9.

The machine-readable benchmark specification is:

`examples/conversation-lineage/recovered-dkg-lineage-v1.json`

## Required intellectual path

The deterministic benchmark reconstructs exactly:

```text
learning UX / parabola
  -> representation mismatch
  -> AI translation layer
  -> failure learning
  -> MAPE-K / KEDB
  -> truth maintenance
  -> temporal knowledge graph
```

Every stage is represented as reconstructed evidence and cites an exact byte span in the immutable source artifact.

## Opposing positions remain retrievable

The benchmark does not collapse alternatives into a consensus sentence.

It separately preserves/query-tests:

1. `database as canonical corpus` vs `durable events become canonical`;
2. `graph as canonical corpus` vs `rebuildable graph projection`.

The current architecture can therefore be queried without deleting the historical alternatives it displaced.

## Claim/review roles preserved

The recovered benchmark includes and provenance-checks examples of:

- observations;
- claims;
- assumptions;
- challenges;
- rebuttals;
- conclusions;
- changes of position;
- decisions.

It also preserves the recovered rule that multi-model agreement is review metadata rather than external evidence, and the corresponding rebuttal that important claims require sources/tests/experiments or other external truth signals.

## Verbatim-vs-reconstructed safety proof

The unit suite proves both directions:

- a synthetic available verbatim source round-trips from immutable artifact bytes to an exact source span/message;
- changing the message text while retaining `verbatim` status is rejected;
- a reconstructed source cannot be silently upgraded to a verbatim message/span.

The synthetic verbatim fixture tests the mechanism only. It does **not** pretend the lost DKG chat was recovered verbatim.

## Durable ingestion event

The benchmark conversation can be represented by a schema-valid durable event:

`conversation.ingested`

The event:

- uses the stable conversation ID as a subject ref;
- records `source_status=reconstructed`;
- lists stable message IDs;
- places the content-addressed source artifact in `evidence_refs`;
- remains deterministically idempotent through the durable event store.

## CI evidence

The first trusted CI run reached the new tests but failed only because six fixture edge IDs were one character shorter than the lineage schema minimum. The schema was **not weakened**; the fixture IDs were corrected.

Successful trusted GitHub Actions run:

- workflow: `DKG contract tests`
- run number: **97**
- run ID: `31340924480`
- job ID: `93314435997`
- CI merge SHA: `03cf0aa308343a77a33c786368a9e0764003aade`
- result: **31 passed in 0.37s**

## Acceptance conclusion

Issue #9 conditions are satisfied:

1. raw/verbatim evidence has an exact immutable preservation path when available;
2. reconstructed recovery material remains explicitly reconstructed;
3. source citations resolve to immutable artifacts and byte spans;
4. claims/challenges/rebuttals/assumptions/conclusions/position changes retain provenance;
5. the required recovered intellectual path is reconstructed deterministically;
6. opposing positions remain separately retrievable;
7. current conclusion and historical path are both queryable;
8. the UI/chat-loss recovery artifact is treated as provenance rather than silently rewritten as verbatim history.

## Scope boundary

This checkpoint proves the durable ingestion/provenance/lineage contract and the first recovered-conversation benchmark. It does not yet claim support for every vendor-specific chat export format. Vendor/export adapters should normalize into this contract without weakening evidence status.

The next Gate 1 task is Issue #8: safe Agent Skills + thin corpus API/MCP boundary. General source-snapshot quality/redaction work in Issue #10 remains cross-cutting and is not closed by this conversation-specific citation proof.
