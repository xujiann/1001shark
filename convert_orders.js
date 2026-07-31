// 把 shark.js 里的中文字段统一转成简体。
//
// ⚠️ 教训：原版只转 `order` 一个字段，物种名/科名里的扩展区罕见字没处理
//   //   导致 50/554 条的名/科/目含 CJK 扩展区字符（如 𩽾𩾌目），多数设备显示为豆腐块。
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

// ⚠️ 有些「简化」结果落在 CJK 扩展区（U+FFFF 以上），很多字体没有这些字，
//    会显示成豆腐块 □ —— 那还不如保留基本区的繁体写法。
//    典型：魟(U+9B5F, 到处都能显示) → 𫚉(U+2B689, 扩展区B, 常缺字)
//         鮟鱇 → 𩽾𩾌 同理。
// 所以：转换结果若引入了 BMP 之外的字符，就放弃这次转换。
function hasAstral(s) {
  for (const ch of s) if (ch.codePointAt(0) > 0xFFFF) return true;
  return false;
}
// 逐字转换：只跳过「转换后会掉进扩展区」的那个字，其余照常简化。
// 整串放弃是不够的——「六鰓魟科」里的 鰓→鳃 该转，只有 魟→𫚉 该保留。
function safeConv(s) {
  let out = "";
  for (const ch of s) {
    const v = conv(ch);
    out += (hasAstral(v) && !hasAstral(ch)) ? ch : v;
  }
  return out;
}
// 源数据里本就带的 CJK 扩展区字符（如 𩽾𩾌、𬶟），多数设备字体缺失 → 豆腐块。
// 不硬编码映射表（容易猜错：𬶟 其实是 鯻 不是我以为的字），
// 而是用 OpenCC 反向转换（简→繁）求它在基本区的正字，纯数据推导。
const s2t = OpenCC.Converter({ from: "cn", to: "t" });
const astralCache = new Map();
function deAstral(str) {
  let out = "";
  for (const ch of str) {
    if (ch.codePointAt(0) <= 0xFFFF) { out += ch; continue; }
    if (!astralCache.has(ch)) {
      const t = s2t(ch);
      const ok = [...t].every(x => x.codePointAt(0) <= 0xFFFF);
      astralCache.set(ch, ok ? t : ch);      // 反查不出基本区就原样保留
    }
    out += astralCache.get(ch);
  }
  return out;
}


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
      const v = deAstral(safeConv(o[f]));
      if (v !== o[f]) { o[f] = v; hits[f] = (hits[f] || 0) + 1; total++; }
    }
  }
  return JSON.stringify(o) + (hadComma ? "," : "");
});

fs.writeFileSync(path, out.join("\n"), "utf8");
console.log("  转换 " + total + " 处：" +
  FIELDS.map(f => f + " " + (hits[f] || 0)).join(" / "));
