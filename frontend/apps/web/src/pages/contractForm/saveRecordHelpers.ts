import type { FieldDescriptor } from '@sc/schema';
import {
  BusinessErrorCodes,
  businessErrorKey,
  createBusinessErrorTarget,
  createBusinessFieldError,
  type BusinessFieldError,
} from '../../app/businessValidationError';
import { fieldType } from './fieldUtils';
import { isMissingRequiredValue, isRequiredFieldEmptyByType } from './valueUtils';
import type { LayoutNode, SubmissionFeedback } from './types';

export type SaveRecordValidationResult = {
  editableMap?: Record<string, unknown>;
  fieldErrors?: Record<string, BusinessFieldError>;
  ok: boolean;
  showOne2manyErrors?: boolean;
  validationErrors?: string[];
  submissionFeedback?: SubmissionFeedback;
};

export function createSingleFlightSave<TArgs extends unknown[], T>(
  execute: (...args: TArgs) => Promise<T>,
): (...args: TArgs) => Promise<T> {
  let active: Promise<T> | null = null;
  return (...args: TArgs) => {
    if (active) return active;
    active = execute(...args).finally(() => {
      active = null;
    });
    return active;
  };
}

export async function validateBeforeSaveRecord(params: {
  collectSceneValidationPrecheckErrors: (fieldLabels: Record<string, string>) => string[];
  collectWritableValues: () => Record<string, unknown>;
  formData: Record<string, unknown>;
  isWritableFieldVisible: (name: string) => boolean;
  layoutNodes: LayoutNode[];
  layoutFieldLabels: () => Record<string, string>;
  normalizeFieldValue: (name: string, value: unknown) => unknown;
  one2manyFieldErrors: Record<string, BusinessFieldError>;
  one2manyIssues: string[];
  /** Business model the saved values belong to; part of every error target. */
  model: string;
  recordId: number | null;
  resolvePendingInlineRelationCreates: () => Promise<string[]>;
  resolvePendingMany2manyTagCreates: () => Promise<string[]>;
}): Promise<SaveRecordValidationResult> {
  if (params.one2manyIssues.length) {
    return {
      ok: false,
      showOne2manyErrors: true,
      validationErrors: params.one2manyIssues.slice(0, 5),
      fieldErrors: params.one2manyFieldErrors,
      submissionFeedback: { kind: 'warn', message: '创建失败，请检查填写内容' },
    };
  }
  const labels = params.layoutFieldLabels();
  const scenePrecheckIssues = params.collectSceneValidationPrecheckErrors(labels);
  if (scenePrecheckIssues.length) {
    return {
      ok: false,
      showOne2manyErrors: false,
      validationErrors: scenePrecheckIssues,
      submissionFeedback: { kind: 'warn', message: '创建失败，请检查填写内容' },
    };
  }
  const relationCreateIssues = await params.resolvePendingInlineRelationCreates();
  if (relationCreateIssues.length) {
    return {
      ok: false,
      showOne2manyErrors: false,
      validationErrors: relationCreateIssues,
      submissionFeedback: { kind: 'warn', message: '创建失败，请检查填写内容' },
    };
  }
  const tagCreateIssues = await params.resolvePendingMany2manyTagCreates();
  if (tagCreateIssues.length) {
    return {
      ok: false,
      showOne2manyErrors: false,
      validationErrors: tagCreateIssues,
      submissionFeedback: { kind: 'warn', message: '创建失败，请检查填写内容' },
    };
  }
  const editableMap = params.collectWritableValues();
  {
    const requiredValidation = collectRequiredFieldValidation({
      formData: params.formData,
      isWritableFieldVisible: params.isWritableFieldVisible,
      layoutNodes: params.layoutNodes,
      model: params.model,
      normalizeFieldValue: params.normalizeFieldValue,
      recordId: params.recordId,
      values: editableMap,
      submittedFieldsOnly: Boolean(params.recordId),
    });
    if (requiredValidation.messages.length) {
      return {
        ok: false,
        showOne2manyErrors: false,
        validationErrors: requiredValidation.messages,
        fieldErrors: requiredValidation.fieldErrors,
        submissionFeedback: { kind: 'warn', message: '请先补充必填信息，再保存草稿或提交。' },
      };
    }
  }
  return {
    editableMap,
    ok: true,
    showOne2manyErrors: false,
  };
}

export function collectRequiredFieldIssues(params: {
  formData: Record<string, unknown>;
  isWritableFieldVisible: (name: string) => boolean;
  layoutNodes: LayoutNode[];
  model: string;
  normalizeFieldValue: (name: string, value: unknown) => unknown;
  recordId: number | null;
  values: Record<string, unknown>;
}) {
  return collectRequiredFieldValidation(params).messages;
}

export function collectRequiredFieldValidation(params: {
  formData: Record<string, unknown>;
  isWritableFieldVisible: (name: string) => boolean;
  layoutNodes: LayoutNode[];
  /** Business model that owns the missing values. */
  model: string;
  normalizeFieldValue: (name: string, value: unknown) => unknown;
  /** Persisted record id, or null for the unsaved draft. */
  recordId: number | null;
  values: Record<string, unknown>;
  submittedFieldsOnly?: boolean;
}) {
  const missing = params.layoutNodes
    .filter((node) => node.kind === 'field' && !node.readonly && (
      params.submittedFieldsOnly
        ? Object.prototype.hasOwnProperty.call(params.values, node.name)
        : params.isWritableFieldVisible(node.name)
    ))
    .filter((node) => {
      const descriptor = node.descriptor;
      if (!descriptor?.required) return false;
      const value = Object.prototype.hasOwnProperty.call(params.values, node.name)
        ? params.values[node.name]
        : params.normalizeFieldValue(node.name, params.formData[node.name]);
      return isRequiredFieldEmptyByType(value, fieldType(descriptor));
    })
    .map((node) => ({
      name: node.name,
      label: String(node.label || node.descriptor?.string || node.name).trim(),
    }))
    .filter((item) => Boolean(item.name && item.label));
  return buildRequiredFieldErrorPayload(missing, { model: params.model, recordId: params.recordId });
}

/**
 * Turn rejected business field codes into the one error shape the form uses.
 *
 * Shared so a field rejected by the precheck and a field rejected by the
 * official form engine produce the same summary, the same per-field message and
 * the same store key. A second producer must never mean a second message or a
 * second authority over the same field.
 */
export function buildRequiredFieldErrorPayload(
  missing: readonly { name: string; label: string }[],
  scope: { model: string; recordId: number | null },
) {
  if (!missing.length) return { messages: [] as string[], fieldErrors: {} as Record<string, BusinessFieldError> };
  const unique = Array.from(new Map(missing.map((item) => [item.name, item])).values()).slice(0, 5);
  const message = `保存前请填写：${unique.map((item) => item.label).join('、')}`;
  const fieldErrors: Record<string, BusinessFieldError> = {};
  unique.forEach((item) => {
    const target = createBusinessErrorTarget({
      model: scope.model,
      recordId: scope.recordId,
      fieldCode: item.name,
      row: null,
    });
    const error = createBusinessFieldError({
      code: BusinessErrorCodes.REQUIRED_VALUE_MISSING,
      message: `${item.label}不能为空`,
      target,
    });
    if (!error) return;
    fieldErrors[businessErrorKey(error.target)] = error;
  });
  return { messages: [message], fieldErrors };
}

export type WritableValueDecisionInput = {
  recordId: number | null;
  dirty: boolean;
  value: unknown;
  descriptor?: FieldDescriptor;
};

/**
 * Decides whether one normalized draft value belongs in a write payload.
 *
 * - `null` means "untouched numeric": never write it. Serializing an untouched
 *   number as `false` makes Odoo silently store `0` instead of keeping the
 *   stored value (or letting the model own its default).
 * - Edit mode only sends explicitly changed fields.
 * - Create mode sends every changed field, and skips untouched *empty* values so
 *   an empty string never overrides a model default. Untouched non-empty values
 *   (context/onchange hydrated) are still sent.
 */
export function shouldWriteFieldValue(input: WritableValueDecisionInput): boolean {
  if (input.value === null) return false;
  if (input.recordId) return input.dirty;
  if (input.dirty) return true;
  return !isMissingRequiredValue(input.value, fieldType(input.descriptor));
}

export type SaveRecordPayloadBuildInput = {
  comparableFieldValue: (name: string, value: unknown) => unknown;
  formFields: Record<string, FieldDescriptor>;
  dirtyFieldSet: Set<string>;
  editableMap: Record<string, unknown>;
  formData: Record<string, unknown>;
  originalValues: Record<string, unknown>;
  recordId: number | null;
};

export function buildSaveRecordPayload(params: SaveRecordPayloadBuildInput) {
  return Object.entries(params.editableMap).reduce<Record<string, unknown>>((acc, [key, value]) => {
    if (!params.recordId) {
      acc[key] = value;
      return acc;
    }
    const ttype = fieldType(params.formFields[key]);
    if (ttype === 'many2many'
      && params.comparableFieldValue(key, params.formData[key]) === params.comparableFieldValue(key, params.originalValues[key])) {
      return acc;
    }
    if (ttype === 'many2many' || ttype === 'one2many') {
      if (Array.isArray(value) && value.length) {
        acc[key] = value;
      }
      return acc;
    }
    if (!params.dirtyFieldSet.has(key)) {
      return acc;
    }
    if (params.comparableFieldValue(key, params.formData[key]) !== params.comparableFieldValue(key, params.originalValues[key])) {
      acc[key] = value;
    }
    return acc;
  }, {});
}

export function collectRecordSaveValues(params: SaveRecordPayloadBuildInput) {
  return buildSaveRecordPayload(params);
}
