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
- Core standardizes investigation semantics and deterministic routing primitives.
- Overlays (vendor/org/extension layers) define concrete investigative execution detail.

## Canonical Sources
Core graph content is authored from structured source files:
- `drafts/core/source/nodes.jsonl`
- `drafts/core/source/edges.jsonl`
- `drafts/core/source/entry_nodes.json`

Build output is generated via:
- `python3 scripts/build_core_graph_from_source.py --version <VER> --draft-only`

Quality reports use an explicit input and an output directory outside `releases/`:

```sh
python3 scripts/lint_core_graph_quality.py --graph-path drafts/core/tensor.core.graph.json --entry-path drafts/core/source/entry_nodes.json --output-dir /tmp/tensor-draft-quality
```

The linter emits graph-quality, coverage-matrix, and math-assurance reports labeled with the exact source and digest. It evaluates the graph quality gates and fails when their thresholds are missed. It never refreshes stable pointers or historical reports. To lint JSONL directly, provide `--nodes-path`, `--edges-path`, `--entry-path`, an expected `--version`, and `--output-dir`.

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

## Backbone Rules
- Core graph must be a DAG (acyclic).
- Every non-terminal node has exactly three outgoing edges:
  - one `yes`
  - one `no`
  - one `unknown`
- Terminal nodes have zero outgoing edges.
- For each non-terminal node, each decision maps to exactly one target.
- Every node must be reachable from at least one entry node.
- `entryNodeIds` must include at least one valid entry node.
- Entry sets are intentionally flexible; overlays may define additional/dynamic entry signals.
- Semantic routing guardrails:
  - `yes` edges must preserve forward investigative logic (`same archetype` or `next archetype` only).
  - `yes` edges from `detect` and `validate` must stay within the same domain (no early-stage domain jumps on positive assertions).

## Coverage and Scale Guidance
- Node and edge counts are intentionally not fixed.
- Expand the graph to the size needed for investigation quality and breadth.
- Keep all seven domains represented with meaningful coverage.
- Cross-domain edge ratio: >= 25%

## Fan-In Constraints
- Default max fan-in (non-terminal nodes): 8
- Exception max fan-in (non-terminal nodes): 12
- Terminal max fan-in (sink nodes): 24
- Non-terminal exceptions must be listed in `entry_nodes.json` under `fanInExceptionNodeIds`

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

Current gate families include:
- Structural invariants (DAG, reachability, branch totality)
- Routing quality (cross-domain pivots, centralization)
- Robustness (targeted reachability under node removal)
- Information quality (no negative information gain)
- Composite optimization score floor

Gate outcomes are tracked per release in:
- `releases/core/reports/history/math-assurance-history.json`

## Pre-v1 Versioning Exception
For approved pre-v1 releases, a full node-id reindex may be shipped without a major version bump when explicitly authorized in release notes.
