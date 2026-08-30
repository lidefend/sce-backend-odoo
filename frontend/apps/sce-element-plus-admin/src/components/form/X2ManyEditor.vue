<template>
  <div v-if="isTags" class="x2many-editor x2many-editor--tags">
    <div class="x2many-toolbar">
      <span>{{ relationCount }} 个关联</span>
      <el-button v-if="disabled && allowViewEdit" size="small" :icon="Plus" @click="requestOrAdd">添加</el-button>
    </div>
    <relation-field
      :field="field"
      :model-value="modelValue"
      multiple
      :disabled="disabled"
      :values="values"
      :context="context"
      :domain-patch="domainPatch"
      @update:model-value="$emit('update:modelValue', $event)"
      @change="$emit('change')"
    />
  </div>
  <div v-else class="x2many-editor">
    <div class="x2many-toolbar">
      <span>{{ rows.length }} 条明细</span
      ><el-button v-if="!disabled || allowViewEdit" size="small" :icon="Plus" @click="requestOrAdd"
        >添加一行</el-button
      >
    </div>
    <el-table :data="rows" size="small" stripe>
      <el-table-column label="状态" width="72" align="center">
        <template #default="{ row }">
          <el-tag size="small" effect="plain" :type="rowStateType(row)">{{ rowStateLabel(row) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column
        v-for="column in columns"
        :key="column.name"
        :label="column.widget === 'handle' ? '' : column.label"
        :min-width="column.widget === 'handle' ? 54 : 130"
      >
        <template #default="{ row, $index }">
          <button
            v-if="column.widget === 'handle'"
            type="button"
            class="drag-handle"
            draggable="true"
            aria-label="拖动排序"
            @dragstart="startDrag($event, $index)"
            @dragover.prevent
            @drop.prevent="dropRow($index, column.name)"
          ><el-icon><Rank /></el-icon></button>
          <el-switch
            v-else-if="column.type === 'boolean'"
            v-model="row[column.name]"
            :disabled="disabled || column.readonly"
            @change="emitRows"
          />
          <el-select
            v-else-if="column.type === 'selection'"
            v-model="row[column.name]"
            :disabled="disabled || column.readonly"
            @change="emitRows"
          >
            <el-option v-for="option in column.selection" :key="String(option.value)" :label="option.label" :value="option.value" />
          </el-select>
          <relation-field
            v-else-if="column.type === 'many2one'"
            :field="columnField(column)"
            :model-value="row[column.name]"
            :disabled="disabled || column.readonly"
            :values="relationValues(row)"
            :context="context"
            :domain-patch="column.domain"
            @update:model-value="row[column.name] = $event"
            @change="emitRows"
          />
          <el-input-number
            v-else-if="['integer', 'float', 'monetary'].includes(column.type)"
            v-model="row[column.name]"
            :disabled="disabled || column.readonly"
            controls-position="right"
            @change="emitRows"
          />
          <el-date-picker
            v-else-if="column.type === 'date'"
            v-model="row[column.name]"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled="disabled || column.readonly"
            @change="emitRows"
          />
          <el-input
            v-else
            v-model="row[column.name]"
            :disabled="disabled || column.readonly"
            @change="emitRows"
          />
        </template>
      </el-table-column>
      <el-table-column v-if="!disabled" label="操作" width="70"
        ><template #default="{ $index }"
          ><el-button link type="danger" @click="removeRow($index)"
            >删除</el-button
          ></template
        ></el-table-column
      >
      <template #empty
        ><el-empty description="暂无明细" :image-size="48"
      /></template>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Plus, Rank } from "@element-plus/icons-vue";
import RelationField from "./RelationField.vue";
import { listData } from "@/api/odoo";
import type { Dictionary, FieldSpec } from "@/types/contracts";

interface ColumnSpec {
  name: string;
  label: string;
  type: string;
  relation?: string;
  readonly?: boolean;
  widget?: string;
  domain?: unknown;
  config?: Dictionary;
  selection: Array<{ label: string; value: unknown }>;
}

const responsibilityRoles = [
  ["manager", "项目经理"], ["cost", "成本负责人"], ["finance", "财务"],
  ["cashier", "出纳"], ["material", "材料员"], ["safety", "安全员"],
  ["quality", "质检员"], ["document", "资料员"],
].map(([value, label]) => ({ value, label }));

const relationColumnMap: Record<string, ColumnSpec[]> = {
  "project.responsibility": [
    { name: "role_key", label: "角色", type: "selection", selection: responsibilityRoles },
    { name: "user_id", label: "责任人", type: "many2one", relation: "res.users", selection: [] },
    { name: "note", label: "说明/授权范围", type: "char", selection: [] },
  ],
  "project.collaborator": [
    { name: "partner_id", label: "协作成员", type: "many2one", relation: "res.partner", selection: [] },
  ],
};
const props = defineProps<{
  field: FieldSpec;
  modelValue: unknown;
  disabled?: boolean;
  allowViewEdit?: boolean;
  values?: Dictionary;
  context?: Dictionary;
  domainPatch?: unknown;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: unknown];
  change: [];
  "request-edit": [continueAction?: () => void];
}>();
const rows = ref<Dictionary[]>([]);
const draggingIndex = ref<number | null>(null);
const relationCount = computed(() => normalize(props.modelValue).length);
const isTags = computed(() => props.field.type === "many2many" || String(
  props.field.config.componentKey || props.field.config.component_key || "",
) === "sc.select.tags");
const relation = computed(() => String(
  props.field.relation ||
  props.field.config.relation ||
  props.field.config.fieldInfo?.relation ||
  props.field.config.field_info?.relation ||
  "",
));
const columns = computed<ColumnSpec[]>(() => {
  const config = props.field.config || {};
  const entry =
    config.relationEntry ||
    config.relation_entry ||
    config.fieldInfo?.relation_entry ||
    {};
  const subview =
    config.subview ||
    config.subView ||
    entry.subview ||
    entry.search_dialog ||
    {};
  const tree = subview.tree && typeof subview.tree === "object" && !Array.isArray(subview.tree)
    ? subview.tree as Dictionary
    : {};
  const treeColumns = Array.isArray(tree.column_occurrences) && tree.column_occurrences.length
    ? tree.column_occurrences
    : Array.isArray(tree.columns) && tree.columns.length
      ? tree.columns
      : Array.isArray(tree.columns_schema)
        ? tree.columns_schema
        : [];
  const source = treeColumns.length
    ? treeColumns
    : Array.isArray(subview.columns)
      ? subview.columns
      : Array.isArray(config.columns)
        ? config.columns
        : [];
  if (source.length)
    return source
      .slice(0, 8)
      .map((item: Dictionary | string) => {
        const row = typeof item === "string" ? { name: item } : item;
        const attributes = row.attributes && typeof row.attributes === "object" && !Array.isArray(row.attributes)
          ? row.attributes as Dictionary
          : {};
        const descriptor = row.fieldInfo || row.field_info || row.fieldDescriptor || row.field_descriptor || {};
        const name = String(row.name || row.field || row.fieldCode || row.field_code || descriptor.name || "").trim();
        const type = String(row.type || row.fieldType || row.field_type || row.ttype || descriptor.type || descriptor.ttype || "char").toLowerCase();
        const modifiers = row.modifiers && typeof row.modifiers === "object" && !Array.isArray(row.modifiers)
          ? row.modifiers as Dictionary
          : {};
        return {
          name,
          label: localizedLabel(name) || String(attributes.string || row.label || row.string || descriptor.label || descriptor.string || name),
          type,
          relation: String(row.relation || descriptor.relation || ""),
          readonly: row.readonly === true || attributes.readonly === true || modifiers.readonly === true,
          widget: String(row.widget || attributes.widget || "").toLowerCase(),
          domain: row.domain ?? row.domainRaw ?? row.domain_raw ?? descriptor.domain,
          config: { ...descriptor, ...row },
          selection: normalizeSelection(row.selection || row.choices || descriptor.selection),
        };
      })
      .filter((item: ColumnSpec) => item.name && !isHiddenColumn(item));
  if (relationColumnMap[relation.value]) return relationColumnMap[relation.value];
  const keys = [
    ...new Set(
      rows.value.flatMap((row) =>
        Object.keys(row).filter((key) => !["id", "res_id", "project_id", "company_id"].includes(key)),
      ),
    ),
  ].slice(0, 8);
  if (!keys.length && relation.value)
    return [{ name: "display_name", label: "关联记录", type: "char", readonly: true, selection: [] }];
  return keys.map((name) => ({
    name,
    label: fallbackLabel(name),
    type: typeof rows.value[0]?.[name] === "number" ? "float" : "char",
    readonly: name === "display_name",
    selection: [],
  }));
});
function normalize(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (Array.isArray(item) && typeof item[0] === "number") {
      if (item.length === 2 && typeof item[1] === "string")
        return [{ id: item[0], display_name: item[1] }];
      if ([2, 3].includes(item[0]) && item.length === 2) return [];
      if (item[0] === 6 && Array.isArray(item[2]))
        return item[2].map((id: unknown) => ({ id: Number(id) }));
      return [
        {
          id: Number(item[1] || 0) || undefined,
          ...(item[2] && typeof item[2] === "object" ? item[2] : {}),
        },
      ];
    }
    return item && typeof item === "object"
      ? [{ ...(item as Dictionary) }]
      : Number(item) > 0
        ? [{ id: Number(item) }]
        : [];
  });
}
function emitRows() {
  const writableColumns = new Set(columns.value.filter((column) => !column.readonly).map((column) => column.name));
  emit(
    "update:modelValue",
    rows.value.map((row) => Object.fromEntries(
      Object.entries(row).filter(([key]) => key === "id" || writableColumns.has(key)),
    )),
  );
  emit("change");
}
function requestOrAdd() {
  if (props.disabled) {
    if (props.allowViewEdit) emit("request-edit", isTags.value ? undefined : addRow);
    return;
  }
  addRow();
}
function rowStateLabel(row: Dictionary) {
  return Number(row.id || 0) > 0 ? "未变更" : "新增";
}
function rowStateType(row: Dictionary) {
  return Number(row.id || 0) > 0 ? "info" : "success";
}
function addRow() {
  const row = Object.fromEntries(
    columns.value.map((column: { name: string; type: string }) => [
      column.name,
      column.type === "boolean" ? false : "",
    ]),
  );
  rows.value.push(row);
  emitRows();
}
function removeRow(index: number) {
  rows.value.splice(index, 1);
  emitRows();
}
function startDrag(event: DragEvent, index: number) {
  draggingIndex.value = index;
  event.dataTransfer?.setData("text/plain", String(index));
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}
function dropRow(index: number, sequenceField: string) {
  const source = draggingIndex.value;
  draggingIndex.value = null;
  if (source === null || source === index) return;
  const [row] = rows.value.splice(source, 1);
  rows.value.splice(index, 0, row);
  rows.value.forEach((item, rowIndex) => { item[sequenceField] = (rowIndex + 1) * 10; });
  emitRows();
}
function normalizeSelection(value: unknown): Array<{ label: string; value: unknown }> {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => Array.isArray(item)
    ? [{ value: item[0], label: String(item[1] ?? item[0]) }]
    : item && typeof item === "object"
      ? [{ value: (item as Dictionary).value, label: String((item as Dictionary).label || (item as Dictionary).value) }]
      : []);
}
function fallbackLabel(name: string) {
  return ({
    display_name: "关联记录", name: "名称", login: "账号", partner_id: "协作成员", user_id: "责任人", role_key: "角色", note: "说明/授权范围",
    child_ids: "联系人", bank_ids: "账户明细", category_id: "标签", project_ids: "关联项目", task_ids: "任务", company_ids: "所属公司", comment: "备注",
    tender_name: "投标名称", tender_round: "投标轮次", owner_id: "招标人/业主", bid_amount: "投标报价", amount_total: "清单合计", state: "状态", deadline: "投标截止时间",
  } as Record<string, string>)[name] || name;
}
function localizedLabel(name: string) {
  return ({
    display_name: "关联记录", name: "名称", login: "账号", partner_id: "协作成员", user_id: "责任人", role_key: "角色", note: "说明/授权范围",
    child_ids: "联系人", bank_ids: "账户明细", category_id: "标签", project_ids: "关联项目", task_ids: "任务", company_ids: "所属公司", comment: "备注",
    phone: "电话", mobile: "手机", email: "邮箱", acc_number: "账号", bank_id: "银行", acc_holder_name: "账户持有人",
    tender_name: "投标名称", tender_round: "投标轮次", owner_id: "招标人/业主", bid_amount: "投标报价", amount_total: "清单合计", state: "状态", deadline: "投标截止时间",
  } as Record<string, string>)[name] || "";
}
function isHiddenColumn(column: ColumnSpec) {
  const config = column.config || {};
  const modifiers = config.modifiers && typeof config.modifiers === "object" && !Array.isArray(config.modifiers)
    ? config.modifiers as Dictionary
    : {};
  return [config.invisible, config.hidden, config.column_invisible, config.optional === "hide", config.attributes?.optional === "hide", modifiers.invisible, modifiers.column_invisible]
    .some((value) => value === true || value === 1 || value === "1" || value === "true");
}
function columnField(column: ColumnSpec): FieldSpec {
  return {
    code: column.name,
    label: column.label,
    type: "many2one",
    required: false,
    readonly: Boolean(column.readonly),
    relation: String(column.relation || ""),
    selection: [],
    config: {
      ...(column.config || {}),
      ...(column.domain !== undefined ? { domain: column.domain } : {}),
    },
  };
}
function relationValues(row: Dictionary): Dictionary {
  return { ...(props.values || {}), ...row };
}
async function hydrateRows() {
  const ids = rows.value.map((row) => Number(row.id || 0)).filter((id) => id > 0);
  if (!relation.value || !ids.length) return;
  const fields = [...new Set(["id", ...columns.value.map((column) => column.name)])];
  try {
    const result = await listData({
      model: relation.value,
      fields,
      domain: [["id", "in", ids]],
      limit: ids.length,
    });
    const byId = new Map((result.records || result.rows || []).map((row) => [Number(row.id), row]));
    rows.value = rows.value.map((row) => ({ ...row, ...(byId.get(Number(row.id)) || {}) }));
  } catch {
    // Keep the ID-only rows visible when the relation is not readable.
  }
}
watch(
  () => props.modelValue,
  (value) => {
    rows.value = normalize(value);
    void hydrateRows();
  },
  { immediate: true, deep: true },
);
</script>

<style scoped>
.x2many-editor {
  width: 100%;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  overflow: hidden;
}
.x2many-toolbar {
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.drag-handle { display: inline-grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 3px; background: transparent; color: var(--el-text-color-secondary); cursor: grab; }
.drag-handle:hover { background: var(--el-fill-color); color: var(--el-color-primary); }
.drag-handle:active { cursor: grabbing; }
</style>
