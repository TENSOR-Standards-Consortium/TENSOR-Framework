import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

test('multiple answer routes and cross-domain cycles validate against the unchanged published graph schema',async()=>{
  const read=async path=>JSON.parse(await readFile(new URL(`../../${path}`,import.meta.url),'utf8'));
  const schema=await read('releases/core/schemas/v0.20260206e/tensor.core.schema.json');
  const ajv=new Ajv2020({allErrors:true});addFormats(ajv);
  const validate=ajv.compile(schema);
  for(const path of ['drafts/core/tensor.core.graph.json','releases/core/graphs/v0.20260206e/tensor.core.graph.json']) {
    assert.ok(validate(await read(path)),JSON.stringify(validate.errors));
  }
});
