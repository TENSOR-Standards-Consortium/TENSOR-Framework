#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

function validateDir(base, coreList) {
  fs.readdirSync(base).forEach(item => {
    const p = path.join(base, item);
    if (fs.statSync(p).isDirectory()) {
      validateDir(p, coreList);
    } else {
      const name = path.basename(p);
      const validCore = coreList.some(c => name.startsWith(c));
      if (base.endsWith('core') && !validCore) throw new Error(`${p} not valid in core`);
    }
  });
}

try {
  validateDir('schemas/core', ['core.schema']);
  validateDir('graphs/core', ['tensor-core.graph']);
  console.log('✅ Naming OK');
} catch(e) {
  console.error('❌ Naming error:', e.message);
  process.exit(1);
}
