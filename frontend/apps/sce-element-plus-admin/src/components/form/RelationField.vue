<template>
  <div class="relation-field">
    <el-select
      :model-value="normalizedValue"
      :multiple="multiple"
      filterable
      remote
      clearable
      reserve-keyword
      :remote-method="search"
      :loading="loading"
      :disabled="disabled"
      class="relation-select"
      @visible-change="onVisible"
      @change="updateValue"
    >
      <el-option
        v-for="option in options"
        :key="option.value"
        :label="option.label"
        :value="option.value"
      />
    </el-select>
    <el-tooltip content="搜索更多">
      <el-button :icon="Search" :disabled="disabled || !relation" @click="openSearchDialog" />
    </el-tooltip>
    <el-tooltip v-if="canOpen" content="打开关联记录"
      ><el-button :icon="View" :disabled="!selectedId" @click="openSelected"
    /></el-tooltip>
      <el-tooltip v-if="canCreate" content="新建关联记录"
      ><el-button :icon="Plus" @click="createRelated"
    /></el-tooltip>

    <el-dialog v-model="dialogOpen" :title="dialogTitle" width="min(920px, 92vw)" destroy-on-close>
      <div class="search-toolbar">
        <el-input
          v-model="dialogKeyword"
          clearable
          autofocus
          placeholder="输入名称或关键字搜索"
          @keyup.enter="runDialogSearch"
        />
        <el-button type="primary" :icon="Search" :loading="dialogLoading" @click="runDialogSearch">搜索</el-button>
      </div>
      <div v-if="dialogColumns.length > 1" class="filter-toolbar">
        <el-select v-model="filterField" placeholder="筛选字段" class="filter-field">
          <el-option v-for="column in dialogColumns" :key="column.name" :label="column.label" :value="column.name" />
        </el-select>
        <el-select v-model="filterOperator" class="filter-operator">
          <el-option v-for="operator in filterOperators" :key="operator.value" :label="operator.label" :value="operator.value" />
        </el-select>
        <el-input v-model="filterValue" clearable placeholder="筛选值" @keyup.enter="addFilter" />
        <el-button @click="addFilter">添加条件</el-button>
      </div>
      <div v-if="activeFilters.length" class="active-filters">
        <el-tag v-for="(item, index) in activeFilters" :key="`${item.field}-${index}`" closable @close="removeFilter(index)">
          {{ item.label }} {{ item.operatorLabel }} {{ item.value }}
        </el-tag>
      </div>
      <el-table
        v-loading="dialogLoading"
        :data="dialogPageRows"
        row-key="id"
        highlight-current-row
        @row-click="selectDialogRow"
        @row-dblclick="confirmDialogRow"
      >
        <el-table-column width="54" align="center">
          <template #default="{ row }"><el-radio v-model="selectedDialogId" :value="Number(row.id)" /></template>
        </el-table-column>
        <el-table-column v-for="column in dialogColumns" :key="column.name" :label="column.label" :min-width="column.name === primaryColumn ? 220 : 140">
          <template #default="{ row }">{{ displayCell(row[column.name] ?? row.values?.[column.name]) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!dialogLoading && !dialogRows.length" description="未找到匹配记录" />
      <div class="dialog-pagination">
        <span>共 {{ dialogRows.length }} 条</span>
        <el-pagination v-if="dialogRows.length" v-model:current-page="dialogPage" v-model:page-size="dialogPageSize" layout="prev, pager, next" :total="dialogRows.length" />
      </div>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedDialogId" @click="confirmDialogSelection">选择</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Plus, Search, View } from "@element-plus/icons-vue";
import { relationOptions } from "@/api/odoo";
import { resolveRelationDomain } from "@/runtime/modifiers";
import type { Dictionary, FieldSpec } from "@/types/contracts";

const props = defineProps<{
  field: FieldSpec;
  modelValue: unknown;
  multiple?: boolean;
  disabled?: boolean;
  values?: Dictionary;
  context?: Dictionary;
  domainPatch?: unknown;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: unknown];
  change: [];
}>();
const router = useRouter();
const loading = ref(false);
const options = ref<Array<{ value: number; label: string }>>([]);
const dialogOpen = ref(false);
const dialogLoading = ref(false);
const dialogKeyword = ref("");
const dialogRows = ref<Dictionary[]>([]);
const selectedDialogId = ref<number | null>(null);
const dialogPage = ref(1);
const dialogPageSize = ref(20);
const filterField = ref("");
const filterOperator = ref("ilike");
const filterValue = ref("");
const activeFilters = ref<Array<{ field: string; label: string; operator: string; operatorLabel: string; value: string }>>([]);
let searchSequence = 0;
const entry = computed<Dictionary>(
  () =>
    props.field.config.relationEntry ||
    props.field.config.relation_entry ||
    props.field.config.fieldInfo?.relation_entry ||
    {},
);
const relation = computed(
  () => props.field.relation || String(entry.value.model || ""),
);
const dialogTitle = computed(() => String(entry.value.ui_labels?.dialog_title || `${props.field.label || "关联记录"}：搜索更多`));
const dialogColumns = computed(() => {
  const rows: unknown[] = Array.isArray(entry.value.search_dialog?.columns) ? entry.value.search_dialog.columns : [];
  const normalized = rows
    .map((item) => {
      const row = item && typeof item === "object" ? item as Dictionary : {};
      const name = String(row.name || row.field || "").trim();
      return name ? { name, label: String(row.label || row.string || name) } : null;
    })
    .filter((item): item is { name: string; label: string } => Boolean(item));
  if (normalized.length) return normalized.slice(0, 8);
  return [{ name: "display_name", label: "名称" }];
});
const primaryColumn = computed(() => dialogColumns.value[0]?.name || "display_name");
const filterOperators: Array<{ value: string; label: string }> = [
  { value: "ilike", label: "包含" },
  { value: "=", label: "等于" },
  { value: "!=", label: "不等于" },
  { value: "not ilike", label: "不包含" },
  { value: ">=", label: "大于等于" },
  { value: "<=", label: "小于等于" },
];
const dialogPageRows = computed(() => {
  const start = (dialogPage.value - 1) * dialogPageSize.value;
  return dialogRows.value.slice(start, start + dialogPageSize.value);
});
const normalizedValue = computed(() =>
  props.multiple ? ids(props.modelValue) : ids(props.modelValue)[0],
);
const selectedId = computed(() => ids(props.modelValue)[0]);
const canOpen = computed(
  () =>
    entry.value.can_open !== false &&
    entry.value.can_read !== false &&
    Boolean(relation.value),
);
const canCreate = computed(
  () =>
    !props.disabled &&
    entry.value.can_create === true &&
    String(entry.value.create_mode || "page") !== "disabled",
);

function ids(value: unknown): number[] {
  return relationRows(value).flatMap((item) => {
    if (Array.isArray(item)) {
      const code = commandCode(item);
      if (code === 6) return Array.isArray(item[2]) ? item[2] : [item[2]];
      if (code !== null && [4, 1].includes(code)) return [item[1]];
      if (code !== null) return [];
      if (item.length === 2 && typeof item[1] === "string") return [item[0]];
      return [];
    }
    if (item && typeof item === "object") return [(item as Dictionary).id];
    return [typeof item === "string" && item.includes(",") ? item.split(",")[0] : item];
  }).map(Number).filter((id) => id > 0);
}
function seed(value: unknown) {
  relationRows(value).forEach((item) => {
    const tuple = Array.isArray(item) ? item as unknown[] : [];
    const code = tuple.length ? commandCode(tuple) : null;
    const commandIds: unknown[] = code === 6
      ? Array.isArray(tuple[2]) ? tuple[2] : [tuple[2]]
      : code !== null && [1, 4].includes(code) ? [tuple[1]] : [];
    if (commandIds.length) {
      commandIds.forEach((commandId) => seedOption(commandId));
      return;
    }
    const id = Number(
      Array.isArray(item) ? item[0] : item && typeof item === "object" ? (item as Dictionary).id : item,
    );
    const label = Array.isArray(item)
      ? String(item[1] ?? item[0])
      : item && typeof item === "object"
        ? String(
            (item as Dictionary).display_name ||
              (item as Dictionary).name ||
              id,
          )
        : String(item || "");
    if (id > 0 && !options.value.some((option) => option.value === id)) options.value.push({ value: id, label });
  });
}
function commandCode(item: unknown[]): number | null {
  if (!item.length || !Number.isInteger(Number(item[0]))) return null;
  const code = Number(item[0]);
  if (code === 6) return Array.isArray(item[2]) || (item[1] === 0 && Number.isFinite(Number(item[2]))) ? code : null;
  if (![0, 1, 2, 3, 4, 5].includes(code)) return null;
  return Number.isFinite(Number(item[1])) ? code : null;
}
function seedOption(value: unknown, label?: unknown) {
  const id = Number(value);
  if (id > 0 && !options.value.some((option) => option.value === id)) options.value.push({ value: id, label: String(label ?? id) });
}
function relationRows(value: unknown): unknown[] {
  if (Array.isArray(value) && value.length === 2 && typeof value[0] === "number" && typeof value[1] === "string") return [value];
  return Array.isArray(value) ? value : [value];
}
async function search(term = "") {
  if (!relation.value) return;
  const sequence = ++searchSequence;
  loading.value = true;
  try {
    const dialog = entry.value.search_dialog || {};
    const sourceDomain = props.domainPatch ?? entry.value.domain ?? props.field.config.domain ?? [];
    const result = await relationOptions({
      model: relation.value,
      search: term,
      domain: resolveRelationDomain(sourceDomain, props.values || {}, props.context || {}, props.field.code),
      limit: Number(dialog.limit || 60),
      fields: dialog.read_fields || ["id", "display_name", "name"],
      order: String(dialog.order || ""),
      context: entry.value.context || {},
    });
    if (sequence !== searchSequence) return;
    const rows = result.records || result.rows || [];
    options.value = rows
      .map((row) => ({
        value: Number(row.id),
        label: String(row.display_name || row.name || row.label || row.id),
      }))
      .filter((option) => option.value > 0);
    seed(props.modelValue);
  } finally {
    if (sequence === searchSequence) loading.value = false;
  }
}
function openSearchDialog() {
  if (props.disabled || !relation.value) return;
  dialogOpen.value = true;
  dialogKeyword.value = "";
  selectedDialogId.value = selectedId.value || null;
  dialogPage.value = 1;
  activeFilters.value = [];
  filterField.value = dialogColumns.value[0]?.name || "";
  filterValue.value = "";
  void runDialogSearch();
}
function addFilter() {
  const value = filterValue.value.trim();
  if (!filterField.value || !value) return;
  const column = dialogColumns.value.find((item: { name: string; label: string }) => item.name === filterField.value);
  const operator = filterOperators.find((item) => item.value === filterOperator.value) || filterOperators[0];
  activeFilters.value = [
    ...activeFilters.value.filter((item) => item.field !== filterField.value),
    { field: filterField.value, label: column?.label || filterField.value, operator: operator.value, operatorLabel: operator.label, value },
  ];
  filterValue.value = "";
  void runDialogSearch();
}
function removeFilter(index: number) {
  activeFilters.value.splice(index, 1);
  void runDialogSearch();
}
async function runDialogSearch() {
  if (!relation.value) return;
  const sequence = ++searchSequence;
  dialogLoading.value = true;
  try {
    const dialog = entry.value.search_dialog || {};
    const baseDomain = props.domainPatch ?? entry.value.domain ?? props.field.config.domain ?? [];
    const filters = activeFilters.value.map((item) => [item.field, item.operator, item.operator === "ilike" || item.operator === "not ilike" ? `%${item.value}%` : item.value]);
    const result = await relationOptions({
      model: relation.value,
      search: dialogKeyword.value,
      domain: [...(Array.isArray(baseDomain) ? baseDomain : []), ...filters],
      limit: Number(dialog.limit || 120),
      fields: Array.from(new Set(["id", "display_name", "name", ...(Array.isArray(dialog.read_fields) ? (dialog.read_fields as unknown[]).map(String) : []), ...dialogColumns.value.map((item: { name: string; label: string }) => item.name)])),
      order: String(dialog.order || ""),
      context: entry.value.context || {},
    });
    if (sequence !== searchSequence) return;
    dialogRows.value = (result.records || result.rows || []).filter((row) => Number(row.id) > 0);
    dialogPage.value = 1;
  } finally {
    if (sequence === searchSequence) dialogLoading.value = false;
  }
}
function selectDialogRow(row: Dictionary) {
  selectedDialogId.value = Number(row.id) || null;
}
function confirmDialogRow(row: Dictionary) {
  selectDialogRow(row);
  confirmDialogSelection();
}
function confirmDialogSelection() {
  const row = dialogRows.value.find((item) => Number(item.id) === selectedDialogId.value);
  if (!row || !selectedDialogId.value) return;
  const label = displayCell(row[primaryColumn.value] ?? row.display_name ?? row.name ?? selectedDialogId.value);
  if (!options.value.some((option) => option.value === selectedDialogId.value)) options.value.push({ value: selectedDialogId.value, label });
  updateValue(selectedDialogId.value);
  dialogOpen.value = false;
}
function displayCell(value: unknown): string {
  if (value === false || value === null || value === undefined || value === "") return "";
  if (Array.isArray(value)) return String(value[1] ?? value[0] ?? "");
  if (typeof value === "object") {
    const row = value as Dictionary;
    return String(row.display_name || row.name || row.label || row.id || "");
  }
  return String(value);
}
function onVisible(visible: boolean) {
  if (visible && !options.value.length) void search();
}
function updateValue(value: unknown) {
  emit("update:modelValue", value);
  emit("change");
}
function openSelected() {
  if (selectedId.value)
    void router.push({
      name: "Record",
      params: { model: relation.value, id: selectedId.value },
      query: {
        mode: "view",
        action_id: entry.value.action_id || undefined,
        menu_id: entry.value.menu_id || undefined,
      },
    });
}
function createRelated() {
  void router.push({
    name: "Record",
    params: { model: relation.value, id: "new" },
    query: {
      mode: "create",
      action_id: entry.value.action_id || undefined,
      menu_id: entry.value.menu_id || undefined,
      return_url: encodeURIComponent(router.currentRoute.value.fullPath),
    },
  });
}
watch(() => props.modelValue, seed, { immediate: true, deep: true });
watch(() => [relation.value, JSON.stringify(ids(props.modelValue))], () => {
  void hydrateSelectedLabels();
}, { immediate: true });
watch(
  () => props.domainPatch,
  (next, previous) => {
    if (JSON.stringify(next) === JSON.stringify(previous)) return;
    searchSequence += 1;
    options.value = [];
    if (relation.value) void search();
  },
  { deep: true },
);
async function hydrateSelectedLabels() {
  const selected = ids(props.modelValue);
  if (!relation.value || !selected.length) return;
  const dialog = entry.value.search_dialog || {};
  try {
    const result = await relationOptions({
      model: relation.value,
      domain: [["id", "in", selected]],
      limit: selected.length,
      fields: Array.from(new Set(["id", "display_name", "name", ...(Array.isArray(dialog.read_fields) ? (dialog.read_fields as unknown[]).map(String) : [])])),
      order: String(dialog.order || ""),
      context: entry.value.context || {},
    });
    const rows = result.records || result.rows || [];
    rows.forEach((row) => {
      const id = Number(row.id);
      if (!id) return;
      const label = String(row.display_name || row.name || id);
      const existing = options.value.find((option) => option.value === id);
      if (existing) existing.label = label;
      else options.value.push({ value: id, label });
    });
  } catch {
    // Keep the raw id visible when the relation model is not readable.
  }
}
</script>

<style scoped>
.relation-field {
  display: flex;
  gap: 6px;
  width: 100%;
}
.relation-select {
  flex: 1;
  min-width: 0;
}
.search-toolbar,
.filter-toolbar,
.active-filters,
.dialog-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
}
.search-toolbar { margin-bottom: 12px; }
.search-toolbar .el-input { flex: 1; }
.filter-toolbar { margin-bottom: 10px; }
.filter-field { width: 180px; }
.filter-operator { width: 120px; }
.active-filters { flex-wrap: wrap; margin-bottom: 12px; }
.dialog-pagination { justify-content: space-between; margin-top: 12px; }
@media (max-width: 720px) {
  .filter-toolbar { flex-wrap: wrap; }
  .filter-field,
  .filter-operator { width: calc(50% - 4px); }
  .filter-toolbar > .el-input { width: 100%; }
}
</style>
