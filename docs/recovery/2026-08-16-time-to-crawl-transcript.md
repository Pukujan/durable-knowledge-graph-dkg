# Time to Crawl project-scope transcript

Source URL: https://chatgpt.com/share/6a81ec29-8d24-83ea-9fdd-db97df8ee576?ogimg=plain  
Capture date: 2026-08-16  
Target project: `Pukujan/time-to-crawl`  
FOSSIL destination: `Pukujan/fossil-core`  
Evidence status: reconstructed

This is a normalized, decision-bearing transcript reconstructed from the visible
shared-page payload. It is not a verbatim ChatGPT export. The public page and
the normalized capture are retained as separate evidence classes; this file
must not be treated as a verbatim source or as independently verified research.
The source conversation requested a project-scope and methodology summary
before any GitHub issue hierarchy is created. No GitHub issues are created by
this intake.

## Turn 0 — human

Please ingest this research into my FOSSIL Core repository. Use
`Pukujan/time-to-crawl` as the separate product project, summarize the agreed
project scope and project methodology first, and leave issue-list creation for
later.

## Turn 1 — assistant

Use `Pukujan/time-to-crawl` as the canonical product repository. Do not import
the conversation verbatim into that project. Distill it into specifications,
architecture decision records, module manifests, GitHub milestone/issue
structure, and walking-skeleton acceptance scenarios.

Time to Crawl is a modular deal-intelligence platform.

## Turn 2 — human

The end goal should be whether a realistic shopper finds a useful result, not
just whether a crawler fetched pages or returned valid JSON. Human review should
define and calibrate the scenarios, but should not be required for every run.

## Turn 3 — assistant

Make a black-box synthetic-shopper evaluation the top-level acceptance test.
Generate realistic paraphrases, typos, budgets, locations, ambiguity, and
condition requirements. Automated checks should verify relevance, provenance,
duplicates, price and location constraints, and result usefulness. Humans
calibrate scenario families and adjudicate evaluation design, not every
execution.

## Turn 4 — human

The crawler should discover both specified and previously unknown sources,
support multiple extraction strategies, use a VPS/tailnet for operation, and
remain modular enough to add or remove source types and schemas without making
an unmaintainable pile of code. It also needs strict boundaries, quality gates,
fuzzing, mutation tests, documentation, and agent handoff rules.

## Turn 5 — assistant

Build a modular monolith with ports-and-adapters boundaries. The application
contains a `Merchant Scout` acquisition subsystem and a `Deal Finder`
purchasing-intelligence subsystem. Use shared crawler infrastructure with
generic, platform, domain-specific, and structured-LLM extraction fallbacks.
Treat all Internet content as untrusted: approved sources receive configured
policies, unknown sources enter quarantine, and a deterministic Scope Guard
authorizes domains, redirects, methods, ports, budgets, and network targets.
LLMs may classify, extract, or recommend; deterministic policy validates and
authorizes.

Use PostgreSQL for canonical live state, R2/object storage for raw evidence,
and CSV/Parquet for exports and analysis. Preserve provenance from source URL
through raw artifact, extraction version, schema version, observation, and
ranked result. Keep browser workers isolated and deny them credentials and
private-network access.

## Turn 6 — human

Make the development process agent-first but reproducible: specifications,
module ownership, an architecture compiler, strict typing, import checks,
property/state-machine tests, fuzzing, mutation testing, replay fixtures,
documentation-as-definition-of-done, explicit write scopes, and GitHub project
tracking. Start with a real walking skeleton rather than a throwaway demo.

## Turn 7 — assistant

The implementation method is spec-driven and evidence-led. Begin with a
governance milestone that proves the guardrails catch illegal imports, broken
contracts, undeclared dependencies, missing documentation, surviving mutants,
and forbidden file changes. Then build one thin end-to-end path through
discovery, scope enforcement, frontier, fetch, raw artifact, extraction,
product/offer persistence, ranking, API, export, telemetry, and verification.

Use GitHub as execution coordination (`project → milestone → epic → capability
→ task → subtask`), while repository specifications and durable FOSSIL evidence
remain technical authority. Keep replay evaluation separate from real-Internet
expeditions, declare VPS-required checks explicitly, and do not call optional
infrastructure foundational until corpus-specific evidence justifies it.
