# Core candidate reviewer packet

Review target: proposal `0.1.0` and candidate binding `0.1.0-draft.1`. This is an invitation package, not evidence that invitations have been sent, roles accepted, or reviews performed.

## What to review

Start with the [charter](../proposals/founding-core-v0.1.0/00-charter.md), [logical contract](../proposals/founding-core-v0.1.0/01-core-contract.md), [candidate binding](../core/v0.1.0-draft.1/binding.md), [coverage](../core/v0.1.0-draft.1/coverage.md), and [standards crosswalk](../proposals/founding-core-v0.1.0/03-standards-crosswalk.md). The two [synthetic examples](../core/v0.1.0-draft.1/examples/README.md) cover an agent-related investigation and a conventional investigation with mixed participation.

Reviewers should challenge:

1. Whether the model retains the question, exact context, source definition, evidence basis, uncertainty, dissent, and decision rationale needed to understand a case.
2. Whether an independent implementation preserves that meaning through export/import, including unknown optional metadata, partial records, required unsupported extensions, and conflicting revisions.
3. Whether authority assertions remain separate from receiver-local authorization and whether any imported text can be misread as an instruction.
4. Whether CASE/UCO reuse should replace or specialize the trial format, with concrete mappings and recorded loss rather than similarity of labels.
5. Whether a conventional human-led case works as well as an agent-led case, and whether any vendor-specific assumption leaks into Core.

## Reproduce

From an exact checkout using Node.js 22 or newer:

```sh
git rev-parse HEAD
npm ci
npm run check
node core/v0.1.0-draft.1/cli.mjs core/v0.1.0-draft.1/examples/case-a.bundle.json
node core/v0.1.0-draft.1/cli.mjs core/v0.1.0-draft.1/examples/case-b.bundle.json
```

Retain the commit, environment, complete report, fixture digests, and exclusions. A pass from this reference validator is an observation about this implementation, not an independent interoperability result.

## Independent exchange trial

Use at least two implementations developed independently. Record their authors, affiliations, versions, shared code or generated dependencies, supported roles, and profiles. A wrapper around the same validator is not a second independent implementation.

For both cases, have one implementation produce/export and the other read/re-export. Compare the resulting meanings under the candidate equality rules; reverse direction. Include valid uncertainty, an omitted protected dependency, a required unsupported extension, an optional unknown metadata field, a digest mismatch, and a changed assessment requiring review. Report passes, failures, indeterminate interpretation, and losses. State what was not tested. Do not modify a failing input silently to obtain a success.

## Return a review

Use the **Implementation report** issue template with a synthetic reproduction. Reference TC requirement IDs and exact paths. Distinguish blocking ambiguity from an enhancement or stylistic preference. Include alternative language or a counterexample when possible. Sensitive data follows [SECURITY.md](../SECURITY.md).

The proposed stable gate calls for substantive review by at least two reviewers independent of the principal authors and of each other. Publish affiliations and conflicts; independence is a claim to substantiate, not a label for another agent or process in the same authoring task.

A useful reviewer summary is: “I reviewed [commit/binding], exercised [roles/cases], observed [results], found [issues], and did not assess [limits].” Avoid blanket statements of certification, legal compliance, safety, or endorsement.
