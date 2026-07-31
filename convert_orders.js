// 把 shark.js 里的中文字段统一转成简体。
//
// ⚠️ 教训：本脚本从 1001fish 复制而来，原版只转 `order` 一个字段
//   （鱼站的物种名在采集阶段已由 convert_more.js 转过）。
//   软骨鱼站没有那一步，导致 339/554 物种名、150 个科名一直是繁体。
//   现在统一转 name / family / order 三类字段。
//
// 依赖 1001art 的 node_modules（该项目搬过位置），逐个候选路径尝试；
// 找不到就跳过而不报错——这是可选美化步骤，不该卡住整条部署流水线。
const fs = require("fs");

const CANDIDATES = [
  "C:/Users/drxuj/Claude/Projects/1001art/node_modules/opencc-js",
  "opencc-js",
];

let OpenCC = null;
for (const c of CANDIDATES) {
  try { OpenCC = require(c); break; } catch (e) { /* 试下一个 */ }
}
if (!OpenCC) {
  console.log("  ⚠ 未找到 opencc-js，跳过繁转简（不影响部署）");
  process.exit(0);
}

const conv = OpenCC.Converter({ from: "t", to: "cn" });
const FIELDS = ["name", "family", "order"];   // 展示用的三个中文字段
const path = "shark.js";
const lines = fs.readFileSync(path, "utf8").split(/\r?\n/);
const hits = {};
let total = 0;

const out = lines.map(line => {
  const t = line.trim();
  if (!t.startsWith('{"id"')) return line;
  const hadComma = t.endsWith(",");
  const o = JSON.parse(hadComma ? t.slice(0, -1) : t);
  for (const f of FIELDS) {
    if (o[f]) {
      const v = conv(o[f]);
      if (v !== o[f]) { o[f] = v; hits[f] = (hits[f] || 0) + 1; total++; }
    }
  }
  return JSON.stringify(o) + (hadComma ? "," : "");
});

fs.writeFileSync(path, out.join("\n"), "utf8");
console.log("  转换 " + total + " 处：" +
  FIELDS.map(f => f + " " + (hits[f] || 0)).join(" / "));
