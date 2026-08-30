<template>
  <div class="record-page">
    <div class="page-heading">
      <div>
        <el-breadcrumb
          ><el-breadcrumb-item @click="router.back()"
            >业务列表</el-breadcrumb-item
          ><el-breadcrumb-item>{{ title }}</el-breadcrumb-item></el-breadcrumb
        >
        <div class="heading-title">
          <h1>{{ pageHeadingTitle }}</h1>
          <el-tag v-if="statusLabel" :type="statusType" effect="light">{{ statusLabel }}</el-tag>
        </div>
        <p v-if="pageHeadingSubtitle" class="record-name">{{ pageHeadingSubtitle }}</p>
      </div>
      <div class="heading-actions">
        <el-tag v-if="recordId" size="small" effect="plain" :type="hasChanges ? 'warning' : 'info'">
          {{ hasChanges ? '已修改' : '尚未修改' }}
        </el-tag>
        <span v-if="statusLabel" class="heading-status-label">当前状态</span>
        <el-tag v-if="statusLabel" size="small" :type="statusType" effect="plain">{{ statusLabel }}</el-tag>
        <el-button v-if="canEdit && mode === 'view'" type="primary" @click="mode = 'edit'">编辑</el-button>
        <el-button v-if="mode !== 'view'" @click="cancelEdit">取消</el-button>
        <el-button v-if="mode !== 'view'" type="primary" :loading="saving" :disabled="operationBusy" @click="save">保存修改</el-button>
        <el-button @click="router.back()">返回列表</el-button>
        <el-button
          v-if="canDelete && recordId"
          type="danger"
          plain
          :loading="removing"
          :disabled="operationBusy"
          @click="remove"
          >删除</el-button
        >
      </div>
    </div>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="mb-16"
      ><template #default
        ><span v-if="traceId">Trace ID: {{ traceId }}</span
        ><el-button link type="primary" @click="load">重试</el-button></template
      ></el-alert
    >
    <el-skeleton v-if="loading" :rows="8" animated />
    <div v-else class="record-content">
          <el-form
            ref="formRef"
            :model="values"
            :rules="formRules"
            label-position="top"
            class="record-form"
            ><semantic-record-form
              v-if="useSemanticForm"
              :model="semanticForm"
              :values="values"
              :mode="mode"
              :record-model="model"
              :record-id="recordId"
              :context="sourceContext"
              :field-state="fieldState"
              :onchange="onchange"
              :request-edit="requestRelationEdit"
              :run-action="runSemanticAction"
              :modifier-patch="modifierPatch"
            /><el-tabs v-else-if="tabs.length" v-model="activeTab"
        ><el-tab-pane
          v-for="tab in tabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
          ><div class="field-grid">
            <template v-for="field in tab.fields" :key="field.code"
              ><el-form-item v-if="!fieldState(field).invisible"
                :label="field.label"
                :prop="field.code"
                :required="fieldState(field).required"
                :class="{ 'field-wide': ['one2many','many2many','binary','text','html'].includes(field.type) }"
                ><form-field-control
                  v-model="values[field.code]" :field="field"
                  :readonly="mode === 'view' || fieldState(field).readonly"
                  :allow-view-edit="mode === 'view' && !fieldState(field).readonly && Boolean(recordId)"
                  :model="model" :record-id="recordId" :values="values" :context="sourceContext"
                  :patch="modifierPatch[field.code] || {}"
                  @change="onchange(field)" @request-edit="requestRelationEdit(field, $event)" @uploaded="load"
                /></el-form-item
            ></template></div>
          </el-tab-pane
            ></el-tabs>
            <div v-else class="field-grid">
        <el-form-item
          v-for="field in fields"
          :key="field.code"
          :label="field.label"
          :prop="field.code"
          ><form-field-control :field="field" :model-value="values[field.code]" readonly :model="model" :record-id="recordId" :values="values" :context="sourceContext" /></el-form-item
        >
            </div>
            <div v-if="!nativeFormTree && !intakeCreateMode && (groupedActions.direct.length || groupedActions.overflow.length || groupedActions.configuration.length)" class="business-command-actions">
              <el-button
                v-for="action in groupedActions.direct"
                :key="action.key"
                :type="action.type"
                :plain="action.type !== 'danger'"
                :loading="activeActionKey === action.key"
                :disabled="operationBusy || action.enabled === false"
                :title="action.reasonCode || ''"
                @click="runAction(action)"
              >{{ action.label }}</el-button>
              <el-dropdown v-if="groupedActions.overflow.length" @command="runCommandAction">
                <el-button plain :disabled="operationBusy">更多操作<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="action in groupedActions.overflow"
                      :key="action.key"
                      :command="action.key"
                      :disabled="action.enabled === false"
                    >{{ action.label }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-dropdown v-if="groupedActions.configuration.length" @command="runConfigurationAction">
                <el-button plain :disabled="operationBusy"><el-icon><Setting /></el-icon>表单设置<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="action in groupedActions.configuration"
                      :key="action.key"
                      :command="action.key"
                      :disabled="action.enabled === false"
                    >{{ action.label }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <inline-business-action-tabs
              v-if="!nativeFormTree && !intakeCreateMode && groupedActions.inline.length"
              ref="inlineActionTabsRef"
              :actions="groupedActions.inline"
              :model="model"
              :record-id="recordId"
              :record-values="values"
              :current-query="route.query"
              :run-action="runAction"
            />
            <div v-if="mode !== 'view'" class="form-footer">
              <el-button @click="cancelEdit">取消</el-button>
              <el-button type="primary" :loading="saving" :disabled="operationBusy" @click="save">保存修改</el-button>
            </div>
          </el-form>
      <section v-if="recordId && chatterEnabled" class="record-chatter">
        <header class="record-chatter__header"><h2>沟通记录</h2></header>
        <chatter-panel :model="model" :record-id="recordId" />
      </section>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowDown, Setting } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import FormFieldControl from "@/components/form/FormFieldControl.vue";
import SemanticRecordForm from "@/components/form/SemanticRecordForm.vue";
import InlineBusinessActionTabs from "@/components/form/InlineBusinessActionTabs.vue";
import ChatterPanel from "@/components/collaboration/ChatterPanel.vue";
import {
  createRecord,
  deleteRecords,
  executeButton,
  loadPageContract,
  readRecord,
  relationOptions,
  triggerOnchange,
  updateRecord,
} from "@/api/odoo";
import type { BusinessAction, Dictionary, FieldSpec } from "@/types/contracts";
import { useSessionStore } from "@/stores/session";
import {
  buildWritableFormValues,
  decodePageContract,
  effectiveRights,
  formSourceContext,
  normalizeFieldWriteValue,
  pageTitle,
  resolveActions,
  resolveFieldSpecs,
  resolveSemanticFormModel,
} from "@/utils/contract";
import { displayValue } from "@/utils/format";
import { usesExecuteButtonIntent } from "@/utils/action";
import { groupRecordBusinessActions } from "@/utils/action";
import { runtimeFieldState } from "@/runtime/modifiers";
import type InlineBusinessActionTabsComponent from "@/components/form/InlineBusinessActionTabs.vue";
const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const model = computed(() => String(route.params.model || ""));
const recordId = computed(() => {
  const n = Number(route.params.id);
  return Number.isFinite(n) && n > 0 ? n : null;
});
const mode = ref(
  String(route.query.mode || "view") as "view" | "edit" | "create",
);
const loading = ref(false);
const saving = ref(false);
const removing = ref(false);
const activeActionKey = ref("");
const operationBusy = computed(() => saving.value || removing.value || Boolean(activeActionKey.value));
const error = ref("");
const traceId = ref("");
const contract = ref(decodePageContract({}));
const values = reactive<Dictionary>({});
const original = ref<Dictionary>({});
const formRef = ref<FormInstance>();
const activeTab = ref("main");
const recordVersion = ref("");
const modifierPatch = reactive<Record<string, Dictionary>>({});
const inlineActionTabsRef = ref<InstanceType<typeof InlineBusinessActionTabsComponent> | null>(null);
let onchangeSequence = 0;
const sourceContext = computed(() => formSourceContext(contract.value));
const chatterEnabled = computed(() => {
  const raw = contract.value.raw || {};
  const chatter = raw.form?.chatter || contract.value.runtimeContract.chatter || {};
  return Boolean(recordId.value) && chatter.enabled !== false;
});
const wizardMode = computed(() => route.query.wizard === "1" || /(^|\.)wizard$/i.test(model.value));
const intakeCreateMode = computed(() => ["quick", "standard"].includes(String(route.query.intake_mode || "").trim().toLowerCase()));
const fields = computed<FieldSpec[]>(() => resolveFieldSpecs(contract.value));
const semanticForm = computed(() => resolveSemanticFormModel(contract.value));
const useSemanticForm = computed(() => semanticForm.value.primaryNodes.length > 0);
const nativeFormTree = computed(() => {
  const layout = contract.value.layoutContract || {};
  const tree = layout.containerTree ?? layout.container_tree;
  return useSemanticForm.value || (Array.isArray(tree) && tree.length > 0);
});
const rights = computed(() => effectiveRights(contract.value));
const canEdit = computed(
  () => mode.value === "create" || rights.value.write !== false,
);
const canDelete = computed(
  () =>
    (Boolean(recordId.value) && rights.value.unlink === true) ||
    rights.value.delete === true,
);
const actions = computed<BusinessAction[]>(() =>
  resolveActions(contract.value, "form", {
    nativeTree: nativeFormTree.value,
    intakeMode: intakeCreateMode.value,
  }).filter((a) => a.key !== "form.save"),
);
const groupedActions = computed(() => groupRecordBusinessActions(actions.value, {
  isPlatformAdmin: session.isAdmin,
}));
const title = computed(() =>
  pageTitle(contract.value, loading.value ? "业务详情" : model.value || "业务详情"),
);
const pageHeadingTitle = computed(() => mode.value === "create" ? "新建业务" : "业务办理");
const pageHeadingSubtitle = computed(() => {
  const label = title.value && title.value !== "业务详情" ? title.value : recordName.value;
  return mode.value === "create" ? (label ? `新建${label}` : "新建业务") : (label || "编辑业务");
});
const hasChanges = computed(() => {
  if (mode.value === "create") return Object.keys(values).some((key) => values[key] !== undefined && values[key] !== false && values[key] !== "");
  return fields.value.some((field) => JSON.stringify(values[field.code]) !== JSON.stringify(original.value[field.code]));
});
const recordName = computed(() => {
  const value = values.display_name ?? values.name;
  return value && String(value).trim() && String(value).trim() !== title.value
    ? displayValue(value)
    : "";
});
const statusField = computed(() =>
  fields.value.find((f) =>
    [
      "state",
      "status",
      "lifecycle_state",
      "sc_state",
      "stage_id",
      "workflow_state",
      "approval_state",
    ].includes(f.code),
  ),
);
const statusLabel = computed(() =>
  statusField.value ? displayValue(values[statusField.value.code]) : "",
);
const statusType = computed(() =>
  /完成|通过|approved|done/i.test(statusLabel.value)
    ? "success"
    : /取消|驳回|拒绝/i.test(statusLabel.value)
      ? "danger"
      : "primary",
);
const tabs = computed(() => [{ key: "main", label: "表单信息", fields: fields.value }]);
const formRules = computed<FormRules>(() =>
  Object.fromEntries(
    fields.value
      .filter((f) => fieldState(f).required && !fieldState(f).invisible)
      .map((f) => [
        f.code,
        [{ required: true, message: `请输入${f.label}`, trigger: "blur" }],
      ]),
  ),
);
function format(v: unknown) {
  return displayValue(v);
}
function cancelEdit() {
  Object.assign(values, original.value);
  mode.value = "view";
}
function requestRelationEdit(field: FieldSpec, continueAction?: () => void) {
  if (!recordId.value || mode.value !== "view" || !canEdit.value || fieldState(field).readonly) return;
  mode.value = "edit";
  if (continueAction) void nextTick(continueAction);
}
function staticFlag(value: unknown) {
  return value === true || value === 1 || value === "1" || value === "true";
}
function fieldState(field: FieldSpec) {
  const config = field.config || {};
  const modifiers = (config.modifiers || config.fieldInfo?.modifiers || config.field_info?.modifiers || {}) as Dictionary;
  const dynamic = runtimeFieldState(modifiers, modifierPatch[field.code] || {}, values);
  return {
    invisible: /^chatter\.field\.\d+$/i.test(field.code) || field.hidden === true || staticFlag(config.invisible) || staticFlag(config.componentConfig?.invisible) || dynamic.invisible,
    readonly: field.readonly || staticFlag(config.readonly) || staticFlag(config.componentConfig?.readonly) || dynamic.readonly,
    required: field.required || staticFlag(config.required) || staticFlag(config.componentConfig?.required) || dynamic.required,
  };
}
function onchange(field: FieldSpec) {
  if (!model.value) return;
  const sequence = ++onchangeSequence;
  if (model.value === "project.cost.plan" && field.code === "project_id") {
    values.boq_version_id = false;
  }
  const dependencies = new Set<string>([field.code]);
  fields.value.forEach((candidate) => {
    const config = candidate.config || {};
    const descriptor = config.fieldDescriptor || config.field_descriptor || {};
    const entry = config.relationEntry || config.relation_entry || config.fieldInfo?.relation_entry || config.field_info?.relation_entry || {};
    const domain = config.domain ?? config.domainRaw ?? config.domain_raw ?? descriptor.domain ?? descriptor.domainRaw ?? descriptor.domain_raw ?? entry.domain;
    if (domain && JSON.stringify(domain).includes(field.code)) dependencies.add(candidate.code);
  });
  if (field.code === "project_id") {
    ["boq_version_id", "contract_id", "settlement_id", "material_settlement_id", "payment_request_id", "wbs_id", "parent_id", "worker_id", "usage_id"].forEach((code) => dependencies.add(code));
  }
  dependencies.forEach((code) => { if (code !== field.code && Object.prototype.hasOwnProperty.call(values, code)) values[code] = false; });
  void triggerOnchange({
    model: model.value,
    values: Object.fromEntries(fields.value.map((item) => [item.code, normalizeFieldWriteValue(values[item.code], item)])),
    fieldName: field.code,
    recordId: recordId.value || undefined,
  })
    .then((result) => {
      if (sequence !== onchangeSequence) return;
      Object.assign(values, result.patch || result.values || result.value || {});
      if (result.modifiers_patch) Object.assign(modifierPatch, result.modifiers_patch);
      dependencies.forEach((code) => {
        if (code !== field.code && Object.prototype.hasOwnProperty.call(values, code)) values[code] = false;
      });
      (result.warnings || []).forEach((warning) => ElMessage.warning(warning.message || warning.title || "字段联动提示"));
    })
    .catch(() => undefined);
}
function relationIds(value: unknown): number[] {
  if (!Array.isArray(value)) {
    const id = Number(value || 0);
    return Number.isInteger(id) && id > 0 ? [id] : [];
  }
  return value.flatMap((item) => {
    if (Array.isArray(item)) {
      if (item.length === 2 && typeof item[0] === "number" && typeof item[1] === "string") return [item[0]];
      if (Number(item[0]) === 6 && Array.isArray(item[2])) return item[2];
      if (Number(item[0]) === 1 || Number(item[0]) === 4) return [item[1]];
      return item.length === 1 ? [item[0]] : [];
    }
    if (item && typeof item === "object") return [(item as Dictionary).id];
    return [item];
  }).map(Number).filter((id) => Number.isInteger(id) && id > 0);
}
function relationValueHasLabels(value: unknown, type: string): boolean {
  if (type === "many2one") return Array.isArray(value) && value.length >= 2 && typeof value[1] === "string";
  if (!Array.isArray(value) || !value.length) return true;
  return value.every((item) => Array.isArray(item) && item.length >= 2 && typeof item[1] === "string");
}
async function hydrateRelationLabels(data: Dictionary) {
  const tasks = fields.value
    .filter((field) => ["many2one", "many2many"].includes(field.type) && field.relation)
    .map(async (field) => {
      const current = data[field.code];
      if (relationValueHasLabels(current, field.type)) return;
      const ids = relationIds(current);
      if (!ids.length) return;
      try {
        const result = await relationOptions({
          model: field.relation,
          domain: [["id", "in", ids]],
          limit: ids.length,
          fields: ["id", "display_name", "name"],
          context: formSourceContext(contract.value),
        });
        const rows = result.records || result.rows || [];
        const labeled = rows
          .map((row) => [Number(row.id), String(row.display_name || row.name || row.id)] as [number, string])
          .filter(([id]) => id > 0);
        if (!labeled.length) return;
        data[field.code] = field.type === "many2one" ? labeled[0] : labeled;
      } catch {
        // Keep raw IDs when a related model is not readable in the current scope.
      }
    });
  await Promise.all(tasks);
}
let loadSequence = 0;
async function load() {
  const sequence = ++loadSequence;
  loading.value = true;
  error.value = "";
  try {
    const raw = await loadPageContract({
      model: model.value,
      recordId: recordId.value || undefined,
      actionId: Number(route.query.action_id || 0) || undefined,
      menuId: Number(route.query.menu_id || 0) || undefined,
      renderProfile: mode.value,
      source: wizardMode.value ? "action" : undefined,
    });
    if (sequence !== loadSequence) return;
    contract.value = decodePageContract(raw);
    Object.keys(modifierPatch).forEach((key) => delete modifierPatch[key]);
    Object.keys(values).forEach((key) => delete values[key]);
    const data = (contract.value.dataContract.mainData ||
      contract.value.dataContract.main_data ||
      contract.value.raw.record ||
      {}) as Dictionary;
    if (recordId.value) {
      const missing = fields.value
        .filter((field) => !field.hidden && !Object.prototype.hasOwnProperty.call(data, field.code))
        .map((field) => field.code);
      if (missing.length) {
        try {
          const requestedFields = Array.from(
            new Set(fields.value.map((field) => field.code).concat(missing)),
          );
          const hydrated = await readRecord(
            model.value,
            recordId.value,
            requestedFields,
            formSourceContext(contract.value),
          );
          const row = hydrated.records?.[0] || hydrated.rows?.[0];
          if (row) Object.assign(data, row);
        } catch {
          // Contract data remains authoritative when scoped read hydration is unavailable.
        }
      }
      await hydrateRelationLabels(data);
    }
    Object.assign(values, data);
    original.value = { ...values };
    recordVersion.value = String(
      data.record_version ||
        data.write_date ||
        data.__last_update ||
        contract.value.raw.record_version ||
        "",
    );
    activeTab.value = tabs.value[0]?.key || "main";
  } catch (cause) {
    if (sequence !== loadSequence) return;
    error.value = cause instanceof Error ? cause.message : "详情契约加载失败";
    traceId.value = (cause as any)?.traceId || "";
  } finally {
    if (sequence === loadSequence) loading.value = false;
  }
}
async function save() {
  if (operationBusy.value) return;
  saving.value = true;
  try {
    const valid = await formRef.value?.validate().catch(() => false);
    if (valid === false) return;
    const payload = buildWritableFormValues(fields.value, values);
    const context = formSourceContext(contract.value);
    const result = recordId.value
      ? await updateRecord(
          model.value,
          recordId.value,
          payload,
          context,
          recordVersion.value,
        )
      : await createRecord(model.value, payload, context);
    ElMessage.success("保存成功");
    const id = Number((result as Dictionary).id || recordId.value || 0);
    if (!recordId.value && id)
      await router.replace({
        name: "Record",
        params: { model: model.value, id },
        query: { ...route.query, mode: "view" },
      });
    else {
      mode.value = "view";
      await load();
    }
  } catch (cause) {
    ElMessage.error(cause instanceof Error ? cause.message : "保存失败");
  } finally {
    saving.value = false;
  }
}
async function remove() {
  if (!recordId.value || operationBusy.value) return;
  removing.value = true;
  try {
    await ElMessageBox.confirm("删除后不可恢复，确定继续吗？", "删除确认", {
      type: "warning",
    });
    await deleteRecords(model.value, [recordId.value]);
    ElMessage.success("删除成功");
    await router.back();
  } catch (cause) {
    if (cause !== "cancel")
      ElMessage.error(cause instanceof Error ? cause.message : "删除失败");
  } finally {
    removing.value = false;
  }
}
async function runAction(action: BusinessAction) {
  if (!action.button || operationBusy.value) return;
  activeActionKey.value = action.key;
  try {
    let actionRecordId = recordId.value;
    if (!actionRecordId && mode.value === "create" && wizardMode.value) {
      const payload = buildWritableFormValues(fields.value, values);
      const defaultProjectId = Number(route.query.default_project_id || route.query.project_id || 0);
      if (!payload.project_id && defaultProjectId > 0 && fields.value.some((field) => field.code === "project_id")) {
        payload.project_id = defaultProjectId;
      }
      const created = await createRecord(model.value, payload, sourceContext.value);
      actionRecordId = Number((created as Dictionary).id || 0) || null;
    }
    if (!actionRecordId) return;
    if (await inlineActionTabsRef.value?.prepareAction(action)) return;
    if ((action.intent === "ui.contract" || action.intent === "open") && (action.target?.route || action.target?.action_id || action.target?.actionId || action.target?.model)) {
      if (await navigateActionResult({ effect: { type: "navigate", target: action.target } }, action)) return;
    }
    if (action.confirmMessage || action.type === "danger")
      await ElMessageBox.confirm(
        action.confirmMessage || `确定执行“${action.label}”吗？`,
        "操作确认",
        { type: "warning" },
      );
    let result: Dictionary;
    const actionIntent = String(action.intent || "").trim();
    if (!usesExecuteButtonIntent(actionIntent, action.button) && actionIntent)
      result = await (
        await import("@/api/odoo")
      ).intent(actionIntent, {
        model: model.value,
        record_id: actionRecordId,
        ...action.params,
      });
    else
      result = await executeButton({
        model: model.value,
        recordId: actionRecordId,
        button: {
          ...action.button,
          action_id: action.actionId || action.button.action_id || action.button.actionId,
          backend_identity: action.backendIdentity || action.button.backend_identity || action.button.backendIdentity,
          source_widget_id: action.sourceWidgetId || action.button.source_widget_id || action.button.sourceWidgetId,
        },
        values: { ...values },
        meta: {
          action_id: routeQueryNumber("action_id"),
          menu_id: routeQueryNumber("menu_id"),
        },
      });
    if (await navigateActionResult(result, action)) return;
    ElMessage.success(`${action.label}已完成`);
    await load();
  } catch (cause) {
    if (cause !== "cancel")
      ElMessage.error(
        cause instanceof Error ? cause.message : `${action.label}失败`,
      );
  } finally {
    activeActionKey.value = "";
  }
}

async function runSemanticAction(action: BusinessAction) {
  if (action.key === 'form.save' || action.actionId === 'form.save') {
    await save();
    return;
  }
  await runAction(action);
}

function runCommandAction(key: string) {
  const action = groupedActions.value.overflow
    .find((candidate) => candidate.key === key);
  if (action) void runAction(action);
}

function runConfigurationAction(key: string) {
  const action = groupedActions.value.configuration.find((candidate) => candidate.key === key);
  if (action) void runAction(action);
}

async function navigateActionResult(result: Dictionary, action: BusinessAction) {
  if (await inlineActionTabsRef.value?.handleActionResult(result, action)) return true;
  const envelope = result && typeof result === "object" ? result : {};
  const effect = envelope.effect && typeof envelope.effect === "object" ? envelope.effect : {};
  const payload = envelope.result && typeof envelope.result === "object" ? envelope.result : {};
  const target = effect.target && typeof effect.target === "object"
    ? effect.target
    : payload.target && typeof payload.target === "object" ? payload.target : {};
  const entryTarget = target.entry_target && typeof target.entry_target === "object"
    ? target.entry_target
    : payload.entry_target && typeof payload.entry_target === "object" ? payload.entry_target : {};
  const targetRoute = String(entryTarget.route || target.route || payload.route || "").trim();
  if (targetRoute) {
    await router.push(targetRoute);
    return true;
  }
  const kind = String(target.kind || "").toLowerCase();
  const targetModel = String(
    target.model || entryTarget.model || payload.model || payload.res_model || model.value,
  ).trim();
  const targetId = Number(target.id || target.record_id || payload.id || payload.res_id || 0);
  const actionId = Number(
    target.action_id || target.actionId || target.action_ref || entryTarget.action_id || entryTarget.actionId || entryTarget.action_ref || payload.action_id || payload.window_action_id || 0,
  );
  const menuId = Number(target.menu_id || target.menuId || entryTarget.menu_id || entryTarget.menuId || routeQueryNumber("menu_id") || 0);
  const projectId = relationValueId(values.project_id);
  const query: Dictionary = {
    ...route.query,
    action_id: actionId || undefined,
    menu_id: menuId || undefined,
    project_id: projectId || undefined,
    default_project_id: projectId || undefined,
  };
  if (kind === "record" && targetModel && targetId > 0) {
    await router.push({ name: "Record", params: { model: targetModel, id: targetId }, query: { ...query, mode: "view" } });
    return true;
  }
  if (targetModel && (kind === "create" || String(target.mode || entryTarget.mode || "").toLowerCase() === "create")) {
    await router.push({ name: "Record", params: { model: targetModel, id: "new" }, query: { ...query, mode: "create" } });
    return true;
  }
  if (actionId > 0 && (kind === "action" || action.intent === "ui.contract" || action.intent === "open")) {
    await router.push({ name: "Action", params: { actionId: String(actionId) }, query: { ...query, model: targetModel || undefined } });
    return true;
  }
  return false;
}

function routeQueryNumber(key: string) {
  const value = Number(route.query[key] || 0);
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function relationValueId(value: unknown) {
  const raw = Array.isArray(value) ? value[0] : value && typeof value === "object" ? (value as Dictionary).id : value;
  const id = Number(raw || 0);
  return Number.isInteger(id) && id > 0 ? id : 0;
}
watch(
  () => [route.params.model, route.params.id, route.query.mode, route.query.action_id, route.query.menu_id],
  ([, , nextMode]) => {
    if (nextMode === "view" || nextMode === "edit" || nextMode === "create") mode.value = nextMode;
    void load();
  },
  { immediate: true },
);
</script>
<style scoped>
.record-page {
  display: grid;
  gap: 16px;
  width: 100%;
  max-width: none;
  min-width: 0;
  margin: 0;
  overflow-x: hidden;
}
.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 0 4px 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.heading-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.heading-title h1 {
  font-size: 24px;
  line-height: 1.25;
  margin: 12px 0 4px;
}
.record-name {
  max-width: min(720px, 70vw);
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.heading-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.heading-status-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.record-form {
  background: #fff;
  padding: 20px 24px 24px;
  border-radius: 4px;
  min-width: 0;
  max-width: 100%;
  border: 1px solid var(--el-border-color-lighter);
}
.record-content {
  min-width: 0;
}
.record-content-tabs :deep(.el-tabs__content) {
  overflow: visible;
}
.record-content-tabs :deep(.el-tabs__header),
.record-content-tabs :deep(.el-tabs__nav-wrap),
.record-content-tabs :deep(.el-tabs__nav-scroll) {
  max-width: 100%;
  overflow: hidden;
}
.record-content-tabs :deep(.el-tabs__nav) {
  max-width: 100%;
  display: flex;
  flex-wrap: wrap;
}
.record-content-tabs :deep(.el-tabs__item) {
  max-width: 100%;
  min-width: 0;
  height: auto;
  min-height: 40px;
  line-height: 20px;
  padding-top: 10px;
  padding-bottom: 10px;
  white-space: normal;
  overflow-wrap: anywhere;
  text-align: center;
}
.record-content-tabs--single :deep(.el-tabs__header) {
  display: none;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  min-width: 0;
  max-width: 100%;
  column-gap: 28px;
  row-gap: 3px;
}
.field-grid .el-form-item {
  margin-bottom: 18px;
}
.field-grid .field-wide {
  grid-column: 1 / -1;
}
.readonly-value {
  min-height: 32px;
  padding: 7px 11px;
  background: #f5f7fa;
  border-radius: 4px;
  color: #606266;
  line-height: 18px;
  white-space: pre-wrap;
  word-break: break-word;
}
.full-width {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}
.business-command-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
  max-width: 100%;
  margin-top: 10px;
  padding-top: 18px;
  border-top: 1px solid var(--el-border-color-lighter);
  flex-wrap: wrap;
}
.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.record-chatter {
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  padding: 20px 24px 24px;
}
.record-chatter__header {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.record-chatter__header h2 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 17px;
  font-weight: 600;
}
@media (max-width: 900px) {
  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .heading-actions {
    width: 100%;
    justify-content: flex-start;
  }
  .heading-actions .el-button {
    flex: 1;
  }
  .field-grid {
    grid-template-columns: 1fr;
  }
  .record-form {
    padding: 18px;
  }
  .record-name {
    max-width: 100%;
  }
  .record-page {
    margin: 0;
  }
}
</style>
