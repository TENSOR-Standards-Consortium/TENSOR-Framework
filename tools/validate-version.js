#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

function checkFile(filePath, regex) {
  const file = path.basename(filePath);
  const m = file.match(regex);
  if (!m) throw new Error(`Filename mismatch: ${file}`);
  const verName = m[1];
  const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (content.tensorVersion !== verName) {
    throw new Error(`${file}: filename version ${verName} != tensorVersion ${content.tensorVersion}`);
  }
}

function walk(dir, regex) {
  fs.readdirSync(dir).forEach(name => {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) walk(full, regex);
    else if (regex.test(name)) checkFile(full, regex);
  });
}

try {
  walk('schemas', /^.+\.schema\.([0-9.]+)\.json$/);
  walk('graphs', /^.+\.graph\.([0-9.]+)\.json$/);
  console.log('✅ Versions match filenames');
} catch(e) {
  console.error('❌ Version check failed:', e.message);
  process.exit(1);
}
