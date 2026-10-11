# Evidence-bound entry routes

Policy update, 2026-10-11: the graph and evidence content described here are unchanged. Current acceptance follows [graph assurance policy `tensor-graph-assurance/1`](../../standards/graph-assurance-policy.md), which supersedes the score-gating discussion below. The [topology review](reviews/2026-10-11-topology-policy/README.md) retains the original document and explains the decision.

The entry foundation was merged in **0.20261011a**. Current working draft **0.20261011b** extends it through [evidence-bound positive routes](POSITIVE-REVIEW.md), using the unchanged schema **0.20260206e**. Neither draft is a published release. All published releases and the separate investigation-record candidate remain unchanged.

This entry foundation covers the seven entries, independent-source checks, adjacent record validators and negative/unresolved endings: **42 questions**. Their predicates and routes remain unchanged in the positive-route revision. The current [public evidence criteria](entry-evidence-criteria.json) cover all 103 active questions and are pinned to the graph digest. They provide each question's proposition, subject fields, assessment record requirements and yes/no/unknown rules. Optional namespaced node annotations locate the cards; a schema pass does not prove a consumer applied them.

## Meaning before traversal

Bind exact subjects and a time interval. Entries ask whether the **examined material contains a matching event record**. Yes does not establish maliciousness, authorization, intent, attribution or source authenticity.

- **No matching record:** assess whether the evidence supports excluding this specific event. Only an evidenced, applicable coverage and complete-search basis supports exclusion. Missing logs, partial retention, unsuitable logging, uncertain clocks or a current snapshot for a historical claim leave the event unresolved.
- **Unknown match:** look for a separately originating record with the same subjects and interval. A forwarded log, indexed copy or second report of one source is not independent corroboration. If it remains unavailable or uncertain, stop unresolved.
- **Matching record:** assess provenance and event interpretation. Rejected or unverified records stop unresolved without asserting event absence. New evidence can justify a new assessment; no route silently overwrites an earlier answer.
- **Terminal:** this hypothesis route stops. Preserve the answer, evidence and limits. It does not close an investigation or authorize action.

The event is an identity action, process execution, network communication, cloud control-plane operation, message delivery, application request handling or file presence. A request does not prove execution; a signature does not prove benignness; a valid login does not prove user consent.

| Domain | Entry | Independent source | Primary / independent validation | Exclusion / unresolved terminal |
|---|---|---|---|---|
| Identity | Q1 | Q8 | Q155 / Q150 | Q589 / Q596 |
| Host | Q2 | Q9 | Q156 / Q151 | Q590 / Q597 |
| Network | Q3 | Q10 | Q152 / Q82 | Q591 / Q598 |
| Cloud | Q4 | Q11 | Q153 / Q83 | Q592 / Q599 |
| Email | Q5 | Q12 | Q154 / Q147 | Q593 / Q600 |
| Application | Q6 | Q13 | Q85 / Q148 | Q594 / Q601 |
| File | Q7 | Q14 | Q86 / Q149 | Q595 / Q602 |

All entry transitions preserve domain, subjects, proposition and interval. PR #8 stopped evaluation at the classification boundary. The current [positive-route review](POSITIVE-REVIEW.md) repairs that continuation and extends the evaluator through qualified endings without changing these entry predicates.

## Investigation scenarios and proof limits

The original **77 entry cases** remain within the current [252-case scenario set](scenarios/entry-evidence-cases.json), across all seven domains:

- Seven public-report-only cases retain missing victim identifiers, event times and evidence as unknown. Sources are [Mandiant's UNC3944 investigation](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications), [SUNBURST reporting](https://cloud.google.com/blog/topics/threat-intelligence/evasive-attacker-leverages-solarwinds-supply-chain-compromises-with-sunburst-backdoor), [Microsoft's AiTM investigation](https://www.microsoft.com/en-us/security/blog/2026/01/21/multistage-aitm-phishing-bec-campaign-abusing-sharepoint/), [Storm-0558 analysis](https://www.microsoft.com/en-us/security/blog/2023/07/14/analysis-of-storm-0558-techniques-for-unauthorized-email-access/), and [MITRE's OpenClaw report](https://www.mitre.org/sites/default/files/2026-02/PR-26-00176-1-MITRE-ATLAS-OpenClaw-Investigation.pdf). OpenClaw is a reported researcher demonstration, not victim telemetry.
- Seventy synthetic reconstructions test supported records, bounded absence, missing logs, independent recovery, copied sources, rejected provenance, conflicting evidence, wrong subjects, out-of-window records and unknown coverage. Identifiers, dates, provenance and coverage assertions are author-created; they are not original incident logs.

The evaluator derives answers from normalized observations and supplied assessment claims. Expected paths are separate assertions. It does not parse native logs, verify bytes or source honesty, establish actual authorization, contact systems, execute tools or test candidate Core conformance. Datetime support is bounded to microseconds; unsupported precision remains unknown.

Regressions also reject the original unsupported pivot, block exclusions contradicted by another record, preserve uncertain provenance and enforce subject/time bounds. No private incident dataset, raw incident replay, independent implementation exchange or independent investigator study was performed. Practitioners still need to review these criteria and test authorized evidence packages.

## Reproduce

```sh
python3 scripts/build_core_graph_from_source.py --version 0.20261011b --schema-version 0.20260206e --draft-only
python3 scripts/evaluate_entry_scenarios.py --output /tmp/tensor-entry-scenarios.json
python3 -m unittest discover -s tests/legacy -v
python3 scripts/validate_release_contract.py
python3 scripts/lint_core_graph_quality.py --graph-path drafts/core/tensor.core.graph.json --entry-path drafts/core/source/entry_nodes.json --draft-review --output-dir /tmp/tensor-entry-quality
```

Scenario output refuses overwrite; use a new receipt filename on reruns. Receipts retain input digests.

## Structural diagnostics and preservation

The entry revision had **184 nodes and 429 edges**. Removing unsupported entry/validation pivots disconnected 49 older questions. Their original text and 147 outgoing edges are preserved as [detached review material](reviews/2026-10-11-entry-evidence/detached-draft-material.json), with the original commit and digest. They were not reconnected solely to satisfy reachability or removed from historical releases. The current positive-route draft has 103 nodes and 225 edges, with its own prior-graph snapshot and preservation receipts.

Authoring checks still enforce acyclicity, reachability, deterministic branches, labels, domain/archetype presence, fan-in and positive-stage progression. The strict linter also fails this draft's simulated robustness, targeted-resilience and centralization thresholds. The original values and failures remain visible in assurance reports.

Explicit **--draft-review** mode is restricted to the canonical unpromoted draft. It treats synthetic optimization and historical cross-domain quota failures as warnings while keeping structural and other authoring errors fatal. It changes neither score calculations nor release contracts, hides no gate failures, and approves no publication. CI uses it alongside semantic scenario regressions. Strict mode remains the default and still fails for the documented gates; see the [current diagnostic scope](POSITIVE-REVIEW.md#structural-policy-and-preservation).

Evidence-justified routes take precedence over optimizing synthetic topology. Future promotion still requires a recorded policy/release decision and substantive review.
