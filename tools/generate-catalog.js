#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

function scan(dir,type) {
  const items=[];
  function rec(d) {
    fs.readdirSync(d).forEach(ent => {
      const full=path.join(d,ent);
      if(fs.statSync(full).isDirectory()) rec(full);
      else {
        const [ns,name,,,,ver]=ent.split('.');
        items.push({ns,name,type,ver,path:full});
      }
    });
  }
  rec(dir);
  return items;
}
const cat={
  schemas:scan('schemas','schema'),
  graphs:scan('graphs','graph'),
  generatedAt:new Date().toISOString()
};
fs.writeFileSync('catalog.json',JSON.stringify(cat,null,2));
console.log('✅ catalog.json generated');
