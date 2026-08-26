import assert from 'node:assert/strict';
import { build } from '../../frontend/apps/web/node_modules/esbuild/lib/main.js';

const source = 'frontend/apps/web/src/app/presentation/collectionStatusPresentation.ts';
const result = await build({ entryPoints: [source], bundle: true, format: 'esm', platform: 'node', write: false });
const encoded = Buffer.from(result.outputFiles[0].text).toString('base64');
const { resolveCollectionStatusPresentation } = await import(`data:text/javascript;base64,${encoded}`);

const authority = resolveCollectionStatusPresentation({
  value: 'approved',
  selection: [{ value: 'approved', label: '已批准' }],
  toneByValue: { approved: 'success' },
});
assert.deepEqual(authority, { value: 'approved', label: '已批准', tone: 'success' });

assert.equal(resolveCollectionStatusPresentation({ value: '已批准' }).tone, 'neutral');
assert.equal(resolveCollectionStatusPresentation({ value: '风险' }).tone, 'neutral');
assert.equal(resolveCollectionStatusPresentation({ value: 'approved', toneByValue: { approved: 'brand-blue' } }).tone, 'neutral');
assert.equal(resolveCollectionStatusPresentation({ value: ['approved', '已批准'], toneByValue: { approved: 'success' } }).label, '已批准');

console.log('[frontend_collection_status_presentation] PASS cases=5');
