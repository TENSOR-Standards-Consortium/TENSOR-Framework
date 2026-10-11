import { writeFile, readFile } from 'node:fs/promises';
import { schemas } from '../schemas.mjs';
let failed = false;
for (const [name, schema] of Object.entries(schemas)) {
  const path = new URL(`../schemas/${name}.schema.json`, import.meta.url);
  const output = `${JSON.stringify(schema, null, 2)}\n`;
  if (process.argv.includes('--check')) {
    if (await readFile(path, 'utf8').catch(() => '') !== output) { process.stderr.write(`Schema artifact differs: ${name}\n`); failed = true; }
  } else await writeFile(path, output);
}
if (failed) process.exitCode = 1;
