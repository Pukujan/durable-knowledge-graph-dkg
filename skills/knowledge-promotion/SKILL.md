# Knowledge Promotion

Load this methodology when project/domain knowledge appears reusable enough for a broader pack.

1. Retrieve the source claim/knowledge and its provenance.
2. Verify the target pack is a permitted write target for the caller.
3. Preserve the original source pack unchanged.
4. Create a new `knowledge.promoted` event in the target pack that points back to the source pack and stable subjects.
5. Include evidence refs and a promotion reason.
6. Preserve actor/model/harness/skill provenance and an idempotency key.
7. Validate and commit the durable event before any projection update.
