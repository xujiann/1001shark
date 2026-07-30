// 把 shark.js 里的「目」名繁体转简体。
// 依赖 1001art 的 node_modules（该项目搬过位置），逐个候选路径尝试；
// 找不到就跳过而不报错——这是可选美化步骤，不该卡住整条部署流水线。
const fs = require("fs");

const CANDIDATES = [
  "C:/Users/drxuj/Claude/Projects/1001art/node_modules/opencc-js",
  "C:/Users/drxuj/OneDrive/claude/1001art/node_modules/opencc-js",
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
const path = "shark.js";
const lines = fs.readFileSync(path, "utf8").split(/\r?\n/);
let n = 0;
const out = lines.map(line => {
  const t = line.trim();
  if (!t.startsWith('{"id"')) return line;
  const hadComma = t.endsWith(",");
  const o = JSON.parse(hadComma ? t.slice(0, -1) : t);
  if (o.order) {
    const v = conv(o.order);
    if (v !== o.order) { o.order = v; n++; }
  }
  return JSON.stringify(o) + (hadComma ? "," : "");
});
fs.writeFileSync(path, out.join("\n"), "utf8");
console.log("  转换 " + n + " 条");
