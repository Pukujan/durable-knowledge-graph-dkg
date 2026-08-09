# Gate 1 Agent Skills + Thin Corpus API/MCP Proof

Date: 2026-08-09  
Issue: #8 — Agent Skills + thin corpus API/MCP contract

This checkpoint records the first safe agent-facing boundary over FOSSIL. The boundary is deliberately protocol-independent at the domain layer: Agent Skills provide lazily loaded methodology, the corpus service exposes a small capability surface, and MCP is represented only as a replaceable adapter.

## Result

**PASS.** Agent proposals can be searched/read/derived/validated/committed only through pack- and Skill-gated corpus capabilities; committed agent events preserve actor/model/harness/skill provenance; durable commit remains authoritative; and the normal adapter exposes no arbitrary Neo4j/Graphiti mutation escape hatch.

## Progressive-disclosure Skills

The repository now contains six validated Skill manifests plus methodology files:

- `skill_corpus-search`
- `skill_research-ingestion`
- `skill_citation-audit`
- `skill_contradiction-review`
- `skill_stale-assumption-review`
- `skill_knowledge-promotion`

Contract: `schemas/agent-skill/v1.schema.json`.

Each manifest contains small discovery metadata (name, summary, triggers, allowed corpus capabilities, methodology reference). `SkillRegistry` validates/discovers manifests without reading the full `SKILL.md` body. Methodology text is loaded only through the explicit `load_methodology()` call.

This keeps routine tool/methodology context small while retaining versioned, auditable workflows in Git.

## Protocol-independent domain service

`src/dkg/agent.py` adds `CorpusService` with the deliberately small capability vocabulary:

- `search`
- `read`
- `lineage`
- `propose`
- `validate`
- `commit`
- `manage`

The service imports no MCP SDK and owns no Graphiti/Neo4j client. Durable event commit is the normal mutation path; projection workers remain downstream of accepted events.

`DurableEventStore` now exposes a non-mutating `prepare`/`validate` path so agent proposals can receive deterministic event identity and schema validation before publication.

## Agent provenance

Every agent session uses an `AgentContext` containing:

- actor ID;
- model ID;
- harness version;
- Skill ID;
- Skill version.

A proposed durable event places those values in the event's canonical `actor` object. The service additionally records the Skill version in `provenance.prompt_or_policy_ref`.

`validate` and `commit` reject an event whose actor/model/harness/Skill provenance does not exactly match the active agent context. This prevents a caller from passing a proposal generated under one model/Skill context while claiming it was committed under another.

## Two independent permission gates

Normal mutation requires both:

1. **pack permission** — target pack must be in `PackAccess.write_targets`;
2. **Skill capability** — the active Skill manifest must grant the requested corpus capability.

Example: contradiction review can propose and validate review events but its initial Skill contract does not grant `commit`. Research ingestion and knowledge promotion do grant commit because their workflows explicitly include validated durable publication.

The tests prove a caller mounted on the AI pack cannot write the common pack unless its pack access explicitly permits that target.

## Search/read boundary

Search operates over durable event content and only returns events from mounted readable packs. Results use stable FOSSIL event/pack/subject/evidence IDs and do not expose graph-native node identifiers.

Read re-checks the event's pack before returning it.

Lineage is injected into the service as a domain object and is likewise pack-gated; the service returns current/historical lineage and exact citations without requiring the transport adapter to understand the underlying storage/projection.

## Knowledge promotion

The `skill_knowledge-promotion` workflow uses the existing explicit `knowledge.promoted` durable event contract:

- source pack remains unchanged;
- target pack must be writable;
- source pack must be readable;
- stable subject and evidence refs are retained;
- agent/model/harness/Skill provenance is retained;
- the event receives deterministic idempotency identity before commit.

## Thin MCP adapter

`ThinMCPAdapter` is intentionally a small dictionary adapter over `CorpusService` with only:

- `fossil.search`
- `fossil.read`
- `fossil.lineage`
- `fossil.propose`
- `fossil.validate`
- `fossil.commit`
- `fossil.manage`

The domain service has no MCP-specific types. A future real MCP server, HTTP API, CLI, or another agent protocol can map onto the same domain service without changing durable corpus schemas.

Unknown tools are rejected. The proof explicitly rejects attempted calls such as:

- `neo4j.cypher`
- `graphiti.add_episode`

`fossil.manage` is allowlisted to safe status/metadata operations; its capability response explicitly reports `arbitrary_graph_mutation: false`.

## CI evidence

Trusted GitHub Actions `DKG contract tests` run:

- run number: **118**
- run ID: `31341456769`
- job ID: `93315824532`
- CI merge SHA: `77562725f5aa632da023219c4a99cb9c838bb446`
- result: **39 passed in 0.51s**

Disposable CI PR #22 is not part of product code and remains unmerged.

## Acceptance conclusion

Issue #8 conditions are satisfied:

1. six required Agent Skill methodologies exist and validate;
2. methodology supports progressive disclosure rather than eager context loading;
3. internal corpus capability logic is protocol-independent;
4. the external/MCP-shaped surface is small and replaceable;
5. normal agents cannot execute arbitrary graph/database mutations;
6. pack read/write boundaries still apply at the agent layer;
7. Skill capabilities independently gate operations;
8. proposals/commits preserve actor/model/harness/Skill provenance;
9. validation can occur without mutating the durable event store;
10. durable commit remains the canonical mutation before projection.

The remaining executable Gate 1 checklist item is Issue #10: general source snapshots, citation provenance/quality, and explicit redaction/tombstone behavior. Retrieval/model benchmarking in Issue #7 remains the next replaceable-service performance gate after the durable provenance contract is complete.
