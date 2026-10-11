# Release preparation and claims

This checklist separates an implementation candidate from a stable public standard. Unchecked entries are gates to verify, not claims of missing code. Record exact commits, commands, results, URLs, and dates in the release review; do not substitute an old result after relevant changes.

## Candidate source gate

- [ ] Identify framework and website commits, candidate version, proposal revision, artifacts, and SHA-256 digests.
- [ ] Run `npm ci` and `npm run check` on the final framework commit.
- [ ] Run `python3 -m unittest discover -s tests/legacy -v` and `python3 scripts/validate_release_contract.py`.
- [ ] Verify all pre-existing versioned `releases/` bytes match the baseline commit; do not repair a mismatch by regenerating checksums.
- [ ] Confirm generated schemas and examples match their source and that published URLs identify the candidate, not a stable release.
- [ ] Review validator findings, limits, and unsupported semantics; retain notRun and indeterminate outcomes.
- [ ] Confirm no private incident data, credentials, unapproved content, or inferred governance appointments are included.
- [ ] Record remaining reviewer findings, fixes, and decisions.

## Website and distribution gate

- [ ] Verify dedicated TENSOR ownership and recovery access for production hosting, domains, deployment credentials, and project contact identities; temporary support is not a permanent affiliation.
- [ ] Synchronize runtime and public candidate artifacts from the exact framework source; retain provenance.
- [ ] Run the website's validation and dependency checks against its final commit.
- [ ] Verify both sample cases and a local file through import, inspection, validation, export, and re-import in a browser.
- [ ] Verify malformed data, wrong digests, missing references, required unsupported semantics, and resource limits produce truthful results.
- [ ] Verify desktop/mobile navigation, light/dark readability, downloads, keyboard operation, console behavior, and Content Security Policy.
- [ ] Check that local investigation imports are not sent to analytics, error collectors, or remote services.
- [ ] Deploy to a named preview and verify the actual public artifact bytes and runtime behavior there.
- [ ] Record the separately verified production deployment, if performed; a preview and a merged PR do not establish production state.

## Before the first stable Core release

- [ ] Publish concrete CASE/UCO reuse and mapping decisions with information-loss analysis.
- [ ] Freeze a reviewed binding, equality rules, supported profile/dependency rules, and namespace policy.
- [ ] Complete bidirectional exchange with two independently developed implementations and publish reproducible results.
- [ ] Obtain substantive reviews by at least two independent reviewers, disclose conflicts, and resolve or explicitly defer objections.
- [ ] Adopt governance and applicable rights policies through a public decision; publish accepted steward roles and a reporting contact.
- [ ] Complete the applicable public review window and compatibility/migration decision.
- [ ] Publish immutable specification, schemas, fixtures, changelog, digests, decision record, and scoped capability statements together.

## What each evidence layer permits

| Evidence | Supported statement | Unsupported inference |
| --- | --- | --- |
| Source and passing local checks | Named reference implementation passes named checks | Complete semantic correctness, safe operation, or institutional approval |
| Verified preview | Named candidate works in that observed preview | Production release or durable availability |
| Independent exchange reports | Named implementations preserve specified meanings for tested cases | Universal interoperability |
| Adopted governance and stable decision | Identified group approved identified text under its recorded process | Recognition by an outside standards body |
| Published reference or signed partnership | Exact documented relationship | Broad endorsement beyond that document |

Do not use “certified,” “ratified,” “industry standard,” “MITRE partner,” or “production ready” without evidence supporting that exact claim. Preserve unsuccessful evaluations as part of the review record.
