# ADR 001: trial JSON binding for the Core contract

Status: **selected for implementation trials; unratified**. Proposal `0.1.0`; binding `0.1.0-draft.1`. Date: October 10, 2026.

## Problem

The founding proposal states a logical investigative contract but cannot demonstrate exchange by prose alone. Existing question graphs contain reusable questions and branches; they do not contain a particular investigation's attributed evidence, assessments, or decisions. A testable wire representation is needed to expose ambiguities before asking institutions to adopt the standard.

## Decision

Implement a small standalone JSON candidate and preserve the original logical proposal. Use separate bundle, record, and definition schemas, explicit typed references, detached SHA-256 pins for exact UTF-8 definition bytes, immutable entry identities, and explicit full/partial exchange declarations. Keep unknown required semantics visible as indeterminate. Keep operational execution outside the contract.

The [binding](../core/v0.1.0-draft.1/binding.md) is the authority for this candidate's representation, namespace syntax, equality, and review-status rules. The [coverage statement](../core/v0.1.0-draft.1/coverage.md) bounds the reference validator's claims. The candidate is identified separately from both proposal `0.1.0` and existing dated graph releases. It does not ratify D10 or settle a permanent format.

## Reuse decision still required

CASE/UCO overlaps materially with the investigation-record model. A prototype is justified here to test TENSOR's question-instance, paired-transition, uncertainty, revision, and exchange requirements; this is not evidence that a separate permanent format is preferable. Before a stable binding, compare the two synthetic cases against a CASE profile, a CASE extension, and a separately mapped format. Record preserved meaning, unsupported features, duplication, dependencies, and information loss. See the [source-backed crosswalk](../proposals/founding-core-v0.1.0/03-standards-crosswalk.md) and [CASE design](https://caseontology.org/resources/case_design_document.html).

JSON Schema Draft 2020-12 describes structural constraints; semantic checks remain separate. JSON object ordering and whitespace do not define record meaning. Exact-byte definition hashing does not claim JSON canonicalization, digital signatures, or authenticity. See the [JSON Schema specification](https://json-schema.org/draft/2020-12/json-schema-core) for the schema vocabulary.

## Consequences and reversal

Implementers can exercise one explicit candidate now. The costs are a temporary additional representation and future migration work. If reuse review chooses a different binding, publish a new candidate version, an explicit mapping and loss report, and fixtures covering the differences. Keep this candidate retrievable; do not change its meaning under the same public identity after publication.

Stable release still requires independent exchange evidence, review of the standards boundary, adopted stewardship and rights decisions, and a recorded compatibility decision. The [release checklist](release-checklist.md) separates those gates.
