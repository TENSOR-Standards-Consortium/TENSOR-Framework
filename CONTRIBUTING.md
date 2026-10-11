# Contributing to TENSOR

TENSOR welcomes public review and implementations for all cyber investigations. Buying a product, membership, or sponsorship is not required to review the public materials or submit a contribution. Repository maintainers retain merge control; the [governance proposal](GOVERNANCE.md) has not yet been adopted.

## Choose the right track

- Correct or discuss the proposed semantics in `proposals/founding-core-v0.1.0/`. Reference requirement IDs such as TC-13.
- Change the executable candidate in `core/v0.1.0-draft.1/` with corresponding fixtures, scope documentation, and tests.
- Author existing question-graph content in `drafts/core/source/` using the [legacy playbook](standards/core-graph-authoring-playbook.md).
- Propose a public domain profile, standards mapping, vendor integration, or business overlay with explicit dependencies and limitations. A profile is a public semantic specialization; an integration or policy does not redefine Core meaning.

Use the **Core RFC** issue template for a meaning, compatibility, or format change. Use the **Implementation report** template for reproducible trial results. Do not describe an unreviewed mapping as supported interoperability.

## A useful proposal

State the concrete investigative problem, affected role, current behavior, intended behavior, and smallest example that distinguishes them. Include alternatives and existing-standard reuse; name any lost information, security/privacy effects, extension requirements, or compatibility break. Disclose relevant affiliations and conflicts. Include opposing or uncertain evidence rather than removing it to obtain a passing example.

For technical changes, provide:

1. Exact source and binding versions, requirement IDs, changed artifact paths, and digests where applicable.
2. A synthetic reproduction and expected pass, fail, indeterminate, or notRun result.
3. The test command, observed result, environment, and known exclusions.
4. Migration behavior for existing records and handling of unsupported semantics.

## Local checks

Use Node.js 24 LTS (see `.node-version`) and Python 3:

```sh
npm ci
npm run check
python3 -m unittest discover -s tests/legacy -v
python3 scripts/validate_release_contract.py
```

For legacy graph changes, also run:

```sh
python3 scripts/lint_core_graph_quality.py --graph-path drafts/core/tensor.core.graph.json --entry-path drafts/core/source/entry_nodes.json --output-dir /tmp/tensor-draft-quality
```

Generated candidate schemas must match `schemas.mjs`. Regenerate with `node core/v0.1.0-draft.1/scripts/write-schemas.mjs` and include source plus generated changes. Do not modify existing versioned release artifacts to make a test pass. Do not regenerate stable checksums after changing historical bytes.

Keep changes focused. Use commit subjects such as `docs(core): clarify partial exchange` or `fix(core): reject an invalid transition`. A pull request should explain the problem, final behavior, exact validation, and remaining risks. A candidate change remains a candidate after merge unless the separate release gate is satisfied.

## Rights, evidence, and conduct

The repository's [existing license](LICENSE) is unchanged. Submit material you have the right to contribute; identify incorporated third-party material and its terms. Do not add confidential records, credentials, personal information, or unapproved incident evidence. Prefer synthetic fixtures, explicitly labeled as such. Respect contributors and make technical objections specific and evidence-based.

No additional contributor agreement, certification entitlement, patent covenant, or conduct enforcement body is created by this guide. Selection of those policies and responsible contacts remains part of bootstrap governance. Follow [SECURITY.md](SECURITY.md) for sensitive reports; a public issue is not a private reporting channel.
