import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { schemas } from '../../core/v0.1.0-draft.1/schemas.mjs';
import { validateSchema, validTimestamp, validURI } from '../../core/v0.1.0-draft.1/schema-validator.mjs';

const fixtureRoot = new URL('../../core/v0.1.0-draft.1/examples/', import.meta.url);
const cases = await Promise.all(['a', 'b'].map(async (name) =>
  [name, JSON.parse(await readFile(new URL(`case-${name}.bundle.json`, fixtureRoot), 'utf8'))]));
const clone = (value) => JSON.parse(JSON.stringify(value));

// AJV exercises the complete Draft 2020-12 structural vocabulary. The candidate
// binding intentionally has narrower URI and timestamp limits than generic RFC
// format checkers; supplying those same formats isolates schema-evaluator parity.
const ajv = new Ajv2020({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addFormat('date-time', { type: 'string', validate: validTimestamp });
ajv.addFormat('uri', { type: 'string', validate: validURI });
const compiled = Object.fromEntries(Object.entries(schemas).map(([name, schema]) => [name, ajv.compile(schema)]));

function* locations(value, path = []) {
  yield { value, path };
  if (value !== null && typeof value === 'object') {
    for (const key of Object.keys(value)) yield* locations(value[key], [...path, key]);
  }
}
function atPath(root, path) { return path.reduce((value, key) => value[key], root); }
function jsonPointer(path) { return `/${path.map((part) => part.replaceAll('~', '~0').replaceAll('/', '~1')).join('/')}`; }
function assertParity(name, value, description) {
  const portableErrors = validateSchema(value, schemas[name]);
  const ajvValid = compiled[name](value);
  assert.equal(portableErrors.length === 0, ajvValid,
    `${description}\nPortable: ${JSON.stringify(portableErrors.slice(0, 3))}\nAJV: ${JSON.stringify(compiled[name].errors?.slice(0, 3))}`);
}

for (const [caseName, bundle] of cases) {
  for (const [schemaName, source] of [
    ['bundle', bundle], ['record', bundle.record], ['definition', JSON.parse(bundle.definitions[0].content)]
  ]) {
    test(`AJV structural parity for case ${caseName.toUpperCase()} ${schemaName} and recursive mutations`, () => {
      assertParity(schemaName, source, 'Unmodified fixture');
      let mutations = 0;
      for (const { value, path } of locations(source)) {
        if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
          for (const key of Object.keys(value)) {
            const changed = clone(source);
            delete atPath(changed, path)[key];
            assertParity(schemaName, changed, `Delete ${jsonPointer([...path, key])}`);
            mutations++;
          }
          const changed = clone(source);
          atPath(changed, path).unexpectedCoreMember = true;
          assertParity(schemaName, changed, `Unknown member at ${jsonPointer(path)}`);
          mutations++;
        }
        if (path.length) {
          const changed = clone(source);
          const parent = atPath(changed, path.slice(0, -1));
          const key = path.at(-1);
          parent[key] = value === null ? [] : typeof value === 'string' ? 7 : null;
          assertParity(schemaName, changed, `Wrong shape at ${jsonPointer(path)}`);
          mutations++;
        }
      }
      assert.ok(mutations > 100, 'The corpus explores nested fields, alternatives, and required/optional members.');
    });
  }
}

test('published schemas compile under a full Draft 2020-12 engine with ordinary formats', () => {
  const standardsEngine = new Ajv2020({ strict: false, allErrors: true });
  addFormats(standardsEngine);
  const standardValidators = Object.fromEntries(Object.entries(schemas).map(([name, schema]) => [name, standardsEngine.compile(schema)]));
  for (const [name, bundle] of cases) {
    for (const [kind, value] of [ ['bundle', bundle], ['record', bundle.record], ['definition', JSON.parse(bundle.definitions[0].content)] ]) {
      assert.equal(standardValidators[kind](value), true, `Case ${name} ${kind}: ${JSON.stringify(standardValidators[kind].errors)}`);
    }
  }
});
