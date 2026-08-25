import assert from 'node:assert/strict';
import {
  buildProfessionalRelationCancelledMessage,
  buildProfessionalRelationCreatedMessage,
  resolveProfessionalRelationLifecycleEvent,
  settleProfessionalRelationLifecycle,
} from '../src/pages/contractForm/professionalRelationLifecycleModel';

const query = {
  relation_create_mode: 'dialog',
  relation_dialog_nonce: 'relation-nonce-1234',
  relation_return_field: 'partner_id',
  relation_return_model: 'sale.order',
};
const created = buildProfessionalRelationCreatedMessage({ query, createdId: 42, relationModel: 'res.partner', label: '伙伴 A' });
const cancelled = buildProfessionalRelationCancelledMessage({ query, relationModel: 'res.partner' });
assert.deepEqual(created, {
  type: 'sc.relation_record_created.v1', nonce: 'relation-nonce-1234', fieldName: 'partner_id',
  parentModel: 'sale.order', relationModel: 'res.partner', id: 42, label: '伙伴 A',
});
assert.equal(buildProfessionalRelationCreatedMessage({ query: {}, createdId: 42, relationModel: 'res.partner' }), null);
assert.ok(cancelled);
const context = { nonce: 'relation-nonce-1234', fieldName: 'partner_id', parentModel: 'sale.order', relationModel: 'res.partner' };
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: created })?.kind, 'created');
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://evil.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: created }), null);
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: false, payload: created }), null);
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: { ...created, nonce: 'wrong-nonce' } }), null);
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: cancelled })?.kind, 'cancelled');

let active = true;
let createdCount = 0;
let closeSearchCount = 0;
assert.equal(settleProfessionalRelationLifecycle({
  active, closeLifecycle: () => { active = false; }, kind: 'created', restoreSearchOnCancel: true,
  restoreSearch: () => assert.fail('success must not restore search'),
  closeSearch: () => { closeSearchCount += 1; }, onCreated: () => { createdCount += 1; },
}), true);
assert.equal(settleProfessionalRelationLifecycle({
  active, closeLifecycle: () => {}, kind: 'created', restoreSearchOnCancel: true,
  restoreSearch: () => {}, closeSearch: () => { closeSearchCount += 1; }, onCreated: () => { createdCount += 1; },
}), false);
assert.equal(createdCount, 1);
assert.equal(closeSearchCount, 1);

active = true;
let restoreCount = 0;
assert.equal(settleProfessionalRelationLifecycle({
  active, closeLifecycle: () => { active = false; }, kind: 'cancelled', restoreSearchOnCancel: true,
  restoreSearch: () => { restoreCount += 1; }, closeSearch: () => assert.fail('cancel must preserve search'),
}), true);
assert.equal(restoreCount, 1);
console.log('[professional_relation_lifecycle_model_test] PASS cases=12 exact_once=1 dirty_preservation=1');
