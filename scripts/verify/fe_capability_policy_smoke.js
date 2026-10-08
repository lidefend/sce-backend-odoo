#!/usr/bin/env node
'use strict';

const path = require('path');
const { pathToFileURL } = require('url');

let assertionCount = 0;

function assert(cond, msg) {
  assertionCount += 1;
  if (!cond) throw new Error(msg);
}

async function main() {
  const modulePath = pathToFileURL(
    path.resolve(__dirname, '../../frontend/apps/web/src/app/capabilityPolicyCore.js'),
  ).href;
  const policy = await import(modulePath);
  const { evaluateCapabilityPolicy, capabilityTooltip } = policy;

  const base = evaluateCapabilityPolicy({ required: ['cap.a'], available: ['cap.a', 'cap.b'] });
  assert(base.state === 'enabled', 'expected enabled when capabilities satisfied');

  const missing = evaluateCapabilityPolicy({ required: ['cap.a'], available: ['cap.b'] });
  assert(missing.state === 'disabled_capability', 'expected disabled_capability');
  assert(missing.missing.includes('cap.a'), 'expected missing cap.a');
  assert(capabilityTooltip(missing).includes('Missing capabilities'), 'expected missing tooltip');

  const perm = evaluateCapabilityPolicy({ required: [], available: [], groups: ['g1'], userGroups: ['g2'] });
  assert(perm.state === 'disabled_permission', 'expected disabled_permission when groups mismatch');
  assert(capabilityTooltip(perm) === 'Permission required', 'expected permission tooltip');

  // Contract-2.0-Spec section 2.0: the projected capability_state is the authority.
  const projectedDeny = evaluateCapabilityPolicy({
    required: ['cap.a'],
    available: ['cap.a'],
    catalog: { 'cap.a': { capability_state: 'deny', capability_state_reason: 'PERMISSION_DENIED' } },
  });
  assert(projectedDeny.state === 'disabled_permission', 'expected projected deny to win over the grant list');
  assert(projectedDeny.reason_code === 'PERMISSION_DENIED', 'expected the published capability_state_reason');
  assert(projectedDeny.authority === 'contract', 'expected the contract projection authority');
  assert(capabilityTooltip(projectedDeny) === 'PERMISSION_DENIED', 'expected the contract reason in the tooltip');

  const projectedPending = evaluateCapabilityPolicy({
    required: ['cap.b'],
    available: ['cap.b'],
    catalog: { 'cap.b': { capability_state: 'pending' } },
  });
  assert(projectedPending.state === 'disabled_capability', 'expected projected pending to disable the capability');
  assert(projectedPending.missing.includes('cap.b'), 'expected the blocked capability to be reported');

  const projectedComingSoon = evaluateCapabilityPolicy({
    required: ['cap.c'],
    available: ['cap.c'],
    catalog: { 'cap.c': { capability_state: 'coming_soon' } },
  });
  assert(projectedComingSoon.state === 'disabled_capability', 'expected projected coming_soon to disable the capability');

  const projectedAllow = evaluateCapabilityPolicy({
    required: ['cap.d'],
    available: [],
    catalog: { 'cap.d': { capability_state: 'allow' } },
  });
  assert(projectedAllow.state === 'enabled', 'expected projected allow to enable without the grant list');
  assert(projectedAllow.authority === 'contract', 'expected the contract projection authority');

  const projectedReadonly = evaluateCapabilityPolicy({
    required: ['cap.e'],
    available: [],
    catalog: { 'cap.e': { capability_state: 'readonly' } },
  });
  assert(projectedReadonly.state === 'enabled', 'expected projected readonly to stay usable');

  const contractStateField = evaluateCapabilityPolicy({
    required: ['cap.f'],
    available: [],
    catalog: { 'cap.f': { state: 'READY', capability_state: 'allow' } },
  });
  assert(contractStateField.state === 'enabled', 'expected the runtime state alias to be accepted');

  const ungranted = evaluateCapabilityPolicy({ required: ['cap.g'], available: [] });
  assert(ungranted.state === 'disabled_capability', 'expected an ungranted capability to stay a capability gap');
  assert(ungranted.authority === 'contract-grant', 'expected the contract grant set to be reported');

  console.log(`[fe_capability_policy_smoke] PASS assertions=${assertionCount}`);
}

main().catch((err) => {
  console.error(`[fe_capability_policy_smoke] FAIL: ${err.message}`);
  process.exit(1);
});
