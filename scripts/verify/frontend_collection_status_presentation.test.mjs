import assert from 'node:assert/strict';
import { build } from '../../frontend/apps/web/node_modules/esbuild/lib/main.js';

const source = 'frontend/apps/web/src/app/presentation/collectionStatusPresentation.ts';
const result = await build({ entryPoints: [source], bundle: true, format: 'esm', platform: 'node', write: false });
const encoded = Buffer.from(result.outputFiles[0].text).toString('base64');
const { resolveCollectionStatusPresentation, resolveStatusTone } = await import(`data:text/javascript;base64,${encoded}`);

// The status colour is resolved by the frontend presentation layer from the
// authoritative status value; the contract carries no colour.
assert.deepEqual(
  resolveCollectionStatusPresentation({ value: 'approved', selection: [{ value: 'approved', label: '已批准' }] }),
  { value: 'approved', label: '已批准', tone: 'success' },
);
assert.deepEqual(
  resolveCollectionStatusPresentation({ value: 'approve' }),
  { value: 'approve', label: 'approve', tone: 'warning' },
);
assert.equal(resolveStatusTone(['approved', '已批准']), 'success');

// A display label is never a colour authority: an unknown or localised value
// keeps the design-system default badge.
assert.equal(resolveCollectionStatusPresentation({ value: '已批准' }).tone, 'neutral');
assert.equal(resolveCollectionStatusPresentation({ value: '风险' }).tone, 'neutral');
assert.equal(resolveStatusTone('not_a_declared_state'), 'neutral');
assert.equal(resolveStatusTone(''), 'neutral');

// The label still comes from the declared selection, falling back to the raw text.
assert.equal(resolveCollectionStatusPresentation({ value: ['approved', '已批准'] }).label, '已批准');
assert.equal(resolveCollectionStatusPresentation({ value: 'custom_state' }).tone, 'neutral');

// The legacy generic vocabulary stays coloured, but from the same table.
assert.equal(resolveStatusTone('rejected'), 'danger');
assert.equal(resolveStatusTone('overdue'), 'danger');
assert.equal(resolveStatusTone('pending'), 'warning');
assert.equal(resolveStatusTone('in_progress'), 'info');

// Business-value presentation must reuse the same status policy instead of
// keeping a second value-to-tone table of its own.
const businessValueBundle = await build({
  entryPoints: ['frontend/apps/web/src/app/presentation/businessValuePresentation.ts'],
  bundle: true,
  format: 'esm',
  platform: 'node',
  write: false,
});
const businessValue = await import(
  `data:text/javascript;base64,${Buffer.from(businessValueBundle.outputFiles[0].text).toString('base64')}`
);
assert.equal(businessValue.statusBadgeSemantic('approved'), 'success');
assert.equal(businessValue.statusBadgeSemantic('approve'), 'warning');
assert.equal(businessValue.statusBadgeSemantic('rejected'), 'danger');
assert.equal(businessValue.statusBadgeSemantic('not_a_declared_state'), 'default');

console.log('[frontend_collection_status_presentation] PASS cases=15');
