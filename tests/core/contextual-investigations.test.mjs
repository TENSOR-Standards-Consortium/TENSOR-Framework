import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateBundle,parseBundle,serializeBundle} from '../../core/v0.1.0-draft.1/index.mjs';
const fixture=JSON.parse(await readFile(new URL('../../examples/investigations/v1/parallel-followup.bundle.json',import.meta.url)));
for(const domain of ['Identity','Email','Cloud','Host','File','Network','Application'])test(`${domain}: two fresh return contexts preserve parallel answers and historical selections`,async()=>{
  const bundle=structuredClone(fixture),record=bundle.record,entries=record.entries,definition=JSON.parse(bundle.definitions[0].content);
  const question=definition.questions.find(q=>q.metadata.domain===domain);
  const source=entries.find(e=>e.type==='QuestionInstance'&&e.questionId===question.id);
  const assessment=entries.find(e=>e.type==='Assessment'&&e.targetInstanceId===source.id);
  const stem=`urn:tensor:example:context-check:${domain}:`,old=structuredClone(entries);
  const targets=[1,2].map(n=>{
    const instance=structuredClone(source);instance.id=stem+`return-${n}`;
    instance.subjectBindings={subject:stem+`subject-${n}`};
    instance.timeContext={status:'bounded',start:'2026-10-13T10:00:00Z',end:'2026-10-13T10:15:00Z'};
    instance.parameterBindings={subject:instance.subjectBindings.subject,window:instance.timeContext};
    instance.origin={kind:'transition',originDecisionId:stem+'decision',rationale:'A separate acquisition identifies a different subject and later interval. Earlier contexts remain retained.'};
    return instance;
  });
  const selections=targets.map((target,i)=>{
    const id=stem+`route-${i}`;definition.transitions.push({id,sourceQuestionId:question.id,targetQuestionId:question.id,guardOutcome:assessment.outcome});
    return {transitionId:id,targetInstanceId:target.id};
  });
  const originalDecision=entries.find(e=>e.type==='Decision'&&e.targetInstanceId===source.id);
  entries.push({...structuredClone(originalDecision),id:stem+'decision',recordedAt:'2026-10-13T10:20:00Z',selectedAssessmentId:assessment.id,
    selectedInputIds:[assessment.id],disposition:'transition',selections,rationale:'Open two explicitly bound return contexts. The earlier answer supplies no finding about either new subject.'},...targets);
  for(const [i,target] of targets.entries()){
    const evidence={id:stem+`evidence-${i}`,type:'EvidenceReference',recordedAt:'2026-10-13T10:21:00Z',attribution:assessment.attribution,
      description:`Separate illustrative acquisition for ${target.subjectBindings.subject}; no bytes from the original subject are reused.`,source:{label:'Fictional independent acquisition',provenanceStatus:'Authored example'},availability:'unavailable',locatorAbsentReason:'Fictional evidence, no real source bytes.'};
    const observation={id:stem+`observation-${i}`,type:'Observation',recordedAt:'2026-10-13T10:22:00Z',attribution:assessment.attribution,
      statement:`A distinct supplied observation for ${target.subjectBindings.subject}; ${i?'coverage unresolved':'the declared discriminator is supported'}.`,evidenceRefIds:[evidence.id],method:'Author supplied bounded example',eventTime:target.timeContext};
    const answer={...structuredClone(assessment),id:stem+`assessment-${i}`,targetInstanceId:target.id,recordedAt:'2026-10-13T10:23:00Z',
      outcome:i?'unknown':'yes',rationale:i?'The new subject lacks the required independent coverage.':'The separate new-subject observation supports the declared discriminator.',inputs:[{entryId:observation.id,role:i?'context':'supports'}]};
    delete answer.supersedes;delete answer.unknownReasons;
    if(i)answer.unknownReasons=[{code:'insufficient',explanation:'Coverage for this separate subject is unresolved.'}];
    entries.push(evidence,observation,answer);
  }
  const content=JSON.stringify(definition);bundle.definitions[0].content=content;
  const digest=createHash('sha256').update(content).digest('hex');
  for(const pin of [...record.definitionReferences,...entries.filter(e=>e.type==='QuestionInstance').map(e=>e.definitionRef)])pin.sha256=digest;
  // Repinning exact definition bytes changes no earlier evidence, answer or selection.
  for(const e of old.filter(e=>e.type!=='QuestionInstance'))assert.deepEqual(entries.find(x=>x.id===e.id),e);
  const report=await validateBundle(bundle);assert.equal(report.status,'pass',JSON.stringify(report.checks.filter(c=>c.status==='fail')));
  const recovered=parseBundle(serializeBundle(bundle));assert.deepEqual(recovered.record.entries,entries);
  assert.equal((await validateBundle(recovered)).status,'pass');
  const answers=entries.filter(e=>e.type==='Assessment'&&targets.some(t=>t.id===e.targetInstanceId));
  assert.deepEqual(answers.map(e=>e.outcome),['yes','unknown']);assert.notEqual(answers[0].targetInstanceId,answers[1].targetInstanceId);
  const bad=structuredClone(bundle),changed=bad.record.entries.find(e=>e.id===targets[0].id);changed.parameterBindings.subject=targets[1].subjectBindings.subject;
  assert.equal((await validateBundle(bad)).status,'fail','A neighboring parallel subject cannot replace the exact binding');
});
