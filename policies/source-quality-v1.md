# Source and Evidence Quality Policy v1

A source does not receive one universal truth tier. Its usefulness is judged **for the claim being evaluated**.

## Record separately

Where applicable, record:

- **source type** — standard/specification, primary paper, dataset, official documentation, source code, court/government material, book, review, article, conversation, observation, model output, etc.;
- **primary vs secondary**;
- **domain authority** — whether the source has authority/expertise for this specific question;
- **directness** — whether it directly establishes/tests the claim or only discusses adjacent material;
- **method strength** — study/design/test quality appropriate to the domain;
- **independence** — including meaningful conflicts of interest or vendor self-evaluation when relevant;
- **publication/observed/retrieval dates**;
- **version/current validity**;
- **replication/reproducibility** where relevant;
- **exact evidence location** — passage/span/table/commit/test result when available.

## Rules

1. Prefer official/primary sources for factual questions about a system's own behavior or specification.
2. Prefer original research for research claims; separately record replication status.
3. Vendor benchmark results are vendor evidence unless independently reproduced.
4. A standards document can be highly authoritative about its standard and irrelevant to an unrelated empirical claim.
5. Model output is **not** external evidence simply because multiple models agree.
6. A summary, citation index, or another agent's note must not be allowed to launder itself into a primary source.
7. If evidence is only indirect, label it indirect.
8. Preserve evidence that challenges the current favored conclusion.
9. Temporal claims must include the version/date for which they are intended to hold.
10. When evidence is insufficient, preserve `open`/`disputed` rather than manufacturing certainty.

## Derived source tiers

A workflow may compute a simple tier for ranking/review, but the tier must be derived from the stored dimensions and should be scoped to a question/domain. The underlying dimensions remain canonical.
