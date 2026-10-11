# Review of the six failing topology gates

Baseline: `b4bea9ffd8dea9887f4634b7a6eec6cfcf7f2b62`, PR #9 before this policy review. Graph `0.20261011b`, schema `0.20260206e`, criteria and all 252 evidence scenarios remain byte-identical. This review changes prospective authoring acceptance, not graph content, schema, published releases or the investigation-record Core candidate.

Decision: none of the six numerical failures is justified as a release blocker by the reviewed implementation or authoring documentation. Several measure useful maintenance sensitivities, but the thresholds are uncalibrated, duplicate one another, or reward changes unrelated to evidence quality. Preserve them as diagnostics and replace their blocking role with direct structural and evidence-profile checks. The [versioned policy decision](../../../../standards/graph-assurance-policy.md) defines the new requirements and limits.

## Gate assessment

| Gate and current value | What it actually measures | Decision |
|---|---|---|
| `cross_domain_pivots`: 0 vs >= 0.25 | Fraction of edges whose endpoint category labels differ. It cannot establish a valid subject/time relationship. | Remove the blocking quota. Check explicit relationship context and every evidence-profile transition. |
| `routing_score`: 80 vs >= 100 | 35% branch completeness + 35% reachability + 20% quota attainment + 10% DAG. The valid graph loses only the quota term. | Keep structural invariants directly; the derived scalar is diagnostic. |
| `robustness_score`: 81.6327 vs >= 85 | Exactly 100 times targeted reachability. | Duplicate of the next failure; diagnostic only. |
| `targeted_resilience`: 0.816327 vs >= 0.85 | Remaining nodes reachable after removing the five highest-betweenness eligible questions, including their edges. This deletes prerequisites from a definition. | Useful maintenance sensitivity, with no evidenced outage model or calibration to investigator outcomes. Missing observations require unknown routes, not bypasses around deleted validation. |
| `routing_centralization`: 0.029056 vs <= 0.02 | Maximum node betweenness divided by summed betweenness. It is sensitive to size, duplication and question granularity. | Rename its interpretation to maximum betweenness share; retain the legacy field/value for comparisons. Review important questions, without an arbitrary numeric blocker. |
| `overall_score`: 70.32654 vs >= 80 | 30% coverage + 30% routing + 20% information proxy + 20% robustness. It repeats the quota and removal model. | Diagnostic only. A weighted average cannot substitute for individually satisfied safety properties. |

The current graph receives **zero information score** because all routes retain their domain context. That contributes a 20-point penalty to the overall score, despite saying nothing about whether evidence supports a hypothesis. The currently passing `information_gain` threshold is also diagnostic under the new policy: entropy of terminal-domain labels under assumed uniform branches is not evidence uncertainty, and nonnegative gain is expected from entropy concavity. No score or threshold was recalibrated.

The original thresholds are constants in the February implementation; the reviewed code, commit message and authoring documentation contain no calibration dataset, investigator outcome model or threshold justification. This is a bounded repository finding, not a claim that topology metrics have no use elsewhere.

## Reproducible counterexamples

[Counterexample receipt](counterexamples.json) pins the actual graph, evidence inputs and implementation. The [reviewed graph snapshot](reviewed-graph.graph.json) preserves that exact baseline for future counterexample regressions without freezing future working graph content. Experiments mutate copies in memory and never write an alternative graph.

| Experiment | Observed result | Implication |
|---|---|---|
| Replace every predicate with the same meaningless question | Every historical score unchanged; authoring text-format checks alone also miss the loss of meaning. Exact evidence-card binding rejects the unreviewed edit. | Topology scores are blind to investigative meaning. Matching cards still require substantive human review; mechanically consistent wording can be wrong. |
| Scatter domain labels across the unchanged topology | Cross-domain ratio rises to 0.782222; routing becomes 100 and overall 95.79083, while 99 authoring errors appear. | A higher score can reward incoherent labels. Independent blockers must not be averaged away. |
| Add an identical disconnected copy of every route | Maximum betweenness share halves from 0.029056 to 0.014528, crossing the threshold. Original routes do not improve. | The <= 0.02 threshold can be satisfied by duplication. |
| Delete a validator in a three-node toy chain | Remaining reachability rises from 0.5 to 1 when an unsafe shortcut bypasses the prerequisite. | Percolation reachability alone rewards bypassing required evidence checks. This is a countermodel, not an operational failure simulation or proposed route. |
| Compare robustness with targeted reachability | 81.6327 = 100 × 0.816327 | These are one failure counted twice. |

The betweenness calculation is a shortest-path measure, as described in the [NetworkX documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html). Standard graph centralization instead aggregates differences from the maximum node score and can normalize by a theoretical maximum; see the [igraph centralization definition](https://cran.r-project.org/web/packages/igraph/refman/igraph.html#centralize). This implementation's maximum-share ratio is a different measure. No external graph-analysis dependency was added.

## Replacement safeguards

Default lint now has ten blocking checks: graph authoring, policy catalog, DAG, reachability, complete branching, declared domain/archetype presence, evidence cards, every evidence-profile transition, scenario agreement, and scenario coverage. Absent evidence checks are `notRun` and fail acceptance. An unreviewed change to the diagnostic/blocker catalog fails closed. Removing negative fixtures cannot make a positive-only suite sufficient.

Every entry and classification question requires yes/no/unknown scenarios; scope, correlation, attribution and impact require all three assessments in every domain. Each domain retains a report-only case whose missing victim evidence remains unresolved. Every graph edge is checked against the explicit evidence profile independently of scenario coverage. This is a bounded minimum profile, not exhaustive path coverage, source authentication, native incident replay or an independent investigator study.

Current `monitoring.publishGates` contains scoped authoring acceptance. `monitoring.legacyReferenceThresholds` retains every original numeric value, formula and threshold result. [Current reports](current/math-assurance.md) pin the exact graph, criteria, suite, policy document and implementation. Historical published reports and PR #8/#9's prior receipts are untouched. The compatibility `--draft-review` spelling applies the same checks as default; CI no longer requires an exception mode.

The builder prepares structurally valid, unpromoted content only. A missing evidence package still fails current acceptance, and preparation cannot update manifests, checksums or stable pointers. This policy does not authorize a release. Independent review and the recorded release checklist remain necessary.

## Observed verification

- `python3 -m unittest discover -s tests/legacy -q`: **58 passed**, including unsafe-route mutations, missing/different evidence inputs, mismatched pins, omission of negative/public-report fixtures, unknown gate catalogs, score counterexamples and exact historical numeric comparisons.
- `fnm exec --using=24.21.0 npm run check`: **161 tests passed**, schema-source checks and both Core examples passed. The working graph still conforms to its unchanged released JSON Schema.
- `python3 scripts/evaluate_entry_scenarios.py`: **252/252 passed**.
- Default lint on the actual graph with its evidence package: **passed**, with all six unmet historical thresholds visible as diagnostics.
- Explicit noncanonical graph with matching evidence: passed; missing evidence: failed, as required.
- `python3 scripts/validate_release_contract.py`: passed; `git diff --check`: passed.
- [Preservation receipt](preservation.json): every graph, source, criteria, scenario, schema, published release, Core candidate and prior receipt remains unchanged. Only the two working review documents gained supersession notices; their exact earlier bytes are retained as [prior entry review](prior-ENTRY-REVIEW.md) and [prior positive review](prior-POSITIVE-REVIEW.md).

Reproduce with a fresh receipt path:

```sh
python3 scripts/review_topology_gates.py --output /tmp/tensor-topology-counterexamples.json
python3 scripts/lint_core_graph_quality.py --graph-path drafts/core/tensor.core.graph.json --entry-path drafts/core/source/entry_nodes.json --output-dir /tmp/tensor-current-assurance
python3 -m unittest discover -s tests/legacy -v
```
