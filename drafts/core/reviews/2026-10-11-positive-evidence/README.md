# Downstream positive-route review receipts

Baseline: merged PR #8, commit `17a14fe281c5e7adabd13153abfbf8bb09291a2e`. Working content revision: `0.20261011b`, using unchanged schema `0.20260206e`.

Observed author-side checks:

- `python3 scripts/evaluate_entry_scenarios.py --output drafts/core/reviews/2026-10-11-positive-evidence/scenario-results.json`: **252/252 passed**. [Receipt](scenario-results.json) includes exact graph, public criteria and encoded scenario-suite digests, selected records, answers and assessment reasons. Downstream trace items retain supplied method and evidence references. Seven cases are public-report-only and remain unresolved; 245 are synthetic reconstructions.
- `python3 -m unittest discover -s tests/legacy -q`: **43 passed**, including downstream evidence mutations, all 13 classification nodes' yes/no/unknown paths, input binding, prior-graph retention, protected-file preservation, strict release-policy enforcement and fixture expansion safeguards.
- `fnm exec --using=24.21.0 npm run check`: **161 tests passed**, schema-source checks passed and both Core examples passed. The added test checks the actual working legacy graph against its unchanged released JSON Schema. This does not change or establish conformance of the separate Core candidate.
- `python3 scripts/validate_release_contract.py`: passed.
- `python3 scripts/lint_core_graph_quality.py --graph-path drafts/core/tensor.core.graph.json --entry-path drafts/core/source/entry_nodes.json --draft-review --output-dir drafts/core/reviews/2026-10-11-positive-evidence/structural`: passed with disclosed topology warnings. [Reports](structural/graph-quality.md) pin exact inputs and confirm all 103 nodes reachable, acyclicity, total deterministic branching, full domain/archetype coverage and positive stage progression.
- The same linter without `--draft-review`, writing to `/tmp/tensor-positive-strict-final`: **intentionally failed** the cross-domain quota and six strict gates. Those unchanged gate values and failures are retained in [math assurance](structural/math-assurance.json).
- All **60 protected files** matched their before-edit SHA-256 values: every published release file, the draft schema and the separate investigation-record candidate. [Preservation receipt](preservation.json).

| Failed strict gate | Actual | Required |
|---|---:|---:|
| Cross-domain edge ratio | 0 | >= 0.25 |
| Routing score | 80 | >= 100 |
| Robustness score | 81.6327 | >= 85 |
| Targeted reachability | 0.816327 | >= 0.85 |
| Betweenness centralization | 0.029056 | <= 0.02 |
| Overall score | 70.32654 | >= 80 |

No gate calculation or threshold changed. Canonical draft-review mode and draft-only builds report the topology quota as advisory; strict lint and release preparation retain it as blocking. A future release needs an explicit recorded policy/release decision, not an inference from draft CI passing.

The [exact prior graph](prior-draft.graph.json) and [manifest](prior-draft-manifest.json) retain all original wording and edges, including 88 newly detached questions. PR #8's earlier review receipts remain unchanged. Draft node IDs are scoped by graph version; do not apply prior meanings or assessments to rewritten questions by ID alone.

These are normalized author-side tests using supplied evidence assessments. No native incident replay, private victim dataset, independent investigator study, implementation exchange, publication, website deployment or institutional acceptance was performed. See [review scope and next evidence needs](../../POSITIVE-REVIEW.md).
