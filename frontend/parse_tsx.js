const fs = require('fs');
const acorn = require('acorn');
const jsx = require('acorn-jsx');

const code = fs.readFileSync('src/remotion/scenes/AtlasScene.tsx', 'utf8');

try {
  acorn.Parser.extend(jsx()).parse(code, { sourceType: 'module', ecmaVersion: 2020 });
  console.log("No syntax errors!");
} catch (e) {
  console.log("Syntax Error at line", e.loc.line, "column", e.loc.column);
  console.log(e.message);
}
