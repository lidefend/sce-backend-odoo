import assert from 'node:assert/strict';
import { normalizeSceneFieldControlValue } from '../../../packages/ui/src/components/primitives/sceneFieldControlValue';
import { resolveModelContractRenderProfile } from '../src/api/modelContractProfile';
import { resolveActionSurfaceRenderer } from '../src/app/renderers/actionSurfaceRendererRegistry';
import { resolveContractFormComponentDriverDecision, resolveSceneComponentDriverDecision } from '../src/app/renderers/sceneComponentDriverPolicy';
import {
  normalizeContractFormDriverValue,
  toContractFormDriverFieldChange,
  toContractFormSceneField,
  usesContractFormDriverField,
} from '../src/components/template/contractFormDriverField';
import {
  readSceneComponentDriverTelemetry,
  recordSceneComponentDriverEvent,
} from '../src/app/renderers/sceneComponentDriverTelemetry';
import {
  resolveSceneReadonlyCollectionBridge,
  sceneCollectionRowToRecord,
} from '../src/app/renderers/sceneReadonlyCollectionBridge';

const identity = {
  productName: 'Enterprise Platform',
  companyName: 'Example Company',
  roleName: 'Reader',
  breadcrumbs: ['Directory'],
  workTabs: [],
};

assert.equal(
  resolveModelContractRenderProfile({ viewType: 'form' }),
  'create',
  'recordless form model requests must fail closed to the create profile',
);
assert.equal(
  resolveModelContractRenderProfile({ viewType: 'form', recordId: 7 }),
  '',
  'existing-record model requests must not invent an edit profile',
);
assert.equal(
  resolveModelContractRenderProfile({ viewType: 'form', renderProfile: 'readonly' }),
  'readonly',
  'an explicit governed profile must remain authoritative',
);
assert.equal(
  resolveModelContractRenderProfile({ viewType: 'tree' }),
  '',
  'recordless collection requests must not be reclassified as create forms',
);

function normalizedContract(actions: Array<Record<string, unknown>> = []) {
  return {
    __unified_page_contract_v2: {
      pageInfo: {
        pageId: 'page.department.list',
        sceneKey: 'organization.directory',
        pageName: 'Department Directory',
        model: 'hr.department',
        viewType: 'tree',
        layoutType: 'collection',
        contractVersion: '2.0.0',
        clientType: 'web_pc',
      },
      layoutContract: {
        layoutType: 'collection',
        adaptMode: 'responsive',
        containerTree: [{
          containerId: 'main',
          containerType: 'list',
          title: 'Directory',
          children: [],
          widgetList: [
            { widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', componentKey: 'sc.display.text' },
            { widgetId: 'field.manager_id', widgetType: 'many2one', fieldCode: 'manager_id', label: 'Manager', componentKey: 'sc.display.text' },
          ],
        }],
        listProfile: {
          columns: ['name', 'manager_id'],
          column_labels: { name: 'Name', manager_id: 'Manager' },
          row_primary: 'name',
          cross_device_critical_columns: ['name', 'manager_id'],
          selection_policy: { enabled: false },
          source_authority: {
            formal_projection: true,
            no_business_fact_authority: true,
            source_key: 'normalized.list.profile',
          },
        },
        componentRegistry: {},
      },
      statusContract: {
        globalStatus: { pageVisible: true, pageAuth: 'read' },
        widgetStatus: [
          { widgetId: 'field.name', visible: true },
          { widgetId: 'field.manager_id', visible: true },
        ],
        buttonStatus: [],
      },
      actionContract: { actionRuleList: actions },
      dataContract: {},
      runtimeContract: {},
      meta: {},
    },
  };
}

const bridge = resolveSceneReadonlyCollectionBridge({
  actionContract: normalizedContract(),
  records: [{ id: 7, name: 'Finance', manager_id: 'Ada' }],
  columnLabels: {},
  totalCount: 1,
  identity,
});
assert.equal(bridge.ok, true);
assert.equal(bridge.contract?.readonly, true);
assert.equal(bridge.contract?.selectionMode, 'none');
assert.deepEqual(bridge.contract?.table.rows[0]?.values, { name: 'Finance', manager_id: 'Ada' });
assert.deepEqual(
  sceneCollectionRowToRecord(bridge.contract!.table.rows[0]!),
  { id: '7', name: 'Finance', manager_id: 'Ada' },
);

const actionBridge = resolveSceneReadonlyCollectionBridge({
  actionContract: normalizedContract([{ actionId: 'action.create' }]),
  records: [],
  columnLabels: {},
  totalCount: 0,
  identity,
});
assert.equal(actionBridge.ok, false);
assert.equal(actionBridge.hasMutationActions, true);
assert.equal(actionBridge.reasonCode, 'SCENE_DRIVER_MUTATION_ACTION_PRESENT');

const enabledFlag = {
  enabled: true,
  read_only_only: true,
  action_ids: [77],
  allowed_kits: ['sc-native', 'tdesign-modern', 'ui5-horizon'],
  system_default_kit: 'tdesign-modern',
  allow_user_override: true,
};
assert.equal(resolveSceneComponentDriverDecision({
  featureFlag: {}, actionId: 77, model: 'hr.department', sceneKey: '', viewMode: 'tree', pageAuth: 'read',
  hasMutationActions: false, selectionEnabled: false,
}).reasonCode, 'SCENE_DRIVER_POLICY_DISABLED');
assert.equal(resolveSceneComponentDriverDecision({
  featureFlag: {}, actionId: 77, model: 'hr.department', sceneKey: '', viewMode: 'tree', pageAuth: 'read',
  hasMutationActions: false, selectionEnabled: false,
}).targeted, false);
assert.equal(resolveSceneComponentDriverDecision({
  featureFlag: { ...enabledFlag, action_ids: [] }, actionId: 77, model: 'hr.department', sceneKey: '', viewMode: 'tree', pageAuth: 'read',
  hasMutationActions: false, selectionEnabled: false,
}).reasonCode, 'SCENE_DRIVER_SCOPE_EMPTY');

const decision = resolveSceneComponentDriverDecision({
  featureFlag: enabledFlag, actionId: 77, model: 'hr.department', sceneKey: '', viewMode: 'tree', pageAuth: 'read',
  hasMutationActions: false, selectionEnabled: false, userKit: 'ui5-horizon',
});
assert.equal(decision.eligible, true);
assert.equal(decision.targeted, true);
assert.equal(decision.resolution.kit, 'ui5-horizon');
assert.equal(decision.allowUserOverride, true);

const deniedMutation = resolveSceneComponentDriverDecision({
  featureFlag: enabledFlag, actionId: 77, model: 'hr.department', sceneKey: '', viewMode: 'tree', pageAuth: 'read',
  hasMutationActions: true, selectionEnabled: false,
});
assert.equal(deniedMutation.targeted, true);
assert.equal(deniedMutation.eligible, false);
assert.equal(deniedMutation.reasonCode, 'SCENE_DRIVER_MUTATION_ACTION_PRESENT');

const readonlyForm = resolveContractFormComponentDriverDecision({
  featureFlag: enabledFlag, actionId: 77, model: 'hr.department', renderMode: 'readonly', userKit: 'tdesign-modern',
});
assert.equal(readonlyForm.eligible, true);
assert.equal(readonlyForm.resolution.kit, 'tdesign-modern');
assert.equal(resolveContractFormComponentDriverDecision({
  featureFlag: enabledFlag, actionId: 77, model: 'hr.department', renderMode: 'edit', userKit: 'tdesign-modern',
}).reasonCode, 'SCENE_DRIVER_FORM_MODE_UNSUPPORTED');
const formEnabledFlag = {
  ...enabledFlag,
  read_only_only: false,
  form_modes: ['create', 'edit', 'readonly'],
};
for (const renderMode of ['create', 'edit', 'readonly'] as const) {
  const formDecision = resolveContractFormComponentDriverDecision({
    featureFlag: formEnabledFlag,
    actionId: 77,
    model: 'hr.department',
    renderMode,
    userKit: 'tdesign-modern',
  });
  assert.equal(formDecision.eligible, true, `${renderMode} must be explicitly enabled by entitlement`);
  assert.equal(formDecision.resolution.kit, 'tdesign-modern');
}
assert.equal(resolveContractFormComponentDriverDecision({
  featureFlag: { ...formEnabledFlag, form_modes: [] },
  actionId: 77,
  model: 'hr.department',
  renderMode: 'edit',
}).reasonCode, 'SCENE_DRIVER_FORM_MODES_MISSING');
const driverField = {
  key: 'name', name: 'name', label: 'Name', type: 'char', required: true, readonly: false,
  invalid: true, inputValue: 'Draft', selectionOptions: [],
};
assert.equal(usesContractFormDriverField(driverField, 'sc-native'), false);
assert.equal(usesContractFormDriverField(driverField, 'tdesign-modern'), true);
assert.deepEqual(toContractFormSceneField(driverField, 'field-name', 'Enter name'), {
  id: 'field-name', label: 'Name', value: 'Draft', kind: 'text', required: true, readonly: false,
  invalid: true, placeholder: 'Enter name', options: [],
});
assert.equal(
  toContractFormSceneField({ ...driverField, type: 'date', inputValue: false }, 'field-date', 'Choose date').value,
  '',
  'Odoo false empty values must not become an invalid literal driver value',
);
assert.equal(normalizeContractFormDriverValue(false), '');
assert.equal(normalizeContractFormDriverValue('false'), 'false');
assert.equal(normalizeContractFormDriverValue('false', 'date'), '');
assert.equal(normalizeSceneFieldControlValue(false), '');
assert.equal(normalizeSceneFieldControlValue([false]), '');
assert.equal(normalizeSceneFieldControlValue('false', 'date'), '');
assert.equal(normalizeSceneFieldControlValue(['2026-08-17']), '2026-08-17');
assert.deepEqual(toContractFormDriverFieldChange(driverField, 'Updated'), {
  name: 'name', type: 'char', widget: undefined, value: 'Updated', descriptor: undefined,
});
assert.equal(
  usesContractFormDriverField({ ...driverField, readonly: true }, 'tdesign-modern'),
  true,
  'supported readonly fields must be rendered by the selected professional driver',
);
assert.equal(
  usesContractFormDriverField({ ...driverField, readonly: true }, 'ui5-horizon'),
  true,
  'readonly driver delegation must remain vendor-neutral',
);
assert.equal(
  usesContractFormDriverField({ ...driverField, readonly: true, type: 'html' }, 'tdesign-modern'),
  false,
  'unsupported rich readonly values must retain the safe Native renderer',
);

const standard = resolveActionSurfaceRenderer({ semantic: 'table', label: '', groupField: '', groupedLanes: false, config: {} }, 'tree');
assert.equal(standard.activeRendererKey, 'core.standard_collection');
const scene = resolveActionSurfaceRenderer(
  { semantic: 'table', label: '', groupField: '', groupedLanes: false, config: {} },
  'tree',
  { eligible: true, config: { contract: bridge.contract } },
);
assert.equal(scene.activeRendererKey, 'core.scene_collection');
assert.equal(scene.outlet, 'component');

for (let index = 0; index < 65; index += 1) {
  recordSceneComponentDriverEvent({
    timestamp: index,
    actionId: 77,
    model: 'hr.department',
    requestedKit: 'ui5-horizon',
    resolvedKit: 'ui5-horizon',
    source: 'user',
    reasonCode: '',
  });
}
const telemetry = readSceneComponentDriverTelemetry();
assert.equal(telemetry.length, 60);
assert.equal(telemetry[0]?.timestamp, 5);

console.log('[scene-component-driver-bridge] PASS cases=37');
