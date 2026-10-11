# Candidate Core validation tests

Run from the repository root with Node.js 22 or newer:

```sh
npm ci
npm test
```

These tests exercise the `0.1.0-draft.1` candidate binding and reference implementation. They do not certify the founding contract, establish factual correctness, execute response actions, or demonstrate exchange with an independently developed implementation.

- `contract.test.mjs` uses the two synthetic bundles for positive and adversarial tests of parsing, exact-byte definition pins, identity conflicts, attribution, typed references, bound context, uncertainty, transitions, revisions, partial exchange, extensions, current-view review status, and import safety. Optional prior-record comparisons check conflicts that are observable in supplied history. Unseen history remains outside the validator's scope.
- `fixture-integrity.test.mjs` verifies every declared fixture digest, complete manifest coverage, exact definition bytes within bundles, and equality between the bundled and separate records.
- `schema-parity.test.mjs` compares the portable schema evaluator with AJV's full JSON Schema Draft 2020-12 engine. It recursively deletes members, introduces unknown members, and changes value types in both cases' bundles, records, and definitions. This comparison uses the candidate's URI and timestamp format checks in both engines to isolate structural semantics. A separate test verifies that all original fixtures also pass AJV with ordinary `ajv-formats` validators.
- `serialization-budget.test.mjs` checks that a minified import near the receiver's byte limit can be exported and reimported without losing opaque content or changing embedded definition bytes.
- `reviewer-regressions.test.mjs` exercises stale review bases, revised-review downstream effects, definition-pin conflicts in supplied history, full fractional timestamp ordering, failed transition prerequisites and URI syntax checked against unmodified `ajv-formats` rather than the runtime's own predicate.

The full-engine dependency is used only for development tests; browser validation has no AJV runtime dependency. Structural parity is additional evidence about the published schemas and the bounded evaluator, not exhaustive JSON Schema support or independent investigative interoperability. The suite preserves the distinction between invalid input, missing or unsupported meaning, and a valid investigative `unknown` outcome.
