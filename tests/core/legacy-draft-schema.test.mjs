import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

test('the working legacy graph conforms to its unchanged released schema', () => {
  const read = (path) => JSON.parse(readFileSync(new URL(`../../${path}`, import.meta.url), 'utf8'));
  const graph = read('drafts/core/tensor.core.graph.json');
  const schema = read('releases/core/schemas/v0.20260206e/tensor.core.schema.json');
  const ajv = new Ajv2020({ allErrors: true });
  addFormats(ajv);
  const validate = ajv.compile(schema);
  assert.equal(graph.schemaVersion, '0.20260206e');
  assert.equal(validate(graph), true, JSON.stringify(validate.errors));
});
