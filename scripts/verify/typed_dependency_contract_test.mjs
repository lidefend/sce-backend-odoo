import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const temp = mkdtempSync(path.join(tmpdir(), 'sce-types-'));
try {
  const config = path.join(temp, 'tsconfig.json');
  writeFileSync(config, JSON.stringify({ extends: path.join(root, 'frontend/apps/web/tsconfig.json'), compilerOptions: { types: [path.join(root, 'frontend/apps/web/node_modules/@types/node'), path.join(root, 'frontend/apps/web/node_modules/vite/client')] }, include: [path.join(root, 'frontend/apps/web/scripts/typed_dependency_contract_test.ts'), path.join(root, 'frontend/apps/web/src/env.d.ts')] }));
  execFileSync(path.join(root, 'frontend/apps/web/node_modules/.bin/vue-tsc'), ['--noEmit', '-p', config], { cwd: root, stdio: 'inherit' });
  console.log('[typed_dependency_contract_test] PASS cases=6');
} finally { rmSync(temp, { recursive: true, force: true }); }
