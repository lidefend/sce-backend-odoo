'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { fileURLToPath } = require('node:url');

function assertProbeSupported(filename) {
  const root = path.resolve(__dirname, '../../..');
  const file = String(filename).startsWith('file:') ? fileURLToPath(filename) : filename;
  const relative = path.relative(root, path.resolve(file)).split(path.sep).join('/');
  const registry = JSON.parse(fs.readFileSync(path.join(root, 'config/frontend/probe_toolchain_registry.json'), 'utf8'));
  const entry = registry.tools[relative];
  if (!entry || entry.status !== 'supported') {
    throw new Error(`PROBE_TOOL_UNSUPPORTED: ${relative}; ${entry?.reason || 'unregistered probe'}; no runtime request is authorized by this tool. See config/frontend/probe_toolchain_registry.json`);
  }
}

module.exports = { assertProbeSupported };
