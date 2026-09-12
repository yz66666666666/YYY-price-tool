// 临时语法检查：提取产物 <script> 内容用 V8 编译（不执行）
const fs = require("fs");
const vm = require("vm");
const src = fs.readFileSync("价格打码水印工具.html", "utf8");
const m = src.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.log("NO SCRIPT FOUND"); process.exit(1); }
const code = m[1];
const t0 = Date.now();
try {
  new vm.Script(code, { filename: "tool.js" });
  console.log("JS syntax OK, script length:", code.length, "(", Date.now() - t0, "ms )");
} catch (e) {
  console.log("SYNTAX ERROR:", e.message);
  process.exit(1);
}
