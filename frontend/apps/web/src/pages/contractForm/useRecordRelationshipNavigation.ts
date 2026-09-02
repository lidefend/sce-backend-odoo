/* eslint-disable @typescript-eslint/no-explicit-any */
import type { FieldDescriptor } from '@sc/schema';
import { resolveContractV2FormFieldMap } from '../../app/contracts/v2/store';
import { resolveRecordOpenTarget } from '../../app/runtime/recordEntryContract';

type NavigationDependencies = Record<string, any>;

export function useRecordRelationshipNavigation(dependencies: NavigationDependencies) {
  const { actionId, createContractFormRecord, fetchRelationOptions, formData, loadModelContractV2, model, normalizeFieldValue, one2manyRelationModel, openRelationCreateDialog, pickContractNavQuery, queryRelationOptions, relationCreateMode, relationEntry, relationFieldDescriptors, relationIds, relationInlineCreate, relationKeyword, relationModel, relationUiLabel, route, router, sanitizeUiErrorMessage, setMany2oneOption, validationErrors } = dependencies;
  async function ensureRelationFieldDescriptors(name: string) {
    const relation = one2manyRelationModel(name);
    if (!relation) return;
    if (relationFieldDescriptors.value[relation]) return;
    try {
      const response = await loadModelContractV2(relation, {
        viewType: 'form',
        renderProfile: 'edit',
      });
      const fields = resolveContractV2FormFieldMap(response.store) as Record<string, FieldDescriptor>;
      if (Object.keys(fields).length) {
        relationFieldDescriptors.value = {
          ...relationFieldDescriptors.value,
          [relation]: fields as Record<string, FieldDescriptor>,
        };
      }
    } catch {
      // best effort; fallback to char fields
    }
  }

  async function openRelationCreateForm(
    fieldName: string,
    descriptor?: FieldDescriptor,
    options: { restoreSearchOnCancel?: boolean } = {},
  ) {
    const relation = String((descriptor as Record<string, unknown> | undefined)?.relation || '').trim();
    if (!relation) return;
    const mode = relationCreateMode(descriptor);
    if (mode === 'none') {
      validationErrors.value = [relationUiLabel(descriptor, 'missing_create_entry')];
      return;
    }
    if (mode === 'quick') {
      const currentKeyword = relationKeyword(fieldName).trim();
      if (!currentKeyword) {
        validationErrors.value = [relationUiLabel(descriptor, 'missing_name', relationUiLabel(descriptor, 'quick_create_prompt', '请先输入要新增的名称'))];
        return;
      }
      await quickCreateRelation(fieldName, descriptor, currentKeyword);
      return;
    }
    const entry = relationEntry(descriptor);
    const relationActionId = entry?.actionId || null;
    const menuId = entry?.menuId || 0;
    if (!relationActionId) {
      validationErrors.value = [relationUiLabel(descriptor, 'missing_page_entry')];
      return;
    }
    const defaultQuery = Object.entries(entry?.defaultVals || {}).reduce<Record<string, unknown>>((acc, [key, value]) => {
      if (!key) return acc;
      acc[`default_${key}`] = value;
      return acc;
    }, {});
    Object.entries(entry?.defaultFromFields || {}).forEach(([targetField, sourceFieldRaw]) => {
      const sourceField = String(sourceFieldRaw || '').trim();
      if (!targetField || !sourceField) return;
      const value = normalizeFieldValue(sourceField, formData[sourceField]);
      if (value === undefined || value === null || value === '') return;
      defaultQuery[`default_${targetField}`] = value;
    });
    const nextQuery = pickContractNavQuery(route.query as Record<string, unknown>, {
      action_id: relationActionId,
      menu_id: menuId || undefined,
      view_mode: 'form',
      ...defaultQuery,
    });
    if (mode === 'dialog') {
      const nonce = window.crypto.randomUUID();
      const dialogRoute = router.resolve({
        name: 'model-form',
        params: { model: relation, id: 'new' },
        query: {
          ...nextQuery,
          relation_create_mode: 'dialog',
          relation_dialog_nonce: nonce,
          relation_return_field: fieldName,
          relation_return_model: model.value,
        },
      });
      openRelationCreateDialog({
        title: relationUiLabel(descriptor, 'create_and_edit', `新建${String((descriptor as Record<string, unknown>)?.string || '')}`),
        src: new URL(dialogRoute.href, window.location.origin).toString(),
        nonce,
        fieldName,
        parentModel: model.value,
        relationModel: relation,
        restoreSearchOnCancel: Boolean(options.restoreSearchOnCancel),
      });
      return;
    }
    const returnUrl = `${window.location.pathname}${window.location.search}`;
    try {
      await router.push({
        name: 'model-form',
        params: { model: relation, id: 'new' },
        query: {
          ...nextQuery,
          return_url: encodeURIComponent(returnUrl),
          return_field: fieldName,
          return_model: model.value,
          return_action_id: actionId.value || undefined,
          return_menu_id: Number(route.query.menu_id || 0) || undefined,
        },
      });
    } catch (err) {
      validationErrors.value = [sanitizeUiErrorMessage(err instanceof Error ? err.message : err, relationUiLabel(descriptor, 'create_page_failed'))];
    }
  }

  function currentRelationRecordId(fieldName: string) {
    const id = Number(relationIds(fieldName)[0] || 0);
    return Number.isFinite(id) && id > 0 ? Math.trunc(id) : 0;
  }

  function canOpenRelationRecord(fieldName: string, recordId: number, descriptor?: FieldDescriptor) {
    const relation = relationModel(fieldName);
    const entry = relationEntry(descriptor);
    return Boolean(relation && Number.isFinite(recordId) && recordId > 0
      && entry?.canRead === true && entry?.canOpen === true);
  }

  function canOpenRelationRecordForm(fieldName: string, descriptor?: FieldDescriptor) {
    return canOpenRelationRecord(fieldName, currentRelationRecordId(fieldName), descriptor);
  }

  async function openRelationRecord(fieldName: string, recordId: number, descriptor?: FieldDescriptor) {
    const relation = relationModel(fieldName);
    const entry = relationEntry(descriptor);
    if (!relation || !Number.isFinite(recordId) || recordId <= 0) return;
    if (entry?.canRead !== true || entry?.canOpen !== true) {
      validationErrors.value = [relationUiLabel(descriptor, 'missing_read_entry')];
      return;
    }
    const relationActionId = entry?.actionId || null;
    const menuId = entry?.menuId || 0;
    const nextQuery = pickContractNavQuery(route.query as Record<string, unknown>, {
      action_id: relationActionId || undefined,
      menu_id: menuId || undefined,
      view_mode: 'form',
    });
    const returnUrl = `${window.location.pathname}${window.location.search}`;
    try {
      const target = resolveRecordOpenTarget({
        model: relation,
        recordId,
        entryIntent: entry?.entryIntent || 'open',
        modelWriteAuthority: entry?.modelWriteAuthority ?? null,
        actionId: relationActionId || undefined,
        menuId: menuId || undefined,
        carryQuery: {
          ...nextQuery,
          return_url: encodeURIComponent(returnUrl),
          return_field: fieldName,
          return_model: model.value,
          return_action_id: actionId.value || undefined,
          return_menu_id: Number(route.query.menu_id || 0) || undefined,
        },
      });
      if (target) await router.push(target as never);
    } catch (err) {
      validationErrors.value = [sanitizeUiErrorMessage(err instanceof Error ? err.message : err, relationUiLabel(descriptor, 'open_record_failed'))];
    }
  }

  async function openRelationRecordForm(fieldName: string, descriptor?: FieldDescriptor) {
    await openRelationRecord(fieldName, currentRelationRecordId(fieldName), descriptor);
  }

  async function quickCreateRelation(
    fieldName: string,
    descriptor: FieldDescriptor | undefined,
    label: string,
    options: { stayInDialog?: boolean } = {},
  ) {
    const relation = String((descriptor as Record<string, unknown> | undefined)?.relation || '').trim();
    if (!relation) return;
    const entry = relationEntry(descriptor);
    try {
      const existing = await fetchRelationOptions(fieldName, label, 20);
      const exact = existing.find((item) => item.label.trim().toLowerCase() === label.trim().toLowerCase());
      if (exact) {
        setMany2oneOption(fieldName, exact);
        return;
      }
      const inline = relationInlineCreate(descriptor);
      const nameField = inline.nameField || 'name';
      const vals: Record<string, unknown> = { ...(entry?.defaultVals || {}), [nameField]: label };
      const created = await createContractFormRecord({ model: relation, vals });
      const id = Number(created?.id || 0);
      if (Number.isFinite(id) && id > 0) {
        const option = { id: Math.trunc(id), label };
        setMany2oneOption(fieldName, option);
        if (!options.stayInDialog) await queryRelationOptions(fieldName, label);
      }
    } catch (err) {
      const message = sanitizeUiErrorMessage(err instanceof Error ? err.message : err, relationUiLabel(descriptor, 'quick_create_failed'));
      validationErrors.value = [message];
    }
  }

  return { ensureRelationFieldDescriptors, openRelationCreateForm, currentRelationRecordId, canOpenRelationRecord, canOpenRelationRecordForm, openRelationRecord, openRelationRecordForm, quickCreateRelation };
}
