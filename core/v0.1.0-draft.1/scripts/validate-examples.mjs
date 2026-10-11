import { readFile } from 'node:fs/promises';
import { parseBundle, validateBundle } from '../index.mjs';
let failed = false;
for (const name of ['case-a', 'case-b']) {
  const bundle = parseBundle(await readFile(new URL(`../examples/${name}.bundle.json`, import.meta.url), 'utf8'));
  const result = await validateBundle(bundle);
  process.stdout.write(`${name}: ${result.status}; ${result.checks.length} bounded checks; ${result.checks.filter(c => c.status === 'notRun').length} outside-scope checks notRun\n`);
  if (result.status !== 'pass') { failed = true; process.stderr.write(`${JSON.stringify(result.checks.filter(c => ['fail', 'indeterminate'].includes(c.status)), null, 2)}\n`); }
}
if (failed) process.exitCode = 1;
