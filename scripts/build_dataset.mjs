#!/usr/bin/env node
// One public inventory for the graph, profiles and reference records. No audience variants.
import { createHash } from 'node:crypto';
import { lstat, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const pairs = [
  ['releases/core/schemas/v0.20260206e/tensor.core.schema.json', '/assets/data/core.schema.json'],
  ...['tensor.core.graph.json', 'entry-evidence-criteria.json', 'source/entry_nodes.json', 'coverage-inventory.json',
    ...['catalog.json','definitions.json','scenarios.json','validation.json'].map(n => `event-profiles/${n}`)
  ].map(name => [`drafts/core/${name}`, `/graphs/working/${name}`]),
];
for (const [folder, prefix] of [
  ['examples/investigations/v1', '/investigations/v1'],
  ['examples/layers', '/examples/layers'],
  ['core/v0.1.0-draft.1/examples', '/core/0.1.0-draft.1/examples'],
  ['core/v0.1.0-draft.1/schemas', '/core/0.1.0-draft.1/schemas'],
]) for (const name of (await readdir(path.join(root, folder))).sort()) {
  if (name.endsWith('.json')) pairs.push([`${folder}/${name}`, `${prefix}/${name}`]);
}
const files = [];
for (const [source, publicPath] of pairs.sort((a,b) => a[0].localeCompare(b[0], 'en'))) {
  const file = path.join(root, source), info = await lstat(file);
  if (!info.isFile() || info.isSymbolicLink()) throw new Error(`Dataset input must be a regular file: ${source}`);
  const bytes = await readFile(file);
  files.push({ source, publicPath, bytes: bytes.length, sha256: hash(bytes) });
}
const graph = JSON.parse(await readFile(path.join(root, 'drafts/core/tensor.core.graph.json')));
const profiles = JSON.parse(await readFile(path.join(root, 'drafts/core/event-profiles/catalog.json')));
const definitions = JSON.parse(await readFile(path.join(root, 'drafts/core/event-profiles/definitions.json')));
const investigations = JSON.parse(await readFile(path.join(root, 'examples/investigations/v1/catalog.json')));
const manifest = {
  format: 'tensor-current-dataset', manifestVersion: 1,
  id: `urn:tensor:dataset:sha256:${hash(JSON.stringify(files))}`,
  graphVersion: graph.version, graphSchemaVersion: graph.schemaVersion, bindingVersion: '0.1.0-draft.1',
  counts: { questions: graph.nodes.length, routes: graph.edges.length, domains: new Set(graph.nodes.map(n=>n.category)).size,
    eventProfiles: Object.keys(profiles.profiles).length,
    qualifiedDefinitions: Object.values(definitions.profiles).reduce((n,p)=>n+Object.keys(p).length,0),
    referenceCases: investigations.scenarios.length },
  graphSchema: '/assets/data/core.schema.json',
  graph: '/graphs/working/tensor.core.graph.json', criteria: '/graphs/working/entry-evidence-criteria.json',
  eventProfiles: '/graphs/working/event-profiles/catalog.json', referenceCases: '/investigations/v1/catalog.json',
  reviewPackage: '/review/current/review-package.zip',
  scope: 'The same current public reference dataset for exploration, implementation and review. Case records and event profiles supply declared contexts; they are not audience-specific graph versions. Historical releases are archives.',
  files,
};
const output = path.join(root, 'dataset/current.json'), text = JSON.stringify(manifest, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (await readFile(output, 'utf8') !== text) throw new Error('Current dataset inventory differs from its source. Run node scripts/build_dataset.mjs.');
} else { await mkdir(path.dirname(output), {recursive:true}); await writeFile(output,text); }
console.log(`Current dataset ${manifest.graphVersion}: ${manifest.counts.questions} questions, ${manifest.counts.routes} routes; ${files.length} exact artifacts ${process.argv.includes('--check')?'verified':'inventoried'}.`);
