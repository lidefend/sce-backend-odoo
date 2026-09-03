/* eslint-disable @typescript-eslint/no-explicit-any */
import type { FieldDescriptor } from '@sc/schema';
import { reactive } from 'vue';
import { resolveContractV2FormFieldMap } from '../../app/contracts/v2';
import type { NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import type { NativeLayoutLikeNode } from './nativeLayoutUtils';
import type { One2ManyColumn, One2ManyInlineRow, RelationOption } from './types';

type FieldDependencies = Record<string, any>;

export function useRecordRelationshipFields(dependencies: FieldDependencies) {
  const { ApiError, contractFieldLabel, deniedRelationModels, ensureOne2manyRows, fieldType, findNativeFieldNodeInTree, formData, isWritableFieldVisible, mergeHydratedOne2manyRecords, mergeRelationOptions, nativeFieldSubviewFromTree, nativeFormLayoutNodes, nativeNodeFieldDescriptorFromNode, normalizeRelationIds, one2manyCanCreateFromPolicies, one2manyCanInlineEditFromPolicies, one2manyCanUnlinkFromPolicies, one2manyColumnsFromSubview, one2manyCreateLabelFromPolicies, one2manyDraftSummary, one2manyFieldRows, one2manyPrimaryColumnFromColumns, one2manyRowLabelFromPrimary, one2manySubviewPolicies, one2manyValidation, readContractFormRecord, relationEntry, relationFieldDescriptors, relationModel, relationOptions, relationOptionsForFieldFromRuntime, relationOptionsFromRecords, relationReadFields, selectOne2manySubview, selectedRelationOptionsFromRuntime, v2ContractStore } = dependencies;
  const formFields = () => resolveContractV2FormFieldMap(v2ContractStore.value) as Record<string, FieldDescriptor>;
  const one2manyHydrating = reactive<Record<string, boolean>>({});

  function isOne2manyHydrating(name: string) {
    return one2manyHydrating[String(name || '').trim()] === true;
  }
  function relationIds(name: string): number[] {
    return normalizeRelationIds(formData[name]);
  }

  function selectedRelationOptions(name: string): RelationOption[] {
    return selectedRelationOptionsFromRuntime(name, formData[name]);
  }

  function many2oneValue(name: string) {
    const ids = relationIds(name);
    if (!ids.length) return '';
    return String(ids[0]);
  }

  function relationOptionsForField(name: string) {
    return relationOptionsForFieldFromRuntime(name, formData[name]);
  }

  async function hydrateSelectedRelationOptions() {
    const fields = formFields();
    await Promise.all(Object.entries(fields).map(async ([name, descriptor]) => {
      const type = fieldType(descriptor);
      if (!['many2one', 'many2many'].includes(type)) return;
      const relation = relationModel(name);
      const entry = relationEntry(descriptor);
      if (entry?.canRead !== true) return;
      if (!relation || deniedRelationModels.has(relation)) return;
      const ids = relationIds(name);
      if (!ids.length) return;
      const existingIds = new Set((relationOptions.value[name] || []).map((option) => option.id));
      const missingIds = ids.filter((id) => !existingIds.has(id));
      if (!missingIds.length) return;
      try {
        const response = await readContractFormRecord({
          model: relation,
          ids: missingIds,
          fields: relationReadFields(descriptor),
        });
        const options = relationOptionsFromRecords(response.records, descriptor);
        if (options.length) mergeRelationOptions(name, options);
      } catch (err) {
        if (err instanceof ApiError) {
          const denied = err.status === 403 || String(err.reasonCode || '').toUpperCase() === 'PERMISSION_DENIED';
          if (denied) deniedRelationModels.add(relation);
        }
      }
    }));
  }

  function one2manyRelationModel(name: string) {
    const descriptor = formFields()[name] as Record<string, unknown> | undefined;
    return String(descriptor?.relation || '').trim();
  }

  function one2manyRelationFieldDescriptor(fieldName: string, column: string) {
    const model = one2manyRelationModel(fieldName);
    if (!model) return null;
    const map = relationFieldDescriptors.value[model] || {};
    const descriptor = map[column];
    return descriptor || null;
  }

  function nativeNodeFieldDescriptor(nodeRaw: NativeFormLayoutNode, fallback?: FieldDescriptor): FieldDescriptor | undefined {
    return nativeNodeFieldDescriptorFromNode(nodeRaw as NativeLayoutLikeNode, fallback, contractFieldLabel);
  }

  function findNativeFieldNode(name: string): NativeFormLayoutNode | null {
    return findNativeFieldNodeInTree(nativeFormLayoutNodes.value as NativeLayoutLikeNode[], name) as NativeFormLayoutNode | null;
  }

  function effectiveFieldDescriptor(name: string): FieldDescriptor | undefined {
    const normalized = String(name || '').trim();
    if (!normalized) return undefined;
    const fallback = formFields()[normalized];
    const nativeNode = findNativeFieldNode(normalized);
    return nativeNode ? nativeNodeFieldDescriptor(nativeNode, fallback) : fallback;
  }

  function nativeFieldSubview(name: string): Record<string, unknown> | null {
    return nativeFieldSubviewFromTree(nativeFormLayoutNodes.value as NativeLayoutLikeNode[], name);
  }

  function one2manyColumns(name: string): One2ManyColumn[] {
    const descriptorSubview = (formFields()[name] as Record<string, unknown> | undefined)?.subview;
    const nativeSubview = nativeFieldSubview(name);
    const fieldSubview = selectOne2manySubview(descriptorSubview, nativeSubview);
    return one2manyColumnsFromSubview(fieldSubview, (column) => one2manyRelationFieldDescriptor(name, column));
  }

  function one2manyPolicies(name: string) {
    const descriptorSubview = (formFields()[name] as Record<string, unknown> | undefined)?.subview;
    const nativeSubview = nativeFieldSubview(name);
    const fieldSubview = selectOne2manySubview(descriptorSubview, nativeSubview);
    return one2manySubviewPolicies(fieldSubview);
  }

  function one2manyCanCreate(name: string) {
    return one2manyCanCreateFromPolicies(one2manyPolicies(name));
  }

  function one2manyCanUnlink(name: string) {
    return one2manyCanUnlinkFromPolicies(one2manyPolicies(name));
  }

  function one2manyCanInlineEdit(name: string) {
    return one2manyCanInlineEditFromPolicies(one2manyPolicies(name));
  }

  function one2manyRowRecordId(row: One2ManyInlineRow) {
    const id = Number(row.id || 0);
    return !row.isNew && Number.isFinite(id) && id > 0 ? Math.trunc(id) : 0;
  }

  function one2manyCreateLabel(name: string, fieldLabel = '') {
    const label = String(fieldLabel || contractFieldLabel(name) || formFields()[name]?.string || '').trim();
    return one2manyCreateLabelFromPolicies(one2manyPolicies(name), label);
  }

  function one2manyPrimaryColumn(name: string) {
    return one2manyPrimaryColumnFromColumns(one2manyColumns(name));
  }

  function one2manyRowLabel(fieldName: string, row: One2ManyInlineRow) {
    return one2manyRowLabelFromPrimary(one2manyPrimaryColumn(fieldName), row);
  }

  function one2manySummary(name: string) {
    return one2manyDraftSummary(one2manyFieldRows(name));
  }

  async function hydrateOne2manyRows(name: string) {
    const relation = one2manyRelationModel(name);
    if (!relation) return;
    const entry = relationEntry(formFields()[name]);
    if (entry?.canRead === false) {
      deniedRelationModels.add(relation);
      return;
    }
    if (deniedRelationModels.has(relation)) return;
    const rows = ensureOne2manyRows(name).filter((row) => row.id && !row.isNew);
    if (!rows.length) return;
    const columns = one2manyColumns(name);
    if (!columns.length) return;
    // 注意：不请求 'name' —— 部分子模型（如 payment.request.line）无 name 字段，
    // 请求会触发后端 ValueError 导致整行 hydrate 失败（catch 静默吞掉后列值全空）。
    // display_name 已覆盖名称展示需求。
    const fields = Array.from(new Set(['id', 'display_name', ...columns.map((column) => column.name)]));
    try {
      const response = await readContractFormRecord({
        model: relation,
        ids: rows.map((row) => Number(row.id)).filter((id) => Number.isFinite(id) && id > 0),
        fields,
      });
      const records = Array.isArray(response.records) ? response.records : [];
      mergeHydratedOne2manyRecords(name, records as Array<Record<string, unknown>>);
    } catch {
      // Keep the id/display-name fallback when the child model is not readable.
    }
  }

  function prepareVisibleOne2manyHydration() {
    const fields = formFields();
    const names = Object.entries(fields)
      .filter(([, descriptor]) => fieldType(descriptor) === 'one2many')
      .map(([name]) => name)
      .filter((name) => isWritableFieldVisible(name) || one2manyFieldRows(name).length > 0);
    names.forEach((name) => { one2manyHydrating[name] = true; });
    return names;
  }

  async function hydrateVisibleOne2manyRows() {
    const names = prepareVisibleOne2manyHydration();
    await Promise.all(names.map(async (name) => {
      try {
        await hydrateOne2manyRows(name);
      } finally {
        one2manyHydrating[name] = false;
      }
    }));
  }

  function one2manyRowErrors(fieldName: string, rowKey: string) {
    return one2manyValidation.value.rowErrors[`${fieldName}:${rowKey}`] || [];
  }


  return { relationIds, selectedRelationOptions, many2oneValue, relationOptionsForField, hydrateSelectedRelationOptions, one2manyRelationModel, one2manyRelationFieldDescriptor, nativeNodeFieldDescriptor, findNativeFieldNode, effectiveFieldDescriptor, nativeFieldSubview, one2manyColumns, one2manyPolicies, one2manyCanCreate, one2manyCanInlineEdit, one2manyCanUnlink, one2manyRowRecordId, one2manyCreateLabel, one2manyPrimaryColumn, one2manyRowLabel, one2manySummary, hydrateOne2manyRows, prepareVisibleOne2manyHydration, hydrateVisibleOne2manyRows, isOne2manyHydrating, one2manyRowErrors };
}
