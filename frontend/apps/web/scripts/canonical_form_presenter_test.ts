import assert from 'node:assert/strict';
import contractV2Schema from '../../../../docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import {
  createContractV2Store, resolveContractV2EffectiveFormCapabilities, resolveContractV2FieldDescriptorMap,
} from '../src/app/contracts/v2/store';
import type { ContractV2FormStructureRoleName, ContractV2Snapshot } from '../src/app/contracts/v2/types';
import {
  CONTRACT_V2_FORM_STRUCTURE_ROLES,
  canonicalRoleForFormStructureRole,
} from '../src/app/contracts/v2/formStructureRoles';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import { composeCanonicalFormFloorplan } from '../src/app/presentation/canonicalFormFloorplan';
import {
  canonicalFieldToFormSection,
  canonicalNodeHasContent,
  canonicalSectionFields,
  visibleCanonicalChildren,
} from '../src/pages/contractForm/canonicalFormRenderer';
import {
  collectCanonicalFormActions,
  resolveCanonicalFormActionExecution,
  validateCanonicalFormActionExecutors,
} from '../src/pages/contractForm/canonicalFormActionExecutor';
import {
  MANY2ONE_CREATE_OPTION,
  MANY2ONE_OPEN_RECORD_OPTION,
  MANY2ONE_SEARCH_MORE_OPTION,
  type ContractAction,
} from '../src/pages/contractForm/types';
import { contractActionConfirmationPrompt } from '../src/pages/contractForm/actionContract';
import { canonicalFormActionIconClass } from '../src/pages/contractForm/canonicalFormActionIcon';
import {
  buildCanonicalNativeFormBridge,
  resolveCanonicalNativeFieldSchemas,
} from '../src/pages/contractForm/canonicalNativeFormBridge';
import { normalizeContractFieldValue } from '../src/pages/contractForm/valueUtils';
import { relationCreateMode } from '../src/pages/contractForm/relationDescriptor';
import { resolveContractFormExitPresentation } from '../src/pages/contractForm/contractFormExitPresentation';
import {
  buildContractFormActions,
  resolveContractActionForNativeOccurrence,
} from '../src/pages/contractForm/contractActionPresentation';
import {
  applyInternalRelationContextSwitch,
  settleRelationSelectionContextSwitch,
} from '../src/pages/contractForm/relationSelectionRuntime';
import {
  executeRecordFormReturn,
  resolveRelationCreateDialogCancelMessage,
  resolveRelationCreateDialogMessage,
} from '../src/pages/contractForm/useCreatedRecordNavigationRuntime';
import {
  resolveRelationCreateDialogEvent,
  settleRelationCreateDialog,
  type RelationCreateDialogState,
} from '../src/pages/contractForm/relationCreateDialogRuntime';
import {
  formatMonetaryDisplayValue,
  monetaryInputStep,
  normalizeMonetaryDigits,
  resolveCurrencyDisplayLabel,
} from '../src/components/template/formSection.mapper';
import { resolveBusinessCategoryContext } from '../src/pages/contractForm/contractRuntimeVm';
import { useRelationRuntime } from '../src/pages/contractForm/useRelationRuntime';
import { collectUnifiedPageContractV2FieldWidgets } from '../src/app/contracts/unifiedPageContractV2';

const relationRuntime = useRelationRuntime();
relationRuntime.relationSearchDialog.fieldName = 'project_id';
relationRuntime.relationSearchDialog.descriptor = undefined;
relationRuntime.relationSearchDialog.keyword = '唯一项目';
relationRuntime.relationSearchDialog.options = [{ id: 41, label: '唯一项目' }];
let selectedExactRelationId = 0;
await relationRuntime.createRelationFromSearchDialog({
  resolveDescriptor: () => ({ type: 'many2one', relation: 'project.project' } as never),
  resolveMode: () => 'quick',
  selectOption: (option) => { selectedExactRelationId = option.id; },
  quickCreate: async () => { throw new Error('exact option must not quick-create'); },
  readValidationErrors: () => [],
  clearValidationErrors: () => {},
  openCreateForm: async () => { throw new Error('exact option must not open create form'); },
});
assert.equal(selectedExactRelationId, 41, 'an exact governed option must be selected without creating a duplicate');

relationRuntime.relationSearchDialog.open = true;
relationRuntime.relationSearchDialog.keyword = '新项目';
relationRuntime.relationSearchDialog.options = [];
let openedCreateField = '';
let openedCreateModel = '';
await relationRuntime.createRelationFromSearchDialog({
  resolveDescriptor: () => ({ type: 'many2one', relation: 'project.project' } as never),
  resolveMode: () => 'dialog',
  selectOption: () => { throw new Error('missing option must not be selected'); },
  quickCreate: async () => { throw new Error('dialog mode must not quick-create'); },
  readValidationErrors: () => [],
  clearValidationErrors: () => {},
  openCreateForm: async (fieldName, descriptor) => {
    openedCreateField = fieldName;
    openedCreateModel = String(descriptor?.relation || '');
  },
});
assert.equal(openedCreateField, 'project_id');
assert.equal(openedCreateModel, 'project.project', 'dialog creation must resolve the current canonical field descriptor');
assert.equal(relationRuntime.relationSearchDialog.open, false, 'dialog creation temporarily hides the preserved search surface');

assert.equal(resolveBusinessCategoryContext({
  contractRecord: null,
  routeQuery: {},
  relationBusinessCategoryLabel: '仅为搜索关键词',
  relationBusinessCategorySelected: false,
}).label, '', 'an unselected relation search keyword must not become business context authority');
assert.equal(resolveBusinessCategoryContext({
  contractRecord: null,
  routeQuery: {},
  relationBusinessCategoryLabel: '已选业务分类',
  relationBusinessCategorySelected: true,
}).label, '已选业务分类', 'a selected relation may supply its display label');

assert.deepEqual(normalizeMonetaryDigits([16, 2]), [16, 2]);
assert.equal(normalizeMonetaryDigits([16, -1]), undefined);
assert.equal(normalizeMonetaryDigits([2, 3]), undefined);
assert.equal(resolveCurrencyDisplayLabel([7, 'USD']), 'USD');
assert.equal(resolveCurrencyDisplayLabel({ id: 7, symbol: '€', name: 'EUR' }), 'EUR');
assert.equal(monetaryInputStep([16, 2]), '0.01');
assert.equal(monetaryInputStep(undefined), 'any');
assert.equal(formatMonetaryDisplayValue(1234.5, [16, 2], 'USD', 'en-US'), '$1,234.50');
assert.equal(formatMonetaryDisplayValue(1234.5, [16, 1], '元', 'en-US'), '1,234.5 元');
assert.equal(formatMonetaryDisplayValue('', [16, 2], 'USD', 'en-US'), '-');
assert.equal(normalizeContractFieldValue({
  name: 'amount', value: '12.345', descriptor: { type: 'monetary', digits: [16, 2] } as never,
  originalValue: 0, buildOne2manyValue: () => [],
}), 12.35);

assert.equal(relationCreateMode({
  relation: 'project.project',
  relation_entry: {
    can_read: true,
    can_create: false,
    create_mode: 'page',
    action_id: 91,
  },
} as never), 'none', 'a readonly page entry must not be projected as a create capability');
assert.equal(relationCreateMode({
  relation: 'project.project',
  relation_entry: {
    can_read: true,
    can_create: true,
    create_mode: 'page',
    action_id: 91,
  },
} as never), 'page', 'a backend-authorized page create entry must remain available');
assert.equal(relationCreateMode({
  relation: 'project.project',
  relation_entry: {
    can_read: true,
    can_create: true,
    create_mode: 'dialog',
    action_id: 91,
    menu_id: 12,
  },
} as never), 'dialog', 'a backend-authorized dialog create entry must remain in-page');

for (const scenario of [
  { managed: false, decisionMode: false, label: '返回列表', semanticIdentity: 'return-list' },
  { managed: false, decisionMode: true, label: '返回列表', semanticIdentity: 'return-list' },
  { managed: true, decisionMode: false, label: '取消', semanticIdentity: 'cancel-edit' },
  { managed: true, decisionMode: true, label: '取消', semanticIdentity: 'cancel-edit' },
] as const) {
  assert.deepEqual(
    resolveContractFormExitPresentation(scenario.managed),
    { label: scenario.label, semanticIdentity: scenario.semanticIdentity },
    `container exit presentation must stay unique when decisionMode=${scenario.decisionMode}`,
  );
}

assert.deepEqual(resolveRelationCreateDialogMessage({
  query: {
    relation_create_mode: 'dialog',
    relation_dialog_nonce: 'dialog-nonce-1234',
    relation_return_field: 'project_id',
    relation_return_model: 'payment.request',
  },
  createdId: 123,
  relationModel: 'project.project',
  label: '新建项目',
}), {
  type: 'sc.relation_record_created.v1',
  nonce: 'dialog-nonce-1234',
  fieldName: 'project_id',
  parentModel: 'payment.request',
  relationModel: 'project.project',
  id: 123,
  label: '新建项目',
}, 'dialog creation must emit a scoped record identity without navigating the parent');

const relationDialogQuery = {
  relation_create_mode: 'dialog',
  relation_dialog_nonce: 'dialog-nonce-1234',
  relation_return_field: 'project_id',
  relation_return_model: 'payment.request',
};
const relationDialogCancelMessage = resolveRelationCreateDialogCancelMessage({
  query: relationDialogQuery,
  relationModel: 'project.project',
});
assert.deepEqual(relationDialogCancelMessage, {
  type: 'sc.relation_record_cancelled.v1',
  nonce: 'dialog-nonce-1234',
  fieldName: 'project_id',
  parentModel: 'payment.request',
  relationModel: 'project.project',
}, 'managed relation forms must emit a scoped cancel message instead of navigating');
let managedCancelPosts = 0;
let managedHistoryBacks = 0;
assert.equal(await executeRecordFormReturn({
  query: relationDialogQuery,
  relationModel: 'project.project',
  embedded: true,
  postCancel: () => { managedCancelPosts += 1; },
  navigateBack: () => { managedHistoryBacks += 1; },
}), 'dialog_cancel');
assert.equal(managedCancelPosts, 1);
assert.equal(managedHistoryBacks, 0, 'managed dialog cancel must never traverse browser history');
let independentHistoryBacks = 0;
assert.equal(resolveRelationCreateDialogCancelMessage({
  query: {},
  relationModel: 'project.project',
}), null, 'independent relation forms must keep their normal page navigation behavior');
assert.equal(await executeRecordFormReturn({
  query: {},
  relationModel: 'project.project',
  embedded: false,
  postCancel: () => { throw new Error('independent form must not post a dialog cancel'); },
  navigateBack: () => { independentHistoryBacks += 1; },
}), 'history');
assert.equal(independentHistoryBacks, 1, 'independent form must retain its normal history return');

const openRelationDialog = (): RelationCreateDialogState => ({
  open: true,
  title: '新建项目',
  src: 'http://127.0.0.1:18081/f/project.project/new',
  nonce: 'dialog-nonce-1234',
  fieldName: 'project_id',
  parentModel: 'payment.request',
  relationModel: 'project.project',
  restoreSearchOnCancel: true,
});
const expectedOrigin = 'http://127.0.0.1:18081';
assert.deepEqual(resolveRelationCreateDialogEvent({
  dialog: openRelationDialog(),
  eventOrigin: expectedOrigin,
  expectedOrigin,
  sourceMatches: true,
  payload: relationDialogCancelMessage,
}), { kind: 'cancelled' }, 'a fully scoped cancel message must be accepted');
assert.equal(resolveRelationCreateDialogEvent({
  dialog: openRelationDialog(), eventOrigin: 'https://example.invalid', expectedOrigin, sourceMatches: true, payload: relationDialogCancelMessage,
}), null, 'a cancel message from the wrong origin must fail closed');
assert.equal(resolveRelationCreateDialogEvent({
  dialog: openRelationDialog(), eventOrigin: expectedOrigin, expectedOrigin, sourceMatches: false, payload: relationDialogCancelMessage,
}), null, 'a cancel message from a stale iframe source must fail closed');
assert.equal(resolveRelationCreateDialogEvent({
  dialog: openRelationDialog(), eventOrigin: expectedOrigin, expectedOrigin, sourceMatches: true,
  payload: { ...relationDialogCancelMessage, nonce: 'wrong-nonce-1234' },
}), null, 'a cancel message with the wrong nonce must fail closed');
assert.equal(resolveRelationCreateDialogEvent({
  dialog: openRelationDialog(), eventOrigin: expectedOrigin, expectedOrigin, sourceMatches: true,
  payload: { ...relationDialogCancelMessage, parentModel: 'other.parent' },
}), null, 'a cancel message with the wrong parent model must fail closed');
assert.equal(resolveRelationCreateDialogEvent({
  dialog: openRelationDialog(), eventOrigin: expectedOrigin, expectedOrigin, sourceMatches: true,
  payload: { ...relationDialogCancelMessage, fieldName: 'other_field' },
}), null, 'a cancel message with the wrong parent field must fail closed');
assert.equal(resolveRelationCreateDialogEvent({
  dialog: openRelationDialog(), eventOrigin: expectedOrigin, expectedOrigin, sourceMatches: true,
  payload: { ...relationDialogCancelMessage, relationModel: 'other.model' },
}), null, 'a cancel message with the wrong relation model must fail closed');

const cancelDialog = openRelationDialog();
const preservedSearch = { open: false, keyword: 'S69', rows: [7, 9], selectedId: 9 };
const preservedParentFields = { project_id: false, partner_id: 42, amount: 37.25 };
const preservedParentUrl = '/f/payment.request/new?menu_id=358&action_id=689';
let restoredSearchCount = 0;
assert.equal(settleRelationCreateDialog({
  dialog: cancelDialog,
  kind: 'cancelled',
  restoreSearch: () => { preservedSearch.open = true; restoredSearchCount += 1; },
  closeSearch: () => { throw new Error('cancel must not discard search state'); },
}), true, 'cancel must close only the create dialog and restore its search context');
assert.deepEqual(preservedSearch, { open: true, keyword: 'S69', rows: [7, 9], selectedId: 9 });
assert.deepEqual(preservedParentFields, { project_id: false, partner_id: 42, amount: 37.25 });
assert.equal(preservedParentUrl, '/f/payment.request/new?menu_id=358&action_id=689');
assert.equal(settleRelationCreateDialog({
  dialog: cancelDialog,
  kind: 'cancelled',
  restoreSearch: () => { restoredSearchCount += 1; },
  closeSearch: () => {},
}), false, 'duplicate cancel messages must be idempotent');
assert.equal(restoredSearchCount, 1);

const successDialog = openRelationDialog();
let backfillCount = 0;
let closeSearchCount = 0;
const successEvent = resolveRelationCreateDialogEvent({
  dialog: successDialog,
  eventOrigin: expectedOrigin,
  expectedOrigin,
  sourceMatches: true,
  payload: {
    type: 'sc.relation_record_created.v1',
    nonce: successDialog.nonce,
    fieldName: successDialog.fieldName,
    parentModel: successDialog.parentModel,
    relationModel: successDialog.relationModel,
    id: 123,
    label: '新建项目',
  },
});
assert.equal(successEvent?.kind, 'created');
assert.equal(settleRelationCreateDialog({
  dialog: successDialog,
  kind: 'created',
  restoreSearch: () => {},
  closeSearch: () => { closeSearchCount += 1; },
  onCreated: () => { backfillCount += 1; },
}), true, 'success must backfill once and close both dialog layers');
assert.equal(settleRelationCreateDialog({
  dialog: successDialog,
  kind: 'created',
  restoreSearch: () => {},
  closeSearch: () => { closeSearchCount += 1; },
  onCreated: () => { backfillCount += 1; },
}), false, 'duplicate success messages must be idempotent');
assert.equal(backfillCount, 1);
assert.equal(closeSearchCount, 1);

const contextSwitchFormData: Record<string, unknown> = { business_category_id: 7, note: '保留未保存内容' };
const contextSwitchKeywords: Record<string, string> = { business_category_id: '付款申请' };
let contextCode = '';
let contextReloads = 0;
let valueSeenByRouteGuard: unknown = 'not-observed';
let otherDirtyValueSeenByRouteGuard = '';
assert.equal(await applyInternalRelationContextSwitch({
  fieldName: 'business_category_id',
  formData: contextSwitchFormData,
  relationKeywords: contextSwitchKeywords,
  previousValue: false,
  previousKeyword: '',
  replaceRoute: async () => {
    valueSeenByRouteGuard = contextSwitchFormData.business_category_id;
    otherDirtyValueSeenByRouteGuard = String(contextSwitchFormData.note || '');
    contextCode = 'finance.payment.apply.pay';
  },
  contextApplied: () => contextCode === 'finance.payment.apply.pay',
  reload: async () => { contextReloads += 1; },
}), true);
assert.equal(valueSeenByRouteGuard, false, 'internal context navigation must not dirty itself');
assert.equal(otherDirtyValueSeenByRouteGuard, '保留未保存内容', 'unrelated dirty values must remain guarded');
assert.equal(contextSwitchFormData.business_category_id, 7, 'selected required relation must survive route replacement');
assert.equal(contextSwitchKeywords.business_category_id, '付款申请');
assert.equal(contextReloads, 1, 'an applied internal context route must reload exactly once');

contextCode = '';
contextReloads = 0;
assert.equal(await applyInternalRelationContextSwitch({
  fieldName: 'business_category_id',
  formData: contextSwitchFormData,
  relationKeywords: contextSwitchKeywords,
  previousValue: false,
  previousKeyword: '',
  replaceRoute: async () => {},
  contextApplied: () => false,
  reload: async () => { contextReloads += 1; },
}), false);
assert.equal(contextSwitchFormData.business_category_id, 7, 'cancelled navigation must preserve the selected relation');
assert.equal(contextReloads, 0, 'cancelled navigation must not reload and clear the form');

let settledDirtyCount = 0;
let settledDependentClearCount = 0;
let settledError = '';
assert.equal(await settleRelationSelectionContextSwitch({
  switchContext: async () => true,
  finalizeUnswitchedSelection: () => {
    settledDirtyCount += 1;
    settledDependentClearCount += 1;
  },
  reportError: (error) => { settledError = String(error); },
}), true, 'an applied context switch must remain owned by reload');
assert.equal(settledDirtyCount, 0, 'an applied context switch must not duplicate dirty bookkeeping');
assert.equal(settledDependentClearCount, 0, 'an applied context switch must not clear dependents twice');
assert.equal(settledError, '');

assert.equal(await settleRelationSelectionContextSwitch({
  switchContext: async () => false,
  finalizeUnswitchedSelection: () => {
    settledDirtyCount += 1;
    settledDependentClearCount += 1;
  },
  reportError: (error) => { settledError = String(error); },
}), false, 'cancelled context navigation must settle as an ordinary local selection');
assert.equal(settledDirtyCount, 1, 'cancelled navigation must mark the selection dirty exactly once');
assert.equal(settledDependentClearCount, 1, 'cancelled navigation must clear dependents exactly once');
assert.equal(contextSwitchFormData.business_category_id, 7, 'cancel bookkeeping must retain the selected value');

const rejectedContextFormData: Record<string, unknown> = {
  business_category_id: 11,
  note: '拒绝后仍保留的其他未保存内容',
};
const rejectedContextKeywords: Record<string, string> = { business_category_id: '付款申请' };
let rejectedReloads = 0;
let rejectedGuardValue: unknown = 'not-observed';
let rejectedErrorReports = 0;
assert.equal(await settleRelationSelectionContextSwitch({
  switchContext: () => applyInternalRelationContextSwitch({
    fieldName: 'business_category_id',
    formData: rejectedContextFormData,
    relationKeywords: rejectedContextKeywords,
    previousValue: false,
    previousKeyword: '',
    replaceRoute: async () => {
      rejectedGuardValue = rejectedContextFormData.business_category_id;
      throw new Error('ROUTE_REPLACE_REJECTED');
    },
    contextApplied: () => false,
    reload: async () => { rejectedReloads += 1; },
  }),
  finalizeUnswitchedSelection: () => {
    settledDirtyCount += 1;
    settledDependentClearCount += 1;
  },
  reportError: (error) => {
    rejectedErrorReports += 1;
    settledError = error instanceof Error ? error.message : String(error);
  },
}), false, 'a rejected route replacement must be contained as an unswitched selection');
assert.equal(settledDirtyCount, 2, 'rejected navigation must mark dirty exactly once');
assert.equal(settledDependentClearCount, 2, 'rejected navigation must clear dependents exactly once');
assert.equal(settledError, 'ROUTE_REPLACE_REJECTED', 'rejected navigation must remain diagnosable');
assert.equal(rejectedErrorReports, 1, 'rejected navigation must report its error exactly once');
assert.equal(rejectedGuardValue, false, 'the selected relation must not trip its own route guard');
assert.equal(rejectedReloads, 0, 'rejected navigation must never reload');
assert.equal(rejectedContextFormData.business_category_id, 11, 'rejected navigation must restore the selected value');
assert.equal(rejectedContextKeywords.business_category_id, '付款申请', 'rejected navigation must restore the selected label');
assert.equal(rejectedContextFormData.note, '拒绝后仍保留的其他未保存内容', 'other unsaved fields must remain protected');

function snapshot(): ContractV2Snapshot {
  return {
    pageInfo: {
      pageId: 'page.x.document.form', sceneKey: 'x.document.form', pageName: 'Document',
      model: 'x.document', viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.2.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.document.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 }, componentRegistry: {
        'sc.input.text': { version: '1.0', adapter: { web_pc: 'ElInput' }, selectedAdapter: 'TDesignInput' },
        'sc.display.status': { version: '1.0', adapter: { web_pc: 'ElInput' } },
        'sc.display.text': { version: '1.0', adapter: { web_pc: 'ElInput' } },
        'sc.relation.many2one': { version: '1.0', adapter: { web_pc: 'ElSelect' } },
        'sc.relation.table': { version: '1.0', adapter: { web_pc: 'ElTable' } },
      },
      containerTree: [{
        containerId: 'section.identity', containerType: 'group', type: 'group', title: 'Identity', span: 24,
        children: [{
          containerId: 'field.name', containerType: 'field', type: 'field', name: 'name', title: '', span: 12,
          label: 'Name', nolabel: true,
          children: [], widgetList: [{
            widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', span: 12,
            componentKey: 'sc.input.text', capabilities: [], componentConfig: {}, fieldType: 'char',
            ownerContainerId: 'field.name',
          }],
        }, {
          containerId: 'field.state', containerType: 'field', type: 'field', name: 'state', title: '', span: 12,
          children: [], widgetList: [{
            widgetId: 'field.state', widgetType: 'selection', fieldCode: 'state', label: 'State', span: 12,
            componentKey: 'sc.display.status', capabilities: [], componentConfig: {}, fieldType: 'selection',
            ownerContainerId: 'field.state',
          }],
        }],
        widgetList: [],
      }, {
        containerId: 'native.notebook', containerType: 'notebook', type: 'notebook', title: 'Related', span: 24,
        sourceAuthority: { projection_only: true, no_business_fact_authority: true },
        children: [{
          containerId: 'field.line_ids', containerType: 'field', type: 'field', name: 'line_ids', title: '', span: 24,
          children: [], widgetList: [{
            widgetId: 'field.line_ids', widgetType: 'one2many', fieldCode: 'line_ids', label: 'Lines', span: 24,
            componentKey: 'sc.relation.table', capabilities: [], componentConfig: {}, fieldType: 'one2many',
            ownerContainerId: 'field.line_ids',
          }],
        }], widgetList: [],
      }, {
        containerId: 'native.attachment', containerType: 'attachment', type: 'attachment', title: 'Attachments', span: 24,
        sourceAuthority: { projection_only: true, no_business_fact_authority: true }, children: [], widgetList: [],
      }, {
        containerId: 'native.chatter', containerType: 'chatter', type: 'chatter', title: 'Activity', span: 24,
        sourceAuthority: { projection_only: true, no_business_fact_authority: true }, children: [], widgetList: [],
      }],
    },
    actionContract: {
      actionRuleList: [{
        actionId: 'action.submit', backendIdentity: 'button:object:action_submit', triggerType: 'click',
        sourceWidgetId: 'page.root', targetIds: [], dispatchMode: 'serverBlocking', targetScope: 'page',
        refreshMode: 'full', actionKey: 'action_submit', label: 'Submit', allowed: true, enabled: true,
        disabled: false, entitlementEvaluated: true,
        visibleProfiles: ['edit', 'readonly'], presentation: { tier: 'primary', icon: 'fa-check' },
        actionSafety: { level: 'danger', requiresConfirmation: true },
      }], dependencyGraph: { 'action.submit': ['field.name'] },
    },
    statusContract: {
      globalStatus: {
        pageVisible: true,
        pageAuth: 'edit',
        reasonCode: '',
        modelRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        recordRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        viewCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        entryCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRecordCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRenderProfile: 'edit',
      },
      widgetStatus: [
        { widgetId: 'field.name', visible: true, readonly: false, required: true, disabled: false },
        { widgetId: 'field.state', visible: false, readonly: true, required: false, disabled: true, reasonCode: 'STATE_CONTEXT_ONLY' },
        { widgetId: 'field.line_ids', visible: true, readonly: true, required: false, disabled: false },
      ],
      buttonStatus: [{ btnId: 'action.submit', visible: true, disabled: false }],
      containerStatus: [], selectorStatus: [],
    },
    dataContract: {
      mainData: { name: 'D-001', state: 'draft', line_ids: [7] }, tableRows: {}, relationRows: {},
      dictData: {}, pagination: {}, dataSource: {}, dataMeta: {},
    },
    runtimeContract: {
      patchStrategy: 'full', cachePolicy: 'snapshot', optimistic: false, lazyContainer: [],
      virtualization: {}, retryPolicy: {},
    },
    meta: {
      etag: 'e', snapshotId: 's', traceId: 't', requestId: 'r', sourceType: 'ui.contract',
      lifecycle: {
        lifecycleVersion: '1', stage: 'sealed',
        definition: { schemaId: 'v2', schemaVersion: '2', schemaSha256: 'schema', contractVersion: '2', normativeStatus: 'active' },
        generation: { generator: 'test', generatorVersion: '1', sourceType: 'test', sourceSha256: 'source' },
        runtime: { requestId: 'r', traceId: 't', clientType: 'web_pc', traceSource: 'test' },
        integrity: { algorithm: 'sha256', contractSha256: 'contract-sha' }, authority: {},
      },
    },
  };
}

function collectFields(nodes: ReturnType<typeof presentContractV2Form>['zones']['primary']) {
  return nodes.flatMap((node): typeof node.fields => [...node.fields, ...collectFields(node.children)]);
}

function collectTexts(nodes: ReturnType<typeof presentContractV2Form>['zones']['primary']): string[] {
  return nodes.flatMap((node) => [node.text, ...collectTexts(node.children)]).filter(Boolean);
}

const source = snapshot();
const before = JSON.stringify(source);
const store = createContractV2Store(decodeContractV2Snapshot(source));

for (const legacyVersion of ['2.0.0', '2.1.0']) {
  const legacyServerSnapshot = snapshot() as ContractV2Snapshot & {
    layoutContract: { containerTree: Array<Record<string, unknown>> };
  };
  legacyServerSnapshot.pageInfo.contractVersion = legacyVersion;
  const legacyRoot = legacyServerSnapshot.layoutContract.containerTree[0];
  const legacyChildren = legacyRoot.children as Array<Record<string, unknown>>;
  legacyRoot.children = [legacyChildren[0]];
  legacyRoot.tabs = [legacyChildren[1]];
  for (const child of [...legacyRoot.children as Array<Record<string, unknown>>, ...legacyRoot.tabs as Array<Record<string, unknown>>]) {
    for (const widget of child.widgetList as Array<Record<string, unknown>>) delete widget.ownerContainerId;
  }
  const normalizedLegacyStore = createContractV2Store(decodeContractV2Snapshot(legacyServerSnapshot));
  assert.deepEqual(
    collectFields(presentContractV2Form(normalizedLegacyStore, 'edit').zones.primary).map((field) => field.fieldCode),
    ['name', 'state'],
    `a new client must normalize an old ${legacyVersion} child carrier and ownership before the strict store`,
  );
}

const malformedLegacyChildCarrier = snapshot() as ContractV2Snapshot & {
  layoutContract: { containerTree: Array<Record<string, unknown>> };
};
malformedLegacyChildCarrier.pageInfo.contractVersion = '2.0.0';
malformedLegacyChildCarrier.layoutContract.containerTree[0].tabs = { invalid: true };
assert.throws(
  () => decodeContractV2Snapshot(malformedLegacyChildCarrier),
  /tabs is not allowed/,
  'legacy compatibility must not erase a malformed child carrier before strict decoding',
);
const unsupportedFutureVersion = snapshot();
unsupportedFutureVersion.pageInfo.contractVersion = '2.3.0';
assert.throws(
  () => decodeContractV2Snapshot(unsupportedFutureVersion),
  /must be a negotiated 2\.0, 2\.1, or 2\.2 version/,
  'an unadvertised future minor must fail closed instead of using the 2.2 decoder',
);
assert.deepEqual(
  collectUnifiedPageContractV2FieldWidgets(snapshot()).map((widget) => widget.fieldCode),
  ['name', 'state', 'line_ids'],
  'the previous client collector must remain able to consume the new children-only 2.2 payload',
);

function governedFormStructure(role: ContractV2FormStructureRoleName) {
  return {
    source: 'ui.contract.v2.form_structure_contract' as const,
    structureVersion: '1.1' as const,
    model: 'x.document',
    viewType: 'form' as const,
    mode: 'business_task_form',
    presentationMode: 'task' as const,
    layoutPolicy: 'governed_slots',
    objectProfile: {
      model: 'x.document', kind: 'business_form' as const, factAuthority: 'business_object_model_and_view',
    },
    navigation: { title: 'Document' },
    slots: [{ slot: 'governed', title: 'Governed', role, fieldRefs: ['name'] }],
    fieldRoles: { name: { role, slot: 'governed', group: 'governed' } },
    sourceAuthority: {
      kind: 'unified_page_contract_v2' as const,
      runtime_carrier: 'ui.contract.v2.form_structure_contract' as const,
      projection_only: true as const,
      no_business_fact_authority: true as const,
      governed_form_structure: true as const,
      governance_source: { source: 'business_view_orchestration', ownerLayer: 'smart_core' },
    },
  };
}

for (const role of CONTRACT_V2_FORM_STRUCTURE_ROLES) {
  const roleSnapshot = snapshot();
  roleSnapshot.formStructureContract = governedFormStructure(role);
  roleSnapshot.layoutContract.containerTree[0].children[0].formStructureRole = {
    role, slot: 'governed', group: 'governed',
  };
  roleSnapshot.layoutContract.containerTree[0].children[0].widgetList[0].formStructureRole = {
    role, slot: 'governed', group: 'governed',
  };
  const decoded = decodeContractV2Snapshot(roleSnapshot);
  const projected = collectFields(presentContractV2Form(createContractV2Store(decoded), 'readonly').zones.primary)
    .find((field) => field.fieldCode === 'name');
  assert.equal(
    projected?.semanticRole,
    canonicalRoleForFormStructureRole(role),
    `form structure role ${role} must survive decoder/store/presenter projection`,
  );
}

const schemaFormStructureRoles = (
  contractV2Schema.$defs.formStructureRoleName.enum as string[]
);
assert.deepEqual(
  [...CONTRACT_V2_FORM_STRUCTURE_ROLES].sort(),
  [...schemaFormStructureRoles].sort(),
  'TypeScript and JSON Schema canonical form-structure role vocabularies must remain identical',
);

const invalidRoleSnapshot = snapshot() as ContractV2Snapshot & { formStructureContract?: Record<string, unknown> };
invalidRoleSnapshot.formStructureContract = governedFormStructure('context') as unknown as Record<string, unknown>;
((invalidRoleSnapshot.formStructureContract.fieldRoles as Record<string, Record<string, unknown>>).name).role = 'invented_role';
assert.throws(() => decodeContractV2Snapshot(invalidRoleSnapshot), /unsupported form structure role invented_role/);

const unknownStructureFieldSnapshot = snapshot() as ContractV2Snapshot & { formStructureContract?: Record<string, unknown> };
unknownStructureFieldSnapshot.formStructureContract = {
  ...governedFormStructure('context'), presentationColor: 'red',
};
assert.throws(() => decodeContractV2Snapshot(unknownStructureFieldSnapshot), /presentationColor is not allowed/);

const missingStructureAuthoritySnapshot = snapshot() as ContractV2Snapshot & { formStructureContract?: Record<string, unknown> };
missingStructureAuthoritySnapshot.formStructureContract = governedFormStructure('context') as unknown as Record<string, unknown>;
delete missingStructureAuthoritySnapshot.formStructureContract.sourceAuthority;
assert.throws(() => decodeContractV2Snapshot(missingStructureAuthoritySnapshot), /sourceAuthority.*must be an object/);

const missingPresentationModeSnapshot = snapshot() as ContractV2Snapshot & { formStructureContract?: Record<string, unknown> };
missingPresentationModeSnapshot.formStructureContract = governedFormStructure('context') as unknown as Record<string, unknown>;
delete missingPresentationModeSnapshot.formStructureContract.presentationMode;
assert.throws(
  () => decodeContractV2Snapshot(missingPresentationModeSnapshot),
  /presentationMode.*must equal task or workspace/,
  'form shape authority must be explicit rather than inferred from the legacy mode label',
);

const legacyStructureSnapshot = snapshot() as ContractV2Snapshot & { formStructureContract?: Record<string, unknown> };
legacyStructureSnapshot.formStructureContract = governedFormStructure('context') as unknown as Record<string, unknown>;
legacyStructureSnapshot.formStructureContract.structureVersion = '1.0';
delete legacyStructureSnapshot.formStructureContract.presentationMode;
assert.equal(
  decodeContractV2Snapshot(legacyStructureSnapshot).formStructureContract?.presentationMode,
  'workspace',
  'a deployed 1.0 structure must take the explicit conservative workspace compatibility path',
);

const decoderBypassSnapshot = snapshot();
decoderBypassSnapshot.formStructureContract = governedFormStructure('context');
const decodedBypassStore = createContractV2Store(decodeContractV2Snapshot(decoderBypassSnapshot));
const invalidBypassStore = {
  ...decodedBypassStore,
  snapshot: {
    ...decodedBypassStore.snapshot,
    formStructureContract: { ...decodedBypassStore.snapshot.formStructureContract!, presentationMode: undefined },
  },
} as unknown as typeof decodedBypassStore;
assert.throws(
  () => presentContractV2Form(invalidBypassStore, 'edit'),
  /CANONICAL_FORM_PRESENTATION_MODE_MISSING/,
  'a store constructed outside the decoder must not silently default a missing presentation authority',
);

const structurePresentationSnapshot = snapshot();
structurePresentationSnapshot.formStructureContract = {
  ...governedFormStructure('context'),
  navigation: { title: 'Authoritative task title' },
  fieldLabels: { name: 'Contract name' },
  fieldRoles: {
    name: { role: 'context', slot: 'governed', group: 'identity' },
    state: { role: 'context', slot: 'governed', group: 'identity' },
  },
  slots: [{
    slot: 'governed', title: 'Governed', role: 'context', readonly: true, fieldRefs: ['name', 'state'],
    groups: [{
      name: 'identity', title: 'Contract identity', role: 'context', fieldRefs: ['name', 'state'],
      fieldLabels: { state: 'Contract status' }, columns: 2,
    }],
  }],
};
structurePresentationSnapshot.layoutContract.containerTree[0].formStructureRole = {
  role: 'risk', slot: 'governed', group: 'identity',
};
structurePresentationSnapshot.layoutContract.containerTree[0].span = 16;
structurePresentationSnapshot.layoutContract.containerTree[0].styleToken = 'surface.task.identity';
Object.assign(structurePresentationSnapshot.layoutContract.containerTree[0], {
  displayLabel: 'Identity display', semanticTitle: 'Identity semantic', semanticAnchor: 'identity-anchor',
  filename: 'attachment_name', badge: { field: 'state' }, options: { collapsible: true },
  class: 'native-identity', fieldSize: 'large', size: 'lg',
});
structurePresentationSnapshot.statusContract.widgetStatus[0].placeholder = 'Contract placeholder';
const structurePresentationModel = presentContractV2Form(
  createContractV2Store(decodeContractV2Snapshot(structurePresentationSnapshot)),
  'edit',
);
assert.equal(
  structurePresentationModel.shell.title,
  'Authoritative task title',
  'the formal form-structure navigation title must reach the canonical shell',
);
const structurePresentationFields = collectFields(structurePresentationModel.zones.primary);
assert.equal(
  structurePresentationFields.find((field) => field.fieldCode === 'name')?.label,
  'Contract name',
  'top-level form-structure field labels must override layout widget display labels',
);
assert.equal(
  structurePresentationFields.find((field) => field.fieldCode === 'state')?.label,
  'Contract status',
  'group-scoped form-structure field labels must reach their canonical fields',
);
assert.equal(
  structurePresentationModel.zones.primary[0].title,
  'Contract identity',
  'the matching formal group title must override the repeated native container title',
);
assert.equal(
  structurePresentationModel.zones.primary[0].columns,
  2,
  'the matching formal group column authority must reach the canonical node',
);
assert.equal(
  structurePresentationModel.zones.primary[0].semanticRole,
  'context',
  'the formal group role must override a stale duplicated layout role carrier',
);
assert.equal(
  structurePresentationFields.find((field) => field.fieldCode === 'name')?.readonly,
  true,
  'a readonly formal slot must remain readonly even when widget status permits editing',
);
assert.deepEqual(
  {
    role: structurePresentationFields.find((field) => field.fieldCode === 'name')?.semanticRole,
    slot: structurePresentationFields.find((field) => field.fieldCode === 'name')?.semanticSlot,
    group: structurePresentationFields.find((field) => field.fieldCode === 'name')?.semanticGroup,
  },
  { role: 'context', slot: 'governed', group: 'identity' },
  'top-level fieldRoles must be the semantic identity authority consumed by the presenter',
);
assert.equal(
  structurePresentationFields.find((field) => field.fieldCode === 'name')?.placeholder,
  'Contract placeholder',
  'widget status placeholder authority must reach the canonical field',
);
assert.equal(
  canonicalFieldToFormSection(structurePresentationFields.find((field) => field.fieldCode === 'name')!).inputPlaceholder,
  'Contract placeholder',
  'canonical placeholder authority must reach the professional field adapter',
);
assert.deepEqual(
  {
    adapter: structurePresentationFields.find((field) => field.fieldCode === 'name')?.componentResolution.contractAdapter,
    version: structurePresentationFields.find((field) => field.fieldCode === 'name')?.componentResolution.contractVersion,
  },
  { adapter: 'TDesignInput', version: '1.0' },
  'the delivered client adapter binding must reach the professional component resolution',
);

const missingComponentRegistrySnapshot = snapshot();
delete missingComponentRegistrySnapshot.layoutContract.componentRegistry['sc.input.text'];
assert.throws(
  () => presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(missingComponentRegistrySnapshot)), 'edit'),
  /PROFESSIONAL_COMPONENT_CONTRACT_REGISTRY_MISSING:sc\.input\.text/,
  'a widget without its delivered component registry authority must fail closed',
);
assert.deepEqual(
  {
    span: structurePresentationModel.zones.primary[0].span,
    styleToken: structurePresentationModel.zones.primary[0].styleToken,
  },
  { span: 16, styleToken: 'surface.task.identity' },
  'container geometry and style-token identities must survive canonical projection',
);
assert.equal(
  structurePresentationModel.zones.primary[0].span,
  16,
  'the canonical node span must remain available to the professional layout adapter',
);
const structureNativeNode = buildCanonicalNativeFormBridge(structurePresentationModel).primaryNodes[0];
assert.deepEqual(
  {
    displayLabel: structureNativeNode.displayLabel,
    semanticTitle: structureNativeNode.semanticTitle,
    semanticAnchor: structureNativeNode.semanticAnchor,
    filename: structureNativeNode.filename,
    badge: structureNativeNode.badge,
    options: structureNativeNode.options,
    class: structureNativeNode.class,
    fieldSize: structureNativeNode.fieldSize,
    size: structureNativeNode.size,
  },
  {
    displayLabel: 'Identity display', semanticTitle: 'Identity semantic', semanticAnchor: 'identity-anchor',
    filename: 'attachment_name', badge: { field: 'state' }, options: { collapsible: true },
    class: 'native-identity', fieldSize: 'large', size: 'lg',
  },
  'formal native presentation metadata must survive decoder, presenter, and the professional native bridge',
);

const fieldAuthSnapshot = snapshot();
fieldAuthSnapshot.statusContract.widgetStatus[0].auth = 'read';
fieldAuthSnapshot.statusContract.widgetStatus[0].readonly = false;
const fieldAuthName = collectFields(presentContractV2Form(
  createContractV2Store(decodeContractV2Snapshot(fieldAuthSnapshot)),
  'edit',
).zones.primary).find((field) => field.fieldCode === 'name')!;
assert.equal(fieldAuthName.auth, 'read', 'field-level auth must survive canonical projection');
assert.equal(fieldAuthName.readonly, true, 'field-level read authority must not become editable through page authority');
assert.equal(
  canonicalFieldToFormSection(fieldAuthName).auth,
  'read',
  'field auth must reach the professional component adapter and semantic DOM carrier',
);

const widgetIdentitySnapshot = snapshot();
widgetIdentitySnapshot.layoutContract.containerTree[0].children[0].widgetList[0].widgetType = 'radio';
widgetIdentitySnapshot.layoutContract.containerTree[0].children[0].widgetList[0].nativeLocator = '/form/sheet/group/field[1]';
widgetIdentitySnapshot.layoutContract.containerTree[0].children[0].widgetList[0].occurrenceIndex = 1;
widgetIdentitySnapshot.layoutContract.containerTree[0].children[0].widgetList[0].sourcePosition = 7;
const widgetIdentityField = collectFields(presentContractV2Form(
  createContractV2Store(decodeContractV2Snapshot(widgetIdentitySnapshot)),
  'edit',
).zones.primary).find((field) => field.fieldCode === 'name')!;
assert.deepEqual(
  {
    widget: canonicalFieldToFormSection(widgetIdentityField).widget,
    nativeLocator: canonicalFieldToFormSection(widgetIdentityField).nativeLocator,
    occurrenceIndex: canonicalFieldToFormSection(widgetIdentityField).occurrenceIndex,
    sourcePosition: canonicalFieldToFormSection(widgetIdentityField).sourcePosition,
  },
  {
    widget: 'radio', nativeLocator: '/form/sheet/group/field[1]', occurrenceIndex: 1, sourcePosition: 7,
  },
  'widget kind and native occurrence identity must reach the professional field adapter',
);

const selectorReadonlySnapshot = snapshot();
selectorReadonlySnapshot.statusContract.selectorStatus = [{
  selector: 'field.*', readonly: true, reasonCode: 'ROLE_READONLY',
}];
const selectorReadonlyFields = collectFields(presentContractV2Form(
  createContractV2Store(decodeContractV2Snapshot(selectorReadonlySnapshot)),
  'edit',
).zones.primary);
assert.equal(
  selectorReadonlyFields.find((field) => field.fieldCode === 'name')?.readonly,
  true,
  'selector readonly authority must reach every matching canonical field',
);
assert.equal(
  selectorReadonlyFields.find((field) => field.fieldCode === 'name')?.reasonCode,
  'ROLE_READONLY',
  'selector denial reason must survive canonical projection',
);

const selectorHiddenSnapshot = snapshot();
selectorHiddenSnapshot.statusContract.selectorStatus = [{
  selector: 'section.identity', visible: false, reasonCode: 'SECTION_HIDDEN',
}];
const selectorHiddenModel = presentContractV2Form(
  createContractV2Store(decodeContractV2Snapshot(selectorHiddenSnapshot)),
  'edit',
);
assert.equal(selectorHiddenModel.zones.primary[0].visible, false, 'selector visibility must govern matching containers');
assert.equal(
  collectFields(selectorHiddenModel.zones.primary)[0]?.visible,
  false,
  'a selector-hidden container must hide its descendant fields',
);

const legacyChildCarrierSnapshot = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
legacyChildCarrierSnapshot.layoutContract.containerTree[0].tabs = [];
assert.throws(() => decodeContractV2Snapshot(legacyChildCarrierSnapshot), /tabs is not allowed/);

const invalidChildrenSnapshot = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
invalidChildrenSnapshot.layoutContract.containerTree[0].children = 'not-an-array';
assert.throws(() => decodeContractV2Snapshot(invalidChildrenSnapshot), /children must be an array/);

const unknownOwnerSnapshot = snapshot();
unknownOwnerSnapshot.layoutContract.containerTree[0].children[0].widgetList[0].ownerContainerId = 'missing.owner';
assert.throws(() => decodeContractV2Snapshot(unknownOwnerSnapshot), /references unknown owner missing.owner/);

const duplicateWidgetSnapshot = snapshot();
duplicateWidgetSnapshot.layoutContract.containerTree[0].children[1].widgetList.push({
  ...duplicateWidgetSnapshot.layoutContract.containerTree[0].children[0].widgetList[0],
  ownerContainerId: 'field.state',
});
assert.throws(() => decodeContractV2Snapshot(duplicateWidgetSnapshot), /duplicate widget identity field.name/);
assert.deepEqual(resolveContractV2EffectiveFormCapabilities(store), {
  read: true, write: true, create: true, unlink: true, duplicate: true,
});
assert.equal(store.snapshot.statusContract.globalStatus.effectiveRenderProfile, 'edit');
const descriptorSelectionSnapshot = snapshot();
descriptorSelectionSnapshot.layoutContract.containerTree[0].children[1].widgetList[0].fieldDescriptor = {
  name: 'state', type: 'selection', widget: 'statusbar', selection: [['draft', 'Draft'], ['done', 'Done']],
};
assert.deepEqual(
  resolveContractV2FieldDescriptorMap(createContractV2Store(descriptorSelectionSnapshot)).state?.selection,
  [['draft', 'Draft'], ['done', 'Done']],
  'native fieldDescriptor selection must remain available to statusbar rendering',
);
const model = presentContractV2Form(store, 'edit');
assert.deepEqual(model.responsive, {
  adaptMode: 'pc',
  layoutHints: { mobileColumns: 1 },
}, 'canonical responsive authority must preserve the delivered adapt mode and layout hints');
const hiddenActionSnapshot = snapshot();
hiddenActionSnapshot.actionContract.actionRuleList[0].invisible = true;
assert.deepEqual(
  presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(hiddenActionSnapshot)), 'edit').actionBar,
  [],
  'an explicitly hidden action definition must not be revived by a visible button status',
);
const actionReasonSnapshot = snapshot();
actionReasonSnapshot.actionContract.actionRuleList[0].enabled = false;
actionReasonSnapshot.actionContract.actionRuleList[0].disabled = true;
actionReasonSnapshot.actionContract.actionRuleList[0].reasonCode = 'WORKFLOW_BLOCKED';
actionReasonSnapshot.statusContract.buttonStatus[0].reasonCode = '';
assert.equal(
  presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(actionReasonSnapshot)), 'edit')
    .actionBar[0]?.reasonCode,
  'WORKFLOW_BLOCKED',
  'the formal action denial reason must survive when status does not provide a more specific reason',
);
assert.equal(JSON.stringify(source), before, 'presenter must not mutate normalized input');
assert.equal(model.identity.sourceContractSha256, 'contract-sha');
assert.deepEqual(model.zones.subordinate.map((node) => node.kind), ['notebook', 'attachment', 'chatter']);
const fields = collectFields([...model.zones.primary, ...model.zones.subordinate]);
assert.deepEqual(fields.map((field) => field.fieldCode), ['name', 'state', 'line_ids']);
assert.equal(fields.find((field) => field.fieldCode === 'name')?.required, true);
assert.equal(fields.find((field) => field.fieldCode === 'name')?.hideLabel, true);
assert.equal(fields.find((field) => field.fieldCode === 'name')?.componentResolution.renderer, 'ProfessionalBaseFieldControl');
assert.equal(fields.find((field) => field.fieldCode === 'name')?.presentationMode, 'workspace');
assert.equal(fields.find((field) => field.fieldCode === 'name')?.renderProfile, 'edit');
assert.equal(fields.find((field) => field.fieldCode === 'line_ids')?.componentResolution.renderer, 'ProfessionalDetailCollectionControl');
assert.equal(fields.find((field) => field.fieldCode === 'state')?.hideLabel, false);
assert.equal(canonicalFieldToFormSection(fields.find((field) => field.fieldCode === 'name')!).hideLabel, true);
assert.equal(fields.find((field) => field.fieldCode === 'state')?.visible, false);
assert.equal(model.actionBar[0]?.actionRef, store.snapshot.actionContract.actionRuleList[0]);
assert.deepEqual(model.actionBar[0]?.actionRef, source.actionContract.actionRuleList[0]);
assert.equal(model.actionBar[0]?.enabled, true);
assert.equal(model.actionBar[0]?.icon, 'fa-check');
assert.equal(canonicalFormActionIconClass(model.actionBar[0]?.icon || ''), 'check');
assert.equal(canonicalFormActionIconClass('fa-check injected-class'), '');
assert.equal(canonicalFormActionIconClass('oi-check'), '');
assert.deepEqual(presentContractV2Form(store, 'create').actionBar, []);

const runtimeScopedActionSnapshot = structuredClone(snapshot());
runtimeScopedActionSnapshot.actionContract.actionRuleList.push({
  actionId: 'action.form_configuration_apply', backendIdentity: 'contract_action:form_configuration_apply',
  triggerType: 'click', sourceWidgetId: 'mode.form_field_configuration', targetIds: [],
  dispatchMode: 'server', targetScope: 'runtime', refreshMode: 'partial',
  actionKey: 'form_configuration_apply', label: 'Apply configuration',
  allowed: true, enabled: true, disabled: false, entitlementEvaluated: true,
  visibleProfiles: ['edit'], presentation: { tier: 'configuration' },
});
runtimeScopedActionSnapshot.statusContract.buttonStatus.push({
  btnId: 'action.form_configuration_apply', visible: true, disabled: false,
});
const runtimeScopedActionModel = presentContractV2Form(
  createContractV2Store(runtimeScopedActionSnapshot),
  'edit',
);
assert.deepEqual(
  runtimeScopedActionModel.actionBar.map((action) => action.key),
  ['action_submit'],
  'a mode-local runtime action must never be promoted into the product action bar',
);
assert.deepEqual(
  collectCanonicalFormActions(runtimeScopedActionModel).map((action) => action.key),
  ['action_submit'],
  'a runtime orchestration action must not enter product executor validation',
);

const bodyActionSnapshot = structuredClone(snapshot());
bodyActionSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'button.action_open_lines', containerType: 'button', type: 'button', title: 'Open Lines', span: 24,
  action: { actionId: 'action.open_lines', backendIdentity: 'window_action:91' },
  children: [], widgetList: [],
});
bodyActionSnapshot.actionContract.actionRuleList.push({
  actionId: 'action.open_lines', backendIdentity: 'window_action:91', triggerType: 'click',
  sourceWidgetId: 'button.action_open_lines', targetIds: [], dispatchMode: 'clientRoute', targetScope: 'page',
  refreshMode: 'none', actionKey: 'open_lines', label: 'Open Lines', allowed: true, enabled: true,
  disabled: false, entitlementEvaluated: true,
  visibleProfiles: ['edit', 'readonly'], presentation: { tier: 'overflow' },
});
bodyActionSnapshot.statusContract.buttonStatus.push({ btnId: 'action.open_lines', visible: true, disabled: false });
const bodyActionModel = presentContractV2Form(createContractV2Store(bodyActionSnapshot), 'readonly');
const bodyActionNode = bodyActionModel.zones.primary[0].children.find((node) => node.nodeId === 'button.action_open_lines');
assert.equal(bodyActionNode?.action?.actionRef.backendIdentity, 'window_action:91');
assert.equal(canonicalNodeHasContent(bodyActionNode!), true);
assert.deepEqual(bodyActionModel.actionBar.map((action) => action.key), ['action_submit']);
const nativeBridge = buildCanonicalNativeFormBridge(bodyActionModel);
assert.deepEqual(
  resolveCanonicalNativeFieldSchemas([
    {
      key: 'field.is_favorite', name: 'is_favorite', label: 'Favorite', type: 'boolean', widget: 'boolean_favorite',
      required: false, readonly: false, inputValue: false,
    },
    {
      key: 'field.name', name: 'name', label: 'Name', type: 'char', required: true, readonly: true,
      inputValue: 'Canonical record title',
    },
  ]),
  [{
    key: 'field.name', name: 'name', label: 'Name', type: 'char', required: true, readonly: true,
    inputValue: 'Canonical record title',
    favoriteToggle: {
      name: 'is_favorite', label: 'Favorite', active: false, readonly: false, descriptor: undefined,
    },
  }],
  'canonical native title projection must decorate the textual title with favorite state instead of rendering the boolean as H1',
);
assert.deepEqual(
  nativeBridge.subordinateNodes.map((node) => node.type),
  ['notebook', 'container'],
  'canonical native bridge must keep notebook/attachment structure while collaboration stays in its governed panel',
);
const notebookPage = nativeBridge.subordinateNodes[0].children?.[0];
assert.equal(notebookPage?.type, 'page', 'a native notebook without explicit pages must retain its children in a stable default page');
assert.deepEqual(
  nativeBridge.fieldSchemasForNodes(notebookPage?.children || []).map((field) => [field.key, field.name]),
  [['field.line_ids', 'line_ids']],
  'canonical widget occurrence identity and record field name must remain separate through the native renderer bridge',
);
const bridgedBodyAction = nativeBridge.primaryNodes[0].children?.find((node) => node.type === 'button');
assert.equal(
  nativeBridge.actionForPayload(bridgedBodyAction?.action || {})?.backendIdentity,
  'window_action:91',
  'body action execution must resolve through the same canonical backend identity after native structure rendering',
);
assert.deepEqual(
  nativeBridge.actionStateForNode(bridgedBodyAction || {} as never),
  { disabled: false, title: '' },
  'canonical button status must remain authoritative when the native renderer asks for interaction state',
);

const duplicateBodyActionSnapshot = structuredClone(bodyActionSnapshot);
duplicateBodyActionSnapshot.layoutContract.containerTree[0].children.push(structuredClone(
  duplicateBodyActionSnapshot.layoutContract.containerTree[0].children.at(-1)!,
));
const duplicateBodyActionBridge = buildCanonicalNativeFormBridge(
  presentContractV2Form(createContractV2Store(duplicateBodyActionSnapshot), 'readonly'),
);
assert.equal(
  duplicateBodyActionBridge.primaryNodes[0].children?.filter((node) => node.type === 'button' && node.visible).length,
  1,
  'the canonical native bridge must render one visible body occurrence for one backend action identity',
);

const nativeOccurrenceActionSnapshot = structuredClone(snapshot());
nativeOccurrenceActionSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'button.native.submit', containerType: 'button', type: 'button', title: 'Submit Native', span: 24,
  action: { native_identity: { type: 'object', name: 'action_submit', native_locator: '/form/header/button[1]', occurrence_index: 1 } },
  children: [], widgetList: [],
});
nativeOccurrenceActionSnapshot.actionContract.actionRuleList[0].nativeIdentity = {
  type: 'object', name: 'action_submit', native_locator: '/form/header/button[1]', occurrence_index: 1,
};
const nativeOccurrenceModel = presentContractV2Form(createContractV2Store(nativeOccurrenceActionSnapshot), 'edit');
assert.equal(
  nativeOccurrenceModel.zones.primary[0].children.find((node) => node.nodeId === 'button.native.submit')?.action?.actionRef.backendIdentity,
  'button:object:action_submit',
  'native snake-case occurrence identity must resolve to the canonical action rule',
);
assert.equal(
  buildCanonicalNativeFormBridge(nativeOccurrenceModel).primaryNodes[0].children?.find((node) => node.type === 'button')?.visible,
  false,
  'an action already promoted to the canonical header must not remain visible as a duplicate native body occurrence',
);
assert.deepEqual(presentContractV2Form(store, 'edit'), model, 'presenter must be deterministic');

const editFloorplan = composeCanonicalFormFloorplan(model);
assert.deepEqual(editFloorplan.taskNodes.map((node) => node.nodeId), ['section.identity']);
assert.deepEqual(editFloorplan.contextNodes, []);
assert.deepEqual(
  editFloorplan.subordinateNodes.map((node) => node.nodeId),
  model.zones.subordinate.map((node) => node.nodeId),
  'floorplan composition must preserve subordinate node identity and order',
);
const readonlyFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(store, 'readonly'));
assert.deepEqual(
  readonlyFloorplan.taskNodes.map((node) => node.nodeId),
  ['section.identity'],
  'readonly pages must keep the canonical primary content in the main canvas',
);
assert.deepEqual(readonlyFloorplan.contextNodes, []);

const semanticReadonlySnapshot = snapshot();
semanticReadonlySnapshot.formStructureContract = governedFormStructure('context');
semanticReadonlySnapshot.formStructureContract.slots = [{
  slot: 'identity', title: 'Identity', role: 'context',
  groups: [{ name: 'identity', title: 'Identity', role: 'summary', fieldRefs: ['name', 'state'] }],
}];
semanticReadonlySnapshot.formStructureContract.fieldRoles = {
  name: { role: 'summary', slot: 'identity', group: 'identity' },
  state: { role: 'risk', slot: 'identity', group: 'identity' },
};
semanticReadonlySnapshot.layoutContract.containerTree[0].children[0].formStructureRole = {
  role: 'summary', slot: 'identity', group: 'identity',
};
semanticReadonlySnapshot.layoutContract.containerTree[0].children[1].widgetList[0].formStructureRole = {
  role: 'risk', slot: 'identity', group: 'identity',
};
semanticReadonlySnapshot.statusContract.widgetStatus[1] = {
  widgetId: 'field.state', visible: true, readonly: true, required: false, disabled: false,
};
const semanticReadonlyFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(semanticReadonlySnapshot),
  'readonly',
));
assert.deepEqual(
  collectFields(semanticReadonlyFloorplan.summaryNodes).map((field) => [field.fieldCode, field.semanticRole]),
  [['name', 'summary']],
  'readonly summary must be projected mechanically from the normalized field-node formStructureRole',
);
assert.deepEqual(
  collectFields(semanticReadonlyFloorplan.riskNodes).map((field) => [field.fieldCode, field.semanticRole]),
  [['state', 'risk']],
  'readonly risk facts must not fall back into the task canvas',
);
assert.deepEqual(semanticReadonlyFloorplan.taskNodes, []);
assert.deepEqual(semanticReadonlyFloorplan.contextNodes, []);
const semanticEditModel = presentContractV2Form(createContractV2Store(semanticReadonlySnapshot), 'edit');
const semanticEditNameNode = semanticEditModel.zones.primary[0].children.find((node) => (
  node.fields.some((field) => field.fieldCode === 'name')
));
assert.ok(semanticEditNameNode, 'semantic edit fixture must expose the editable name node');
const semanticEditNameField = semanticEditNameNode.fields.find((field) => field.fieldCode === 'name')!;
const relationMappedField = canonicalFieldToFormSection({
  ...semanticEditNameField,
  widgetId: 'field.project_id',
  fieldCode: 'project_id',
  fieldType: 'many2one',
  value: null,
  required: true,
  fieldDescriptor: {
    relation: 'project.project',
    relation_entry: {
      can_read: true,
      can_open: true,
      can_create: true,
      create_mode: 'page',
      action_id: 91,
      menu_id: 12,
      inline_create: { enabled: true, create_on_no_match: true, name_field: 'name' },
    },
  },
}, {
  relationKeyword: () => '演示项目',
  filteredRelationOptions: () => [{ id: 7, label: '演示项目' }],
  selectedRelationOptions: () => [],
  relationCreateMode: () => 'page',
  relationInlineCreate: () => ({ enabled: true, createOnNoMatch: true, nameField: 'name' }),
  relationCreateLabel: () => '新增并编辑',
  relationInlineCreateLabel: () => '快速创建“演示项目”',
  canOpenRelationRecord: () => true,
  relationOpenLabel: () => '维护当前项',
  relationSearchLabel: () => '搜索更多',
});
assert.equal(relationMappedField.many2oneTextValue, '演示项目');
assert.deepEqual(relationMappedField.relationOptions, [{ value: 7, label: '演示项目' }]);
assert.equal(relationMappedField.required, true, 'required many2one authority must survive canonical projection');
assert.equal(relationMappedField.relationCreateMode, 'page');
assert.equal(relationMappedField.many2oneCreateToken, MANY2ONE_CREATE_OPTION);
assert.equal(relationMappedField.many2oneSearchToken, MANY2ONE_SEARCH_MORE_OPTION);
assert.equal(relationMappedField.many2oneOpenToken, MANY2ONE_OPEN_RECORD_OPTION);
assert.equal(relationMappedField.many2oneCreateLabel, '新增并编辑');
assert.equal(relationMappedField.many2oneOpenLabel, '维护当前项');
assert.equal(relationMappedField.many2oneSearchLabel, '搜索更多');
assert.deepEqual(relationMappedField.relationInlineCreate, {
  enabled: true, createOnNoMatch: true, nameField: 'name',
});
semanticEditNameNode.fields.push({
  ...semanticEditNameField,
  widgetId: 'field.note',
  fieldCode: 'note',
  label: 'Note',
  value: null,
  required: false,
  semanticRole: 'context',
  semanticSlot: 'supplement',
  semanticGroup: 'notes',
});
const semanticEditFloorplan = composeCanonicalFormFloorplan(semanticEditModel);
assert.equal(semanticEditFloorplan.decisionMode, true, 'semantic create/edit forms must enter the Product Floorplan');
const nativeAuthoritySnapshot = snapshot();
nativeAuthoritySnapshot.formStructureContract = governedFormStructure('context');
nativeAuthoritySnapshot.formStructureContract!.mode = 'native_structured_form';
nativeAuthoritySnapshot.formStructureContract!.presentationMode = 'workspace';
nativeAuthoritySnapshot.formStructureContract!.layoutPolicy = 'native_authority';
nativeAuthoritySnapshot.layoutContract.containerTree[0].children[0].formStructureRole = {
  role: 'context', slot: 'governed', group: 'governed',
};
assert.equal(
  composeCanonicalFormFloorplan(presentContractV2Form(
    createContractV2Store(nativeAuthoritySnapshot), 'readonly',
  )).decisionMode,
  false,
  'native authority must fail closed even when layout nodes carry semantic roles',
);
const explicitTaskSnapshot = snapshot();
explicitTaskSnapshot.formStructureContract = governedFormStructure('context');
explicitTaskSnapshot.formStructureContract!.mode = 'native_structured_form';
explicitTaskSnapshot.formStructureContract!.presentationMode = 'task';
assert.equal(
  composeCanonicalFormFloorplan(presentContractV2Form(
    createContractV2Store(explicitTaskSnapshot), 'edit',
  )).decisionMode,
  true,
  'the explicit task form shape must win even when the legacy mode label is native',
);
const explicitWorkspaceSnapshot = snapshot();
explicitWorkspaceSnapshot.formStructureContract = governedFormStructure('context');
explicitWorkspaceSnapshot.formStructureContract!.presentationMode = 'workspace';
assert.equal(
  composeCanonicalFormFloorplan(presentContractV2Form(
    createContractV2Store(explicitWorkspaceSnapshot), 'edit',
  )).decisionMode,
  false,
  'the explicit workspace form shape must win even when semantic roles are present',
);
for (const renderMode of ['create', 'edit', 'readonly'] as const) {
  assert.equal(
    presentContractV2Form(createContractV2Store(explicitTaskSnapshot), renderMode).identity.presentationMode,
    'task',
    `task shape must remain explicit for ${renderMode}`,
  );
  assert.equal(
    composeCanonicalFormFloorplan(presentContractV2Form(
      createContractV2Store(explicitTaskSnapshot), renderMode,
    )).decisionMode,
    true,
    `task shape must enter the task Floorplan for ${renderMode}`,
  );
  assert.equal(
    composeCanonicalFormFloorplan(presentContractV2Form(
      createContractV2Store(explicitWorkspaceSnapshot), renderMode,
    )).decisionMode,
    false,
    `workspace shape must stay out of the task Floorplan for ${renderMode}`,
  );
}
assert.equal(
  semanticEditFloorplan.preExecutionInputTitle,
  '',
  'a later-stage section must not render a platform-authored business title without contract authority',
);
assert.deepEqual(
  collectFields(semanticEditFloorplan.summaryNodes).map((field) => field.fieldCode),
  [],
  'editable summary fields must stay in the editing canvas instead of duplicating as readonly facts',
);
assert.deepEqual(
  collectFields(semanticEditFloorplan.riskNodes).map((field) => field.fieldCode),
  ['state'],
  'readonly risk authority must remain factual in create/edit mode',
);
assert.deepEqual(
  collectFields(semanticEditFloorplan.coreInputNodes).map((field) => field.fieldCode),
  ['name'],
  'required editable fields must be directly reachable in the core-input region',
);
assert.deepEqual(
  collectFields(semanticEditFloorplan.supplementaryInputNodes).map((field) => field.fieldCode),
  ['note'],
  'empty optional fields must stay in supplementary input instead of being inferred as required',
);
assert.deepEqual(
  collectFields([
    ...semanticEditFloorplan.summaryNodes,
    ...semanticEditFloorplan.taskNodes,
    ...semanticEditFloorplan.riskNodes,
    ...semanticEditFloorplan.coreInputNodes,
    ...semanticEditFloorplan.conditionInputNodes,
    ...semanticEditFloorplan.preExecutionInputNodes,
    ...semanticEditFloorplan.supplementaryInputNodes,
    ...semanticEditFloorplan.contextNodes,
    ...semanticEditFloorplan.overflowContextNodes,
  ]).map((field) => field.fieldCode),
  ['state', 'name', 'note'],
  'create/edit Product Floorplan regions must not duplicate a field identity',
);

const businessFactSnapshot = structuredClone(semanticReadonlySnapshot);
businessFactSnapshot.formStructureContract!.fieldRoles.name = {
  role: 'context', slot: 'identity', group: 'identity',
};
const businessFactModel = presentContractV2Form(createContractV2Store(businessFactSnapshot), 'edit');
const businessFactField = collectFields(businessFactModel.zones.primary).find((field) => field.fieldCode === 'name');
assert.deepEqual(
  [businessFactField?.semanticRole, businessFactField?.semanticSlot, businessFactField?.semanticGroup],
  ['context', 'identity', 'identity'],
  'canonical context authority must survive Canonical projection as product context metadata',
);
const mixedSemanticTextModel = presentContractV2Form(createContractV2Store(semanticReadonlySnapshot), 'readonly');
const mixedSemanticTextRoot = mixedSemanticTextModel.zones.primary[0];
mixedSemanticTextRoot.text = 'unassigned native guidance';
const taskProjectionChild = mixedSemanticTextRoot.children.find((node) => node.semanticRole === 'summary')!;
taskProjectionChild.semanticRole = 'task';
taskProjectionChild.fields = taskProjectionChild.fields.map((field) => ({ ...field, semanticRole: 'task' }));
const mixedSemanticTextFloorplan = composeCanonicalFormFloorplan(mixedSemanticTextModel);
assert.deepEqual(
  collectTexts([...mixedSemanticTextFloorplan.taskNodes, ...mixedSemanticTextFloorplan.riskNodes]),
  [],
  'unassigned native text must not duplicate across semantic Floorplan projections',
);
const mixedRoleModel = presentContractV2Form(createContractV2Store(semanticReadonlySnapshot), 'readonly');
const mixedRoleParent = mixedRoleModel.zones.primary[0].children.find((node) => node.semanticRole === 'summary');
assert.ok(mixedRoleParent, 'semantic summary parent is required for mixed-role projection coverage');
const mixedRoleChild = structuredClone(mixedRoleParent);
mixedRoleChild.nodeId = `${mixedRoleParent.nodeId}.audit-override`;
mixedRoleChild.semanticRole = 'audit';
mixedRoleChild.fields = mixedRoleChild.fields.map((field) => ({
  ...field,
  widgetId: `${field.widgetId}.audit-override`,
  semanticRole: 'audit',
}));
mixedRoleChild.children = [];
mixedRoleParent.children.push(mixedRoleChild);
const mixedRoleFloorplan = composeCanonicalFormFloorplan(mixedRoleModel);
assert.equal(
  collectFields(mixedRoleFloorplan.summaryNodes).some((field) => field.widgetId.endsWith('.audit-override')),
  false,
  'a parent role must not absorb a descendant semantic override',
);
assert.equal(
  collectFields(mixedRoleFloorplan.auditNodes).some((field) => field.widgetId.endsWith('.audit-override')),
  true,
  'a descendant semantic override must project into its declared Floorplan region',
);
const repeatedSummaryModel = presentContractV2Form(createContractV2Store(semanticReadonlySnapshot), 'readonly');
const repeatedSummaryRoot = structuredClone(repeatedSummaryModel.zones.primary[0]);
repeatedSummaryRoot.nodeId = `${repeatedSummaryRoot.nodeId}.repeated-occurrence`;
repeatedSummaryModel.zones.primary.push(repeatedSummaryRoot);
assert.deepEqual(
  collectFields(composeCanonicalFormFloorplan(repeatedSummaryModel).summaryNodes).map((field) => field.fieldCode),
  ['name'],
  'product summary must project one fact per canonical field even when the native layout repeats an occurrence',
);

const semanticContextSnapshot = structuredClone(semanticReadonlySnapshot);
function addContextGroup(groupId: string, fieldCodes: string[]) {
  const children = fieldCodes.map((fieldCode) => ({
    containerId: `field.${fieldCode}`, containerType: 'field', type: 'field', name: fieldCode, title: '', span: 12,
    children: [], widgetList: [{
      widgetId: `field.${fieldCode}`, widgetType: 'char', fieldCode, label: fieldCode, span: 12,
      componentKey: 'sc.display.text', capabilities: [], componentConfig: {}, fieldType: 'char',
      ownerContainerId: `field.${fieldCode}`,
    }],
  }));
  semanticContextSnapshot.layoutContract.containerTree.splice(-3, 0, {
    containerId: groupId, containerType: 'group', type: 'group', title: groupId, span: 24,
    children, widgetList: [],
  });
  fieldCodes.forEach((fieldCode) => {
    semanticContextSnapshot.statusContract.widgetStatus.push({
      widgetId: `field.${fieldCode}`, visible: true, readonly: true, required: false, disabled: false,
    });
    semanticContextSnapshot.dataContract.mainData[fieldCode] = fieldCode;
  });
}
for (let index = 1; index <= 23; index += 1) addContextGroup(`context.group.${index}`, [`context_${index}`]);
addContextGroup('context.group.boundary', ['context_24', 'context_25']);
addContextGroup('context.group.trailing', ['context_26']);
addContextGroup('governed.audit.section', [
  'approval_fact', 'decision_note', 'source_reference', 'source_timestamp',
]);
semanticContextSnapshot.layoutContract.containerTree
  .find((node) => node.containerId === 'context.group.trailing')!
  .children[0].widgetList[0].formStructureRole = { role: 'relation' };
semanticContextSnapshot.layoutContract.containerTree
  .find((node) => node.containerId === 'governed.audit.section')!
  .formStructureRole = { role: 'audit' };
const semanticContextModel = presentContractV2Form(createContractV2Store(semanticContextSnapshot), 'readonly');
const semanticContextFloorplan = composeCanonicalFormFloorplan(semanticContextModel);
assert.deepEqual(
  collectFields(semanticContextFloorplan.contextNodes).map((field) => field.fieldCode),
  Array.from({ length: 23 }, (_, index) => `context_${index + 1}`),
  'default context must stop before a whole block would exceed the 24-fact limit',
);
assert.deepEqual(
  collectFields(semanticContextFloorplan.overflowContextNodes).map((field) => field.fieldCode),
  ['context_24', 'context_25'],
  'overflow must retain complete blocks and all subsequent context in original order',
);
assert.deepEqual(
  collectFields(semanticContextFloorplan.relationNodes).map((field) => field.fieldCode),
  ['context_26', 'line_ids'],
  'relation-capable canonical facts must form an independent relation region',
);
assert.deepEqual(
  collectFields(semanticContextFloorplan.auditNodes).map((field) => field.fieldCode),
  ['approval_fact', 'decision_note', 'source_reference', 'source_timestamp'],
  'a generic declared audit section must enter the audit region as a complete canonical block',
);
assert.equal(
  collectFields([...semanticContextFloorplan.contextNodes, ...semanticContextFloorplan.overflowContextNodes])
    .some((field) => ['approval_fact', 'decision_note', 'source_reference', 'source_timestamp'].includes(field.fieldCode)),
  false,
  'audit-section fields must not leak into ordinary context regions',
);
assert.deepEqual(
  semanticContextFloorplan.subordinateNodes.map((node) => node.kind),
  ['attachment', 'chatter'],
  'audit classification must not absorb relation, attachment, or chatter zones',
);
assert.equal(
  collectFields(semanticContextFloorplan.relationNodes).some((relationField) => (
    collectFields(semanticContextFloorplan.subordinateNodes)
      .some((subordinateField) => subordinateField.widgetId === relationField.widgetId)
  )),
  false,
  'relation and subordinate regions must not duplicate canonical widget identities',
);
const semanticAtomicFields = collectFields([
  ...semanticContextFloorplan.summaryNodes,
  ...semanticContextFloorplan.taskNodes,
  ...semanticContextFloorplan.riskNodes,
  ...semanticContextFloorplan.contextNodes,
  ...semanticContextFloorplan.overflowContextNodes,
  ...semanticContextFloorplan.auditNodes,
  ...semanticContextFloorplan.relationNodes,
  ...semanticContextFloorplan.subordinateNodes,
]);
assert.deepEqual(
  new Set(semanticAtomicFields.map((field) => field.widgetId)).size,
  semanticAtomicFields.length,
  'floorplan regions must not duplicate canonical widget identities',
);
assert.deepEqual(
  new Set(semanticAtomicFields.map((field) => field.widgetId)),
  new Set(collectFields([...semanticContextModel.zones.primary, ...semanticContextModel.zones.subordinate])
    .map((field) => field.widgetId)),
  'floorplan organization must preserve 100% of canonical atomic fields',
);

const createFloorplanSnapshot = snapshot();
createFloorplanSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'field.empty_context', containerType: 'field', type: 'field', name: 'empty_context', title: '', span: 12,
  children: [], widgetList: [{
    widgetId: 'field.empty_context', widgetType: 'char', fieldCode: 'empty_context', label: 'Empty context', span: 12,
    componentKey: 'sc.display.text', capabilities: [], componentConfig: {}, fieldType: 'char',
    ownerContainerId: 'field.empty_context',
  }],
});
createFloorplanSnapshot.statusContract.widgetStatus.push({
  widgetId: 'field.empty_context', visible: true, readonly: true, required: false, disabled: false,
});
createFloorplanSnapshot.dataContract.mainData.empty_context = false;
createFloorplanSnapshot.actionContract.actionRuleList = [{
  ...createFloorplanSnapshot.actionContract.actionRuleList[0],
  actionId: 'form.save', backendIdentity: 'contract_action:form.save', actionKey: 'form.save',
  visibleProfiles: ['create', 'edit'], presentation: { tier: 'secondary' },
}];
createFloorplanSnapshot.statusContract.buttonStatus = [{ btnId: 'form.save', visible: true, disabled: false }];
const createFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(createFloorplanSnapshot),
  'create',
));
assert.equal(
  collectFields(createFloorplan.taskNodes).some((field) => field.fieldCode === 'empty_context'),
  false,
  'create floorplan must not reserve a control for an empty readonly fact',
);
assert.equal(createFloorplan.effectivePrimaryKey, 'form.save', 'create save must occupy the effective primary slot');
assert.deepEqual(createFloorplan.directActions.map((action) => action.key), ['form.save']);
assert.deepEqual(createFloorplan.overflowActions, []);

const unresolvedCreateIdentitySnapshot = structuredClone(createFloorplanSnapshot);
unresolvedCreateIdentitySnapshot.dataContract.mainData.name = 'New';
unresolvedCreateIdentitySnapshot.statusContract.widgetStatus = unresolvedCreateIdentitySnapshot.statusContract.widgetStatus
  .map((status) => status.widgetId === 'field.name' ? { ...status, readonly: true, required: false } : status);
assert.equal(
  collectFields(composeCanonicalFormFloorplan(presentContractV2Form(
    createContractV2Store(unresolvedCreateIdentitySnapshot),
    'create',
  )).taskNodes).some((field) => field.fieldCode === 'name'),
  false,
  'create floorplan must not expose an unresolved platform identity placeholder',
);

const createBackendPrimarySnapshot = structuredClone(createFloorplanSnapshot);
createBackendPrimarySnapshot.actionContract.actionRuleList.push({
  ...createBackendPrimarySnapshot.actionContract.actionRuleList[0],
  actionId: 'action.submit', backendIdentity: 'button:object:action_submit', actionKey: 'action.submit',
  presentation: { tier: 'primary' },
}, {
  ...createBackendPrimarySnapshot.actionContract.actionRuleList[0],
  actionId: 'action.navigation', backendIdentity: 'window_action:91', actionKey: 'action.navigation',
  presentation: { tier: 'overflow' },
});
createBackendPrimarySnapshot.statusContract.buttonStatus.push({
  btnId: 'action.submit', visible: true, disabled: false,
}, {
  btnId: 'action.navigation', visible: true, disabled: false,
});
const createBackendPrimaryModel = presentContractV2Form(
  createContractV2Store(createBackendPrimarySnapshot),
  'create',
);
assert.deepEqual(
  createBackendPrimaryModel.actionBar.map((action) => action.key),
  ['form.save', 'action.submit', 'action.navigation'],
  'iteration one must preserve the cb6e276 canonical form action collection and order',
);
const createBackendPrimaryFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(createBackendPrimarySnapshot),
  'create',
));
assert.equal(
  createBackendPrimaryFloorplan.effectivePrimaryKey,
  'action.submit',
  'an enabled backend primary must always outrank the platform create-save fallback',
);
assert.deepEqual(createBackendPrimaryFloorplan.directActions.map((action) => action.key), ['action.submit']);
assert.deepEqual(createBackendPrimaryFloorplan.overflowActions.map((action) => action.key), ['form.save', 'action.navigation']);

const createBlockedPrimarySnapshot = structuredClone(createBackendPrimarySnapshot);
createBlockedPrimarySnapshot.statusContract.buttonStatus = [
  { btnId: 'form.save', visible: true, disabled: false },
  { btnId: 'action.submit', visible: true, disabled: true, reasonCode: 'ACTION_NOT_AVAILABLE_IN_STATE' },
  { btnId: 'action.navigation', visible: true, disabled: false },
];
const createBlockedPrimaryFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(createBlockedPrimarySnapshot),
  'create',
));
assert.equal(
  createBlockedPrimaryFloorplan.effectivePrimaryKey,
  '',
  'a disabled backend primary must block create-save promotion instead of failing open',
);
assert.deepEqual(createBlockedPrimaryFloorplan.directActions, []);
assert.deepEqual(createBlockedPrimaryFloorplan.blockedActions.map((action) => action.key), ['action.submit']);
assert.deepEqual(
  createBlockedPrimaryFloorplan.overflowActions.map((action) => action.key),
  ['form.save', 'action.navigation'],
  'blocked primary handling must not remove any other cb6e276 action',
);

const contextRailSnapshot = snapshot();
contextRailSnapshot.layoutContract.containerTree.splice(1, 0, {
  containerId: 'section.context', containerType: 'group', type: 'group', title: 'Context', span: 24,
  children: [{
    containerId: 'field.reference', containerType: 'field', type: 'field', name: 'reference', title: '', span: 24,
    children: [], widgetList: [{
      widgetId: 'field.reference', widgetType: 'char', fieldCode: 'reference', label: 'Reference', span: 24,
      componentKey: 'sc.display.text', capabilities: [], componentConfig: {}, fieldType: 'char',
      ownerContainerId: 'field.reference',
    }],
  }], widgetList: [],
});
contextRailSnapshot.statusContract.widgetStatus.push({
  widgetId: 'field.reference', visible: true, readonly: true, required: false, disabled: false,
});
contextRailSnapshot.dataContract.mainData.reference = 'REF-001';
const contextRailModel = presentContractV2Form(createContractV2Store(contextRailSnapshot), 'edit');
const contextRailFloorplan = composeCanonicalFormFloorplan(contextRailModel);
assert.deepEqual(contextRailFloorplan.taskNodes.map((node) => node.nodeId), ['section.identity']);
assert.deepEqual(contextRailFloorplan.contextNodes.map((node) => node.nodeId), ['section.context']);
assert.deepEqual(
  collectFields([...contextRailFloorplan.taskNodes, ...contextRailFloorplan.contextNodes]).map((field) => field.widgetId),
  collectFields(contextRailModel.zones.primary).map((field) => field.widgetId),
  'floorplan lanes must preserve the exact canonical field identity set and order within each lane',
);

const runtimeValueModel = presentContractV2Form(store, 'edit', { name: 'D-002' });
assert.equal(
  collectFields(runtimeValueModel.zones.primary).find((field) => field.fieldCode === 'name')?.value,
  'D-002',
  'runtime edits must update the ephemeral render model without changing normalized authority',
);

const relationSnapshot = snapshot();
relationSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'field.project_id', containerType: 'field', type: 'field', name: 'project_id', title: '', span: 12,
  children: [], widgetList: [{
    widgetId: 'field.project_id', widgetType: 'many2one', fieldCode: 'project_id', label: 'Project', span: 12,
    componentKey: 'sc.relation.many2one', capabilities: [],
    componentConfig: { relation: 'project.project' }, fieldType: 'many2one',
    ownerContainerId: 'field.project_id',
  }],
});
relationSnapshot.statusContract.widgetStatus.push({
  widgetId: 'field.project_id', visible: true, readonly: true, required: false, disabled: false,
});
relationSnapshot.dataContract.mainData.project_id = [852, 'Road Project'];
const relationModel = presentContractV2Form(createContractV2Store(relationSnapshot), 'readonly', { project_id: 852 });
const relationField = collectFields(relationModel.zones.primary).find((field) => field.fieldCode === 'project_id')!;
assert.deepEqual(
  relationField.value,
  { id: 852, displayName: 'Road Project', model: 'project.project' },
  'runtime scalar relation ids must retain the normalized business display identity',
);
const renderedRelation = canonicalFieldToFormSection(relationField);
assert.deepEqual(
  { value: renderedRelation.value, inputValue: renderedRelation.inputValue, text: renderedRelation.many2oneTextValue },
  { value: 'Road Project', inputValue: 852, text: 'Road Project' },
  'all drivers must receive the same relation display name instead of a naked database id',
);

const emptySnapshot = snapshot();
emptySnapshot.dataContract.mainData.name = false;
const emptyName = collectFields(presentContractV2Form(createContractV2Store(emptySnapshot), 'readonly').zones.primary)
  .find((field) => field.fieldCode === 'name');
assert.equal(emptyName?.value, null, 'non-boolean Odoo false values must normalize to one empty display fact');

const duplicateTitleSnapshot = snapshot();
duplicateTitleSnapshot.layoutContract.containerTree[1].title = 'Related';
duplicateTitleSnapshot.layoutContract.containerTree[1].children[0].title = 'Related';
const duplicateTitleModel = presentContractV2Form(createContractV2Store(duplicateTitleSnapshot), 'readonly');
assert.equal(
  duplicateTitleModel.zones.subordinate[0].children[0].title,
  '',
  'a nested subordinate node must not repeat the same visual title as its parent',
);

const readonlyModel = presentContractV2Form(store, 'readonly');
assert.equal(
  collectFields(readonlyModel.zones.primary).find((field) => field.fieldCode === 'name')?.readonly,
  true,
  'readonly route mode must remain authoritative even when the widget status is editable',
);

const rowActionSnapshot = snapshot();
rowActionSnapshot.actionContract.actionRuleList.push({
  ...rowActionSnapshot.actionContract.actionRuleList[0],
  actionId: 'action.open_form', backendIdentity: 'button:object:open_form', actionKey: 'open_form',
  sourceWidgetId: 'page.row', targetScope: 'runtime', presentation: { tier: 'secondary' },
});
rowActionSnapshot.statusContract.buttonStatus.push({ btnId: 'action.open_form', visible: true, disabled: false });
assert.deepEqual(
  presentContractV2Form(createContractV2Store(rowActionSnapshot), 'readonly').actionBar.map((action) => action.key),
  ['action_submit'],
  'row/runtime actions must remain normalized evidence and must not become form action-bar controls',
);

const readOnlyPrincipal = snapshot();
readOnlyPrincipal.statusContract.globalStatus.pageAuth = 'read';
const readOnlyPrincipalModel = presentContractV2Form(createContractV2Store(readOnlyPrincipal), 'edit');
assert.equal(
  collectFields(readOnlyPrincipalModel.zones.primary).find((field) => field.fieldCode === 'name')?.readonly,
  true,
  'page read authority must not become editable through the requested route mode',
);

const unresolvedWidgetStatus = snapshot();
unresolvedWidgetStatus.statusContract.widgetStatus = unresolvedWidgetStatus.statusContract.widgetStatus
  .filter((status) => status.widgetId !== 'field.name');
const unresolvedField = collectFields(
  presentContractV2Form(createContractV2Store(unresolvedWidgetStatus), 'edit').zones.primary,
).find((field) => field.fieldCode === 'name');
assert.deepEqual(
  { visible: unresolvedField?.visible, readonly: unresolvedField?.readonly, disabled: unresolvedField?.disabled, reasonCode: unresolvedField?.reasonCode },
  { visible: false, readonly: true, disabled: true, reasonCode: 'WIDGET_STATUS_UNRESOLVED' },
  'a field without normalized status authority must fail closed',
);

const hiddenContainer = snapshot();
hiddenContainer.statusContract.containerStatus = [{ containerId: 'section.identity', visible: false, disabled: false }];
const hiddenContainerFields = collectFields(presentContractV2Form(createContractV2Store(hiddenContainer), 'edit').zones.primary);
assert.equal(
  hiddenContainerFields.find((field) => field.fieldCode === 'name')?.visible,
  false,
  'container visibility must constrain descendant fields',
);

const disabledContainer = snapshot();
disabledContainer.statusContract.containerStatus = [{ containerId: 'section.identity', visible: true, disabled: true }];
const disabledContainerField = collectFields(
  presentContractV2Form(createContractV2Store(disabledContainer), 'edit').zones.primary,
).find((field) => field.fieldCode === 'name');
assert.deepEqual(
  { readonly: disabledContainerField?.readonly, disabled: disabledContainerField?.disabled },
  { readonly: true, disabled: true },
  'container disabled state must constrain descendant fields',
);

const productionNativeChildren = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
delete productionNativeChildren.layoutContract.containerTree[0].span;
const nativeChild = productionNativeChildren.layoutContract.containerTree[0].children[0] as Record<string, unknown>;
nativeChild.widgetId = 'field.name';
delete nativeChild.containerId;
delete nativeChild.containerType;
delete nativeChild.title;
delete nativeChild.span;
const normalizedNativeChild = decodeContractV2Snapshot(productionNativeChildren).layoutContract.containerTree[0].children[0];
assert.equal(decodeContractV2Snapshot(productionNativeChildren).layoutContract.containerTree[0].span, 24);
assert.equal(normalizedNativeChild.containerId, 'field.name');
assert.equal(normalizedNativeChild.containerType, 'field');
assert.equal(normalizedNativeChild.title, '', 'native identity must not become a visible title');
assert.equal(normalizedNativeChild.span, 24);

const anonymousNativeContainer = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
const anonymousGroup = anonymousNativeContainer.layoutContract.containerTree[0].children[0] as Record<string, unknown>;
anonymousGroup.containerId = 'container.native.0.children.0';
((anonymousGroup.widgetList as Array<Record<string, unknown>>)[0]).ownerContainerId = 'container.native.0.children.0';
anonymousGroup.containerType = 'group';
anonymousGroup.type = 'group';
delete anonymousGroup.title;
delete anonymousGroup.label;
delete anonymousGroup.string;
anonymousGroup.name = 'native_internal_group';
assert.equal(
  decodeContractV2Snapshot(anonymousNativeContainer).layoutContract.containerTree[0].children[0].title,
  '',
  'anonymous native container identity must remain non-visual',
);

const anonymousNativeRoot = snapshot();
anonymousNativeRoot.layoutContract.containerTree[0].title = '';
assert.equal(
  decodeContractV2Snapshot(anonymousNativeRoot).layoutContract.containerTree[0].title,
  '',
  'anonymous native root container must support an explicitly empty display title',
);

const mixedNativeContent = snapshot();
mixedNativeContent.layoutContract.containerTree[0].children.splice(1, 0, {
  containerId: 'text.native.identity.separator',
  containerType: 'text',
  type: 'text',
  title: '',
  text: '· 状态',
  span: 24,
  children: [],
  widgetList: [],
});
mixedNativeContent.statusContract.containerStatus.push({
  containerId: 'text.native.identity.separator', visible: true, disabled: false,
});
const mixedNativeModel = presentContractV2Form(createContractV2Store(mixedNativeContent), 'edit');
assert.deepEqual(
  mixedNativeModel.zones.primary[0].children.map((node) => [node.kind, node.text]),
  [['field', ''], ['text', '· 状态'], ['field', '']],
  'canonical presenter must preserve mixed native field/text order',
);

const aggregatedNativeChildren = snapshot();
aggregatedNativeChildren.layoutContract.containerTree[0].children[0].widgetList = [];
const aggregatedFields = collectFields(presentContractV2Form(createContractV2Store(aggregatedNativeChildren), 'edit').zones.primary);
assert.deepEqual(
  aggregatedFields.map((field) => field.fieldCode),
  ['state'],
  'normalized store must not synthesize a missing widget from a native field node',
);

const duplicateAcrossRoots = snapshot();
duplicateAcrossRoots.layoutContract.containerTree.splice(1, 0, {
  containerId: 'legacy.identity.mirror', containerType: 'group', type: 'group', title: 'Legacy mirror', span: 24,
  children: [], widgetList: [{
    widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', span: 12,
    componentKey: 'sc.input.text', capabilities: [], componentConfig: {}, fieldType: 'char',
    ownerContainerId: 'legacy.identity.mirror',
  }],
});
assert.throws(
  () => decodeContractV2Snapshot(duplicateAcrossRoots),
  /duplicate widget identity field.name/,
  'the decoder must reject duplicate widget ownership instead of relying on presenter de-duplication',
);

const duplicateOccurrences = snapshot();
const duplicateRoot = duplicateOccurrences.layoutContract.containerTree[0];
const duplicateBaseWidget = duplicateRoot.children[0].widgetList[0];
duplicateRoot.widgetList = [];
duplicateRoot.children = [
  {
    ...duplicateRoot.children[0],
    containerId: 'field.name.occ.first',
    fieldCode: 'name',
    widgetId: 'field.name.occ.first',
    nativeLocator: 'form/field[name=name][1]',
    occurrenceIndex: 1,
    sourcePosition: 1,
    widgetList: [{
      ...duplicateBaseWidget,
      widgetId: 'field.name.occ.first',
      ownerContainerId: 'field.name.occ.first',
      fieldDescriptor: { name: 'name', type: 'char' },
      componentConfig: {
        ...duplicateBaseWidget.componentConfig,
        native_locator: 'form/field[name=name][1]',
        occurrence_index: 1,
        source_position: 1,
      },
    }],
  },
  {
    ...duplicateRoot.children[0],
    containerId: 'field.name.occ.second',
    fieldCode: 'name',
    widgetId: 'field.name.occ.second',
    nativeLocator: 'form/field[name=name][2]',
    occurrenceIndex: 2,
    sourcePosition: 2,
    widgetList: [{
      ...duplicateBaseWidget,
      widgetId: 'field.name.occ.second',
      ownerContainerId: 'field.name.occ.second',
      fieldDescriptor: { name: 'name', type: 'char' },
      componentConfig: {
        ...duplicateBaseWidget.componentConfig,
        native_locator: 'form/field[name=name][2]',
        occurrence_index: 2,
        source_position: 2,
      },
    }],
  },
];
duplicateOccurrences.statusContract.widgetStatus = [
  { widgetId: 'field.name.occ.first', visible: true, readonly: true, required: false, disabled: false, auth: 'read' },
  { widgetId: 'field.name.occ.second', visible: true, readonly: false, required: true, disabled: false, auth: 'edit' },
];
const decodedDuplicateOccurrences = decodeContractV2Snapshot(duplicateOccurrences);
const duplicateOccurrenceStore = createContractV2Store(decodedDuplicateOccurrences);
assert.equal(duplicateOccurrenceStore.widgetsByFieldCodeAll.get('name')?.length, 2);
const duplicateOccurrenceFields = collectFields(
  presentContractV2Form(duplicateOccurrenceStore, 'edit').zones.primary,
);
assert.deepEqual(
  duplicateOccurrenceFields.map((field) => [field.widgetId, field.readonly, field.required]),
  [
    ['field.name.occ.first', true, false],
    ['field.name.occ.second', false, true],
  ],
  'canonical form must preserve same-field occurrences and their independent status',
);
const equivalentCreateOccurrences = structuredClone(duplicateOccurrences);
equivalentCreateOccurrences.statusContract.widgetStatus = [
  { widgetId: 'field.name.occ.first', visible: true, readonly: false, required: true, disabled: false, auth: 'edit' },
  { widgetId: 'field.name.occ.second', visible: true, readonly: false, required: true, disabled: false, auth: 'edit' },
];
assert.deepEqual(
  collectFields(composeCanonicalFormFloorplan(presentContractV2Form(
    createContractV2Store(decodeContractV2Snapshot(equivalentCreateOccurrences)),
    'create',
  )).taskNodes).map((field) => field.widgetId),
  ['field.name.occ.second'],
  'create floorplan must merge equivalent occurrences while preserving the retained canonical identity',
);

const duplicateOccurrenceStatus = snapshot();
const duplicateStatusRoot = duplicateOccurrenceStatus.layoutContract.containerTree[0];
duplicateStatusRoot.widgetList = [];
duplicateStatusRoot.children = [
  { ...duplicateStatusRoot.children[0], widgetId: 'field.name.occ.same', nativeLocator: 'form/field[name=name][1]', occurrenceIndex: 1, sourcePosition: 1, widgetList: [] },
  { ...duplicateStatusRoot.children[0], widgetId: 'field.name.occ.same', nativeLocator: 'form/field[name=name][2]', occurrenceIndex: 2, sourcePosition: 2, widgetList: [] },
];
duplicateOccurrenceStatus.statusContract.widgetStatus = [
  { widgetId: 'field.name.occ.same', visible: true, readonly: false, required: false, disabled: false },
];
assert.throws(() => decodeContractV2Snapshot(duplicateOccurrenceStatus), /duplicate form occurrence widgetId/);

const missingOccurrenceStatus = snapshot();
const missingStatusRoot = missingOccurrenceStatus.layoutContract.containerTree[0];
missingStatusRoot.widgetList = [];
missingStatusRoot.children = [{ ...missingStatusRoot.children[0], widgetId: 'field.name.occ.missing', nativeLocator: 'form/field[name=name]', occurrenceIndex: 1, sourcePosition: 1, widgetList: [] }];
missingOccurrenceStatus.statusContract.widgetStatus = [];
assert.throws(() => decodeContractV2Snapshot(missingOccurrenceStatus), /requires exactly one status/);

const orphanOccurrenceStatus = snapshot();
orphanOccurrenceStatus.statusContract.widgetStatus.push({ widgetId: 'field.name.occ.orphan', visible: true, readonly: false, required: false, disabled: false });
assert.throws(() => decodeContractV2Snapshot(orphanOccurrenceStatus), /orphan form widget status/);

const renderedName = canonicalFieldToFormSection(fields.find((field) => field.fieldCode === 'name')!);
assert.deepEqual(
  { key: renderedName.key, name: renderedName.name, value: renderedName.value, readonly: renderedName.readonly },
  { key: 'field.name', name: 'name', value: 'D-001', readonly: false },
  'renderer mapping must preserve canonical widget identity and state without native layout input',
);
assert.equal(canonicalNodeHasContent(model.zones.subordinate.find((node) => node.kind === 'chatter')!), true);
assert.deepEqual(
  canonicalSectionFields(model.zones.primary[0]).map((field) => field.fieldCode),
  [],
  'a parent must not hoist fields out of native child-node order',
);
assert.equal(
  visibleCanonicalChildren(model.zones.primary[0]).some((node) => node.kind === 'field'),
  true,
  'leaf field nodes must remain in native child-node order',
);

const invalidNativeChild = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
invalidNativeChild.layoutContract.containerTree[0].children = [{ children: [], widgetList: [] }];
assert.throws(() => decodeContractV2Snapshot(invalidNativeChild), /requires a stable native identity/);

const invalidExplicitSpan = snapshot();
invalidExplicitSpan.layoutContract.containerTree[0].span = 0;
assert.throws(() => decodeContractV2Snapshot(invalidExplicitSpan), /span must be an integer between 1 and 24/);

const missingIdentity = snapshot();
delete missingIdentity.actionContract.actionRuleList[0].backendIdentity;
assert.throws(() => presentContractV2Form(createContractV2Store(missingIdentity), 'edit'), /ACTION_REFERENCE_MISSING/);

const missingEntitlement = snapshot();
delete missingEntitlement.actionContract.actionRuleList[0].entitlementEvaluated;
assert.deepEqual(
  presentContractV2Form(createContractV2Store(missingEntitlement), 'edit').actionBar,
  [],
  'an action without explicit entitlement authority must not enter the canonical action bar',
);

const missingCanonicalButtonStatus = snapshot();
missingCanonicalButtonStatus.statusContract.buttonStatus = [];
assert.deepEqual(
  presentContractV2Form(createContractV2Store(missingCanonicalButtonStatus), 'edit').actionBar,
  [],
  'an action without a matching explicit button status must not enter the canonical action bar',
);

const ambiguousCanonicalIdentity = snapshot();
ambiguousCanonicalIdentity.actionContract.actionRuleList.push({
  ...ambiguousCanonicalIdentity.actionContract.actionRuleList[0],
  actionId: 'action.submit.alias', actionKey: 'action_submit_alias',
});
ambiguousCanonicalIdentity.statusContract.buttonStatus.push({
  btnId: 'action.submit.alias', visible: true, disabled: false,
});
assert.deepEqual(
  presentContractV2Form(createContractV2Store(ambiguousCanonicalIdentity), 'edit').actionBar,
  [],
  'an ambiguous backend identity must fail closed before canonical action placement',
);

const mismatchedCanonicalStatus = snapshot();
mismatchedCanonicalStatus.statusContract.buttonStatus[0].backendIdentity = 'button:object:another_action';
assert.deepEqual(
  presentContractV2Form(createContractV2Store(mismatchedCanonicalStatus), 'edit').actionBar,
  [],
  'a mismatched status identity must fail closed before canonical action placement',
);

const mergedWinnerStatusByIdentity = snapshot();
mergedWinnerStatusByIdentity.actionContract.actionRuleList[0].actionId = 'action.runtime_submit_winner';
mergedWinnerStatusByIdentity.actionContract.actionRuleList[0].actionKey = 'runtime_submit_winner';
mergedWinnerStatusByIdentity.statusContract.buttonStatus = [{
  btnId: 'btn.native_submit_occurrence',
  backendIdentity: 'button:object:action_submit',
  visible: true,
  disabled: false,
}];
assert.deepEqual(
  presentContractV2Form(createContractV2Store(mergedWinnerStatusByIdentity), 'edit').actionBar.map((action) => action.key),
  ['runtime_submit_winner'],
  'a merged action winner must join authoritative status by backend identity, not an incidental source key',
);

const ambiguousStatusIdentity = structuredClone(mergedWinnerStatusByIdentity);
ambiguousStatusIdentity.statusContract.buttonStatus.push({
  btnId: 'btn.duplicate_submit_status',
  backendIdentity: 'button:object:action_submit',
  visible: true,
  disabled: false,
});
assert.deepEqual(
  presentContractV2Form(createContractV2Store(ambiguousStatusIdentity), 'edit').actionBar,
  [],
  'duplicate status rows for one backend identity must fail closed',
);

const disabledSecondaryPrimary = snapshot();
disabledSecondaryPrimary.actionContract.actionRuleList.push({
  ...disabledSecondaryPrimary.actionContract.actionRuleList[0],
  actionId: 'action.blocked', backendIdentity: 'button:object:action_blocked', actionKey: 'action_blocked',
  enabled: true, disabled: false,
});
disabledSecondaryPrimary.statusContract.buttonStatus.push({
  btnId: 'btn.action_blocked', visible: true, disabled: true, reasonCode: 'ACTION_NOT_AVAILABLE_IN_STATE',
});
const disabledSecondaryPrimaryModel = presentContractV2Form(
  createContractV2Store(disabledSecondaryPrimary),
  'edit',
);
assert.equal(
  disabledSecondaryPrimaryModel.actionBar.filter((action) => action.visible && action.enabled && action.tier === 'primary').length,
  1,
  'a visible disabled primary must not compete with the one effective primary action',
);
assert.deepEqual(
  disabledSecondaryPrimaryModel.actionBar.find((action) => action.key === 'action_blocked'),
  {
    key: 'action_blocked', label: 'Submit', tier: 'primary', visible: true, enabled: false,
    icon: 'fa-check',
    reasonCode: 'ACTION_NOT_AVAILABLE_IN_STATE', visibleProfiles: ['edit', 'readonly'],
    safety: { level: 'danger', requiresConfirmation: true },
    actionRef: disabledSecondaryPrimary.actionContract.actionRuleList[1],
  },
  'disabled action evidence must remain visible and fail closed',
);
assert.deepEqual(
  composeCanonicalFormFloorplan(disabledSecondaryPrimaryModel).blockedActions.map((action) => action.key),
  ['action_blocked'],
  'a blocked canonical primary must remain explicit floorplan evidence',
);

const duplicatePrimary = snapshot();
duplicatePrimary.actionContract.actionRuleList.push({
  ...duplicatePrimary.actionContract.actionRuleList[0],
  actionId: 'action.other', backendIdentity: 'button:object:action_other', actionKey: 'action_other',
});
duplicatePrimary.statusContract.buttonStatus.push({ btnId: 'action.other', visible: true, disabled: false });
assert.throws(() => presentContractV2Form(createContractV2Store(duplicatePrimary), 'edit'), /MULTIPLE_PRIMARY_ACTIONS/);

const resolvedDuplicateSubmit = snapshot();
resolvedDuplicateSubmit.actionContract.actionRuleList[0] = {
  ...resolvedDuplicateSubmit.actionContract.actionRuleList[0],
  actionId: 'action.native_submit',
  actionKey: 'native_submit',
  backendIdentity: 'native_button:object:action_submit:/form[1]/header[1]/button[1]:1',
  sourceWidgetId: 'page.header',
  button: { name: 'action_submit', type: 'object' },
  presentationPriority: 100,
};
resolvedDuplicateSubmit.actionContract.actionRuleList.push({
  ...resolvedDuplicateSubmit.actionContract.actionRuleList[0],
  actionId: 'action.weak_submit',
  actionKey: 'weak_submit',
  backendIdentity: 'button:object:action_submit',
  sourceWidgetId: 'page.root',
  presentationPriority: 250,
  presentation: { tier: 'secondary' },
});
resolvedDuplicateSubmit.actionContract.primaryResolution = {
  policy: 'single_effective_primary_per_record_state',
  winner: 'native_button:object:action_submit:/form[1]/header[1]/button[1]:1',
  demoted: [{
    actionId: 'action.weak_submit',
    backendIdentity: 'button:object:action_submit',
    previousTier: 'primary',
    effectiveTier: 'secondary',
  }],
};
resolvedDuplicateSubmit.statusContract.buttonStatus = [
  {
    btnId: 'btn.native_submit', visible: true, disabled: false,
    backendIdentity: 'native_button:object:action_submit:/form[1]/header[1]/button[1]:1',
  },
  {
    btnId: 'btn.weak_submit', visible: true, disabled: false,
    backendIdentity: 'button:object:action_submit',
  },
];
const decodedResolvedDuplicateSubmit = decodeContractV2Snapshot(resolvedDuplicateSubmit);
assert.deepEqual(
  decodedResolvedDuplicateSubmit.actionContract.primaryResolution,
  resolvedDuplicateSubmit.actionContract.primaryResolution,
  'the normalized store must retain the backend primary-action verdict',
);
assert.deepEqual(
  presentContractV2Form(createContractV2Store(decodedResolvedDuplicateSubmit), 'readonly')
    .actionBar.map((action) => action.actionRef.actionId),
  ['action.native_submit'],
  'a backend-demoted duplicate must not become a second product action',
);

const prioritizedDuplicateAction = snapshot();
prioritizedDuplicateAction.actionContract.actionRuleList[0] = {
  ...prioritizedDuplicateAction.actionContract.actionRuleList[0],
  actionId: 'action.native_cancel', actionKey: 'native_cancel',
  backendIdentity: 'native_button:object:action_cancel:/form/header/button[1]:1',
  sourceWidgetId: 'page.header', button: { name: 'action_cancel', type: 'object' },
  presentationPriority: 100, presentationAuthority: 'native_contract',
  presentation: { tier: 'overflow' },
};
prioritizedDuplicateAction.actionContract.actionRuleList.push({
  ...prioritizedDuplicateAction.actionContract.actionRuleList[0],
  actionId: 'action.product_cancel', actionKey: 'product_cancel',
  backendIdentity: 'button:object:action_cancel', sourceWidgetId: 'page.root',
  presentationPriority: 250, presentationAuthority: 'product_contract',
  presentation: { tier: 'secondary' },
});
prioritizedDuplicateAction.statusContract.buttonStatus = [
  { btnId: 'action.native_cancel', visible: true, disabled: false },
  { btnId: 'action.product_cancel', visible: true, disabled: false },
];
assert.deepEqual(
  presentContractV2Form(createContractV2Store(prioritizedDuplicateAction), 'readonly')
    .actionBar.map((action) => action.actionRef.actionId),
  ['action.product_cancel'],
  'the highest backend presentation priority must own one duplicated execution identity',
);

const normalizedAction = snapshot().actionContract.actionRuleList[0];
assert.deepEqual(
  contractActionConfirmationPrompt({
    key: 'action_submit', label: 'Submit', hint: '',
    actionSafety: {
      classification: 'danger', requiresConfirm: true,
      confirmMessage: 'Submit this document?', reasonCode: 'NATIVE_BUTTON_DANGEROUS_ACTION',
    },
  } as never),
  { actionLabel: 'Submit', message: 'Submit this document?' },
  'native confirm message must reach the confirmation interaction unchanged',
);
assert.equal(
  contractActionConfirmationPrompt({
    key: 'action_help', label: 'Help', hint: 'Descriptive help only',
  } as never),
  null,
  'button help must never manufacture a confirmation prompt',
);
const readonlySaveSnapshot = snapshot();
readonlySaveSnapshot.actionContract.actionRuleList = [{
  ...readonlySaveSnapshot.actionContract.actionRuleList[0],
  actionId: 'form.save', backendIdentity: 'contract_action:form.save',
  visibleProfiles: ['create', 'edit', 'readonly'],
}];
readonlySaveSnapshot.statusContract.buttonStatus = [{ btnId: 'form.save', visible: true, disabled: false }];
assert.deepEqual(
  presentContractV2Form(createContractV2Store(readonlySaveSnapshot), 'readonly').actionBar,
  [],
  'iteration one must retain the cb6e276 readonly save suppression behavior',
);
assert.equal(
  presentContractV2Form(createContractV2Store(readonlySaveSnapshot), 'edit').actionBar[0]?.visible,
  true,
  'the same normalized save action remains available in edit mode',
);

const contractAction = {
  key: 'action_submit', backendIdentity: 'button:object:action_submit', label: 'Submit', kind: 'object',
  level: 'header', selection: 'none', actionId: null, methodName: 'action_submit', targetModel: 'x.document',
  context: {}, domainRaw: '', target: '', url: '', enabled: true, hint: '', intent: '', semantic: '',
  sourceWidgetId: 'page.root', clientMode: '', visibleProfiles: ['edit', 'readonly'], requiredParams: [], requiresReason: false,
} satisfies ContractAction;
const occurrenceIdentity = {
  type: 'object', name: 'action_submit', native_locator: '/form/header/button[1]', occurrence_index: 1,
};
const occurrenceAction = {
  ...contractAction,
  authorityActionId: 'action.submit',
  nativeIdentity: occurrenceIdentity,
};
const mergedWinner = {
  ...snapshot().actionContract.actionRuleList[0],
  actionId: 'action.product_submit',
  actionKey: 'product_action_submit',
  button: { name: 'action_submit', type: 'object' },
};
const mergedWinnerStatus = {
  btnId: 'native_action_submit', visible: true, disabled: false,
  backendIdentity: 'button:object:action_submit',
};
const runtimeActions = buildContractFormActions({
  model: 'x.document', recordId: 7, renderProfile: 'edit', sceneReadyActions: [],
  v2ButtonStatus: { native_action_submit: mergedWinnerStatus },
  v2ActionRuleList: [mergedWinner],
});
assert.deepEqual(
  runtimeActions.map((action) => action.authorityActionId),
  ['action.product_submit'],
  'runtime action projection must join merged winners to status by backend identity',
);
assert.deepEqual(
  buildContractFormActions({
    model: 'x.document', recordId: 7, renderProfile: 'edit', sceneReadyActions: [],
    v2ButtonStatus: {
      first: mergedWinnerStatus,
      second: { ...mergedWinnerStatus, btnId: 'duplicate_action_submit' },
    },
    v2ActionRuleList: [mergedWinner],
  }),
  [],
  'ambiguous status authority for one backend identity must fail closed',
);
assert.equal(
  resolveContractActionForNativeOccurrence([occurrenceAction], {
    action: { backendIdentity: 'button:object:action_submit' },
  }),
  occurrenceAction,
  'native rendering must resolve the already-authorized action by exact backend identity',
);
assert.equal(
  resolveContractActionForNativeOccurrence([occurrenceAction, { ...occurrenceAction }], {
    action: { backendIdentity: 'button:object:action_submit' },
  }),
  null,
  'ambiguous backend identity must fail closed',
);
assert.equal(
  resolveContractActionForNativeOccurrence([occurrenceAction], {
    action: { actionId: 'action.submit' },
  }),
  occurrenceAction,
  'native rendering may resolve the exact normalized action identity',
);
assert.equal(
  resolveContractActionForNativeOccurrence([occurrenceAction], {
    action: { nativeIdentity: occurrenceIdentity },
  }),
  occurrenceAction,
  'native rendering may resolve the exact effective-view occurrence identity',
);
assert.equal(
  resolveContractActionForNativeOccurrence([occurrenceAction], {
    action: { name: 'action_submit', label: 'Submit' },
  }),
  null,
  'method names and labels must never reconstruct executable authority',
);
assert.deepEqual(
  resolveCanonicalFormActionExecution(
    { ...normalizedAction, actionId: 'form.save', backendIdentity: 'contract_action:form.save' },
    [],
  ),
  { kind: 'save' },
  'standard normalized form.save must use the existing unified save executor',
);
assert.deepEqual(
  resolveCanonicalFormActionExecution(normalizedAction, [contractAction]),
  { kind: 'contract-action', action: contractAction },
  'business actions must resolve only by their normalized backend identity',
);
assert.deepEqual(
  resolveCanonicalFormActionExecution(normalizedAction, []),
  { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING' },
  'an unmapped normalized action must fail closed',
);
assert.deepEqual(
  resolveCanonicalFormActionExecution(normalizedAction, [contractAction, { ...contractAction }]),
  { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_REFERENCE_AMBIGUOUS' },
  'a duplicated normalized backend identity must fail closed',
);
assert.equal(
  validateCanonicalFormActionExecutors([
    { visible: true, enabled: true, actionRef: { ...normalizedAction, actionId: 'form.save', backendIdentity: 'contract_action:form.save' } },
    { visible: true, enabled: false, actionRef: { ...normalizedAction, enabled: true, disabled: false, backendIdentity: 'button:object:unmapped_disabled' } },
  ], []),
  null,
  'save and visible disabled actions keep the canonical page usable without inventing an executor',
);
assert.deepEqual(
  validateCanonicalFormActionExecutors([{ visible: true, enabled: true, actionRef: normalizedAction }], []),
  {
    reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING',
    actionId: 'action.submit',
    backendIdentity: 'button:object:action_submit',
  },
  'an executable action without an exact unified executor adapter must block canonical cutover',
);

assert.deepEqual(
  collectCanonicalFormActions(bodyActionModel).map((action) => action.actionRef.backendIdentity),
  ['button:object:action_submit', 'window_action:91'],
  'body-node actions must join actionBar actions in exact executor validation',
);
assert.deepEqual(
  validateCanonicalFormActionExecutors(collectCanonicalFormActions(bodyActionModel), [contractAction]),
  {
    reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING',
    actionId: 'action.open_lines',
    backendIdentity: 'window_action:91',
  },
  'an executable body-node action without an adapter must fail closed',
);

console.log('[canonical_form_presenter_test] PASS cases=140');
