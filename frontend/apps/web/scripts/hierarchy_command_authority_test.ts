import assert from 'node:assert/strict';
import {
  buildHierarchyCommandRequest,
  hierarchyCommandHasExecutableAuthority,
  normalizeHierarchyCommand,
} from '../src/app/action_runtime/hierarchyCollectionDataSource';

const authorized = normalizeHierarchyCommand({
  key: 'confirm',
  label: 'Confirm',
  method: 'action_confirm',
  authorityActionId: 'action.confirm',
  backendIdentity: 'button:object:action_confirm',
  sourceWidgetId: 'page.header',
  routeActionId: 41,
  menuId: 51,
  allowed: true,
  enabled: true,
  disabled: false,
  entitlementEvaluated: true,
});
assert.equal(hierarchyCommandHasExecutableAuthority(authorized), true);
assert.deepEqual(buildHierarchyCommandRequest({ model: 'x.model', recordId: 7, command: authorized }), {
  model: 'x.model',
  res_id: 7,
  button: {
    name: 'action_confirm',
    type: 'object',
    action_id: 'action.confirm',
    backend_identity: 'button:object:action_confirm',
    source_widget_id: 'page.header',
  },
  context: {},
  meta: { action_id: 41, menu_id: 51 },
});

for (const key of [
  'authorityActionId', 'backendIdentity', 'sourceWidgetId', 'routeActionId', 'menuId',
  'allowed', 'enabled', 'disabled', 'entitlementEvaluated',
]) {
  const row: Record<string, unknown> = {
    key: 'confirm', label: 'Confirm', method: 'action_confirm',
    authorityActionId: 'action.confirm', backendIdentity: 'button:object:action_confirm',
    sourceWidgetId: 'page.header', routeActionId: 41, menuId: 51,
    allowed: true, enabled: true, disabled: false, entitlementEvaluated: true,
  };
  delete row[key];
  const command = normalizeHierarchyCommand(row);
  assert.equal(hierarchyCommandHasExecutableAuthority(command), false, `${key} must fail closed`);
  assert.throws(
    () => buildHierarchyCommandRequest({ model: 'x.model', recordId: 7, command }),
    /HIERARCHY_COMMAND_AUTHORITY_MISSING/,
  );
}

console.log('[hierarchy_command_authority_test] PASS cases=10');
