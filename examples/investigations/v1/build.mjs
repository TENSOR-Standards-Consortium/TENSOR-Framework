import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { scenarios } from './scenarios.mjs';
import { routing } from './routes.mjs';
import { validateBundle } from '../../../core/v0.1.0-draft.1/index.mjs';
const root = new URL('./', import.meta.url);
const version = '1.3.0';
const contractRef = { proposal: '0.1.0', bindingVersion: '0.1.0-draft.1', status: 'candidate; unratified' };
const layers = [
  { id: 'public', label: 'Public investigation questions', owner: 'TENSOR Standards Consortium', version },
  { id: 'vendor', label: 'Example vendor telemetry graph', owner: 'Fictional telemetry vendor', version },
  { id: 'company', label: 'Example company policy graph', owner: 'Fictional company', version },
];
const json = value => JSON.stringify(value, null, 2) + '\n';
const hash = value => createHash('sha256').update(value).digest('hex');
const files = [];
async function artifact(name, value) {
  const content = json(value);
  if (process.argv.includes('--check')) {
    if (await readFile(new URL(name, root), 'utf8') !== content) throw new Error(`Regenerate ${name}`);
  } else await writeFile(new URL(name, root), content);
  files.push({ path: name, sha256: hash(content) });
  return content;
}
const catalog = [];
for (const scenario of scenarios) {
  const plan = routing[scenario.id];
  const base = `urn:tensor:example:${scenario.id}:`;
  const id = suffix => base + suffix;
  const window = { status: 'bounded', start: '2026-10-13T08:35:00Z', end: '2026-10-13T09:00:00Z' };
  const questions = scenario.steps.map((s, i) => ({
    id: id(`${s.layer}:question-${i + 1}`), prompt: s.question,
    proposition: `${s.question} Apply only to the resolved subject and interval; a different context requires a separate question instance.`,
    parameters: { subject: { type: 'URI', required: true, bindsTo: 'subject:subject' }, window: { type: 'timeContext', required: true, bindsTo: 'timeContext' } },
    applicabilityCriteria: 'Applies only to the declared subject and interval with resolved parameters and the named evidence and policy context.',
    assessmentCriteria: s.criteria,
    evidenceRequirements: ['Retained source provenance and interpretation basis; exact subject and interval; falsifiable discriminators and alternatives.', 'Negative findings require authoritative observation or register coverage. Unknowns and separate policy, intent, execution, and delivery propositions remain explicit.'],
    metadata: { title: s.questionTitle||s.title, displayId: `S${i + 1}`, domain: s.domain, layerId: s.layer, layerVersion: version, archetype: i === 0 ? 'detect' : i === scenario.steps.length - 1 ? 'terminal' : s.policyBound ? 'classify' : 'correlate' },
  }));
  for (const [i,s] of scenario.steps.entries()) if(s.revisit) questions[i]=questions[s.revisit-1];
  const definition = {
    id: id('composed-definition'), version, publicationStatus: 'draft', title: scenario.title, contractRef,
    questions: [...new Map(questions.map(q=>[q.id,q])).values()], transitions: plan.routes.map(([source,outcome,target]) => ({
      id: id(`route-${source}-${target}-${outcome}`), sourceQuestionId: questions[source-1].id, targetQuestionId: questions[target-1].id, guardOutcome: outcome,
      metadata: { meaning: `The ${outcome} source assessment permits opening this separate question: ${questions[target-1].prompt} Bind its own subject and evidence; no target answer, causal relationship or response permission is inherited.`,
        selection: 'A human or agent explicitly selects one or several eligible routes. An eligible option is not a recorded selection.' },
    })), entryQuestionIds: [questions[0].id], dependencies: [],
    metadata: { illustrative: true, layers, composition: 'Case-specific questions composed in one pinned artifact. These are additional example definitions, not routes added to the public working or published graph.' },
  };
  const definitionName = `${scenario.id}.definition.json`;
  const definitionContent = await artifact(definitionName, definition);
  const pin = { id: definition.id, version, sha256: hash(definitionContent), artifact: definitionName };
  const entries = [], frames = [];
  const instances = new Map();
  let clock = 0;
  const entry = (type, suffix, actor, fields) => {
    const value = { id: id(suffix), type, recordedAt: new Date(Date.UTC(2026, 9, 13, 9, scenario.id==='parallel-followup'?30:0, clock++)).toISOString(), attribution: { actorId: id(`actor-${actor}`) }, ...fields };
    entries.push(value); return value;
  };
  function ensureInstance(n, originDecisionId) {
    if(instances.has(n)) {
      const previous=instances.get(n);
      if(originDecisionId&&previous.origin.originDecisionId!==originDecisionId) throw new Error('A second selection must create a separate target instance.');
      return previous;
    }
    const s=scenario.steps[n-1];
    const boundWindow=s.window||window;
    const instance=entry('QuestionInstance', `instance-${n}`, s.actor, {definitionRef:pin,questionId:questions[n-1].id,
      metadata:{subjectLabels:{[id(s.subject)]:scenario.subjectLabels[s.subject]}},
      subjectBindings:{subject:id(s.subject)},timeContext:boundWindow,parameterBindings:{subject:id(s.subject),window:boundWindow},
      origin: originDecisionId?{kind:'transition',rationale:'Explicitly selected investigative lead; target evidence and subject remain separate.',originDecisionId}:
        n===1?{kind:'entry',rationale:'Open the bounded example investigation.'}:{kind:'newLead',rationale:'A separately documented review lead; timeline adjacency supplies no route.'}});
    instances.set(n,instance);return instance;
  }
  function decide(n,s,assessment,early=false) {
    const targets=(early?plan.earlySelected?.[n]:plan.selected[n])||[];
    const suffix=early?`early-decision-${n}`:`decision-${n}`;
    const selections=targets.map(target=>{
      if(!plan.routes.some(([source,outcome,destination])=>source===n&&outcome===assessment.outcome&&destination===target)) throw new Error('Selected route is not explicitly declared.');
      return {transitionId:id(`route-${n}-${target}-${assessment.outcome}`),targetInstanceId:id(`instance-${target}`)};
    });
    const final=n===scenario.steps.length;
    const decision=entry('Decision',suffix,s.response?'responder':'analyst',{
      targetInstanceId:id(`instance-${n}`),selectedAssessmentId:assessment.id,
      selectedInputIds: final?entries.filter(e=>e.type==='Assessment').map(e=>e.id):[assessment.id],
      disposition:selections.length?'transition':final?'handoff':'retain',
      rationale:s.response?scenario.operation:selections.length?`Open ${selections.length} independently assessed lead${selections.length===1?'':'s'}; retain this ${assessment.outcome} answer and the unselected alternatives.`:final?'Hand off the separate findings, retained revisions, open evidence gaps and planned response.':'Retain this assessment and its limitations; no additional route is selected by this decision.',
      policyStatus:s.policyBound?{status:'referenced',policyRefIds:[id('policy')]}:{status:'notApplicable'},
      authorityStatus:s.response?{status:'referenced',authorityRefIds:[id('authority')]}:{status:'notApplicable'},
      limitations:[s.limitation],...(selections.length?{selections}:{}),
    });
    for(const target of targets) ensureInstance(target,decision.id);
    return decision;
  }
  for (const [actor, kind, label] of [['analyst','human','SOC analyst'],['agent','agent','Assisting investigation agent'],['responder','human','On-duty response lead']]) {
    entry('Actor', `actor-${actor}`, actor, { kind, label, identityStatus: 'selfDeclared' });
  }
  entry('PolicyReference', 'policy', 'analyst', { policyIdentity: id('company-response-policy'), version, effectiveTime: { status: 'known', start: '2026-10-01T00:00:00Z' }, applicableScope: scenario.purpose, locatorAbsentReason: 'Fictional example policy; conditions are retained here.', conditions: scenario.policy });
  entry('AuthorityAssertion', 'authority', 'responder', { issuerId: id('actor-responder'), granteeId: id('actor-responder'), permittedOperation: scenario.operation, scope: scenario.purpose, validityStatus: { status: 'claimedValid', reason: 'The example asserts this actor is the designated on-duty responder.' }, basisReferences: [id('policy')], receiverLocalVerification: 'notPerformed' });
  for (const [i, s] of scenario.steps.entries()) {
    const n = i + 1;
    ensureInstance(n);
    const assess = (outcome, suffix, observationId, rationale, supersedes) => entry('Assessment', suffix, s.actor, {
      targetInstanceId: id(`instance-${n}`), applicability: { status: 'applicable', rationale: 'The declared subject, interval, and required parameters are resolved.' }, outcome,
      rationale, inputs: [{ entryId: observationId, role: outcome === 'yes' ? 'supports' : outcome === 'no' ? 'contradicts' : 'context' },...(plan.context[n]||[]).filter(k=>entries.some(e=>e.id===id(`assessment-${k}`))).map(k=>({entryId:id(`assessment-${k}`),role:'context'}))], method: 'Authored example applies the pinned question criteria to retained illustrative observations.',
      ...(outcome === 'unknown' ? { unknownReasons: [{ code: 'insufficient', explanation: rationale }] } : {}),
      ...(s.policyBound ? { policyBinding: { policyRefId: id('policy'), parameterBindings: {} } } : {}), ...(supersedes ? { supersedes } : {}),
    });
    if (s.initialUnknown) {
      entry('EvidenceReference', `early-evidence-${n}`, s.actor, { description: s.initialUnknown, source: { label: 'Initial example tool metadata', provenanceStatus: 'Authored fictional evidence' }, availability: 'unavailable', locatorAbsentReason: 'No real source system or source bytes exist.' });
      const early = entry('Observation', `early-observation-${n}`, s.actor, { statement: s.initialUnknown, evidenceRefIds: [id(`early-evidence-${n}`)], method: 'Illustrative initial collection with a declared gap.', eventTime: s.window||window });
      const previous = assess('unknown', `early-assessment-${n}`, early.id, s.initialUnknown);
      const earlyDecision=decide(n,s,previous,true);
      frames.push({ title: 'Content is initially unresolved', assessmentId: previous.id, decisionId:earlyDecision.id, through: entries.length, limitation: s.limitation });
    }
    entry('EvidenceReference', `evidence-${n}`, s.actor, { description: s.evidence, source: { label: `${s.domain} example evidence`, provenanceStatus: 'Authored fictional evidence; no real incident source is authenticated' }, availability: 'unavailable', locatorAbsentReason: 'The example supplies observations and references, not real source evidence bytes.' });
    const observation = entry('Observation', `observation-${n}`, s.actor, { statement: s.evidence, evidenceRefIds: [id(`evidence-${n}`)], method: 'Authored observation; discriminator and collection limits are described in the statement.', eventTime: s.window||window });
    const assessment = assess(s.outcome, `assessment-${n}`, observation.id, `${s.criteria[s.outcome]} ${s.limitation}`, s.initialUnknown ? { entryId: id(`early-assessment-${n}`), reason: 'A later request-body receipt supplies the formerly missing content and destination discriminators.' } : undefined);
    decide(n,s,assessment);
    if (s.response) entry('ActionRecord', `action-${n}`, 'responder', { operationDescription: scenario.operation, operationSubject: id(s.subject), stage: 'planned', decisionId: id(`decision-${n}`), eventTime: { status: 'unknown', reason: 'No action is executed in this example.' } });
    frames.push({ title: s.title, assessmentId: assessment.id, decisionId: id(`decision-${n}`), through: entries.length, limitation: s.limitation });
  }
  const record = {
    snapshotId: id('snapshot-1'), investigationId: id('investigation'), contractRef,
    producer: { label: 'TENSOR illustrative investigation authoring', version, implementationStatus: 'Fictional example, not an operational deployment' },
    recordedAt: entries.at(-1).recordedAt, scope: { purpose: scenario.purpose, subjectBoundary: [...new Set(scenario.steps.map(s => id(s.subject)))] },
    definitionReferences: [pin], dependencies: [], entries,
    completeness: { exchangeScope: 'full', meaning: 'All referenced Core entries and exact definition bytes are included; actual source evidence bytes do not exist in this fictional example.' }, omissions: [], losses: [], view: { mode: 'historical' },
    metadata: { illustrative: true, walkthrough: { format: 'tensor-example-walkthrough', version: 1, id: scenario.id, title: scenario.title, description: scenario.description, domains: scenario.domains, frames } },
  };
  const bundle = { format: 'tensor-investigation-bundle', bindingVersion: contractRef.bindingVersion, record, definitions: [{ path: definitionName, content: definitionContent }] };
  const report = await validateBundle(bundle);
  if (report.status !== 'pass') throw new Error(`${scenario.id}: ${JSON.stringify(report.checks.filter(c => c.status === 'fail'))}`);
  await artifact(`${scenario.id}.bundle.json`, bundle);
  catalog.push({ id: scenario.id, title: scenario.title, description: scenario.description, domains: scenario.domains, frames: frames.length, questions: definition.questions.length, bundle: `${scenario.id}.bundle.json`, definition: definitionName });
}
await artifact('catalog.json', { version, bindingVersion: contractRef.bindingVersion, illustrative: true, scenarios: catalog });
await artifact('manifest.json', { version, files: [...files] });
console.log(`Validated ${catalog.length} cross-domain example bundles; ${catalog.reduce((n,s)=>n+s.frames,0)} walkthrough frames.`);
