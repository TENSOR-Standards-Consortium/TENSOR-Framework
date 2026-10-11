# Security and sensitive reports

The candidate validator and browser lab process investigation data. A validation result is not evidence truth, a verified identity, authorization to act, or a finding that a system is safe. Imported references and metadata must remain data: they must not trigger network retrieval, commands, or operational actions.

## Reporting

For an ordinary defect with a synthetic reproduction and no sensitive details, open a repository issue and identify the exact commit, binding version, environment, expected result, and actual result.

For a vulnerability, accidental disclosure, credentials, or real investigation data, use GitHub's **Report a vulnerability** option in this repository's Security tab if it is available. This document does not claim that private reporting has been enabled or that a staffed response service exists. If the option is unavailable, open a minimal public issue requesting a private contact **without the sensitive details**, and wait for a maintainer to establish that channel. Do not attach exploit secrets, live records, or personal data to a public issue.

No response-time commitment, bounty, support contract, or production security certification is offered by this candidate.

## Maintainer handling

Acknowledge the channel without copying sensitive content into public discussion. Preserve a minimal reproduction using synthetic data, identify affected versions, and document the scope of any fix. Publish corrected candidate artifacts under a distinguishable version when their interpretation changes. Keep prior published artifacts retrievable and publish an advisory where appropriate; do not silently overwrite a historical release.

Verify resource limits, duplicate-member rejection, reference closure, unsupported required semantics, revision integrity, and the no-execution boundary when a change affects imported records. Avoid real-world operational evidence in CI and fixtures.
