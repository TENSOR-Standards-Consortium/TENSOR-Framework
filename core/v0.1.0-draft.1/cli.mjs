#!/usr/bin/env node
import { readFile, stat } from 'node:fs/promises';
import { parseBundle, validateBundle, DEFAULT_LIMITS } from './index.mjs';
const args = process.argv.slice(2);
if (args.length !== 1 || args[0].startsWith('-')) {
  process.stderr.write('Usage: node core/v0.1.0-draft.1/cli.mjs <bundle.json>\nExit codes: 0 bounded checks pass; 1 fail; 2 indeterminate; 64 usage/input error. No locators are fetched or actions executed.\n');
  process.exitCode = 64;
} else {
  try {
    if ((await stat(args[0])).size > DEFAULT_LIMITS.maxBytes) throw new Error('Bundle exceeds the input byte limit');
    const bundle = parseBundle(new TextDecoder('utf-8', { fatal: true }).decode(await readFile(args[0])));
    const result = await validateBundle(bundle);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    process.exitCode = result.status === 'pass' ? 0 : result.status === 'indeterminate' ? 2 : 1;
  } catch (error) {
    process.stderr.write(`${error.message}\n`); process.exitCode = 64;
  }
}
