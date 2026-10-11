# Institutional review and partnership readiness

Prioritized October 11, 2026. TENSOR remains an independent public standard for all cyber investigations, usable by humans and agents, with vendor and business layers above Core. AI-security teams governing agents are the first recruitment audience, not a restriction on the standard's scope.

The candidate contract, executable reference implementation, synthetic cases, public website and automatic publishing exist. They make TENSOR ready to invite critical review. They do not establish independent interoperability, adopted governance, institutional endorsement or a stable standard. This plan supplements the [reviewer packet](reviewer-packet.md) and [90-day adoption plan](adoption-plan.md); dates below are proposed work windows, conditional on accepted owners and available reviewers.

| Priority and window | Work and accountable owner | Evidence required to advance |
| --- | --- | --- |
| P0: operational closeout, now | Maintainer: update CI, deployment instructions, review ownership and maintenance automation; owner: rotate the temporary Pages token before October 18 and verify recovery access | Successful checks on merged heads, successful main deployment, artifact hashes, replacement credential proven before the old one is revoked |
| P1: stewardship, week 1 | Owner and consenting contributors: publish accepted bootstrap appointments, affiliations/conflicts, a responsible private reporting contact and review/appeal procedure; inspect independent account recovery and recruit a second administrator | Accepted public roster, actual private reporting channel, recorded governance status and recoverable TENSOR-owned infrastructure. One person may hold multiple roles, but that is not independent oversight |
| P1: freeze a review snapshot, weeks 1–2 | Core editor and conformance maintainer: select exact contract/binding/fixture commits, publish a concise brief and limitations, inventory licensing/IP/provenance questions, and record the review window and issue-disposition method | A reviewer can retrieve, cite, reproduce and return a finding against one unchanged artifact set. Use existing immutable candidate artifacts; later semantic corrections require a distinguishable revision |
| P2: targeted technical review, weeks 2–4 | Convenor: invite consenting reviewers covering agent security, conventional incident response, independent implementation, and CASE/UCO or evidence modeling | At least two substantive reviews independent of the principal authors and each other; versioned findings, affiliations, conflicts and public responses. An invitation or meeting is not acceptance or endorsement |
| P2: independent exchange, weeks 3–6 | An external implementer and the conformance maintainer: exchange both reference cases in both directions, including uncertain/conflicting assessments, missing evidence and unsupported semantics | Independently authored producer/consumer evidence, exact versions/hashes, declared dependencies and loss, failures retained. A second interface around the reference validator does not qualify |
| P2: standards reuse, weeks 3–6 | Evidence-model reviewer and Core editor: map one complete case to CASE/UCO; document fields reused, gaps and round-trip loss; document the distinct roles of ATT&CK and D3FEND | Reproducible mapping and loss report supporting an explicit reuse/specialization decision. Do not claim compatibility from terminology alone or position TENSOR as replacing those knowledge bases |
| P3: practical usefulness, weeks 5–8 | Practitioner reviewers: compare the same handoff/review task with and without TENSOR, using authorized synthetic or de-identified cases and recording task-order effects | Review time, missing-context errors, unresolved questions, lost meaning, disagreements and burden, with participant/sample limits. Equal investigative conclusions are not the goal |
| P3: scoped partnerships, weeks 6–10 | Owner/convenor and consenting counterpart: agree a contribution such as an independent parser, case evaluation, mapping or coauthored study | Written scope, named accepted owners, public deliverable, timeline and agreed attribution. No exclusive Core access, paid influence on requirements or unsupported partner logos |
| P4: publish results and choose the next candidate, weeks 8–12 | Editors and consenting coauthors: publish reproducible findings, respond to objections, issue a revised candidate where needed, and assess a stewardship/standards venue | Public technical report, objection dispositions, maintenance plan and recorded decision to remain draft or open the required stable-release review. Publication is not ratification |

## October 11 review-preparation update

PR #9 is merged. [Review 2026-10-11.1](../review/2026-10-11.1/README.md) freezes its merged technical source, byte pins, validation baseline, walkthrough and review form. The owner accepted the bootstrap steward/convenor, editor and conformance roles; see [the current record](stewardship.md). Independent reviews, exchange, partnerships and external references remain unverified. Conflict disclosure, recovery/billing confirmation, a consenting second administrator and token replacement remain pending. No invitations or formal review window were initiated. The earlier table records proposed work windows rather than completed outcomes.

## The first review brief

Prepare a short, citable brief that answers these questions before asking anyone to invest time:

1. What recurring problem does TENSOR solve? A person or agent hands off an investigation without losing the question, evidence basis, uncertainty, attribution, decision rationale or revision history.
2. What is available now? The logical contract, candidate binding, validator, two synthetic cases, browser Lab and preserved legacy graph archive. Link the exact versions, not an unqualified moving "latest".
3. What is being asked? Challenge specific requirements, implement a small independent reader/writer, or evaluate a concrete handoff. Ask for a bounded contribution rather than a generic endorsement.
4. What is not proven? Independent exchange, useful field performance, legal admissibility, safety, certification, institutional adoption and governance adoption.
5. What happens to feedback? Use the implementation-report or RFC issue template, reference requirement IDs and versions, publish objections and dispositions, and preserve dissent.

The existing contract, cases, public Lab and reviewer packet are sufficient to begin technical invitations once a responsible contact and review owner accept their roles. Do not delay all review for a custom domain, incorporation, a larger catalog, SDKs in many languages or a broad marketing launch.

## Partnership offers

Start with one bounded offer per prospective collaborator:

- Research group: evaluate a human-led and an agent-related handoff and coauthor a reproducible report, subject to their approval.
- Incident-response or AI-security team: test case portability and identify missing context using synthetic or authorized data.
- CASE/UCO implementer or evidence-model specialist: produce a concrete mapping and loss report and recommend reuse.
- Independent tool developer: implement a minimal import/export path against the public contract with disclosed code dependencies.

Keep Core freely available. Membership, sponsorship and vendor integration must not control investigative meaning, independent review outcomes or public access. Do not send invitations, make institutional submissions or use a collaborator's identity without the owner's specific authorization and the counterpart's consent where applicable.

## Readiness scoreboard

As of this plan, only author/reference-implementation and hosted-publication evidence has been verified. Accepted stewardship appointments, substantive independent reviews, independent implementation exchange, jointly reviewed studies, signed partnerships and external published references remain unverified. Track each separately with links to actual evidence and a consenting owner. Traffic and stars are discovery signals, not substitutes.

Technical maintenance uses the Node 24 LTS version pinned in `.node-version`, commit-pinned actions on the Node 24 action runtime, Ubuntu 24.04 and weekly update proposals. Review the Node LTS patch pin during monthly maintenance; Dependabot's action/npm updates do not update `.node-version`. Both repositories require pull requests, an up-to-date passing primary validation check and resolved review conversations on `main`, including for administrators; force-pushes and deletion are disabled. Independent approving reviews are not yet required because no independent maintainer has accepted the role. GitHub private vulnerability reporting, secret-scanning push protection and Dependabot security updates are enabled in both repositories. Keep the frozen candidate and legacy artifacts unchanged during operational maintenance. The temporary website deployment token expires October 18, 2026; replacement remains the owner's planned action.
