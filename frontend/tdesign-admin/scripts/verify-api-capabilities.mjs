import { readFile } from 'node:fs/promises';

import ts from 'typescript';

import { apiCapabilityRegistry } from '../src/api/capabilityRegistry.ts';

const sdk = await readFile(new URL('../src/api/odoo.ts', import.meta.url), 'utf8');
const source = ts.createSourceFile('odoo.ts', sdk, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
const sdkIntents = new Set();
function visit(node) {
  if (
    ts.isCallExpression(node) &&
    ts.isIdentifier(node.expression) &&
    node.expression.text === 'intent' &&
    node.arguments[0] &&
    ts.isStringLiteralLike(node.arguments[0])
  ) {
    sdkIntents.add(node.arguments[0].text);
  }
  ts.forEachChild(node, visit);
}
visit(source);
const registryIntents = apiCapabilityRegistry.map((entry) => entry.intent);
const registered = new Set(registryIntents);
const missing = [...sdkIntents].filter((intent) => !registered.has(intent)).sort();
const dynamicSdkClients = new Set(['release-operator']);
const stale = apiCapabilityRegistry
  .filter((entry) => !sdkIntents.has(entry.intent) && !dynamicSdkClients.has(entry.client))
  .map((entry) => entry.intent)
  .sort();
const duplicates = [...new Set(registryIntents.filter((intent, index) => registryIntents.indexOf(intent) !== index))].sort();
const invalid = apiCapabilityRegistry.filter(
  (entry) =>
    !entry.intent.trim() ||
    !entry.client.trim() ||
    !entry.pages.length ||
    entry.pages.some((page) => !page.trim()) ||
    !entry.permission.trim() ||
    !entry.test.trim(),
);

if (missing.length || stale.length || duplicates.length || invalid.length) {
  if (missing.length) console.error(`Unregistered SDK intents: ${missing.join(', ')}`);
  if (stale.length) console.error(`Registered intents without SDK implementation: ${stale.join(', ')}`);
  if (duplicates.length) console.error(`Duplicate registry intents: ${duplicates.join(', ')}`);
  if (invalid.length) console.error(`Incomplete registry entries: ${invalid.map((entry) => entry.intent || '<empty>').join(', ')}`);
  process.exitCode = 1;
} else {
  console.log(`API capability registry and SDK match for ${sdkIntents.size} statically referenced intents.`);
}
