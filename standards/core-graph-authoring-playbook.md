# TENSOR Core Graph Authoring Playbook

## Purpose
This playbook covers the existing dated graph track, not the separately versioned investigation-record candidate. It defines how to author and review the Core graph as an investigation backbone. Published graph releases remain immutable.

Core remains investigation-semantic only:
- No business workflow state
- No ticket/case management semantics
- No tool-specific execution steps
- No vendor-specific operational playbook logic (implemented in overlays)

## Core vs Overlay Contract

Core provides guard rails and a shared technical language for investigations; overlays implement
business process and product/tool execution detail on top of Core.

Authoring and review MUST follow: `standards/core-vs-overlay-contract.md`.

Core is a neutral backplane:
- Core standardizes investigation semantics, outcome guards and explicit route selections.
- Overlays (vendor/org/extension layers) define concrete investigative execution detail.

## Canonical Sources
Core graph content is authored from structured source files:
- `drafts/core/source/nodes.jsonl`
- `drafts/core/source/edges.jsonl`
- `drafts/core/source/entry_nodes.json`

Build output is generated via:
- `python3 scripts/build_core_graph_from_source.py --version <VER> --draft-only`

For a content-only revision using an existing schema, add `--schema-version <EXACT_SCHEMA_VER>`. Graph identity and schema identity are separate; this flag does not create or modify a schema. The entry-evidence draft uses unchanged schema `0.20260206e`.

Quality reports use an explicit input and an output directory outside `releases/`:

```sh
python3 scripts/lint_core_graph_quality.py --graph-path drafts/core/tensor.core.graph.json --entry-path drafts/core/source/entry_nodes.json --output-dir /tmp/tensor-draft-quality
```

The linter emits graph-quality, coverage-matrix, and math-assurance reports labeled with exact graph, evidence and policy implementation digests. Default validation follows [graph assurance policy `tensor-graph-assurance/1`](graph-assurance-policy.md): structural invariants, digest-bound evidence cards, safe transitions and scenario agreement/coverage are blocking. Historical topology thresholds retain their original values and formulas as diagnostics. `--draft-review` is a compatibility alias restricted to the canonical draft; it waives no checks and applies the same policy. This is not publication approval.

The linter never refreshes stable pointers or historical reports. The canonical graph automatically selects its adjacent public criteria and scenarios. For any other graph artifact, provide `--criteria-path` and `--scenarios-path` for its exact evidence package. JSONL inputs still permit structural inspection with `--nodes-path`, `--edges-path`, `--entry-path`, `--version` and `--output-dir`, but full authoring acceptance fails closed until the generated graph artifact and its evidence package are assessed.

The builder defaults to writing only the working draft; `--draft-only` remains an explicit compatible spelling. `--prepare-release` instead writes a new versioned graph directory, refuses an existing version, and does not update the draft, latest pointers, manifest, or checksums. It is mutually exclusive with `--draft-only`. A prepared graph is unpromoted and still needs complete reviewed release packaging.

## Node Authoring Model
Required node fields:
- `id`
- `text`
- `label`
- `category`
- `archetype`

Optional node fields:
- `extensions`

### Category
Allowed Core categories:
- `Application`
- `Cloud`
- `Email`
- `File`
- `Host`
- `Identity`
- `Network`

### Archetype
Allowed archetypes:
- `detect`
- `validate`
- `classify`
- `scope`
- `correlate`
- `attribute`
- `impact`
- `terminal`

`terminal` in Core means route termination for a hypothesis path, not case closure/business workflow completion.

## Edge Authoring Model
Required edge fields:
- `id`
- `source`
- `target`
- `decision`

Optional edge fields:
- `label`
- `extensions`

Edge id format:
- `Q<source>-<decision>-Q<target>`

Allowed decisions:
- `yes`
- `no`
- `unknown`

## Working graph routing rules
These rules govern the working draft. Published artifacts and their historical release checks remain unchanged.

- A nonterminal question has at least one declared route for each outcome: `yes`, `no`, and `unknown`. Each outcome may have several target questions.
- An assessment records one outcome for one bound question instance. A decision explicitly selects eligible transition/target-instance pairs. Eligibility does not select every route or assert a target answer.
- Routes can cross domains and return to an earlier question. A question ID or archetype is not a chronological constraint. Revisiting a question uses a fresh instance with its own context and evidence; retained answers are never overwritten.
- Every cross-domain lead identifies its discovery basis, separately bound target subjects and interval, and target evidence requirements. Source negatives and unknowns can coexist with independent leads; they cannot supply missing discovery evidence or establish the target proposition.
- Independent evidence validation may run alongside primary validation. Separate sources require independent provenance, not copies of one record.
- Convergence is permitted when the follow-up remains relevant for each answer. Record the rationale; do not generate three identical routes merely to satisfy a shape or count.
- Terminal nodes have zero outgoing edges.
- Every node must be reachable from at least one entry node.
- `entryNodeIds` must include at least one valid entry node.
- Entry sets are intentionally flexible; overlays may define additional/dynamic entry signals.
- There is no required cross-domain percentage or maximum fan-in. These topology diagnostics do not establish semantic validity. References, unique identities, outcome coverage, independent evidence criteria and explicit selections remain blocking checks.
- Clients must bound automatic traversal. A cycle in a definition never instructs a human or agent to recursively follow every route. The Lab replays retained decisions; it does not execute the graph.

The optional `tensor:investigativeLead` profile in the working draft documents additional readiness conditions. It is authoring metadata, not a new schema or a condition evaluated by the Core guard interpreter. A consumer must explicitly implement the profile or present it for assessment. See [the routing repair](../drafts/core/reviews/2026-10-13-routing/README.md).

The published v0.20260206e graph was authored as an acyclic graph with exactly one route per outcome. Those historical constraints remain part of its preserved release validation; they do not limit the new working draft.
- Evidence prerequisites remain explicit in question criteria and route context. A stage label alone neither supplies nor blocks a prerequisite. Early cross-domain leads are legal when target discovery and bindings are separately supported.

## Coverage and Scale Guidance
- Node and edge counts are intentionally not fixed.
- Expand the graph to the size needed for investigation quality and breadth.
- Keep all seven domains represented with meaningful coverage.
- Cross-domain relationships require explicit subject/time bindings and supported discriminators; no minimum control-flow edge ratio is required by the current policy.

The historical 25% ratio remains a diagnostic reference with its original formula and threshold. A relation between domains can be declared and tested as evidence while the hypothesis route retains its original context; do not invent a pivot to improve a topology score. The [recorded policy decision](graph-assurance-policy.md) separates authoring acceptance from uncalibrated diagnostic thresholds. The builder checks structure and prepares unpromoted content; it does not perform evidence acceptance or move stable pointers.

## Fan-in diagnostics
The historical default (8), exception (12), and terminal (24) limits remain diagnostic references for the working draft. They do not justify redirecting a route to an unrelated question or prohibit a useful shared entry. Published release checks retain their historical limits.

## Text Quality Rules
Node labels must:
- Be short and graph-readable.
- Start with the node domain in the form `<Domain>:` (for example: `Email:`).
- Avoid numeric template labels (for example: `Email detect 12`).

Node text must:
- Be objective and evidence-focused
- Be phrased as a question ending with `?`
- Avoid workflow/tool/process language
- Avoid incident-type or case-typing language (incident naming belongs in overlays)

Forbidden examples in Core text:
- `open a ticket`
- `escalate to`
- `run query in`
- `click dashboard`

## Release Workflow
1. Author source files under `drafts/core/source/` and choose a new version when preparing a release.
2. Build the working graph with `--draft-only`.
3. Run explicit-source quality lint and retain its input identity and digest.
4. Review the candidate graph, schema changes, compatibility, and reports. Never overwrite an existing versioned release.
5. After a recorded release decision, use `--prepare-release` only for a new graph version and add the corresponding reviewed schema snapshots and reports. Update manifest-selected latest pointers together; do not derive stable identity from the working draft.
6. Regenerate checksums for the reviewed release changes and confirm historical bytes have not changed.
7. Run `python3 scripts/validate_release_contract.py` and `python3 -m unittest discover -s tests/legacy -v`.

The `update-latest` workflow checks the existing release contract; it does not publish new draft content. The investigation-record candidate follows its own [release checklist](../docs/release-checklist.md).

## Artifacts Required Per Release
- Graph artifact:
  - `releases/core/graphs/v<VER>/tensor.core.graph.json`
- Schema artifact:
  - `releases/core/schemas/v<VER>/tensor.core.schema.json`
- Reports:
  - `releases/core/reports/v<VER>/graph-quality.md`
  - `releases/core/reports/v<VER>/graph-quality.json`
  - `releases/core/reports/v<VER>/coverage-matrix.md`
  - `releases/core/reports/v<VER>/coverage-matrix.json`
  - `releases/core/reports/v<VER>/math-assurance.md`
  - `releases/core/reports/v<VER>/math-assurance.json`
- Monitoring artifacts:
  - `releases/core/reports/latest/math-assurance.md`
  - `releases/core/reports/latest/math-assurance.json`
  - `releases/core/reports/history/math-assurance-history.md`
  - `releases/core/reports/history/math-assurance-history.json`

## Publish Gates
Math assurance includes release-level publish gates under:
- `monitoring.publishGates.allPassed`
- `monitoring.publishGates.failedGateIds`
- `monitoring.publishGates.gates[]`

Current blocking gates cover graph authoring, reachability/outcome coverage, declared domain/archetype scope, evidence cards, every evidence-profile transition, scenario agreement and scenario coverage. Missing evidence checks remain `notRun` and block acceptance. Current `monitoring.publishGates` is scoped to author-side acceptance, not release authorization.

Historical topology thresholds are retained under `monitoring.legacyReferenceThresholds`. They do not measure evidentiary truth or permit bypassing a prerequisite. All published reports retain their original fields, policy and meaning; future generated reports carry the new policy identity. The release-contract validator continues checking the exact historical artifacts without alteration.

Gate outcomes are tracked per release in:
- `releases/core/reports/history/math-assurance-history.json`

## Pre-v1 Versioning Exception
For approved pre-v1 releases, a full node-id reindex may be shipped without a major version bump when explicitly authorized in release notes.
