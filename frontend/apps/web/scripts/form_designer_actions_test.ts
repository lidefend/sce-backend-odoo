import assert from 'node:assert/strict';
import { ref } from 'vue';
import { useRecordFormDesignerActions, type FormDesignerActionDependencies } from '../src/pages/contractForm/useRecordFormDesignerActions';
import { resolveNativeContractActionState } from '../src/pages/contractForm/contractActionPresentation';
import type { FormSectionFieldSchema } from '../src/components/template/formSection.types';
import type { ContractAction } from '../src/pages/contractForm/types';

const moves: unknown[] = [];
const operations: unknown[] = [];
const deps: FormDesignerActionDependencies = {
  activeContractModeFieldRows: ref([{ fieldKey: 'name', actions: [{ checked: true, value: 'hide' }] }]),
  appendFormConfigOperation: (...args) => { operations.push(args); },
  contractModeFeedback: ref(''), currentFormDesignFieldKeys: ref(['name']),
  currentFormOrderedFieldKeys: ref(['name']), draggingFieldLabel: ref(''),
  effectiveFieldGroupTitleForDraft: () => 'Main', fieldGroupTitleMatches: (a, b) => a === b,
  fieldOrderDraft: ref(['name']), fieldVisibilityBase: ref({}), fieldVisibilityDirtyKeys: {},
  fieldVisibilityDraft: {}, formConfigAuditResult: ref(null), formDesignFieldLabel: (key) => key,
  formDesignerGroupNavigatorItems: ref([{ title: 'Main', fieldKeys: ['name'] }]),
  formSettingsActiveTab: ref(''), isContractFieldOrderEditable: ref(false),
  moveFieldOrder: (...args) => { moves.push(args); }, normalizeFieldGroupTitle: (value) => value.trim(),
  onContractInlineGroupRename: async () => {}, onFieldOrderDragEnd: () => {},
  onFieldOrderDragLeave: () => {}, onFieldOrderDragOver: () => {}, onFieldOrderDragStart: () => {},
  onFieldOrderDrop: (...args) => { moves.push(args); }, onFieldOrderGroupDrop: () => {},
  reload: async () => {}, rememberFormConfigFieldLabel: () => {}, runContractRuleAction: async () => {},
  selectedFormSettingsFieldGroupTitle: ref('Main'), selectedFormSettingsFieldGroupTitleDraft: ref(''),
  selectedFormSettingsFieldGroupTitleEdit: ref(''), selectedFormSettingsFieldKey: ref(''),
  selectedFormSettingsFieldLabel: ref(''), selectedFormSettingsFieldRow: ref(null), setInlineFieldPolicy: async () => {},
};
const actions = useRecordFormDesignerActions(deps);
const field = { name: 'name', key: 'name', label: 'Name' } as FormSectionFieldSchema;
actions.onFormSettingsFieldSelect({ field, groupTitle: 'Main' });
assert.equal(deps.selectedFormSettingsFieldKey.value, '', 'denied selection cannot enter configuration');
assert.deepEqual(deps.fieldVisibilityDraft, {});
(deps.isContractFieldOrderEditable as { value: boolean }).value = true;
actions.onFormSettingsFieldSelect({ field, groupTitle: 'Main' });
assert.equal(deps.fieldVisibilityDraft.name, false, 'selection preserves declared hidden baseline');
assert.equal(deps.selectedFormSettingsFieldKey.value, 'name', 'live enabled ref is consumed');
await actions.onContractFieldAction({ field, action: { value: 'show' } } as Parameters<typeof actions.onContractFieldAction>[0]);
assert.equal(deps.fieldVisibilityDraft.name, true);
assert.equal(deps.fieldVisibilityDirtyKeys.name, true);
assert.equal(operations.length, 1, 'one shared audit operation');
actions.onContractInlineFieldOrderDrop({ field, groupTitle: 'Other', placement: 'after' });
assert.deepEqual(moves, [['name', 'Other', 'after']], 'drop preserves field, group and placement');
assert.deepEqual(resolveNativeContractActionState(null, false), {}, 'unknown action never gains availability');
const action = { enabled: true, hint: 'Ready' } as ContractAction;
assert.deepEqual(resolveNativeContractActionState(action, true), { disabled: true, title: 'Ready' });
assert.deepEqual(resolveNativeContractActionState({ ...action, enabled: false }, false), { disabled: true, title: 'Ready' });
console.log('form_designer_actions_test PASS cases=6');
