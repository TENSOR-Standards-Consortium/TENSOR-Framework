import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { parseBundle, serializeBundle, semanticEqual } from '../../core/v0.1.0-draft.1/index.mjs';
const source = await readFile(new URL('../../core/v0.1.0-draft.1/examples/case-a.bundle.json', import.meta.url), 'utf8');

test('a minified import can roundtrip under an exact byte budget without pretty-print growth', () => {
  const bundle = parseBundle(source);
  bundle.metadata = { unicode: '火'.repeat(20), opaque: { preserved: true } };
  const compact = JSON.stringify(bundle);
  const maxBytes = new TextEncoder().encode(compact).length;
  const exported = serializeBundle(parseBundle(compact, { maxBytes }), { maxBytes });
  assert.equal(new TextEncoder().encode(exported).length, maxBytes);
  assert(semanticEqual(bundle, parseBundle(exported, { maxBytes })));
  assert.equal(parseBundle(exported, { maxBytes }).definitions[0].content, bundle.definitions[0].content);
});

test('compact serialization keeps opaque content and definition bytes without indentation', () => {
  const bundle = parseBundle(source);
  const exported = serializeBundle(bundle, { pretty: false });
  assert.equal(exported, `${JSON.stringify(bundle)}\n`);
  assert(semanticEqual(bundle, parseBundle(exported)));
});
