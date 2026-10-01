/** Count explicit TypeScript type nodes, including Vue template expressions. */
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const require = createRequire(path.join(root, 'frontend/apps/web/package.json'));
const ts = require('typescript');
const { parse } = require('vue/compiler-sfc');

function countTypes(filename, source) {
  let count = 0;
  const tree = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const visit = (node) => {
    if (node.kind === ts.SyntaxKind.AnyKeyword) count += 1;
    ts.forEachChild(node, visit);
  };
  visit(tree);
  return count;
}

export function countExplicitAny(filename, source) {
  if (!filename.endsWith('.vue')) return countTypes(filename, source);
  const { descriptor, errors } = parse(source, { filename });
  if (errors.length) throw new Error(`Cannot parse Vue source: ${filename}`);
  let count = [descriptor.script, descriptor.scriptSetup]
    .reduce((total, script) => total + (script ? countTypes(filename, script.content) : 0), 0);
  const seen = new WeakSet();
  const visit = (node) => {
    if (!node || typeof node !== 'object' || seen.has(node)) return;
    seen.add(node);
    // Vue SimpleExpression nodes carry bindings/interpolations, not text nodes.
    if (node.type === 4 && !node.isStatic && typeof node.content === 'string') {
      count += countTypes(filename, node.content);
      return;
    }
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(visit);
      else if (value && typeof value === 'object') visit(value);
    }
  };
  visit(descriptor.template?.ast);
  return count;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const files = JSON.parse(fs.readFileSync(0, 'utf8'));
  const counts = Object.fromEntries(files.map((file) => [file, countExplicitAny(file, fs.readFileSync(path.join(root, file), 'utf8'))]));
  process.stdout.write(JSON.stringify(counts));
}
