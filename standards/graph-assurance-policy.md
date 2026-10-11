# Graph assurance policy: tensor-graph-assurance/1

Decision date: 2026-10-11. Applies prospectively to generated reports and authoring tools for the dated investigation graph. It changes no graph schema, graph content, published artifact, investigation-record Core contract or historical report. Passing these checks is author-side acceptance of a bounded graph/evidence package; publication, independent review and institutional acceptance are separate decisions.

## Blocking acceptance

Default lint and the compatibility spelling `--draft-review` apply the same policy. There are no score-based exceptions or lowered thresholds.

1. **Graph authoring:** IDs, references, labels, archetypes, complete deterministic yes/no/unknown branches, reachable nodes, acyclicity, terminal structure, fan-in limits and positive-stage coherence must satisfy the existing authoring rules.
2. **Structural properties:** the graph must be a DAG, all nodes reachable, every nonterminal branch complete, and all seven domains by eight archetypes present. Domain/archetype presence is a scope check, not proof of substantive investigative coverage.
3. **Evidence cards:** every active question must have a matching public predicate, role, domain, bound fields, assessment record requirements, version annotation and explicit yes/no/unknown criteria. Domain role bindings must cover every active question exactly once. Evidence criteria must pin the exact graph digest, graph version and schema identity.
4. **Evidence transitions:** check every edge against the evidence profile, including unexercised branches. No matching record routes to bounded exclusion; unknown routes to an alternate record; invalid or unresolved validation stops unresolved. A supported explicit hypothesis continues to scope; a contradicted one ends refuted; an unknown one ends unresolved. Unsupported scope stops unresolved. Relationship, technical-source and observed-effect assessments preserve no/unknown independently through a qualified ending. The source route context is retained while target evidence declares its own context. New roles or continuation patterns require a reviewed policy revision.
5. **Scenario agreement:** the nonempty supplied suite must agree with explicit expected paths and states under the normalized evaluator. Exact graph, criteria, suite, policy and implementation digests accompany reports. No arbitrary expressions, evidence fetching or tool execution is performed.
6. **Scenario coverage:** every entry and classification node needs yes/no/unknown cases. Scope, correlation, attribution and impact need all three assessments in each domain. Each domain retains a public-report-only case that leaves missing victim evidence unresolved. This is a bounded minimum test profile, not exhaustive path or real-world coverage.
7. **Fail closed:** absent/malformed evidence inputs, ambiguous scenario inheritance, mismatched pins, missing checks, or changes to the reference-gate catalog cannot yield a passing acceptance result. Full acceptance requires a generated graph artifact; JSONL-only lint emits diagnostics but remains incomplete until the exact graph and evidence package are assessed.

The canonical draft automatically selects its adjacent criteria and scenario suite. Other graph artifacts require explicit `--criteria-path` and `--scenarios-path`. A historical artifact lacking those new inputs can be inspected but cannot claim current acceptance. Published historical reports retain their original policy and meanings.

## Historical reference thresholds

Retain every original formula, value and threshold under `monitoring.legacyReferenceThresholds`. Current `monitoring.publishGates` describes the blocking checks above, with policy identity and a clear author-side scope. No historical object is rewritten or relabeled in place. The release-contract validator continues to validate the exact published snapshots under their existing contract.

| Historical threshold | Decision and reason |
|---|---|
| Cross-domain edges >= 25% | Diagnostic only. A label-change edge count does not prove an evidence relationship. A single-domain hypothesis can be sound, and cross-domain observations can be explicitly related without changing the source route context. Check context and target bindings instead. |
| Routing score >= 100 | Diagnostic only. It combines existing structural checks with a 20-point cross-domain-quota term. Keep the structural checks directly; do not count the quota twice. |
| Robustness score >= 85 | Diagnostic only. It is 100 times targeted node-removal reachability, duplicating that threshold. Deleting prerequisite questions is not missing-evidence handling. |
| Targeted reachability >= 0.85 after deleting 5% of questions | Maintenance sensitivity diagnostic. Removing questions from a versioned definition is a content change, not an operational outage. Bypassing a necessary validator to keep paths reachable would be unsafe. Missing evidence must use explicit unknown routes. |
| Betweenness centralization <= 0.02 | Maintenance concentration diagnostic. The implementation measures maximum node betweenness divided by summed betweenness, not normalized Freeman centralization. The value is sensitive to graph replication and granularity; required evidence checks can legitimately be hubs. |
| Overall score >= 80 | Diagnostic only. Uncalibrated weighted aggregation repeats the quota and deletion simulation and includes terminal-domain entropy. A scalar must not compensate for a failed safety property or block sound evidence semantics. |
| Nonnegative information gain | Diagnostic only, although currently passing. This is entropy over terminal-domain labels under assumed uniform branches. It measures neither investigation truth nor calibrated uncertainty, and entropy concavity makes nonnegative gain expected by construction. It must not be presented as a semantic safeguard. |

Thresholds and weights were not calibrated against investigator outcomes in the reviewed implementation or authoring documentation. Restoring a numeric blocker requires a defined threat/failure model, relevant measured outcomes, representative independent evidence, calibrated thresholds, demonstrated resistance to padding/renaming/bypass incentives, and a recorded policy decision. Current diagnostic recommendations must not tell authors to bypass evidence prerequisites.

## Limits and release handling

Evidence cards and synthetic expected paths can be authored consistently while still being wrong. The evaluator trusts supplied provenance and fact assessments and supports only its documented discriminators. Mechanical acceptance does not establish source honesty, hypothesis correctness, policy compliance, causal effects, independent interoperability or institutional review. Do not call `allPassed` publication authorization.

The builder checks structure and creates only a working draft or explicitly requested new unpromoted graph directory. Preparation alone cannot satisfy the evidence gates, update a manifest or move stable pointers. Before any future release, assess the exact prepared artifact with its matching evidence package and current policy, then complete the recorded release checklist. Schema and historical artifacts remain immutable.

Review evidence and counterexamples: [topology-gate review](../drafts/core/reviews/2026-10-11-topology-policy/README.md).
