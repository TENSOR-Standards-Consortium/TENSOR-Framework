import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import { semanticEqual } from '../../core/v0.1.0-draft.1/index.mjs';

const fixtureRoot = new URL('../../core/v0.1.0-draft.1/examples/', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('manifest.json', fixtureRoot), 'utf8'));

test('candidate fixture manifest covers each JSON artifact exactly once', async () => {
  const artifacts = (await readdir(fixtureRoot)).filter((name) => name.endsWith('.json') && name !== 'manifest.json').sort();
  const declared = manifest.files.map((file) => file.path).sort();
  assert.equal(new Set(declared).size, declared.length);
  assert.deepEqual(declared, artifacts);
});

for (const file of manifest.files) {
  test(`${file.path} matches its exact-byte manifest SHA-256`, async () => {
    assert.match(file.path, /^case-[ab]\.(?:bundle|record|definition)\.json$/);
    const bytes = await readFile(new URL(file.path, fixtureRoot));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), file.sha256);
  });
}

for (const name of ['a', 'b']) {
  test(`case ${name.toUpperCase()} bundle preserves the separate definition bytes and record semantics`, async () => {
    const [bundleText, definitionText, recordText] = await Promise.all([
      readFile(new URL(`case-${name}.bundle.json`, fixtureRoot), 'utf8'),
      readFile(new URL(`case-${name}.definition.json`, fixtureRoot), 'utf8'),
      readFile(new URL(`case-${name}.record.json`, fixtureRoot), 'utf8')
    ]);
    const bundle = JSON.parse(bundleText);
    assert.equal(bundle.definitions.length, 1);
    assert.equal(bundle.definitions[0].path, `case-${name}.definition.json`);
    assert.equal(bundle.definitions[0].content, definitionText);
    assert.ok(semanticEqual(bundle.record, JSON.parse(recordText)));
  });
}
