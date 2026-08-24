import assert from 'node:assert/strict';
import { formatProfessionalAuditTime, normalizeProfessionalAuditEvent, resolveProfessionalAuditEvents } from '../src/pages/contractForm/professionalAuditModel';

const audit = (overrides = {}) => ({
  key: 'audit-1', type: 'audit', typeLabel: '审计', title: '审批', meta: '', body: '审批意见',
  audit: { actor: 'Administrator', occurred_at: '2026-08-25T08:30:00Z', event: '审批', result: '通过' },
  ...overrides,
} as never);

const normalized = normalizeProfessionalAuditEvent(audit());
assert.deepEqual(normalized, {
  key: 'audit-1', actor: 'Administrator', occurredAt: '2026-08-25T08:30:00Z', event: '审批', result: '通过', detail: '审批意见',
});
assert.equal(normalizeProfessionalAuditEvent({ ...audit(), type: 'message' } as never), null);
assert.equal(normalizeProfessionalAuditEvent(audit({ audit: { actor: '', occurred_at: 'now', event: '审批', result: '通过' } })), null);
assert.equal(normalizeProfessionalAuditEvent(audit({ audit: { actor: 'A', occurred_at: '', event: '审批', result: '通过' } })), null);
assert.equal(normalizeProfessionalAuditEvent(audit({ audit: { actor: 'A', occurred_at: 'now', event: '', result: '通过' } })), null);
assert.equal(normalizeProfessionalAuditEvent(audit({ audit: { actor: 'A', occurred_at: 'now', event: '审批', result: '' } })), null);
assert.equal(resolveProfessionalAuditEvents([audit(), { ...audit(), key: 'message', type: 'message' } as never]).length, 1);
assert.equal(formatProfessionalAuditTime('not-a-date'), 'not-a-date');
assert.match(formatProfessionalAuditTime('2026-08-25T08:30:00Z'), /2026/);
console.log('[professional_audit_model_test] PASS cases=9');
