# TENSOR current technical review

This package contains the **same current public reference dataset** used by the website, graph, profiles and Lab examples. There is no reviewer-only graph. The public graph has {{QUESTIONS}} questions and {{ROUTES}} routes across {{DOMAINS}} domains, with {{PROFILES}} event profiles, {{QUALIFIED}} qualified definitions and {{REFERENCE_CASES}} cross-domain reference cases.

Graph: **{{GRAPH_VERSION}}**. Dataset: **{{DATASET_ID}}**. Exact source: **{{SOURCE_COMMIT}}**. `dataset.json` identifies every active artifact and its SHA-256. Graph and Core schema versions describe their respective formats; case records and vendor/company layers are contexts and additions, not alternate public datasets.

Download [the ZIP](review-package.zip). Extract it into an empty directory. Verify the source archive before extracting it with `python3 verify-snapshot.py`, then verify an extracted source directory with `python3 verify-snapshot.py /absolute/path/to/source`. The archive contains committed source at the identified commit, excluding generated `review/current` packaging to avoid recursion. Historical releases and the earlier review snapshot remain archives.

Use [the walkthrough](walkthrough.md) and [finding form](review-form.md). The candidate remains unratified. Passing author-side checks is distinct from independent review, authenticated incident evidence and interoperability between separately developed implementations.

## Reproduce

Use Node 24.21.0, Python 3.11 or later, and Git for the full-history checks. Start either workflow in the directory where you extracted the review ZIP.

### Standalone archive: Core checks

The source archive contains pinned files, without Git history. Verify it before extraction, then run the Core checks without a repository:

```sh
python3 verify-snapshot.py
mkdir source
tar -xzf source.tar.gz -C source
python3 verify-snapshot.py source
cd source
npm ci
npm run check
```

These checks cover schemas, 176 Core tests, binding examples, cross-domain cases and the current dataset inventory. They do not run the historical-preservation Python regressions.

### Full reproduction: verified checkout with history

The Python regression suite and coverage-lineage audit read earlier committed artifacts using Git. They require a full clone; an archive, `git init`, or a shallow clone does not supply those historical objects. From the extracted review ZIP directory, obtain the exact same pinned source with its history:

```sh
git clone https://github.com/TENSOR-Standards-Consortium/TENSOR-Framework.git TENSOR-review
git -C TENSOR-review checkout --detach {{SOURCE_COMMIT}}
python3 verify-snapshot.py TENSOR-review
cd TENSOR-review
npm ci
npm run check
node scripts/build_dataset.mjs --check
python3 -m unittest discover -s tests/legacy -q
python3 scripts/verify_semantic_review.py
python3 scripts/restore_original_questions.py --check
python3 scripts/build_event_profiles.py --check
python3 scripts/audit_graph_coverage.py --check
python3 scripts/evaluate_entry_scenarios.py
python3 scripts/validate_release_contract.py
```

The verifier compares the clone's source files against the package pins. Both workflows examine the same current dataset; Git history supplies preservation evidence rather than another active graph.

`validation.json` records observed results and exclusions. Current stewardship and the public finding process are in `docs/stewardship.md` and `docs/review-process.md` in the source. No invitations are sent by publishing this package.
