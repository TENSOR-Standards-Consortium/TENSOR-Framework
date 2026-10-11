# Entry-evidence repair review

This unpromoted revision changes no published release or schema. See [scope, criteria and reproduction](../../ENTRY-REVIEW.md).

- Q1–Q7 now ask about a matching bound event record; Q8–Q14 seek a separately originating record for the same event.
- Fourteen adjacent validators retain event subject/time. Negative and unknown branches stop unresolved instead of pivoting to unrelated domains.
- Q589–Q602 add seven bounded-exclusion and seven unresolved terminal questions.
- detached-draft-material.json preserves 49 disconnected older questions and their 147 original outgoing edges with source identity. It is not a standalone runnable graph.
- Existing positive classification questions are declared unreviewed boundaries. These tests do not validate their downstream semantics.

The February review's example through Q408 and Q470 was already stale against its 219-node artifact. That note remains historical. New criteria and receipts pin exact artifact digests rather than using that example as an acceptance test.

Observed checks: 13 baseline preservation tests passed; revised scenarios passed 77/77; the final legacy/entry suite passed 31 tests; release validation and draft building passed. On Node 24.21.0, all 160 candidate tests, schema-generation checks and both example validations passed. The revised graph also passed a full Draft 2020-12 validation against the unchanged schema.

[Scenario results](scenario-results.json) and [structural reports](structural/graph-quality.md) retain exact input digests. [Preservation evidence](preservation.json) compares all 60 protected release, schema and candidate files. No protected bytes changed.

Draft-review mode passed structural checks with visible optimization warnings: simulated robustness is 75.4286 (threshold 85), targeted reachability is 0.754286 (threshold 0.85), and centralization is 0.026993 (threshold 0.02). Strict mode still fails those three gates; no gate values or historical reports were changed.

These are offline author-side checks of normalized observations and supplied assessment claims, not source authenticity verification, raw incident replay or investigation-effectiveness evidence.
