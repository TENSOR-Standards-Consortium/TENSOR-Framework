# TENSOR Framework

TENSOR is being developed as a public standard for **all cyber investigations**, with one shared investigative layer for humans and agents. Public domain profiles, vendor integrations, and business policies build on that layer without silently changing its meaning.

The project preserves its existing question graphs and introduces a **Core investigation-record candidate, `0.1.0-draft.1`**, for public review. The candidate connects questions, evidence references, observations, assessments, decisions, and revisions in a portable record. It is not a ratified standard or a certification program.

## Start here

- **Investigators:** read the [founding charter](proposals/founding-core-v0.1.0/00-charter.md) and [two synthetic cases](core/v0.1.0-draft.1/examples/README.md).
- **Implementers:** use the [candidate binding and API](core/v0.1.0-draft.1/README.md), [schemas](core/v0.1.0-draft.1/schemas/), and [check coverage](core/v0.1.0-draft.1/coverage.md).
- **Reviewers:** use the [review packet](docs/reviewer-packet.md), [38 proposed requirements](proposals/founding-core-v0.1.0/01-core-contract.md), and [standards crosswalk](proposals/founding-core-v0.1.0/03-standards-crosswalk.md).
- **Contributors:** see [CONTRIBUTING](CONTRIBUTING.md), [governance status](GOVERNANCE.md), and the [90-day adoption work plan](docs/adoption-plan.md).

The [public website](https://tensor-website.pages.dev) is hosted on Cloudflare Pages; this repository holds specification source and immutable graph releases. Candidate website features and public artifacts are available only after the corresponding website deployment. A branch or a passing local test is not proof of deployment.

## Run the candidate

Use Node.js 22 or newer. From this checkout:

```sh
npm ci
npm run check
node core/v0.1.0-draft.1/cli.mjs core/v0.1.0-draft.1/examples/case-a.bundle.json
node core/v0.1.0-draft.1/cli.mjs core/v0.1.0-draft.1/examples/case-b.bundle.json
```

The CLI emits a scoped JSON report: exit `0` means its bounded checks passed, `1` means failure, `2` means indeterminate interpretation, and `64` means an input or usage error. Reports retain `notRun` checks. They cannot establish evidence truth, actual authorization, safety, or the quality of an investigation. Importing a record does not authorize actions.

The runtime is usable in Node and browsers without third-party runtime dependencies or network retrieval. This package is private in npm: the commands above use the repository, not a published registry package.

## Two tracks, explicit identities

| Track | Current artifacts | Meaning |
| --- | --- | --- |
| Existing graph releases | Stable graph/schema `0.20260206e`; 588 questions and 1,554 edges | Reusable investigative question definitions under their original release contract |
| Existing graph drafts | `0.20260212e`; 219 questions and 576 edges | Editable graph content, separate from the stable release |
| Founding proposal | `proposals/founding-core-v0.1.0/`; proposal `0.1.0` | Public purpose, logical contract, and proposed governance |
| Core implementation candidate | `core/v0.1.0-draft.1/`; binding `0.1.0-draft.1` | Trial JSON representation, validator, CLI, schemas, and synthetic records |

The graph release numbering convention (`MAJOR.YYYYMMDD[letter]`) remains intact. The candidate binding uses its own explicit draft identifier. Neither implies an upgrade of the other. Published `releases/` bytes are preserved, and a legacy graph does not become an investigation record by relabeling it.

Legacy identifiers such as `Q12` are meaningful only with their source graph version and digest. Use the [migration inventory procedure](docs/legacy-migration.md) before reusing them in a candidate definition. Migration must not invent criteria, evidence, actors, or decisions.

## Repository map

| Path | Purpose |
| --- | --- |
| `core/v0.1.0-draft.1/` | Executable candidate binding, schemas, examples, CLI, and check boundaries |
| `proposals/founding-core-v0.1.0/` | Founding text; proposed requirements TC-01 through TC-38 |
| `drafts/core/source/` | Editable legacy graph questions, edges, and entry nodes |
| `drafts/extensions/`, `drafts/vendors/`, `drafts/orgs/` | Existing extension and overlay authoring tracks |
| `releases/` | Existing immutable snapshots, release catalog, and checksums |
| `standards/` | Existing graph compatibility and authoring policies |
| `tests/`, `scripts/` | Candidate checks and legacy preservation tooling |
| `docs/` | Candidate design decision, reviewer packet, migration, and release preparation |

The Core boundary remains vendor-neutral. A business policy or vendor tool may supply context and perform authorized work; it cannot turn `unknown` into `no`, suppress conflicting assessments, or replace Core semantics under the same identity. Public profiles must remain usable without buying a vendor product.

## Legacy graph checks

Use Python 3 from the repository root:

```sh
python3 scripts/validate_release_contract.py
python3 -m unittest discover -s tests/legacy -v
python3 scripts/lint_core_graph_quality.py --graph-path drafts/core/tensor.core.graph.json --entry-path drafts/core/source/entry_nodes.json --output-dir /tmp/tensor-draft-quality
```

The linter labels results with the exact source artifact and writes outside `releases/`. It does not promote drafts, refresh stable pointers, or rewrite historical reports. See the [graph authoring playbook](standards/core-graph-authoring-playbook.md) for new legacy graph work.

## Public participation and claims

AI security teams governing agents and autonomous systems are the first adoption audience. The contract must also work for conventional identity, cloud, endpoint, network, application, email, and file investigations conducted by humans or mixed teams.

The next gate is reproducible review and exchange by independent implementations, with disclosed losses and limitations. No institutional recognition, partnership, independent council, or stable Core approval is claimed. See the [release checklist](docs/release-checklist.md) for evidence required at each stage.

The existing [Apache License 2.0](LICENSE) remains unchanged. Proposed governance does not create a new legal entity, appoint stewards, or impose additional patent or contributor terms. Citations should identify the exact commit and candidate version; [CITATION.cff](CITATION.cff) supplies project metadata.
