import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { validateBundle } from '../../core/v0.1.0-draft.1/index.mjs';
import { validURI } from '../../core/v0.1.0-draft.1/schema-validator.mjs';

const original = JSON.parse(await readFile(new URL('../../core/v0.1.0-draft.1/examples/case-a.bundle.json', import.meta.url), 'utf8'));
const clone = (value) => JSON.parse(JSON.stringify(value));
const sample = () => clone(original);
const urn = (suffix) => `urn:example:tensor:review-regression:${suffix}`;
const entry = (bundle, suffix) => {
  const result = bundle.record.entries.find((item) => item.id.endsWith(`:${suffix}`));
  assert.ok(result, `Fixture contains ${suffix}`);
  return result;
};
const failures = (result) => JSON.stringify({ status: result.status, findings: result.checks.filter((check) => check.status !== 'pass'), transitions: result.transitions, unresolvedReviews: result.unresolvedReviews }, null, 2);

test('dependency expansion respects a receiver-lowered work budget', async () => {
  const result = await validateBundle(sample(), { maxDependencySteps: 1 });
  assert.equal(result.status, 'fail', failures(result));
  assert.ok(result.checks.some(check => check.requirement === 'TC-35' && check.message.includes('work budget')), failures(result));
  assert.ok(result.transitions.every(transition => transition.status !== 'pass'), failures(result));
});

test('transition results include failures found during later lineage checks', async () => {
  const bundle = sample();
  const sourceAssessment = entry(bundle, 'assessment-transfer-yes');
  sourceAssessment.supersedes = { entryId: sourceAssessment.id, reason: 'Invalid self-revision used to test the prerequisite report.' };
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'fail', failures(result));
  assert.equal(result.transitions[0].status, 'fail', failures(result));
});

function retainPauseReview(bundle) {
  const prior = entry(bundle, 'review-pause-unresolved');
  const retained = clone(prior);
  retained.id = urn('retained-review');
  retained.disposition = 'retained';
  retained.rationale = 'The reviewer retains the original precaution after inspecting the later attachment assessment.';
  retained.supersedes = { entryId: prior.id, reason: 'The pending review has now completed.' };
  bundle.record.entries.push(retained);
  bundle.record.view = { mode: 'current', selectionDecisionIds: [retained.id] };
  return retained;
}

function bindInterval(bundle, start, end) {
  const instance = entry(bundle, 'instance-transfer');
  instance.timeContext = { status: 'bounded', start, end };
  instance.parameterBindings.window = clone(instance.timeContext);
  return instance;
}

test('a selected retained review becomes stale when its selected assessment is superseded', async () => {
  const bundle = sample();
  const retained = retainPauseReview(bundle);
  const previousAssessment = entry(bundle, 'assessment-attachment-yes');
  const replacement = clone(previousAssessment);
  replacement.id = urn('later-attachment-assessment');
  replacement.rationale = 'A later analysis changes the content conclusion and requires renewed review.';
  replacement.outcome = 'no';
  replacement.supersedes = { entryId: previousAssessment.id, reason: 'Later analysis corrects the prior assessment.' };
  bundle.record.entries.push(replacement);
  assert.ok(retained.selectedInputIds.includes(previousAssessment.id));
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'indeterminate', failures(result));
  assert.ok(result.checks.some((check) => check.requirement === 'TC-28' && check.status === 'indeterminate'), failures(result));
  assert.ok(result.unresolvedReviews.some((review) => review.entryId === entry(bundle, 'decision-pause').id), failures(result));
});

test('a revised review makes decisions depending on the replaced assessment need review', async () => {
  const bundle = sample();
  retainPauseReview(bundle);
  const previousAssessment = entry(bundle, 'assessment-transfer-yes');
  const replacement = clone(previousAssessment);
  replacement.id = urn('revised-transfer-assessment');
  replacement.rationale = 'A separate assessment replaces the reviewed conclusion under an explicit revised disposition.';
  delete replacement.supersedes;
  const review = {
    id: urn('transfer-assessment-revised-review'), type: 'Decision',
    recordedAt: '2026-01-12T10:26:00Z', attribution: clone(previousAssessment.attribution),
    targetInvestigationId: bundle.record.investigationId,
    selectedInputIds: [replacement.id], reviewedEntryIds: [previousAssessment.id],
    triggeringEntryIds: [replacement.id], replacementEntryIds: [replacement.id],
    disposition: 'revised', rationale: 'Replace the reviewed assessment with the identified new entry.',
    policyStatus: { status: 'notApplicable' }, authorityStatus: { status: 'notApplicable' }
  };
  bundle.record.entries.push(replacement, review);
  bundle.record.view.selectionDecisionIds.push(review.id);
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'indeterminate', failures(result));
  assert.ok(result.unresolvedReviews.some((item) => item.entryId === entry(bundle, 'decision-open-content').id), failures(result));
});

test('supplied prior definition pins cannot reuse a definition ID and version for another digest', async () => {
  const bundle = sample();
  const previous = clone(bundle.record);
  previous.definitionReferences[0].sha256 = '0'.repeat(64);
  for (const item of previous.entries) if (item.definitionRef) item.definitionRef.sha256 = '0'.repeat(64);
  bundle.record.snapshotId = urn('later-snapshot');
  bundle.record.sourceSnapshotIds = [previous.snapshotId];
  const result = await validateBundle(bundle, { previousRecords: [previous] });
  assert.equal(result.status, 'fail', failures(result));
  assert.ok(result.checks.some((check) => check.requirement === 'TC-05' && check.status === 'fail'), failures(result));
});

// This oracle deliberately uses unmodified ajv-formats rather than the
// candidate predicate, so a defect in validURI cannot make both sides agree.
const uriEngine = new Ajv2020({ strict: false });
addFormats(uriEngine, { mode: 'full' });
const uriOracle = uriEngine.compile({ type: 'string', format: 'uri' });
const uriCases = [
  ['urn:example:ordinary', true],
  ['urn:example:escaped%20value', true],
  ['https://example.org/path?q=value#fragment', true],
  ['https://[::1]/path', true],
  ['https://user:pass@example.org:443/a%2Fb', true],
  ['urn:example:value%GG', false],
  ['urn:example:value%', false],
  ['urn:example:value%2', false],
  ['urn:example:a|b', false],
  ['urn:example:a<b', false],
  ['urn:example:a>b', false],
  ['urn:example:a^b', false],
  ['urn:example:a`b', false],
  ['urn:example:a\\b', false],
  ['urn:example:a{b', false],
  ['urn:example:a}b', false],
  ['https://example.org/path[invalid]', false]
];
for (const [uri, expected] of uriCases) {
  test(`URI syntax agrees with an independent oracle: ${uri}`, async () => {
    assert.equal(uriOracle(uri), expected, 'The independently configured URI engine checks this corpus.');
    assert.equal(validURI(uri), expected);
    const bundle = sample();
    bundle.record.snapshotId = uri;
    const result = await validateBundle(bundle);
    assert.equal(result.status, expected ? 'pass' : 'fail', failures(result));
  });
}

for (const [name, start, end, expected] of [
  ['reversed submillisecond interval', '2026-01-12T10:00:00.0002Z', '2026-01-12T10:00:00.0001Z', 'fail'],
  ['reversed long fractional interval', '2026-01-12T10:00:00.000000000000000000002Z', '2026-01-12T10:00:00.000000000000000000001Z', 'fail'],
  ['positive offset with valid fractional ordering', '2026-01-12T10:00:00.0002+01:00', '2026-01-12T09:00:00.0003Z', 'pass'],
  ['negative offset with valid fractional ordering', '2026-01-12T08:00:00.0002-01:00', '2026-01-12T09:00:00.0003Z', 'pass'],
  ['equivalent fraction values with different precision', '2026-01-12T10:00:00.1000000000001+01:00', '2026-01-12T09:00:00.1000000000001000Z', 'pass'],
  ['offset crossing midnight with reversed fractions', '2026-01-12T23:59:59.999999999-00:01', '2026-01-13T00:00:59.999999998Z', 'fail']
]) {
  test(`timestamp comparison preserves ${name}`, async () => {
    const bundle = sample();
    bindInterval(bundle, start, end);
    const result = await validateBundle(bundle);
    assert.equal(result.status, expected, failures(result));
    if (expected === 'fail') assert.ok(result.checks.some((check) => check.requirement === 'TC-08' && check.status === 'fail'), failures(result));
  });
}

test('a transition cannot report pass after its source instance context fails validation', async () => {
  const bundle = sample();
  entry(bundle, 'instance-transfer').parameterBindings.subject = urn('wrong-subject');
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'fail', failures(result));
  assert.ok(result.checks.some((check) => check.requirement === 'TC-13' && check.status === 'fail'), failures(result));
  const transition = result.transitions.find((item) => item.decisionId === entry(bundle, 'decision-open-content').id);
  assert.ok(transition, 'The transition result remains explicitly reported.');
  assert.equal(transition.status, 'fail', failures(result));
});

test('retained review may compare superseded inputs when it explicitly accounts for their correction', async () => {
  const bundle = sample();
  const retained = retainPauseReview(bundle);
  const historical = entry(bundle, 'assessment-attachment-unknown');
  const replacement = entry(bundle, 'assessment-attachment-yes');
  retained.selectedInputIds = [historical.id, replacement.id];
  retained.triggeringEntryIds = [replacement.id];
  retained.rationale = 'Retain the precaution after comparing its original unknown assessment with the identified correction.';
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'pass', failures(result));
  assert.deepEqual(result.unresolvedReviews, []);
  assert.equal(entry(bundle, 'decision-pause').selectedAssessmentId, historical.id);
});

test('a retained review must acknowledge a new sibling correction of the reviewed decision input', async () => {
  const bundle = sample();
  const retained = retainPauseReview(bundle);
  const sibling = clone(entry(bundle, 'assessment-attachment-yes'));
  sibling.id = urn('parallel-attachment-no');
  sibling.outcome = 'no';
  sibling.rationale = 'A separate attributed correction disagrees with the earlier yes revision.';
  sibling.supersedes = { entryId: entry(bundle, 'assessment-attachment-unknown').id, reason: 'Concurrent correction of the original unknown assessment.' };
  bundle.record.entries.push(sibling);
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'indeterminate', failures(result));
  assert.ok(result.unresolvedReviews.some(review => review.entryId === entry(bundle, 'decision-pause').id), failures(result));

  const reconciled = clone(retained);
  reconciled.id = urn('review-after-parallel-correction');
  reconciled.supersedes = { entryId: retained.id, reason: 'Review now explicitly considers both concurrent corrections.' };
  reconciled.triggeringEntryIds.push(sibling.id);
  reconciled.selectedInputIds.push(sibling.id);
  bundle.record.entries.push(reconciled);
  bundle.record.view.selectionDecisionIds = [reconciled.id];
  const after = await validateBundle(bundle);
  assert.equal(after.status, 'pass', failures(after));
  assert.deepEqual(after.unresolvedReviews, []);
});
