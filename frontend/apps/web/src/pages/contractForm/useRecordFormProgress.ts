import type { FieldDescriptor } from '@sc/schema';
import { computed, type ComputedRef, type Ref } from 'vue';

type ProgressNode = {
  kind: string;
  name: string;
  label?: string;
  readonly?: boolean;
  required?: boolean;
};

type DraftRow = { isNew?: boolean; dirty?: boolean; removed?: boolean };

export function useRecordFormProgress(params: {
  layoutNodes: () => ProgressNode[];
  canonicalFormFields: ComputedRef<Record<string, FieldDescriptor>>;
  formData: Record<string, unknown>;
  originalValues: Ref<Record<string, unknown>>;
  relationKeywords: Record<string, string>;
  fieldType: (descriptor?: FieldDescriptor) => string;
  relationInlineCreate: (descriptor?: FieldDescriptor) => { enabled: boolean; createOnNoMatch: boolean };
  relationKeyword: (name: string) => string;
  relationModel: (name: string) => string;
  one2manyFieldRows: (name: string) => DraftRow[];
  isFieldWritable: (name: string) => boolean;
  isFieldVisible: (name: string) => boolean;
  isIntakeCreateMode: ComputedRef<boolean>;
  nativeStatusbar: () => { field?: string; readonly?: boolean };
  comparableFieldValue: (name: string, value: unknown) => unknown;
}) {
  function hasPendingInlineRelationChange() {
    return params.layoutNodes().some((node) => {
      if (node.kind !== 'field' || node.readonly) return false;
      const descriptor = params.canonicalFormFields.value[node.name];
      if (params.fieldType(descriptor) !== 'many2one') return false;
      const inline = params.relationInlineCreate(descriptor);
      if (!inline.enabled || !inline.createOnNoMatch) return false;
      const currentId = Number(params.formData[node.name] || 0);
      return !(Number.isFinite(currentId) && currentId > 0) && Boolean(params.relationKeyword(node.name).trim());
    });
  }

  function hasPendingMany2manyTagCreate() {
    return Object.entries(params.relationKeywords).some(([name, keyword]) => {
      if (!String(keyword || '').trim() || !params.isFieldWritable(name)) return false;
      const descriptor = params.canonicalFormFields.value[name];
      const inline = params.relationInlineCreate(descriptor);
      return Array.isArray(params.formData[name])
        && inline.enabled && inline.createOnNoMatch && Boolean(params.relationModel(name));
    });
  }

  function hasOne2manyDraftChanges() {
    return params.layoutNodes().some((node) => {
      if (node.kind !== 'field' || node.readonly) return false;
      const descriptor = params.canonicalFormFields.value[node.name];
      return params.fieldType(descriptor) === 'one2many'
        && params.one2manyFieldRows(node.name).some((row) => row.isNew || row.dirty || row.removed);
    });
  }

  const hasChanges = computed(() => {
    if (hasPendingInlineRelationChange() || hasPendingMany2manyTagCreate() || hasOne2manyDraftChanges()) return true;
    const statusbar = params.nativeStatusbar();
    if (statusbar.field && !statusbar.readonly
      && params.comparableFieldValue(statusbar.field, params.formData[statusbar.field])
        !== params.comparableFieldValue(statusbar.field, params.originalValues.value[statusbar.field])) return true;
    return Object.keys(params.formData).some((key) => params.isFieldWritable(key)
      && params.comparableFieldValue(key, params.formData[key])
        !== params.comparableFieldValue(key, params.originalValues.value[key]));
  });

  const intakeRequiredFields = computed(() => params.isIntakeCreateMode.value
    ? params.layoutNodes()
      .filter((node) => node.kind === 'field' && node.required && params.isFieldVisible(node.name))
      .map((node) => ({ name: node.name, label: node.label || node.name }))
    : []);
  const fieldValueIsReady = (value: unknown) => {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim().length > 0;
    if (typeof value === 'number') return Number.isFinite(value) && value > 0;
    if (Array.isArray(value)) return value.length > 0;
    return typeof value === 'boolean' || Boolean(value);
  };
  const intakeRequiredReadyCount = computed(() => params.isIntakeCreateMode.value
    ? intakeRequiredFields.value.filter((field) => fieldValueIsReady(params.formData[field.name])).length
    : 0);
  const intakeMissingRequiredLabels = computed(() => params.isIntakeCreateMode.value
    ? intakeRequiredFields.value
      .filter((field) => !fieldValueIsReady(params.formData[field.name]))
      .map((field) => String(field.label || '').trim()).slice(0, 5)
    : []);
  const intakeRequiredSummary = computed(() => {
    const total = intakeRequiredFields.value.length;
    if (!params.isIntakeCreateMode.value) return '';
    return total > 0 ? `${intakeRequiredReadyCount.value}/${total}` : '当前页面未提供必填字段约束。';
  });
  const intakeMissingSummary = computed(() => {
    if (!params.isIntakeCreateMode.value) return '';
    return intakeMissingRequiredLabels.value.length ? intakeMissingRequiredLabels.value.join('、') : '无';
  });

  return {
    hasChanges,
    hasOne2manyDraftChanges,
    intakeRequiredFields,
    intakeRequiredReadyCount,
    intakeMissingRequiredLabels,
    intakeRequiredSummary,
    intakeMissingSummary,
  };
}
