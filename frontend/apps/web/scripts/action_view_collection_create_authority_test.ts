import assert from 'node:assert/strict';

import type { ContractV2NormalizedStore } from '../src/app/contracts/v2';
import {
  resolveCollectionCreateAuthority,
  resolveCollectionCreateEntry,
} from '../src/app/runtime/actionViewInteractionRuntime';

function store(options: {
  effectiveCreate?: boolean;
  includeCapabilities?: boolean;
  rule?: Record<string, unknown>;
}): ContractV2NormalizedStore {
  const globalStatus = options.includeCapabilities === false
    ? {}
    : { effectiveRecordCapabilities: { create: options.effectiveCreate } };
  return {
    snapshot: {
      statusContract: { globalStatus },
      actionContract: {
        actionRuleList: options.rule ? [{
          actionId: 'action.list.create',
          actionKey: 'list.create',
          triggerType: 'click',
          sourceWidgetId: 'collection.toolbar',
          targetIds: [],
          dispatchMode: 'local',
          targetScope: 'page',
          refreshMode: 'none',
          ...options.rule,
        }] : [],
      },
    },
  } as unknown as ContractV2NormalizedStore;
}

const authorizedRule = {
  allowed: true,
  authorizationAllowed: true,
  entitlementEvaluated: true,
  target: { type: 'record_create', model: 'project.project' },
};

const caseOf = (
  name: string,
  options: Parameters<typeof store>[0],
  actionId: unknown = 7,
) => {
  const contract = store(options);
  return {
    name,
    allowed: resolveCollectionCreateAuthority({
      effectiveCreate: options.includeCapabilities === false
        ? undefined
        : options.effectiveCreate,
      entry: resolveCollectionCreateEntry(contract),
      actionId,
    }),
  };
};

const cases = [
  caseOf('missing effective create capability', { rule: authorizedRule }),
  caseOf('explicit effective create denial', { effectiveCreate: false, rule: authorizedRule }),
  caseOf('explicit effective create grant', { effectiveCreate: true, rule: authorizedRule }),
  caseOf('missing list.create rule', { effectiveCreate: true }),
  caseOf('unauthorized list.create rule', {
    effectiveCreate: true,
    rule: { ...authorizedRule, authorizationAllowed: false },
  }),
  caseOf('incomplete action destination', {
    effectiveCreate: true,
    rule: { ...authorizedRule, target: { type: 'action', action_id: 31 } },
  }),
  caseOf('complete action destination', {
    effectiveCreate: true,
    rule: { ...authorizedRule, target: { type: 'action', action_id: 31, menu_id: 41 } },
  }),
  caseOf('delegated action remains authorized when direct create is denied', {
    effectiveCreate: false,
    rule: { ...authorizedRule, target: { type: 'action', action_id: 31, menu_id: 41 } },
  }),
  caseOf('delegated action remains authorized when direct create capability is absent', {
    includeCapabilities: false,
    rule: { ...authorizedRule, target: { type: 'action', action_id: 31, menu_id: 41 } },
  }),
  caseOf('record create without model', {
    effectiveCreate: true,
    rule: { ...authorizedRule, target: { type: 'record_create' } },
  }),
  caseOf('missing current action identity', { effectiveCreate: true, rule: authorizedRule }, null),
];

assert.deepEqual(cases.map((row) => row.allowed), [
  false,
  false,
  true,
  false,
  false,
  false,
  true,
  true,
  true,
  false,
  false,
]);

console.log('[action_view_collection_create_authority] PASS cases=11');
