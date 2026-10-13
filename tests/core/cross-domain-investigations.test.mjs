import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { validateBundle } from '../../core/v0.1.0-draft.1/index.mjs';
const root = new URL('../../examples/investigations/v1/', import.meta.url);
const read = async name => JSON.parse(await readFile(new URL(name,root),'utf8'));
const catalog = await read('catalog.json');
const bundles = await Promise.all(catalog.scenarios.map(s=>read(s.bundle)));
test('cross-domain examples validate with exact artifact pins and span all seven domains', async () => {
  const manifest=await read('manifest.json');
  for(const f of manifest.files) assert.equal(createHash('sha256').update(await readFile(new URL(f.path,root))).digest('hex'),f.sha256);
  assert.deepEqual(new Set(catalog.scenarios.flatMap(s=>s.domains)),new Set(['Identity','Email','Cloud','Network','File','Host','Application']));
  for(const bundle of bundles) {
    const report=await validateBundle(bundle);assert.equal(report.status,'pass');
    assert.ok(report.transitions.every(t=>t.status==='pass'));
    assert.deepEqual(new Set(bundle.record.entries.filter(e=>e.type==='Actor').map(e=>e.kind)),new Set(['human','agent']));
    const def=JSON.parse(bundle.definitions[0].content);
    assert.deepEqual(new Set(def.questions.map(q=>q.metadata.layerId)),new Set(['public','vendor','company']));
    assert.ok(bundle.record.entries.filter(e=>e.type==='ActionRecord').every(e=>e.stage==='planned'));
    assert.ok(bundle.record.entries.some(e=>e.type==='Assessment'&&e.outcome==='unknown'));
    for(const frame of bundle.record.metadata.walkthrough.frames) {
      assert.equal(bundle.record.entries.find(e=>e.id===frame.assessmentId)?.type,'Assessment');
      assert.ok(bundle.record.entries.slice(0,frame.through).some(e=>e.id===frame.assessmentId));
    }
  }
});
test('cross-domain route selection cannot conceal a mismatched outcome or target', async () => {
  for(const original of bundles) {
    const wrongGuard=structuredClone(original), decision=wrongGuard.record.entries.find(e=>e.type==='Decision'&&e.selections);
    decision.selections[0].transitionId=decision.selections[0].transitionId.replace(/-(yes|no|unknown)$/,'-unknown');
    assert.equal((await validateBundle(wrongGuard)).status,'fail');
    const wrongTarget=structuredClone(original), d=wrongTarget.record.entries.find(e=>e.type==='Decision'&&e.selections);
    d.selections[0].targetInstanceId=wrongTarget.record.entries.filter(e=>e.type==='QuestionInstance').at(-1).id;
    assert.equal((await validateBundle(wrongTarget)).status,'fail');
  }
});
test('evidence and pinned policy definitions cannot be silently replaced', async () => {
  for(const original of bundles) {
    const missing=structuredClone(original);missing.record.entries=missing.record.entries.filter(e=>e.type!=='EvidenceReference');
    assert.equal((await validateBundle(missing)).status,'fail');
    const changed=structuredClone(original);changed.definitions[0].content+=' ';
    assert.equal((await validateBundle(changed)).status,'fail');
  }
});
test('the attachment case retains a content revision without turning unknown delivery into a finding', async () => {
  const bundle=bundles[2], entries=bundle.record.entries;
  const revised=entries.find(e=>e.type==='Assessment'&&e.supersedes);
  assert.equal(revised.outcome,'yes');
  assert.equal(entries.find(e=>e.id===revised.supersedes.entryId).outcome,'unknown');
  assert.notDeepEqual(revised.inputs,entries.find(e=>e.id===revised.supersedes.entryId).inputs);
  assert.equal(entries.find(e=>e.id.endsWith(':assessment-7')).outcome,'unknown');
  assert.ok(entries.filter(e=>e.type==='Decision').every(e=>e.selectedAssessmentId!==revised.supersedes.entryId));
});
