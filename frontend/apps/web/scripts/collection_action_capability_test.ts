/**
 * Declared collection capabilities: the list surface publishes one action list
 * (scope + intent per entry).  These cases lock what the client does with that
 * declaration — routing by declared scope, resolving the declared intent onto a
 * client executor, and reporting a declared-but-unexecutable action instead of
 * dropping or guessing it.  They assert the consumption of the declaration, not
 * the presence of any string in the source.
 */
import assert from 'node:assert/strict';

import { isContractGapError } from '../src/app/contract/contractGap';
import {
  COLLECTION_SCOPE,
  DECLARED_CAPABILITY_EXECUTORS,
  SELECTION_SCOPE,
  resolveDeclaredCapabilities,
  resolveDeclaredSelectionCapability,
  resolveSurfaceCapabilities,
} from '../src/app/runtime/actionViewCollectionCapabilityRuntime';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};
const checkDeep = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const text = (_key: string, fallback: string) => fallback;
const surface = (policies: unknown) => resolveDeclaredCapabilities(policies);

const declared = {
  collection_capabilities: {
    enabled: true,
    actions: [
      { action: 'export', scope: 'selection', intent: 'api.data', available: true },
      { action: 'delete', scope: 'selection', intent: 'api.data.unlink', available: true },
      { action: 'import', scope: 'collection', intent: 'api.data.import', available: true },
    ],
  },
};

// --- scope routing comes from the declaration ---
checkDeep(
  resolveSurfaceCapabilities(surface(declared), SELECTION_SCOPE, text).map((row) => row.action),
  ['export', 'delete'],
  'the selection surface offers exactly the declared selection-scope actions',
);
checkDeep(
  resolveSurfaceCapabilities(surface(declared), COLLECTION_SCOPE, text).map((row) => [row.key, row.action, row.enabled]),
  [['collection:import', 'import', true]],
  'the collection surface offers the declared collection-scope action with an empty selection',
);

// --- the declared intent decides the executor ---
checkDeep(
  resolveSurfaceCapabilities(surface(declared), COLLECTION_SCOPE, text).map((row) => [row.intent, row.executor]),
  [['api.data.import', 'import_records']],
  'the declared collection intent resolves to the client executor declared for it',
);
check(
  Object.entries(DECLARED_CAPABILITY_EXECUTORS).every(([intent, executor]) => intent.startsWith('api.') && Boolean(executor)),
  true,
  'the client executor table is keyed by declared intent, so a new action needs no client change',
);

// --- an unexecutable intent is surfaced, never silently dropped ---
const unknownIntent = {
  collection_capabilities: {
    enabled: true,
    actions: [{ action: 'sync', scope: 'collection', intent: 'api.data.unknown', available: true }],
  },
};
checkDeep(
  resolveSurfaceCapabilities(surface(unknownIntent), COLLECTION_SCOPE, text).map((row) => [row.action, row.enabled, row.hint !== '']),
  [['sync', false, true]],
  'a declared action this build cannot execute is reported unresolved rather than dropped',
);
check(
  (() => {
    try {
      surface({
        collection_capabilities: {
          enabled: true,
          actions: [{ action: 'import', scope: 'collection', intent: '', available: true }],
        },
      });
      return 'no-stop';
    } catch (err) {
      return isContractGapError(err) ? 'contract-gap' : 'unexpected-error';
    }
  })(),
  'contract-gap',
  'a declared action with no declared intent stops the surface instead of rendering an unresolved button',
);

// --- declared unavailability is honoured as declared ---
checkDeep(
  resolveSurfaceCapabilities(surface({ collection_capabilities: { enabled: true, actions: [{ action: 'import', scope: 'collection', intent: 'api.data.import', available: false }] } }), COLLECTION_SCOPE, text)
    .map((row) => [row.enabled, row.hint !== '']),
  [[false, true]],
  'an action the contract marks unavailable stays visible but disabled',
);

// --- a collection policy without the declaration is a contract defect ---
const stopped = (() => {
  try {
    surface({ batch_policy: { available_actions: ['export'], execution_intents: { export: 'api.data' } } });
    return null;
  } catch (err) {
    return err;
  }
})();
check(isContractGapError(stopped), true, 'a collection policy without the declaration stops the surface');
check(
  isContractGapError(stopped) ? stopped.defect.missing : '',
  'actionContract.surfacePolicies.collection_capabilities',
  'the stop names the missing declaration instead of rebuilding it from the selection policy',
);
checkDeep(
  surface({ batch_policy: {} }).actions,
  [],
  'a payload that publishes no collection policy yields no actions',
);
checkDeep(
  resolveSurfaceCapabilities(surface({}), COLLECTION_SCOPE, text),
  [],
  'no declared surface means no collection-scope action is invented',
);

// --- the selection capability is consumed verbatim, never defaulted ---
check(
  resolveDeclaredSelectionCapability({ selection_policy: { enabled: true }, collection_capabilities: { enabled: true, actions: [] } }),
  true,
  'a declared selection capability is consumed as declared',
);
check(
  resolveDeclaredSelectionCapability({ selection_policy: { enabled: false }, collection_capabilities: { enabled: true, actions: [] } }),
  false,
  'a declared empty selection capability stays false instead of falling back to a default',
);
check(
  resolveDeclaredSelectionCapability({}),
  false,
  'a payload with no surface policy declares no selection capability',
);
check(
  (() => {
    try {
      resolveDeclaredSelectionCapability({ batch_policy: { available_actions: ['export'] } });
      return 'no-stop';
    } catch (err) {
      return isContractGapError(err) ? err.defect.missing : 'unexpected-error';
    }
  })(),
  'actionContract.surfacePolicies.selection_policy',
  'a collection policy without a selection declaration stops the surface instead of guessing one',
);

// --- a declared collection capability carries a declared action list ---
const gapPath = (run: () => unknown) => {
  try {
    run();
    return 'no-stop';
  } catch (err) {
    return isContractGapError(err) ? err.defect.missing : 'unexpected-error';
  }
};

check(
  gapPath(() => surface({ collection_capabilities: { enabled: true } })),
  'actionContract.surfacePolicies.collection_capabilities.actions',
  'a declared capability with no actions array stops instead of defaulting to an empty list',
);
check(
  gapPath(() => surface({ collection_capabilities: { enabled: true, actions: 'import' } })),
  'actionContract.surfacePolicies.collection_capabilities.actions',
  'a non-array actions declaration stops instead of being coerced',
);
checkDeep(
  surface({ collection_capabilities: { enabled: false, actions: [] } }).actions,
  [],
  'an explicitly declared empty action list is a legal empty set, not a defect',
);
check(
  gapPath(() => surface({ collection_capabilities: { enabled: true, actions: [{ scope: 'selection', intent: 'api.data', available: true }] } })),
  'actionContract.surfacePolicies.collection_capabilities.actions[0].action',
  'an entry without an action name stops instead of being silently dropped',
);
check(
  gapPath(() => surface({ collection_capabilities: { enabled: true, actions: [{ action: 'export', intent: 'api.data', available: true }] } })),
  'actionContract.surfacePolicies.collection_capabilities.actions[0].scope',
  'an entry without a scope stops instead of being silently dropped',
);
check(
  gapPath(() => surface({ collection_capabilities: { enabled: true, actions: [{ action: 'export', scope: 'row', intent: 'api.data', available: true }] } })),
  'actionContract.surfacePolicies.collection_capabilities.actions[0].scope',
  'an entry with an undeclared scope stops instead of being routed by guesswork',
);
checkDeep(
  resolveSurfaceCapabilities(
    surface({ collection_capabilities: { enabled: true, actions: [{ action: 'import', scope: 'collection', intent: 'api.data.import', available: true }] } }),
    COLLECTION_SCOPE,
    text,
  ).map((row) => [row.action, row.enabled]),
  [['import', true]],
  'a fully declared entry still routes and enables exactly as declared after the stricter decode',
);

console.log(`[collection_action_capability_test] PASS cases=${cases}`);
