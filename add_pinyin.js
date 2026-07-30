// 给 fish.js 每条加拼音搜索字段 py（全拼 + 首字母），基于中文名。逐行处理，保结构。
const fs = require('fs');
const { pinyin } = require('C:/Users/drxuj/Claude/Projects/1001art/node_modules/pinyin-pro');
const path = 'C:/Users/drxuj/Claude/Projects/1001shark/shark.js';

function py(name) {
  const full = pinyin(name, { toneType: 'none' }).replace(/[^a-z]/gi, '').toLowerCase();
  const initials = pinyin(name, { pattern: 'first', toneType: 'none', type: 'array' })
    .join('').replace(/[^a-z]/gi, '').toLowerCase();
  return (full + ' ' + initials).trim();
}

const lines = fs.readFileSync(path, 'utf8').split('\n');
let n = 0;
const out = lines.map(line => {
  const t = line.trim();
  if (!t.startsWith('{"id"')) return line;
  const hadComma = t.endsWith(',');
  const obj = JSON.parse(hadComma ? t.slice(0, -1) : t);
  obj.py = py(obj.name || '');
  n++;
  return JSON.stringify(obj) + (hadComma ? ',' : '');
});
fs.writeFileSync(path, out.join('\n'), 'utf8');
console.log('added py to', n, 'entries');
