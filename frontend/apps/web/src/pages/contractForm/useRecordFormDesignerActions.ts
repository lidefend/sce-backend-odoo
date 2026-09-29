import type { Ref } from 'vue';
import type { FormSectionFieldActionPayload, FormSectionFieldSchema } from '../../components/template/formSection.types';
import type { FormConfigAuditResult } from './types';

export interface FormDesignerActionDependencies {
  activeContractModeFieldRows: Readonly<Ref<Array<{ fieldKey: string; actions: Array<{ checked?: boolean; value?: string }> }>>>;
  appendFormConfigOperation: (action: string, summary: string) => void;
  contractModeFeedback: Ref<string>;
  currentFormDesignFieldKeys: Readonly<Ref<string[]>>;
  currentFormOrderedFieldKeys: Readonly<Ref<string[]>>;
  draggingFieldLabel: Ref<string>;
  effectiveFieldGroupTitleForDraft: (key: string) => string;
  fieldGroupTitleMatches: (left: string, right: string) => boolean;
  fieldOrderDraft: Readonly<Ref<string[]>>;
  fieldVisibilityBase: Ref<Record<string, boolean>>;
  fieldVisibilityDirtyKeys: Record<string, boolean>;
  fieldVisibilityDraft: Record<string, boolean>;
  formConfigAuditResult: Ref<FormConfigAuditResult | null>;
  formDesignFieldLabel: (key: string) => string;
  formDesignerGroupNavigatorItems: Readonly<Ref<Array<{ title: string; fieldKeys: string[] }>>>;
  formSettingsActiveTab: Ref<string>;
  isContractFieldOrderEditable: Readonly<Ref<boolean>>;
  moveFieldOrder: (key: string, delta: number) => void;
  normalizeFieldGroupTitle: (key: string) => string;
  onContractInlineGroupRename: (payload: { oldTitle: string; newTitle: string }) => Promise<unknown>;
  onFieldOrderDragEnd: () => void;
  onFieldOrderDragLeave: (key: string) => void;
  onFieldOrderDragOver: (key: string, placement?: 'before' | 'after' | '') => void;
  onFieldOrderDragStart: (key: string, event: DragEvent) => void;
  onFieldOrderDrop: (key: string, group?: string, placement?: 'before' | 'after' | '') => void;
  onFieldOrderGroupDrop: (group: string) => void;
  reload: () => Promise<unknown>;
  rememberFormConfigFieldLabel: (key: string, label: string) => void;
  runContractRuleAction: (raw: NonNullable<FormSectionFieldActionPayload['action']['raw']>) => Promise<unknown>;
  selectedFormSettingsFieldGroupTitle: Readonly<Ref<string>>;
  selectedFormSettingsFieldGroupTitleDraft: Ref<string>;
  selectedFormSettingsFieldGroupTitleEdit: Ref<string>;
  selectedFormSettingsFieldKey: Ref<string>;
  selectedFormSettingsFieldLabel: Ref<string>;
  selectedFormSettingsFieldRow: Readonly<Ref<{ label?: string } | null | undefined>>;
  setInlineFieldPolicy: (key: string, policy: Record<string, unknown>) => Promise<unknown>;
}

/** Field selection, visibility and ordering interactions share the existing designer state. */
export function useRecordFormDesignerActions(dependencies: FormDesignerActionDependencies) {
  const {
    activeContractModeFieldRows,
    appendFormConfigOperation,
    contractModeFeedback,
    currentFormDesignFieldKeys,
    currentFormOrderedFieldKeys,
    draggingFieldLabel,
    effectiveFieldGroupTitleForDraft,
    fieldGroupTitleMatches,
    fieldOrderDraft,
    fieldVisibilityBase,
    fieldVisibilityDirtyKeys,
    fieldVisibilityDraft,
    formConfigAuditResult,
    formDesignFieldLabel,
    formDesignerGroupNavigatorItems,
    formSettingsActiveTab,
    isContractFieldOrderEditable,
    moveFieldOrder,
    normalizeFieldGroupTitle,
    onContractInlineGroupRename,
    onFieldOrderDragEnd,
    onFieldOrderDragLeave,
    onFieldOrderDragOver,
    onFieldOrderDragStart,
    onFieldOrderDrop,
    onFieldOrderGroupDrop,
    reload,
    rememberFormConfigFieldLabel,
    runContractRuleAction,
    selectedFormSettingsFieldGroupTitle,
    selectedFormSettingsFieldGroupTitleDraft,
    selectedFormSettingsFieldGroupTitleEdit,
    selectedFormSettingsFieldKey,
    selectedFormSettingsFieldLabel,
    selectedFormSettingsFieldRow,
    setInlineFieldPolicy,
  } = dependencies;

  async function onContractFieldAction(payload: FormSectionFieldActionPayload) {
    const fieldKey = String(payload.field.name || '').trim();
    const actionValue = String(payload.action.value || '').trim();
    if (isContractFieldOrderEditable.value && fieldKey && ['show', 'hide'].includes(actionValue)) {
      fieldVisibilityDraft[fieldKey] = actionValue === 'show';
      fieldVisibilityDirtyKeys[fieldKey] = true;
      formConfigAuditResult.value = null;
      appendFormConfigOperation(
        actionValue === 'show' ? '显示字段' : '隐藏字段',
        `${formDesignFieldLabel(fieldKey)} 设置为${actionValue === 'show' ? '显示' : '隐藏'}`,
      );
      contractModeFeedback.value = '字段显示设置已调整，保存后生效';
      return;
    }
    if (actionValue === 'reload-requested') {
      await reload();
      return;
    }
    const raw = payload.action.raw;
    if (!raw) return;
    await runContractRuleAction(raw);
  }

  function onFormSettingsFieldSelect(payload: {
    field: FormSectionFieldSchema;
    groupTitle: string;
  }) {
    if (!isContractFieldOrderEditable.value) return;
    const fieldKey = String(payload.field.name || payload.field.key || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    if (!Object.prototype.hasOwnProperty.call(fieldVisibilityBase.value, fieldKey)) {
      const row = activeContractModeFieldRows.value.find((item) => item.fieldKey === fieldKey);
      const checkedAction = row?.actions.find((action) => Boolean(action.checked));
      fieldVisibilityBase.value = {
        ...fieldVisibilityBase.value,
        [fieldKey]: checkedAction ? checkedAction.value === 'show' : true,
      };
      if (!Object.prototype.hasOwnProperty.call(fieldVisibilityDraft, fieldKey)) {
        fieldVisibilityDraft[fieldKey] = checkedAction ? checkedAction.value === 'show' : true;
      }
    }
    selectedFormSettingsFieldKey.value = fieldKey;
    selectedFormSettingsFieldLabel.value = String(payload.field.label || fieldKey).trim();
    selectedFormSettingsFieldGroupTitleDraft.value =
      effectiveFieldGroupTitleForDraft(fieldKey) || normalizeFieldGroupTitle(payload.groupTitle);
    selectedFormSettingsFieldGroupTitleEdit.value = selectedFormSettingsFieldGroupTitleDraft.value;
    formSettingsActiveTab.value = 'fields';
  }

  function selectFormDesignerGroup(title: string) {
    const normalizedTitle = normalizeFieldGroupTitle(title);
    if (!normalizedTitle) return;
    const group = formDesignerGroupNavigatorItems.value.find((item) =>
      fieldGroupTitleMatches(item.title, normalizedTitle),
    );
    const orderedKeys = currentFormOrderedFieldKeys.value.length
      ? currentFormOrderedFieldKeys.value
      : currentFormDesignFieldKeys.value;
    const fieldKey =
      orderedKeys.find((key) => group?.fieldKeys.includes(key)) || group?.fieldKeys[0] || '';
    if (!fieldKey) return;
    onFormSettingsFieldSelect({
      field: {
        name: fieldKey,
        key: fieldKey,
        label: formDesignFieldLabel(fieldKey),
      } as FormSectionFieldSchema,
      groupTitle: normalizedTitle,
    });
  }

  function selectFormDesignerField(fieldKey: string) {
    const key = String(fieldKey || '').trim();
    if (!key) return;
    onFormSettingsFieldSelect({
      field: {
        name: key,
        key,
        label: formDesignFieldLabel(key),
      } as FormSectionFieldSchema,
      groupTitle: effectiveFieldGroupTitleForDraft(key) || '业务配置字段',
    });
  }

  async function onSelectedFormSettingsGroupTitleChange(value: string) {
    const oldTitle = selectedFormSettingsFieldGroupTitle.value;
    const newTitle = String(
      selectedFormSettingsFieldGroupTitleEdit.value || value || '',
    ).trim();
    if (!oldTitle || !newTitle || oldTitle === newTitle) {
      selectedFormSettingsFieldGroupTitleEdit.value = oldTitle;
      return;
    }
    await onContractInlineGroupRename({ oldTitle, newTitle });
  }

  async function onSelectedFormSettingsFieldLabelChange(value: string) {
    const fieldKey = selectedFormSettingsFieldKey.value;
    const label = String(value || '').trim();
    if (!fieldKey || !label || label === selectedFormSettingsFieldRow.value?.label) return;
    selectedFormSettingsFieldLabel.value = label;
    await setInlineFieldPolicy(fieldKey, { label });
  }

  function contractInlineFieldOrderIndex(field: FormSectionFieldSchema) {
    const fieldKey = String(field.name || '').trim();
    if (!fieldKey) return -1;
    return fieldOrderDraft.value.indexOf(fieldKey);
  }

  function onContractInlineFieldOrderMove(payload: {
    field: FormSectionFieldSchema;
    delta: number;
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    moveFieldOrder(fieldKey, payload.delta);
  }

  function onContractInlineFieldOrderDragStart(payload: {
    field: FormSectionFieldSchema;
    event: DragEvent;
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    const fieldLabel = String(payload.field.label || '').trim();
    draggingFieldLabel.value =
      fieldLabel && fieldLabel !== fieldKey ? fieldLabel : formDesignFieldLabel(fieldKey);
    onFieldOrderDragStart(fieldKey, payload.event);
  }

  function onContractInlineFieldOrderDragOver(payload: {
    field: FormSectionFieldSchema;
    groupTitle?: string;
    placement?: 'before' | 'after' | '';
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    onFieldOrderDragOver(fieldKey, payload.placement);
  }

  function onContractInlineFieldOrderDragLeave(payload: {
    field: FormSectionFieldSchema;
    groupTitle?: string;
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    onFieldOrderDragLeave(fieldKey);
  }

  function onContractInlineFieldOrderDrop(payload: {
    field: FormSectionFieldSchema;
    groupTitle?: string;
    placement?: 'before' | 'after' | '';
  }) {
    const fieldKey = String(payload.field.name || '').trim();
    if (!fieldKey) return;
    rememberFormConfigFieldLabel(fieldKey, payload.field.label);
    onFieldOrderDrop(fieldKey, payload.groupTitle, payload.placement);
  }

  function onContractInlineFieldOrderGroupDrop(payload: {
    groupTitle: string;
    groupIndex?: number;
  }) {
    onFieldOrderGroupDrop(payload.groupTitle);
  }

  function onContractInlineFieldOrderDragEnd() {
    onFieldOrderDragEnd();
  }

  return {
    onContractFieldAction,
    onFormSettingsFieldSelect,
    selectFormDesignerGroup,
    selectFormDesignerField,
    onSelectedFormSettingsGroupTitleChange,
    onSelectedFormSettingsFieldLabelChange,
    contractInlineFieldOrderIndex,
    onContractInlineFieldOrderMove,
    onContractInlineFieldOrderDragStart,
    onContractInlineFieldOrderDragOver,
    onContractInlineFieldOrderDragLeave,
    onContractInlineFieldOrderDrop,
    onContractInlineFieldOrderGroupDrop,
    onContractInlineFieldOrderDragEnd,
  };
}
