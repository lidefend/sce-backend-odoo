/* eslint-disable @typescript-eslint/no-explicit-any */
import type { FieldDescriptor } from '@sc/schema';
import type { NativeFormLayoutNode } from '../../components/template/NativeFormTreeRenderer.vue';
import type { NativeLayoutLikeNode } from './nativeLayoutUtils';
import type { One2ManyColumn, One2ManyInlineRow, RelationOption } from './types';

type FieldDependencies = Record<string, any>;

export function useRecordRelationshipFields(dependencies: FieldDependencies) {
  const { ApiError, contractFieldLabel, deniedRelationModels, ensureOne2manyRows, fieldType, findNativeFieldNodeInTree, formData, isWritableFieldVisible, mergeHydratedOne2manyRecords, mergeRelationOptions, nativeFieldSubviewFromTree, nativeFormLayoutNodes, nativeNodeFieldDescriptorFromNode, normalizeRelationIds, one2manyCanCreateFromPolicies, one2manyColumnsFromSubview, one2manyCreateLabelFromPolicies, one2manyDraftSummary, one2manyFieldRows, one2manyPrimaryColumnFromColumns, one2manyRowActionsFromSubview, one2manyRowLabelFromPrimary, one2manySubviewPolicies, one2manyValidation, rawNativeFormLayoutNodes, readContractFormRecord, relationEntry, relationFieldDescriptors, relationModel, relationOptions, relationOptionsForFieldFromRuntime, relationOptionsFromRecords, relationReadFields, resolveOne2manyRowColumnBehavior, selectOne2manySubview, selectedRelationOptionsFromRuntime, v2ContractStore } = dependencies;
  const strictFieldDescriptors=()=>Array.from(v2ContractStore.value?.widgetsById.values()||[]).reduce<Record<string,FieldDescriptor>>((output,widget)=>{if(widget.fieldCode&&widget.fieldDescriptor&&!output[widget.fieldCode])output[widget.fieldCode]=widget.fieldDescriptor as FieldDescriptor;return output;},{});
  const strictFieldDescriptor=(name:string)=>strictFieldDescriptors()[String(name||'').trim()];
  function relationIds(name: string): number[] {
    return normalizeRelationIds(formData[name]);
  }

  function selectedRelationOptions(name: string): RelationOption[] {
    return selectedRelationOptionsFromRuntime(name, formData[name]);
  }

  function many2oneValue(name: string) {
    const ids = relationIds(name);
    return ids.length ? String(ids[0]) : '';
  }

  function relationOptionsForField(name: string) {
    return relationOptionsForFieldFromRuntime(name, formData[name]);
  }

  async function hydrateSelectedRelationOptions() {
    const fields = strictFieldDescriptors();
    await Promise.all(Object.entries(fields).map(async ([name, descriptor]) => {
      const type = fieldType(descriptor);
      if (!['many2one', 'many2many'].includes(type)) return;
      const relation = relationModel(name);
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
    const descriptor = strictFieldDescriptor(name) as Record<string, unknown> | undefined;
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
    const fallback = strictFieldDescriptor(normalized);
    const nativeNode = findNativeFieldNode(normalized);
    return nativeNode ? nativeNodeFieldDescriptor(nativeNode, fallback) : fallback;
  }


  function nativeFieldSubview(name: string): Record<string, unknown> | null {
    return nativeFieldSubviewFromTree(nativeFormLayoutNodes.value as NativeLayoutLikeNode[], name);
  }

  function one2manyColumns(name: string): One2ManyColumn[] {
    return one2manyColumnsFromSubview(nativeFieldSubview(name), (column) => one2manyRelationFieldDescriptor(name, column));
  }

  function one2manyRowActions(name: string) {
    return one2manyRowActionsFromSubview(nativeFieldSubview(name));
  }

  function one2manyRowColumnBehavior(_name: string, row: One2ManyInlineRow, column: One2ManyColumn) {
    return resolveOne2manyRowColumnBehavior(column, row.values || {}, formData, row.modifierPatches || {});
  }

  function visibleOne2manyColumns(name: string) {
    return one2manyColumns(name).filter((column) => (
      !resolveOne2manyRowColumnBehavior(column, {}, formData).columnInvisible
    ));
  }

  function one2manyPolicies(name: string) {
    return one2manySubviewPolicies(nativeFieldSubview(name));
  }

  function one2manyCanCreate(name: string) {
    return one2manyCanCreateFromPolicies(one2manyPolicies(name));
  }

  function one2manyCreateLabel(name: string, fieldLabel = '') {
    const label = String(fieldLabel || strictFieldDescriptor(name)?.string || contractFieldLabel(name) || '').trim();
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
    const entry = relationEntry(strictFieldDescriptor(name));
    if (entry?.canRead === false) {
      deniedRelationModels.add(relation);
      return;
    }
    if (deniedRelationModels.has(relation)) return;
    const rows = ensureOne2manyRows(name).filter((row) => row.id && !row.isNew);
    if (!rows.length) return;
    const columns = one2manyColumns(name);
    if (!columns.length) return;
    const fields = Array.from(new Set(['id', 'display_name', 'name', ...columns.map((column) => column.name)]));
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

  async function hydrateVisibleOne2manyRows() {
    const fields = strictFieldDescriptors();
    const names = Object.entries(fields)
      .filter(([, descriptor]) => fieldType(descriptor) === 'one2many')
      .map(([name]) => name)
      .filter((name) => isWritableFieldVisible(name) || one2manyFieldRows(name).length > 0);
    await Promise.all(names.map((name) => hydrateOne2manyRows(name)));
  }

  function one2manyRowErrors(fieldName: string, rowKey: string) {
    return one2manyValidation.value.rowErrors[`${fieldName}:${rowKey}`] || [];
  }


  return { relationIds, selectedRelationOptions, many2oneValue, relationOptionsForField, hydrateSelectedRelationOptions, one2manyRelationModel, one2manyRelationFieldDescriptor, nativeNodeFieldDescriptor, findNativeFieldNode, effectiveFieldDescriptor, nativeFieldSubview, one2manyColumns, visibleOne2manyColumns, one2manyRowColumnBehavior, one2manyRowActions, one2manyPolicies, one2manyCanCreate, one2manyCreateLabel, one2manyPrimaryColumn, one2manyRowLabel, one2manySummary, hydrateOne2manyRows, hydrateVisibleOne2manyRows, one2manyRowErrors };
}
