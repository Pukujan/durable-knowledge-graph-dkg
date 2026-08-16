# Time to Crawl — project scope and methodology

Source conversation: [shared ChatGPT transcript](https://chatgpt.com/share/6a81ec29-8d24-83ea-9fdd-db97df8ee576?ogimg=plain)  
Product repository: `Pukujan/time-to-crawl`  
FOSSIL intake: `pack_time_to_crawl_scope_20260816`  
Status: reconstructed architectural synthesis; not a final implementation plan

## Evidence boundary

This document is a distilled project brief derived from a shared conversation.
The source conversation is preserved as reconstructed evidence in
`docs/recovery/2026-08-16-time-to-crawl-transcript.md`. Its design decisions are
candidate project scope, not external research findings. External tools,
frameworks, security guarantees, provider limits, and VPS capabilities must be
verified independently before implementation or deployment.

The scope was intentionally captured before creating a GitHub issue hierarchy.
This intake does not create or close issues in `Pukujan/time-to-crawl`.

## Project definition

**Time to Crawl** is a modular deal-intelligence platform. Its user-facing
capability is **Deal Finder**; its acquisition subsystem is **Merchant Scout**.

The top-level product outcome is:

> Given ordinary human shopping intent, discover permitted known and unknown
> sources, retrieve and normalize relevant product offers, assess quality and
> uncertainty, and return a ranked list that helps a shopper make a decision.

The primary acceptance test is therefore a black-box shopper outcome, not a
successful HTTP response, a populated database row, or a syntactically valid
JSON payload.

## Product scope

Representative requests include:

- cheap used chair near New York;
- trustworthy hair dryer under $100;
- second-hand furniture around Brooklyn;
- an obscure international camera deal;
- a product request where useful foreign or niche merchants are not prominent
  in ordinary search results.

When available, a result should carry:

- canonical product and merchant-specific offer;
- price, currency, condition, availability, shipping, and location;
- estimated landed cost for international purchases;
- source URL, source/merchant trust signals, sponsored status, and provenance;
- review count/rating and review-risk signals;
- brand/model/product identifiers, images, and freshness;
- first-seen/last-checked state, price history, relevance, deal score, and
  uncertainty.

CSV is an interchange/export format. PostgreSQL is the live canonical store;
Parquet is for larger historical/analytical exports.

## System shape

Use one repository, one dependency lock, one architecture graph, one release
manifest, and one versioned application. The application may run as several
process roles from the same release:

```text
time-to-crawl api
time-to-crawl scheduler
time-to-crawl worker known-http
time-to-crawl worker known-browser
time-to-crawl worker quarantine-http
time-to-crawl worker quarantine-browser
```

The first architecture is a modular monolith with ports-and-adapters inside
modules and thin MVC-style application boundaries:

```text
API / CLI → controllers → application use cases → domain modules
         → ports/contracts → infrastructure adapters
```

Do not begin with microservices or with separate independently versioned
crawler, ranking, catalog, and API products.

### Merchant Scout

Merchant Scout owns discovery and acquisition:

```text
source registry → discovery → URL frontier → scheduling → scope policy
                → HTTP/browser retrieval → raw artifacts
```

It does not decide whether an offer is a good deal.

### Deal Finder

Deal Finder owns search intent, product matching, offer comparison,
price-history interpretation, merchant/review signals, deal scoring, ranking,
and result presentation.

The handoff is explicit:

```text
RawArtifact → extraction → OfferObservation → catalog
            → canonical Product + Offers → Deal Finder → ranked results
```

### Extraction strategy

Prefer deterministic and structured sources in this order:

```text
JSON-LD/schema.org
→ embedded structured data
→ platform adapter
→ domain-specific deterministic parser
→ generic DOM extraction
→ structured LLM fallback
```

Important/high-volume sources may graduate from generic extraction to dedicated
adapters after replay evidence justifies the maintenance cost.

## Source and security policy

All Internet content remains untrusted. Avoid the word “trusted” for websites;
use **approved source** and **unknown/quarantined source**.

Approved sources can receive configured rate budgets, adapters, sessions, and
browser permissions. Unknown sources begin with no secrets, no persistent
profile or cookies, tiny budgets, low concurrency, strict time/size limits,
public-network-only egress, and disposable workers.

The source lifecycle is:

```text
DISCOVERED → QUARANTINED → CLASSIFIED → APPROVED → ACTIVE
                         ↘ SUSPICIOUS → BLOCKED
```

Every domain has explicit politeness controls: concurrency, delay, request
budget, robots behavior, browser allowance, redirect limit, response size, and
runtime. 429, 403, CAPTCHA, timeouts, abnormal redirects, oversized responses,
and parser-failure spikes trigger degradation, throttling, cooldown, or disable
states. CAPTCHA is a stop/backoff signal, not a bypass feature.

Browser “stealth” means isolation from hostile pages, cookies, tracking, and
host compromise. It is not an anti-bot evasion requirement.

### Deterministic Scope Guard

Scope Guard is a deterministic policy module, not an LLM. It checks before
enqueue and again before network execution:

- scheme, domain, port, method, and redirect targets;
- allowed scope/depth and request budgets;
- response/runtime limits and browser permissions;
- public-network-only destinations, including SSRF/private-address rules.

An advisory `scope_auditor` may identify suspicious behavior, but it cannot
authorize it.

### LLM boundary

Website text is hostile input. Extraction/classification inference receives
content plus a schema and returns strict structured output. It does not receive
shell, arbitrary HTTP, database, secrets, crawler-policy authority, or scope
authority. LLM output is a recommendation/candidate; deterministic validation
and policy authorize persistence and actions.

### Runtime isolation

The intended VPS/tailnet topology keeps administrative services private and
separates approved and quarantine workers. Baseline worker controls include
rootless Podman, non-root execution, dropped capabilities, no host network, no
container socket, resource ceilings, and temporary or read-only filesystems.
High-risk browser workers may add gVisor/runsc and the Chromium sandbox when
the measured threat model justifies the overhead.

Workers must not reach localhost, private address ranges, cloud metadata,
PostgreSQL, admin APIs, SSH, the container socket, or unrelated host services.
Prefer returning a structured `CrawlResult` to a trusted ingestion boundary;
do not give browser workers database credentials.

## Domain model and storage

Keep these concepts separate:

- **Product** — canonical real-world item;
- **Offer** — merchant-specific listing;
- **Observation** — time-specific observation of an offer.

Product identity should use identifiers first (GTIN/UPC/EAN/ISBN, then MPN),
then normalized attributes, lexical/semantic similarity, and only then
ambiguous adjudication. Embeddings or an LLM must never silently merge
products. Preserve both source-native and canonical taxonomy.

PostgreSQL owns products, offers, merchants, observations, price history,
source registry, crawl state, taxonomy, trust, provenance, deal lists, and API
usage. R2/object storage owns raw HTML/JSON/JSON-LD, selected snapshots,
feeds, screenshots, and archived artifacts. Search begins with PostgreSQL and
replaceable adapters; OpenSearch and Neo4j remain deferred extension points.

Content hashes prevent duplicate snapshots. Repeated unchanged fetches update
`last_checked` without rewriting identical content. Historical observations
should record changes rather than duplicate full product snapshots. Secrets stay
in an environment/secrets manager; CSV account registries contain references,
not credentials.

## Quality and evaluation methodology

### Four machine-enforced sources of truth

```text
SPEC      what the capability must do
MANIFEST  where it may live and what it may depend on
COMPILER  whether code obeys the architecture
EVIDENCE  whether it demonstrably worked
```

Each capability specification includes purpose, inputs, outputs, invariants,
success/failure conditions, dependencies, forbidden dependencies, and required
verification. Each module owns its domain types, public contract, schemas,
persistence abstraction, tables, and invariants. Other modules import only its
declared public surface.

The architecture compiler/checker validates manifests, dependency direction,
cycles, public/private imports, declared-vs-actual dependencies, plugin
registrations, schema compatibility, service wiring, table/event ownership,
network permissions, and secret permissions.

Use strict typing, Ruff, import checks, property/state-machine tests,
Schemathesis for API contracts, Hypothesis for generated behavior, Atheris or
equivalent coverage-guided fuzzing, and mutation testing. Fuzz the crawler and
its policies—not arbitrary third-party websites. High-risk targets include URL
scope, redirects, SSRF, size limits, JSON-LD/HTML/price parsing, CSV config,
scheduler idempotency, FastAPI contracts, and the LLM boundary.

### Walking skeleton

The first implementation is a real, thin path through every mandatory seam:

```text
spec → manifest → architecture compile → discovery provider
     → Scope Guard → frontier → fetcher → raw artifact
     → extractor → Product + Offer → PostgreSQL → ranking
     → FastAPI → CSV export → telemetry → docs → evidence
```

This is not a throwaway MVP. It is the smallest end-to-end proof that the
architecture is wired correctly. The governance foundation must first prove
that illegal imports, broken type contracts, missing docs, undeclared
dependencies, surviving mutants, and forbidden file changes fail CI.

### Shopper outcome evaluation

Define scenario families with human input, then run them automatically. A
scenario does not prescribe exact URLs. It supplies shopping intent, constraints,
and expected useful-result properties.

Generate paraphrases, typos, budgets, locations, distances, categories,
condition requirements, ambiguity, and language variation. Evaluate actionable
relevance, geography, price/condition presence, source URLs, provenance,
duplicate control, ranking, freshness, and deal usefulness. A semantic judge can
assist, but deterministic checks and holdout scenarios remain necessary.

The human is in scenario definition and calibration, not every execution. A
system may pass type, unit, architecture, and API checks while still failing
shopper acceptance; that is an intentional failure state.

Keep two evaluation modes:

- **Replay** — deterministic recorded web samples for CI and regression;
- **Expedition** — controlled real-Internet runs from the appropriate VPS/runtime.

Required environment checks must be declared. A local or cloud planning session
cannot claim Podman, gVisor, tailnet, firewall, or live-provider verification
without evidence from that environment.

### Documentation and handoff

Documentation is part of Definition of Done. Public APIs, schemas, module
boundaries, configuration, policies, operations, and ownership changes update
their corresponding docs. `AGENTS.md` is the stable start-here contract;
`docs/HANDOFF.md` records current state, blockers, verification, changed files,
remaining uncertainty, and environment requirements.

Agent tasks declare allowed and forbidden write paths. If a task needs a new
module, public contract, runtime dependency, global schema, database owner, or
security-policy change, it stops and becomes an architecture-change task rather
than silently expanding scope.

GitHub is the execution tracker:

```text
Project → Milestone → Epic → Capability → Task → Subtask
```

Repository specifications and FOSSIL evidence remain technical authority;
GitHub records coordination and execution state. Suggested outcome milestones
are governance/foundation, walking skeleton, discovery/crawl, extraction/
catalog, ranking/deal intelligence, international discovery, review
intelligence, hardening/scale, and operational readiness. These are proposed
seeds, not created issues.

## Explicit non-goals and proof gaps

The following are deliberately not foundational requirements: Neo4j, Kubernetes,
Firecracker, Temporal, a large OpenSearch cluster, multi-region deployment,
custom event infrastructure, a large frontend, or many inference engines.

The shared conversation does not prove that the proposed product works. Before
promoting any design into implementation authority, verify at least:

- actual provider limits, licenses, and APIs;
- current VPS, Podman, gVisor, firewall, and tailnet capabilities;
- extraction, identity, ranking, review-risk, and landed-cost quality on a
  holdout corpus;
- isolation and SSRF behavior under adversarial tests;
- mutation, fuzz, replay, and shopper-outcome thresholds;
- operational cost, storage growth, and acceptable expedition politeness.

The central falsifiable product hypothesis is that the system can improve the
shopper’s decision quality and discovery breadth while preserving provenance,
politeness, isolation, and reproducibility. That hypothesis must be tested by
the project’s evidence, not accepted because the architecture is comprehensive.

