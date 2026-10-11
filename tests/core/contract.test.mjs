import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { validateBundle, parseBundle, serializeBundle, semanticEqual } from '../../core/v0.1.0-draft.1/index.mjs';

const fixtureRoot = new URL('../../core/v0.1.0-draft.1/examples/', import.meta.url);
const originals = Object.fromEntries(await Promise.all(['a', 'b'].map(async (name) =>
  [name, JSON.parse(await readFile(new URL(`case-${name}.bundle.json`, fixtureRoot), 'utf8'))])));
const clone = (value) => JSON.parse(JSON.stringify(value));
const sample = (name = 'a') => clone(originals[name]);
const record = (bundle) => bundle.record;
const entries = (bundle) => record(bundle).entries;
const entry = (bundle, suffix) => {
  const found = entries(bundle).find((candidate) => candidate.id.endsWith(`:${suffix}`));
  assert.ok(found, `Fixture is missing entry ${suffix}`);
  return found;
};
const kind = (bundle, type) => entries(bundle).find((candidate) => candidate.type === type);
const urn = (suffix) => `urn:example:tensor:tests:${suffix}`;
const detail = (result) => JSON.stringify({ status: result.status, findings: result.checks?.filter((check) => check.status !== 'pass'), transitions: result.transitions }, null, 2);
const expect = async (bundle, status, requirement) => {
  const result = await validateBundle(bundle);
  assert.equal(result.status, status, detail(result));
  assert.ok(Array.isArray(result.checks), 'Validation reports named checks');
  for (const check of result.checks) {
    assert.equal(typeof check.id, 'string');
    assert.equal(typeof check.message, 'string');
    assert.ok(['pass', 'fail', 'indeterminate', 'notRun'].includes(check.status));
  }
  if (requirement) assert.ok(result.checks.some((check) =>
    check.requirement === requirement && check.status === status),
    `Expected ${requirement} ${status}: ${detail(result)}`);
  return result;
};

for (const name of ['a', 'b']) {
  test(`case ${name.toUpperCase()} passes the candidate checks`, async () => {
    await expect(sample(name), 'pass');
  });
  test(`case ${name.toUpperCase()} parse and serialization retain semantic content`, async () => {
    const source = sample(name);
    const recovered = parseBundle(serializeBundle(source));
    assert.ok(semanticEqual(source, recovered));
    await expect(recovered, 'pass');
  });
}

const invalidMutations = [
  ['a required envelope field cannot be missing', (b) => { delete record(b).snapshotId; }],
  ['unknown Core attributes cannot silently change meaning', (b) => { kind(b, 'Assessment').assumeTrue = true; }],
  ['entry types cannot be invented', (b) => { kind(b, 'Observation').type = 'ConfirmedTruth'; }],
  ['duplicate entry identities cannot overwrite earlier content', (b) => {
    const second = clone(kind(b, 'Assessment')); second.rationale = 'Conflicting replacement under the same ID'; entries(b).push(second);
  }],
  ['a reusable question cannot stand in for a bound instance', (b) => {
    kind(b, 'Assessment').targetInstanceId = kind(b, 'QuestionInstance').questionId;
  }],
  ['entry references must resolve to their required type', (b) => {
    kind(b, 'Assessment').targetInstanceId = kind(b, 'EvidenceReference').id;
  }],
  ['attribution must resolve to an Actor', (b) => {
    kind(b, 'Observation').attribution.actorId = kind(b, 'EvidenceReference').id;
  }],
  ['entries require attributed or explicitly unknown source identity', (b) => { delete kind(b, 'Observation').attribution; }],
  ['recording time cannot omit its UTC offset', (b) => { kind(b, 'Observation').recordedAt = '2026-01-12T10:08:00'; }],
  ['unknown local offsets are not known recording offsets', (b) => { kind(b, 'Observation').recordedAt = '2026-01-12T10:08:00-00:00'; }],
  ['impossible calendar timestamps are not accepted by Date normalization', (b) => { kind(b, 'Observation').recordedAt = '2026-02-30T10:08:00Z'; }],
  ['bounded instance time cannot run backwards', (b) => {
    kind(b, 'QuestionInstance').timeContext.end = '2026-01-01T00:00:00Z';
  }],
  ['required parameter binding cannot disappear', (b) => { delete kind(b, 'QuestionInstance').parameterBindings.subject; }],
  ['parameter values must satisfy declared types', (b) => { kind(b, 'QuestionInstance').parameterBindings.subject = 17; }],
  ['observation evidence cannot be replaced with a Hypothesis', (b) => {
    kind(b, 'Observation').evidenceRefIds = [kind(b, 'Hypothesis').id];
  }],
  ['observation requires retained evidence or an explicit limitation reference', (b) => { kind(b, 'Observation').evidenceRefIds = []; }],
  ['unavailable evidence requires a locator absence reason', (b) => { delete kind(b, 'EvidenceReference').locatorAbsentReason; }],
  ['assessment outcomes remain yes no or unknown', (b) => { kind(b, 'Assessment').outcome = 'probably'; }],
  ['notApplicable cannot be encoded as a no outcome', (b) => {
    const a = entry(b, 'assessment-attachment-unknown'); a.applicability.status = 'notApplicable'; a.outcome = 'no';
  }],
  ['unresolved applicability cannot carry an outcome', (b) => {
    entry(b, 'assessment-attachment-unknown').applicability.status = 'unresolved';
  }],
  ['unknown outcomes require an explicit reason', (b) => { delete entry(b, 'assessment-attachment-unknown').unknownReasons; }],
  ['empty unknown reasons do not satisfy the contract', (b) => { entry(b, 'assessment-attachment-unknown').unknownReasons = []; }],
  ['other unknown reasons require explanation', (b) => {
    entry(b, 'assessment-attachment-unknown').unknownReasons = [{ code: 'other' }];
  }],
  ['zero assessment inputs require explanation', (b) => { kind(b, 'Assessment').inputs = []; }],
  ['input relationships cannot omit their purpose', (b) => { delete kind(b, 'Assessment').inputs[0].role; }],
  ['transition selection must include an explicit target pair', (b) => { delete entry(b, 'decision-open-content').selections[0].targetInstanceId; }],
  ['selected assessment must target exactly the decision source', (b) => {
    entry(b, 'decision-open-content').selectedAssessmentId = entry(b, 'assessment-attachment-yes').id;
  }],
  ['a selected transition must match the selected assessment outcome', (b) => { entry(b, 'assessment-transfer-yes').outcome = 'no'; }],
  ['transition decisions require at least one explicit selection', (b) => { entry(b, 'decision-open-content').selections = []; }],
  ['transition destination must identify the originating decision', (b) => {
    entry(b, 'instance-attachment').origin.originDecisionId = entry(b, 'decision-pause').id;
  }],
  ['transition destination cannot point to the source question', (b) => {
    entry(b, 'instance-attachment').questionId = entry(b, 'instance-transfer').questionId;
  }],
  ['unknown policy status requires a reason', (b) => { entry(b, 'decision-pause').policyStatus = { status: 'unknown' }; }],
  ['referenced authority must point to AuthorityAssertion entries', (b) => {
    entry(b, 'decision-pause').authorityStatus.authorityRefIds = [kind(b, 'Actor').id];
  }],
  ['action stage is explicit and bounded', (b) => { kind(b, 'ActionRecord').stage = 'recommended'; }],
  ['an action record cannot cite a hypothesis as its authorizing decision', (b) => {
    kind(b, 'ActionRecord').decisionId = kind(b, 'Hypothesis').id;
  }],
  ['an entry cannot supersede itself', (b) => {
    const a = entry(b, 'assessment-attachment-yes'); a.supersedes.entryId = a.id;
  }],
  ['revision lineage must preserve the entry type', (b) => {
    entry(b, 'assessment-attachment-yes').supersedes.entryId = kind(b, 'Observation').id;
  }],
  ['assessment revision lineage must preserve the bound target', (b) => {
    entry(b, 'assessment-attachment-yes').supersedes.entryId = entry(b, 'assessment-transfer-yes').id;
  }],
  ['supersession cannot create a cycle', (b) => {
    entry(b, 'assessment-attachment-unknown').supersedes = {
      entryId: entry(b, 'assessment-attachment-yes').id, reason: 'Adversarial cyclic lineage'
    };
  }],
  ['revision explanation cannot disappear', (b) => { delete entry(b, 'assessment-attachment-yes').supersedes.reason; }],
  ['revised review dispositions must identify replacement entries', (b) => {
    entry(b, 'review-pause-unresolved').disposition = 'revised';
  }],
  ['full exchange cannot hide a dangling evidence reference', (b) => {
    record(b).entries = entries(b).filter((e) => e.id !== entry(b, 'evidence-egress').id);
  }],
  ['a dangling reference is not repaired by an undeclared partial exchange', (b) => {
    const missing = entry(b, 'evidence-egress').id;
    record(b).entries = entries(b).filter((e) => e.id !== missing);
    record(b).completeness.exchangeScope = 'partial';
  }],
];

for (const [title, mutate] of invalidMutations) {
  test(title, async () => { const bundle = sample(); mutate(bundle); await expect(bundle, 'fail'); });
}

test('contradictory assessments remain preserved rather than implicitly reconciled', async () => {
  const bundle = sample();
  const alternative = clone(entry(bundle, 'assessment-attachment-yes'));
  alternative.id = urn('alternative-assessment'); alternative.outcome = 'no';
  alternative.rationale = 'Synthetic conflicting conclusion intentionally retained.';
  delete alternative.supersedes;
  entries(bundle).push(alternative);
  await expect(bundle, 'pass');
  const recovered = parseBundle(serializeBundle(bundle));
  assert.equal(entries(recovered).filter((e) => e.type === 'Assessment' &&
    e.targetInstanceId === alternative.targetInstanceId).length, 3);
});

test('record entry order does not determine semantic equality or selected outcomes', async () => {
  const bundle = sample();
  record(bundle).entries.reverse();
  await expect(bundle, 'pass');
  // Arrays retain order in this draft binding, so equality must not silently rewrite them.
  assert.equal(semanticEqual(bundle, originals.a), false);
  assert.equal(entry(bundle, 'decision-open-content').selectedAssessmentId,
    entry(originals.a, 'decision-open-content').selectedAssessmentId);
});

test('semantic comparison ignores object-key order but preserves values and array order', () => {
  assert.equal(semanticEqual({ x: [1, 2], y: { a: 1, b: 2 } }, { y: { b: 2, a: 1 }, x: [1, 2] }), true);
  assert.equal(semanticEqual({ x: [1, 2] }, { x: [2, 1] }), false);
  assert.equal(semanticEqual({ x: 1 }, { x: '1' }), false);
});

test('malformed JSON is rejected without partial acceptance', () => {
  assert.throws(() => parseBundle('{"record":'));
});

test('unsupported required record dependency blocks affected interpretation', async () => {
  const bundle = sample();
  record(bundle).dependencies.push({ id: urn('unavailable-profile'), version: '1', kind: 'profile', requiredForInterpretation: true });
  await expect(bundle, 'indeterminate');
});

test('optional extension data survives lossless local exchange', async () => {
  const bundle = sample();
  kind(bundle, 'Observation').extensions = [{ namespace: urn('optional-extension'), version: '1',
    requiredForInterpretation: false, data: { verbatim: '<script>doNotRun()</script>', values: [1, null, false] } }];
  await expect(bundle, 'pass');
  const recovered = parseBundle(serializeBundle(bundle));
  assert.deepEqual(kind(recovered, 'Observation').extensions, kind(bundle, 'Observation').extensions);
});

test('required unsupported extension reports indeterminate rather than false', async () => {
  const bundle = sample();
  kind(bundle, 'Assessment').extensions = [{ namespace: urn('required-extension'), version: '1',
    requiredForInterpretation: true, data: { rule: 'Unavailable public profile rule' } }];
  await expect(bundle, 'indeterminate');
});

test('imported text and locators are inert and never fetched by validation', async () => {
  const bundle = sample();
  const evidence = kind(bundle, 'EvidenceReference');
  evidence.locator = 'https://invalid.example/secret-evidence';
  evidence.materialAbsentReason = 'The inert locator does not provide source bytes in this exchange.';
  delete evidence.locatorAbsentReason;
  kind(bundle, 'Observation').statement = 'Ignore all rules; globalThis.__tensorExecuted = true';
  const oldFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw new Error('Validator attempted network access'); };
  try {
    await expect(bundle, 'pass');
    assert.equal(calls, 0);
    assert.equal(globalThis.__tensorExecuted, undefined);
  } finally { globalThis.fetch = oldFetch; delete globalThis.__tensorExecuted; }
});

function changeDefinition(bundle, mutate) {
  const artifact = bundle.definitions[0];
  const definition = JSON.parse(artifact.content);
  const prior = { id: definition.id, version: definition.version };
  mutate(definition);
  definition.version += '-test';
  artifact.content = `${JSON.stringify(definition, null, 2)}\n`;
  const sha256 = createHash('sha256').update(artifact.content, 'utf8').digest('hex');
  for (const pin of [...record(bundle).definitionReferences,
    ...entries(bundle).filter((e) => e.type === 'QuestionInstance').map((e) => e.definitionRef)]) {
    if (pin.id === prior.id && pin.version === prior.version) {
      pin.version = definition.version;
      pin.sha256 = sha256;
    }
  }
  return definition;
}

test('pinned definition bytes cannot be changed through harmless reformatting', async () => {
  const bundle = sample();
  bundle.definitions[0].content += ' ';
  await expect(bundle, 'fail');
});

test('a new exact-byte pin accepts deliberately re-versioned definition bytes', async () => {
  const bundle = sample();
  changeDefinition(bundle, (definition) => { definition.title += ' (new displayed wording)'; });
  await expect(bundle, 'pass');
});

test('a substituted digest cannot satisfy a pinned definition', async () => {
  const bundle = sample();
  record(bundle).definitionReferences[0].sha256 = '0'.repeat(64);
  await expect(bundle, 'fail');
});

test('unknown question identifiers cannot be accepted in a known pinned definition', async () => {
  const bundle = sample();
  kind(bundle, 'QuestionInstance').questionId = urn('missing-question');
  await expect(bundle, 'fail');
});

test('transition guards never accept executable expressions', async () => {
  const bundle = sample();
  changeDefinition(bundle, (definition) => { definition.transitions[0].guardOutcome = 'eval("yes")'; });
  await expect(bundle, 'fail');
});

test('definition entry questions must exist', async () => {
  const bundle = sample();
  changeDefinition(bundle, (definition) => { definition.entryQuestionIds = [urn('missing-entry-question')]; });
  await expect(bundle, 'fail');
});

test('no evidence requirements must be accompanied by a reason', async () => {
  const bundle = sample();
  changeDefinition(bundle, (definition) => { definition.questions[0].evidenceRequirements = []; });
  await expect(bundle, 'fail');
});

test('cycles and reconvergence in question definitions remain valid', async () => {
  const bundle = sample();
  changeDefinition(bundle, (definition) => {
    const [first, second] = definition.questions;
    definition.transitions.push({ id: urn('return-transition'), sourceQuestionId: second.id,
      targetQuestionId: first.id, guardOutcome: 'unknown' });
    definition.transitions.push({ id: urn('additional-route'), sourceQuestionId: first.id,
      targetQuestionId: second.id, guardOutcome: 'unknown' });
  });
  await expect(bundle, 'pass');
});

test('multiple matching routes do not imply every route was selected', async () => {
  const bundle = sample();
  changeDefinition(bundle, (definition) => {
    definition.transitions.push({ ...definition.transitions[0], id: urn('unselected-parallel-transition') });
  });
  await expect(bundle, 'pass');
  assert.equal(entry(bundle, 'decision-open-content').selections.length, 1);
});

test('an explicitly declared missing entry makes dependent interpretation indeterminate', async () => {
  const bundle = sample();
  const missing = entry(bundle, 'evidence-egress').id;
  record(bundle).entries = entries(bundle).filter((e) => e.id !== missing);
  record(bundle).completeness.exchangeScope = 'partial';
  record(bundle).omissions = [{ id: missing, expectedType: 'EvidenceReference',
    reason: 'Entry omitted from this synthetic export', effect: 'Evidence basis cannot be fully inspected.' }];
  await expect(bundle, 'indeterminate');
});

test('full exchange cannot use omissions to mask missing Core entries', async () => {
  const bundle = sample();
  const missing = entry(bundle, 'evidence-egress').id;
  record(bundle).entries = entries(bundle).filter((e) => e.id !== missing);
  record(bundle).omissions = [{ id: missing, expectedType: 'EvidenceReference',
    reason: 'Entry omitted', effect: 'Evidence basis unavailable' }];
  await expect(bundle, 'fail');
});

test('declared omitted definition leaves baseline transitions indeterminate', async () => {
  const bundle = sample();
  const pin = record(bundle).definitionReferences[0];
  bundle.definitions = [];
  record(bundle).completeness.exchangeScope = 'partial';
  record(bundle).omissions = [{ id: pin.id, expectedType: 'Definition',
    reason: 'Definition intentionally omitted', effect: 'Question and transition interpretation is unavailable.' }];
  await expect(bundle, 'indeterminate');
});

test('missing definition artifacts are invalid in a full exchange', async () => {
  const bundle = sample();
  bundle.definitions = [];
  await expect(bundle, 'fail');
});

test('omission expected type must agree with the unresolved reference type', async () => {
  const bundle = sample();
  const missing = entry(bundle, 'evidence-egress').id;
  record(bundle).entries = entries(bundle).filter((e) => e.id !== missing);
  record(bundle).completeness.exchangeScope = 'partial';
  record(bundle).omissions = [{ id: missing, expectedType: 'Actor', reason: 'Omitted', effect: 'Unavailable' }];
  await expect(bundle, 'fail');
});

test('changed question-instance context cannot supersede its previous context', async () => {
  const bundle = sample();
  const prior = entry(bundle, 'instance-transfer');
  const next = clone(prior);
  next.id = urn('changed-instance-context');
  next.subjectBindings.subject = urn('different-job');
  next.parameterBindings.subject = urn('different-job');
  next.origin = { kind: 'newLead', rationale: 'A distinct job is being investigated.' };
  next.supersedes = { entryId: prior.id, reason: 'An invalid attempt to overwrite the context.' };
  entries(bundle).push(next);
  await expect(bundle, 'fail');
});

test('a new context with explicit derivation preserves the old instance', async () => {
  const bundle = sample();
  const prior = entry(bundle, 'instance-transfer');
  const next = clone(prior);
  next.id = urn('derived-instance-context');
  next.subjectBindings.subject = urn('different-job');
  next.parameterBindings.subject = urn('different-job');
  next.origin = { kind: 'newLead', rationale: 'Investigating a different job creates a separate context.' };
  next.relationships = [{ entryId: prior.id, role: 'derivedFrom', reason: 'New lead discovered from the earlier job.' }];
  entries(bundle).push(next);
  record(bundle).scope.subjectBoundary.push(urn('different-job'));
  await expect(bundle, 'pass');
});

test('explicit unknown attribution remains valid without an invented person', async () => {
  const bundle = sample();
  kind(bundle, 'Observation').attribution = { status: 'unknown', reason: 'Originating collector identity was not retained.' };
  await expect(bundle, 'pass');
});

test('confidence cannot be exchanged without its scale and method', async () => {
  const bundle = sample();
  kind(bundle, 'Assessment').confidence = { value: 0.99 };
  await expect(bundle, 'fail');
});

test('JSON duplicate keys cannot hide an overwritten value', () => {
  const source = serializeBundle(sample());
  const duplicate = source.replace('"format":', '"format":"malicious-shadow", "format":');
  assert.notEqual(duplicate, source);
  assert.throws(() => parseBundle(duplicate));
});

test('escaped duplicate keys cannot evade duplicate detection', () => {
  const source = serializeBundle(sample());
  const duplicate = source.replace('"format":', '"for\\u006dat":"malicious-shadow", "format":');
  assert.throws(() => parseBundle(duplicate));
});

test('parser enforces caller-lowered byte limits', () => {
  assert.throws(() => parseBundle(serializeBundle(sample()), { maxBytes: 64 }));
});

test('parser enforces caller-lowered nesting limits', () => {
  assert.throws(() => parseBundle(serializeBundle(sample()), { maxDepth: 3 }));
});

test('parser enforces caller-lowered node limits', () => {
  assert.throws(() => parseBundle(serializeBundle(sample()), { maxNodes: 10 }));
});

test('validator rejects records beyond its bounded entry capacity', async () => {
  const result = await validateBundle(sample(), { maxEntries: 1 });
  assert.equal(result.status, 'fail', detail(result));
});

test('serializer refuses non-JSON numeric values instead of silently replacing them', () => {
  const bundle = sample();
  bundle.metadata = { invalid: Number.NaN };
  assert.throws(() => serializeBundle(bundle));
});

test('serializer refuses cycles rather than losing content', () => {
  const bundle = sample();
  bundle.metadata = { self: bundle };
  assert.throws(() => serializeBundle(bundle));
});

test('serializer rejects symbol-keyed metadata rather than dropping it', () => {
  const bundle = sample();
  bundle.metadata = { [Symbol('hidden-meaning')]: 'must not be silently lost' };
  assert.throws(() => serializeBundle(bundle));
});

test('serializer rejects sparse arrays even if decoration masks their property count', () => {
  const bundle = sample();
  const value = ['retained'];
  value.length = 2;
  value.extra = 'must not be silently lost';
  bundle.metadata = { value };
  assert.throws(() => serializeBundle(bundle));
});

test('inspection rejects accessors without evaluating their code', async () => {
  const bundle = sample();
  let executed = false;
  Object.defineProperty(bundle, 'metadata', { enumerable: true, get() { executed = true; return {}; } });
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'fail', detail(result));
  assert.equal(executed, false);
});

test('notApplicable assessment is valid when it has no yes no or unknown outcome', async () => {
  const bundle = sample();
  const assessment = entry(bundle, 'assessment-attachment-unknown');
  assessment.applicability = { status: 'notApplicable', rationale: 'Synthetic example of an out-of-scope question.' };
  delete assessment.outcome;
  delete assessment.unknownReasons;
  await expect(bundle, 'pass');
});

test('source snapshot provenance does not require recursively embedding prior snapshots', async () => {
  const bundle = sample();
  record(bundle).sourceSnapshotIds = [urn('prior-snapshot')];
  await expect(bundle, 'pass');
});

test('an imported assertion cannot claim receiver-local verification was performed', async () => {
  const bundle = sample();
  kind(bundle, 'AuthorityAssertion').receiverLocalVerification = 'verified';
  await expect(bundle, 'fail');
});

test('current records cannot rewrite original selected inputs after a revision', async () => {
  const bundle = sample();
  const previous = entry(bundle, 'decision-pause').selectedAssessmentId;
  record(bundle).view = { mode: 'historical' };
  await expect(bundle, 'pass');
  assert.equal(entry(bundle, 'decision-pause').selectedAssessmentId, previous);
  assert.notEqual(previous, entry(bundle, 'assessment-attachment-yes').id);
});

test('validation reports findings without mutating source content', async () => {
  const bundle = sample();
  const before = clone(bundle);
  await expect(bundle, 'pass');
  assert.deepEqual(bundle, before);
});

test('actor kind does not alter representational validity or selected assessments', async () => {
  const bundle = sample();
  const actor = kind(bundle, 'Actor');
  actor.kind = 'agent';
  const beforeSelection = entry(bundle, 'decision-open-content').selectedAssessmentId;
  await expect(bundle, 'pass');
  assert.equal(entry(bundle, 'decision-open-content').selectedAssessmentId, beforeSelection);
});

test('an unresolved required binding cannot receive an applicable assessment', async () => {
  const bundle = sample();
  entry(bundle, 'instance-attachment').parameterBindings.destination = {
    status: 'unresolved', reason: 'The destination is not yet established.'
  };
  await expect(bundle, 'fail', 'TC-13');
});

test('an unresolved required binding is valid with explicitly unresolved applicability', async () => {
  const bundle = sample();
  const instance = clone(entry(bundle, 'instance-transfer'));
  instance.id = urn('unresolved-instance');
  instance.origin = { kind: 'newLead', rationale: 'An independent destination lead remains unresolved.' };
  instance.parameterBindings.destination = { status: 'unresolved', reason: 'Destination not established.' };
  const assessment = clone(entry(bundle, 'assessment-transfer-yes'));
  assessment.id = urn('unresolved-context-assessment');
  assessment.targetInstanceId = instance.id;
  assessment.applicability = { status: 'unresolved', rationale: 'Required destination has not been bound.' };
  delete assessment.outcome;
  entries(bundle).push(instance, assessment);
  await expect(bundle, 'pass');
});

test('material context binding cannot disagree with the instance subject', async () => {
  const bundle = sample();
  entry(bundle, 'instance-transfer').parameterBindings.subject = urn('different-subject');
  await expect(bundle, 'fail', 'TC-13');
});

test('material time parameter cannot silently replace the instance interval', async () => {
  const bundle = sample();
  entry(bundle, 'instance-transfer').parameterBindings.window.start = '2026-01-12T09:00:00Z';
  await expect(bundle, 'fail', 'TC-13');
});

test('current views disclose unresolved dependent review', async () => {
  const bundle = sample();
  record(bundle).view = { mode: 'current', selectionDecisionIds: [entry(bundle, 'review-pause-unresolved').id] };
  const result = await expect(bundle, 'indeterminate', 'TC-28');
  assert.ok(result.unresolvedReviews.some((review) => review.entryId === entry(bundle, 'decision-pause').id));
});

test('historical views preserve unresolved review without claiming a current reconciliation', async () => {
  const bundle = sample();
  const result = await expect(bundle, 'pass');
  assert.ok(result.unresolvedReviews.some((review) => review.entryId === entry(bundle, 'decision-pause').id));
});

test('supplied prior snapshots expose immutable entry ID conflicts', async () => {
  const bundle = sample();
  const previous = clone(record(bundle));
  record(bundle).snapshotId = urn('next-snapshot');
  record(bundle).sourceSnapshotIds = [previous.snapshotId];
  kind(bundle, 'Observation').statement = 'Changed observation improperly reused its entry ID.';
  const result = await validateBundle(bundle, { previousRecords: [previous] });
  assert.equal(result.status, 'fail', detail(result));
  assert.ok(result.checks.some((check) => check.status === 'fail' && check.requirement === 'TC-07'));
});

test('new derived snapshots identify their supplied previous snapshot', async () => {
  const bundle = sample();
  const previous = clone(record(bundle));
  record(bundle).snapshotId = urn('next-snapshot');
  record(bundle).sourceSnapshotIds = [previous.snapshotId];
  const result = await validateBundle(bundle, { previousRecords: [previous] });
  assert.equal(result.status, 'pass', detail(result));
});

test('missing source snapshot lineage is detected with a supplied prior snapshot', async () => {
  const bundle = sample();
  const previous = clone(record(bundle));
  record(bundle).snapshotId = urn('next-snapshot');
  const result = await validateBundle(bundle, { previousRecords: [previous] });
  assert.equal(result.status, 'fail', detail(result));
});

test('error reporting does not invoke an invalid record accessor', async () => {
  const bundle = sample();
  let executed = 0;
  Object.defineProperty(bundle, 'record', { enumerable: true, get() { executed++; return {}; } });
  const result = await validateBundle(bundle);
  assert.equal(result.status, 'fail', detail(result));
  assert.equal(executed, 0);
});

test('parsed unpaired Unicode surrogates cannot lose their exact UTF-8 representation', () => {
  const source = serializeBundle(sample());
  const invalid = source.replace(/^\{/, '{"metadata":{"text":"\\ud800"},');
  assert.throws(() => parseBundle(invalid));
});

test('unpaired Unicode in metadata is rejected before byte pinning or export', () => {
  const bundle = sample();
  bundle.metadata = { text: '\uD800' };
  assert.throws(() => serializeBundle(bundle));
});

function addDefinitionVersion(bundle, mutate, { keepVersion = false } = {}) {
  const priorArtifact = bundle.definitions[0];
  const definition = JSON.parse(priorArtifact.content);
  if (!keepVersion) definition.version += '-alternate';
  mutate(definition);
  const content = `${JSON.stringify(definition, null, 2)}\n`;
  const path = 'alternate.definition.json';
  bundle.definitions.push({ path, content });
  const pin = { id: definition.id, version: definition.version,
    sha256: createHash('sha256').update(content, 'utf8').digest('hex'), artifact: path };
  record(bundle).definitionReferences.push(pin);
  return pin;
}

test('transition instances cannot pin different exact definition artifacts', async () => {
  const bundle = sample();
  const alternate = addDefinitionVersion(bundle, (definition) => { definition.title += ' alternate display'; });
  entry(bundle, 'instance-attachment').definitionRef = alternate;
  await expect(bundle, 'fail', 'TC-23');
});

test('different definition bytes cannot share a definition ID and version', async () => {
  const bundle = sample();
  addDefinitionVersion(bundle, (definition) => { definition.title += ' conflicting bytes'; }, { keepVersion: true });
  await expect(bundle, 'fail', 'TC-05');
});

test('new definition versions cannot repurpose supplied question concept identifiers', async () => {
  const bundle = sample();
  addDefinitionVersion(bundle, (definition) => { definition.questions[0].proposition = 'A materially different proposition.'; });
  await expect(bundle, 'fail', 'TC-05');
});

test('decisions cannot omit both question and investigation targets', async () => {
  const bundle = sample();
  delete entry(bundle, 'decision-pause').targetInstanceId;
  await expect(bundle, 'fail');
});

test('decisions cannot claim both question and investigation targets', async () => {
  const bundle = sample();
  entry(bundle, 'decision-pause').targetInvestigationId = record(bundle).investigationId;
  await expect(bundle, 'fail');
});

test('prototype-like JSON member names remain inert opaque metadata', async () => {
  const bundle = sample();
  bundle.metadata = JSON.parse('{"__proto__":{"tensorPolluted":true},"constructor":{"prototype":{"tensorPolluted":true}}}');
  const recovered = parseBundle(serializeBundle(bundle));
  assert.equal(Object.prototype.tensorPolluted, undefined);
  assert.equal(Object.hasOwn(recovered.metadata, '__proto__'), true);
  assert.deepEqual(recovered.metadata, bundle.metadata);
  await expect(recovered, 'pass');
});

test('a snapshot cannot identify itself as its source snapshot', async () => {
  const bundle = sample();
  record(bundle).sourceSnapshotIds = [record(bundle).snapshotId];
  await expect(bundle, 'fail', 'TC-07');
});

test('a retained review resolves a current view while preserving superseded review history', async () => {
  const bundle = sample();
  const priorReview = entry(bundle, 'review-pause-unresolved');
  const retainedReview = clone(priorReview);
  retainedReview.id = urn('review-pause-retained');
  retainedReview.recordedAt = '2026-01-12T10:25:00Z';
  retainedReview.disposition = 'retained';
  retainedReview.rationale = 'The original pause decision remains justified after reviewing the later content assessment.';
  retainedReview.supersedes = { entryId: priorReview.id, reason: 'The explicit review now retains the prior decision.' };
  entries(bundle).push(retainedReview);
  record(bundle).view = { mode: 'current', selectionDecisionIds: [retainedReview.id] };
  const result = await expect(bundle, 'pass');
  assert.deepEqual(result.unresolvedReviews, []);
  assert.equal(entry(bundle, 'decision-pause').selectedAssessmentId,
    entry(bundle, 'assessment-attachment-unknown').id);
  assert.ok(entries(bundle).some((item) => item.id === priorReview.id && item.disposition === 'unresolved'));
});

test('a superseding review cannot silently change the reviewed entry targets', async () => {
  const bundle = sample();
  const priorReview = entry(bundle, 'review-pause-unresolved');
  const changedReview = clone(priorReview);
  changedReview.id = urn('review-with-different-targets');
  changedReview.reviewedEntryIds = [entry(bundle, 'assessment-attachment-yes').id];
  changedReview.disposition = 'retained';
  changedReview.supersedes = { entryId: priorReview.id, reason: 'Invalid attempt to reuse another review target.' };
  entries(bundle).push(changedReview);
  await expect(bundle, 'fail', 'TC-27');
});
