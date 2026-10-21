/**
 * Behavioural lock for the product capability catalog consumption surface.
 *
 * The frontend only projects what `product.configuration.capability.catalog`
 * declares. A declared surface that is malformed must stop with a
 * ContractGapError; an empty declared collection is a legitimate projection
 * (e.g. a non-business_full account has no login_home blocks) and must not be
 * backfilled. The capability list is consumed exactly as projected: no audience,
 * menu, role or model derivation may re-filter it.
 */
import assert from 'node:assert/strict';

import {
  capabilityStatusLabel,
  projectUserCapabilities,
  requireStructuredStartupCapabilities,
  isProductCapabilityCatalogGap,
  projectCapabilities,
  projectConfigurationCards,
  projectLoginHomeBlocks,
} from '../src/app/productCapabilityCatalogProjection';

let cases = 0;

const block = (key: string, available: boolean, reason = available ? 'available' : 'planned') => ({
  key,
  label: key,
  required: true,
  authority: 'authority',
  available,
  reason,
});

const card = (key: string, status: string, available = status !== 'planned') => ({
  key,
  label: key,
  status,
  available,
  reason: available ? 'available' : 'planned',
  entry: key,
  authority: 'authority',
});

const item = (key: string, audience: string, status: string, available = status !== 'planned') => ({
  key,
  label: key,
  audience,
  status,
  available,
  reason: available ? 'available' : 'planned',
  entry: key,
  authority: 'authority',
  description: 'description',
});

function rejected(run: () => unknown, label: string, missing: string): void {
  try {
    run();
  } catch (error) {
    assert.ok(isProductCapabilityCatalogGap(error), `${label}: expected ContractGapError`);
    assert.equal((error as Error & { defect?: { missing?: string } }).defect?.missing, missing, `${label}: defect path`);
    cases += 1;
    return;
  }
  assert.fail(`${label}: expected the surface to stop, but a value was returned`);
}

const businessFullCatalog = {
  schema_version: 'product_configuration_capability.v1',
  manifest_status: 'locked',
  objective: '',
  primary_audience: 'business_full',
  audiences: [],
  login_home: {
    audience: 'business_full',
    empty_state_policy: {},
    blocks: [
      block('today_actions', true),
      block('risks', true),
      block('my_objects', true),
      block('quick_actions', true),
      block('recent', true),
      block('capability_map', false, 'planned'),
    ],
  },
  configuration_cards: [],
  system_parameter_categories: [],
  capabilities: [item('workspace.capability_map', 'business_full', 'planned', false)],
  guardrails: [],
  reason: '',
  success: true,
  reason_code: 'OK',
};

// --- login_home blocks: declared six blocks are projected unchanged ----------
const blocks = projectLoginHomeBlocks(businessFullCatalog);
assert.equal(blocks.length, 6, 'business_full declares six login-home blocks');
assert.equal(blocks[5].key, 'capability_map', 'the sixth block is the capability map');
assert.equal(blocks[5].available, false, 'a planned block is declared unavailable');
assert.equal(blocks[5].reason, 'planned', 'the planned reason is preserved');
cases += 3;

// --- a non-business_full account has an empty login_home projection ----------
const adminCatalog = { ...businessFullCatalog, login_home: {}, configuration_cards: [] };
assert.deepEqual(projectLoginHomeBlocks(adminCatalog), [], 'empty login_home declares no blocks');
assert.deepEqual(projectLoginHomeBlocks(undefined), [], 'a missing catalog declares no blocks');
cases += 2;

// --- a declared but malformed surface stops ----------------------------------
rejected(
  () => projectLoginHomeBlocks({ ...businessFullCatalog, login_home: { blocks: 'not-a-list' } }),
  'non-list login_home.blocks',
  'product.configuration.capability.catalog.login_home.blocks',
);
rejected(
  () => projectLoginHomeBlocks({ ...businessFullCatalog, login_home: { blocks: [null] } }),
  'non-object block row',
  'product.configuration.capability.catalog.login_home.blocks[0]',
);
rejected(
  () => projectConfigurationCards({ configuration_cards: 'not-a-list' }),
  'non-list configuration_cards',
  'product.configuration.capability.catalog.configuration_cards',
);
rejected(
  () => projectCapabilities({ capabilities: [item('cap', 'business_full', 'planned', 'not-a-boolean' as unknown as boolean)] }),
  'non-boolean available',
  'product.configuration.capability.catalog.capabilities[0].available',
);

// --- configuration cards: declared status/available/reason are preserved -----
const cards = projectConfigurationCards({
  configuration_cards: [card('navigation', 'available'), card('approval_permissions', 'partial'), card('numbering', 'partial')],
});
assert.equal(cards.length, 3, 'three declared cards are projected');
assert.equal(cards[0].status, 'available', 'available status preserved');
assert.equal(cards[1].status, 'partial', 'partial status preserved');
assert.equal(cards[1].available, true, 'partial cards remain available');
cases += 3;

// --- capabilities: projected exactly, no audience re-derivation --------------
const capabilities = projectCapabilities({
  capabilities: [
    item('business.centers', 'business_full', 'available'),
    item('platform.tenant_company', 'platform_admin', 'available'),
  ],
});
assert.equal(capabilities.length, 2, 'projection does not re-filter by audience');
assert.equal(capabilities[1].key, 'platform.tenant_company', 'declared row order and identity survive');
cases += 2;

// --- renderer dispatch on declared statuses ----------------------------------
assert.equal(capabilityStatusLabel('available'), '可用', 'available label');
assert.equal(capabilityStatusLabel('partial'), '部分可用', 'partial label');
assert.equal(capabilityStatusLabel('planned'), '未发布', 'planned label');
assert.equal(capabilityStatusLabel('unknown'), 'unknown', 'an unknown declared status is echoed');
cases += 4;

const personal = { ...item('finance', '', 'deny', false), status_label: '无权限', reason: '需要财务权限', reason_code: 'FORBIDDEN' };
assert.deepEqual(projectUserCapabilities({ user_capabilities: { items: [personal], empty_message: '无业务权限' } }).items, [personal]);
assert.deepEqual(projectUserCapabilities({ user_capabilities: { items: [], empty_message: '无业务权限' } }), { items: [], empty_message: '无业务权限' });
for (const invalid of [undefined, {}, { user_capabilities: {} }, { user_capabilities: { items: [personal] } }, { user_capabilities: { items: [{ ...personal, status_label: '' }], empty_message: 'empty' } }]) {
  assert.throws(() => projectUserCapabilities(invalid), isProductCapabilityCatalogGap);
  cases++;
}
requireStructuredStartupCapabilities([]);
requireStructuredStartupCapabilities([{ key: 'finance', state: 'LOCKED', capability_state: 'deny' }]);
for (const invalid of [undefined, ['legacy'], [{ key: 'missing-verdict' }]]) {
  assert.throws(() => requireStructuredStartupCapabilities(invalid), isProductCapabilityCatalogGap);
  cases++;
}
cases += 4;

console.log(`[product_capability_catalog_test] PASS cases=${cases}`);
