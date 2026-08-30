<template>
  <div class="action-page">
    <div class="page-heading">
      <div>
        <el-breadcrumb
          ><el-breadcrumb-item>业务菜单</el-breadcrumb-item
          ><el-breadcrumb-item>{{ title }}</el-breadcrumb-item></el-breadcrumb
        >
        <h1>{{ title }}</h1>
      </div>
      <div class="heading-actions">
        <el-button :loading="loading" :icon="Refresh" @click="load"
          >刷新</el-button
        ><el-button
          v-if="canCreate"
          type="primary"
          :icon="Plus"
          @click="openRecord('new', 'create')"
          >新建</el-button
        >
      </div>
    </div>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      ><div class="error-detail">
        <span v-if="traceId">Trace ID: {{ traceId }}</span
        ><el-button link type="primary" @click="load">重试</el-button>
      </div></el-alert
    >
    <el-card v-else shadow="never" class="content-card">
      <div v-if="presetFilters.length" class="preset-bar">
        <span>快捷筛选</span
        ><el-check-tag
          v-for="filter in presetFilters"
          :key="filter.key"
          :checked="activePresetKeys.includes(filter.key)"
          @change="togglePreset(filter.key)"
          >{{ filter.label }}</el-check-tag
        >
      </div>
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="search"
            clearable
            placeholder="搜索当前列表"
            class="search-input"
            :prefix-icon="Search"
            @keyup.enter="searchRows"
            @clear="searchRows"
          /><el-button type="primary" @click="searchRows">查询</el-button
          ><el-button
            v-if="filterFields.length && selectorEnabled('filter', 'search')"
            :icon="Filter"
            @click="filterVisible = true"
            >筛选<el-badge
              v-if="activeFilters.length"
              :value="activeFilters.length" /></el-button
          ><el-button v-if="hasFilters" text @click="resetFilters"
            >重置</el-button
          >
        </div>
        <div class="toolbar-right">
          <span class="total-count">共 {{ total }} 条</span
          ><el-select
            v-if="savedFilters.length"
            v-model="activeSavedFilter"
            clearable
            placeholder="已保存筛选"
            class="saved-select"
            @change="applySavedFilter"
            ><el-option
              v-for="item in savedFilters"
              :key="item.key"
              :label="item.label"
              :value="item.key" /></el-select
          ><el-button
            v-if="selectorEnabled('favorite', 'favorites')"
            :icon="Star"
            @click="favoriteVisible = true"
            >收藏</el-button
          ><el-select
            v-if="groupOptions.length && selectorEnabled('group_by', 'groupby')"
            v-model="groupBy"
            clearable
            placeholder="分组依据"
            class="group-select"
            @change="searchRows"
            ><el-option
              v-for="item in groupOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value" /></el-select
          ><el-dropdown v-if="viewOptions.length" @command="changeView"
            ><el-button
              >{{ viewLabels[viewMode] || viewMode
              }}<el-icon class="el-icon--right"
                ><ArrowDown /></el-icon></el-button
            ><template #dropdown
              ><el-dropdown-menu
                ><el-dropdown-item
                  v-for="item in viewOptions"
                  :key="item"
                  :command="item"
                  >{{ viewLabels[item] || item }}</el-dropdown-item
                ></el-dropdown-menu
              ></template
            ></el-dropdown
          ><el-button :icon="Setting" @click="columnVisible = true"
            >列设置</el-button
          ><el-button
            :icon="Download"
            :disabled="!rows.length"
            @click="exportCurrent()"
            >导出</el-button
          >
        </div>
      </div>
      <div v-if="activeFilters.length" class="active-filters">
        <el-tag
          v-for="filter in activeFilters"
          :key="filter.id"
          closable
          @close="removeFilter(filter.id)"
          >{{ filter.label }} {{ filter.operator }}
          {{ displayValue(filter.value) }}</el-tag
        >
      </div>
      <div v-if="selectedIds.length" class="batch-bar">
        <span>已选 {{ selectedIds.length }} 条</span
        ><el-button
          v-for="action in batchActions"
          :key="action.key"
          size="small"
          :type="action.type"
          :loading="batchLoading"
          @click="runBatch(action.key)"
          >{{ action.label }}</el-button
        ><el-button text size="small" @click="selectedRows = []"
          >清除选择</el-button
        >
      </div>
      <section v-if="groupBy" class="grouped-view">
        <el-collapse v-model="expandedGroups"
          ><el-collapse-item
            v-for="group in groupedRows"
            :key="group.key"
            :name="group.key"
            ><template #title
              ><strong>{{ group.label }}</strong
              ><el-tag size="small" effect="plain">{{ group.count }} 条</el-tag
              ><span class="group-total">{{
                aggregateText(group.aggregates)
              }}</span></template
            ><el-table :data="group.rows" stripe
              ><el-table-column
                v-for="field in visibleFields"
                :key="field.code"
                :prop="field.code"
                :label="field.label"
                min-width="140"
                ><template #default="{ row }">
                  <el-tag v-if="isStatusField(field)" size="small" effect="plain" :type="fieldTagType(field, row[field.code])">
                    {{ displayFieldValue(row[field.code], field.code, field.selection) }}
                  </el-tag>
                  <template v-else>{{ displayFieldValue(row[field.code], field.code, field.selection) }}</template>
                </template></el-table-column
              ><el-table-column label="操作" width="90"
                ><template #default="{ row }"
                  ><el-button
                    link
                    type="primary"
                    @click="openRecord(String(row.id), 'view')"
                    >详情</el-button
                  ></template
                ></el-table-column
              ></el-table
            ></el-collapse-item
          ></el-collapse
        >
      </section>
      <el-table
        v-else-if="hierarchyEnabled"
        :data="treeRows"
        row-key="id"
        :tree-props="{ children: 'children' }"
        default-expand-all
        stripe
        ><el-table-column
          v-for="field in visibleFields"
          :key="field.code"
          :prop="field.code"
          :label="field.label"
          min-width="150"
          ><template #default="{ row }">
            <el-tag v-if="isStatusField(field)" size="small" effect="plain" :type="fieldTagType(field, row[field.code])">
              {{ displayFieldValue(row[field.code], field.code, field.selection) }}
            </el-tag>
            <template v-else>{{ displayFieldValue(row[field.code], field.code, field.selection) }}</template>
          </template></el-table-column
        ><el-table-column label="操作" width="100"
          ><template #default="{ row }"
            ><div class="row-actions"><el-button
              link
              type="primary"
              @click="openRecord(String(row.id), 'view')"
              >打开</el-button
            ></div
            ></template
          ></el-table-column
        ></el-table
      >
      <el-table
        v-else-if="viewMode === 'list'"
        v-loading="loading"
        :data="rows"
        stripe
        row-key="id"
        class="list-table-no-vertical"
        @selection-change="selectedRows = $event"
        @sort-change="sortChange"
        ><el-table-column type="selection" width="48" /><el-table-column
          v-for="field in visibleFields"
          :key="field.code"
          :prop="field.code"
          :label="field.label"
          :min-width="['text', 'html'].includes(field.type) ? 220 : 140"
          show-overflow-tooltip
          :sortable="false"
          ><template #header
            ><button
              type="button"
              class="sort-header"
              :class="{ 'is-active': activeSortField === field.code }"
              :disabled="field.sortable === false"
              @click="toggleSort(field)"
            >{{ field.label }}<el-icon v-if="activeSortField === field.code"><ArrowDown v-if="activeSortDirection === 'desc'" /><ArrowUp v-else /></el-icon></button>
          </template><template #default="{ row }"
            ><el-tag
              v-if="isStatusField(field) || ['selection', 'many2one'].includes(field.type)"
              size="small"
              effect="plain"
              :type="fieldTagType(field, row[field.code])"
              >{{ displayFieldValue(row[field.code], field.code, field.selection) }}</el-tag
            ><span v-else>{{ displayFieldValue(row[field.code], field.code, field.selection) }}</span></template
          ></el-table-column
        ><el-table-column label="操作" fixed="right" width="170"
          ><template #default="{ row }"
            ><div class="row-actions"><el-button
              link
              type="primary"
              @click="openRecord(String(row.id), 'view')"
              >详情</el-button
            ><el-button
              v-if="canWrite"
              link
              type="primary"
              @click="openRecord(String(row.id), 'edit')"
              >编辑</el-button
            ><el-dropdown
              v-if="rowActions.length"
              @command="(key: string) => runRowAction(row, key)"
              ><el-button link type="primary"
                >更多<el-icon><ArrowDown /></el-icon></el-button
              ><template #dropdown
                ><el-dropdown-menu
                  ><el-dropdown-item
                    v-for="action in rowActions"
                    :key="action.key"
                    :command="action.key"
                    :disabled="action.enabled === false"
                    >{{ action.label }}</el-dropdown-item
                  ></el-dropdown-menu
                ></template
              ></el-dropdown></div
            ></template
          ></el-table-column
        ><template #empty
          ><el-empty
            description="暂无符合条件的数据"
            :image-size="90" /></template
      ></el-table>
      <div v-else-if="viewMode === 'cards'" class="card-grid">
        <el-card v-for="row in rows" :key="row.id" shadow="hover"
          ><h3>{{ recordTitle(row) }}</h3>
          <dl>
            <template
              v-for="field in visibleFields.slice(0, 6)"
              :key="field.code"
              ><dt>{{ field.label }}</dt>
              <dd>
                <el-tag v-if="isStatusField(field)" size="small" effect="plain" :type="fieldTagType(field, row[field.code])">
                  {{ displayFieldValue(row[field.code], field.code, field.selection) }}
                </el-tag>
                <template v-else>{{ displayFieldValue(row[field.code], field.code, field.selection) }}</template>
              </dd></template
            >
          </dl>
          <el-button
            link
            type="primary"
            @click="openRecord(String(row.id), 'view')"
            >详情</el-button
          ></el-card
        >
      </div>
      <div v-else-if="viewMode === 'kanban'" class="kanban-grid">
        <el-card
          v-for="lane in kanbanLanes"
          :key="lane.key"
          shadow="never"
          class="kanban-lane"
          ><template #header
            ><strong
              >{{ lane.label }}
              <el-tag size="small">{{ lane.rows.length }}</el-tag></strong
            ></template
          ><el-card
            v-for="row in lane.rows"
            :key="row.id"
            shadow="hover"
            class="kanban-card"
            @click="openRecord(String(row.id), 'view')"
            ><h3>{{ recordTitle(row) }}</h3>
            <span v-for="field in visibleFields.slice(0, 3)" :key="field.code">
              {{ field.label }}：
              <el-tag v-if="isStatusField(field)" size="small" effect="plain" :type="fieldTagType(field, row[field.code])">
                {{ displayFieldValue(row[field.code], field.code, field.selection) }}
              </el-tag>
              <template v-else>{{ displayFieldValue(row[field.code], field.code, field.selection) }}</template>
            </span
            ></el-card
          ></el-card
        >
      </div>
      <advanced-collection-view
        v-else
        :mode="viewMode as any"
        :rows="rows"
        :fields="fields"
        :config="advancedConfig"
        @open="(row) => openRecord(String(row.id), 'view')"
      />
      <div v-if="!groupBy" class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadRows"
          @size-change="loadRows"
        />
      </div>
    </el-card>
    <el-dialog v-model="filterVisible" title="筛选条件" width="560px"
      ><el-form label-width="95px"
        ><el-form-item
          v-for="item in filterDraft"
          :key="item.field"
          :label="item.label"
          ><el-select v-model="item.operator" class="operator-select"
            ><el-option
              v-for="op in item.operators"
              :key="op.value"
              :label="op.label"
              :value="op.value" /></el-select
          ><el-select v-if="item.choices.length" v-model="item.value" clearable
            ><el-option
              v-for="choice in item.choices"
              :key="String(choice.value)"
              :label="choice.label"
              :value="choice.value" /></el-select
          ><el-switch
            v-else-if="item.type === 'boolean'"
            v-model="item.value" /><el-date-picker
            v-else-if="item.type.includes('date')"
            v-model="item.value"
            type="date"
            value-format="YYYY-MM-DD" /><el-input
            v-else
            v-model="item.value" /></el-form-item></el-form
      ><template #footer
        ><el-button @click="filterVisible = false">取消</el-button
        ><el-button type="primary" @click="applyFilters"
          >应用筛选</el-button
        ></template
      ></el-dialog
    >
    <el-dialog v-model="columnVisible" title="列显示设置" width="480px"
      ><el-checkbox-group v-model="visibleColumnCodes" class="column-grid"
        ><el-checkbox
          v-for="field in fields"
          :key="field.code"
          :value="field.code"
          >{{ field.label }}</el-checkbox
        ></el-checkbox-group
      ><template #footer
        ><el-button
          @click="visibleColumnCodes = fields.map((field) => field.code)"
          >全选</el-button
        ><el-button type="primary" @click="saveColumns"
          >保存</el-button
        ></template
      ></el-dialog
    >
    <el-dialog v-model="favoriteVisible" title="保存当前筛选" width="420px"
      ><el-form label-position="top"
        ><el-form-item label="名称"
          ><el-input v-model="favoriteName" /></el-form-item
        ><el-form-item
          ><el-checkbox v-model="favoriteDefault"
            >设为默认</el-checkbox
          ></el-form-item
        ></el-form
      ><template #footer
        ><el-button @click="favoriteVisible = false">取消</el-button
        ><el-button
          type="primary"
          :disabled="!favoriteName.trim()"
          @click="saveFavorite"
          >保存</el-button
        ></template
      ></el-dialog
    >
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  ArrowDown,
  ArrowUp,
  Download,
  Filter,
  Plus,
  Refresh,
  Search,
  Setting,
  Star,
} from "@element-plus/icons-vue";
import AdvancedCollectionView from "@/components/action/AdvancedCollectionView.vue";
import {
  batchUpdateRecords,
  deleteRecords,
  executeButton,
  exportCsv,
  getUserViewPreference,
  listData,
  loadPageContract,
  saveSearchFavorite,
  setUserViewPreference,
} from "@/api/odoo";
import type { Dictionary, FieldSpec } from "@/types/contracts";
import {
  decodePageContract,
  effectiveRights,
  pageTitle,
  resolveActions,
  resolveListFieldSpecs,
} from "@/utils/contract";
import { displayFieldValue, displayValue, downloadText, fieldLabel } from "@/utils/format";
import { statusTagType } from "@/utils/widget";

interface ActiveFilter {
  id: string;
  field: string;
  label: string;
  operator: string;
  value: any;
}
const route = useRoute();
const router = useRouter();
const loading = ref(false);
const error = ref("");
const traceId = ref("");
const contract = ref(decodePageContract({}));
const rows = ref<Dictionary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const search = ref("");
const order = ref("");
const groupBy = ref("");
const groupedRaw = ref<Dictionary[]>([]);
const viewMode = ref("list");
const selectedRows = ref<Dictionary[]>([]);
const filterVisible = ref(false);
const activeFilters = ref<ActiveFilter[]>([]);
const filterDraft = ref<any[]>([]);
const activePresetKeys = ref<string[]>([]);
const activeSavedFilter = ref("");
const savedDomain = ref<unknown[]>([]);
const batchLoading = ref(false);
const columnVisible = ref(false);
const visibleColumnCodes = ref<string[]>([]);
const favoriteVisible = ref(false);
const favoriteName = ref("");
const favoriteDefault = ref(false);
const expandedGroups = ref<string[]>([]);
const model = computed(() =>
  String(contract.value.pageInfo.model || route.query.model || ""),
);
const title = computed(() => pageTitle(contract.value, "业务列表"));
const formOnlyAction = computed(() => {
  const raw = contract.value.actionContract.view_modes || contract.value.actionContract.viewMode || contract.value.pageInfo.view_modes || contract.value.pageInfo.viewMode || "";
  const modes = (Array.isArray(raw) ? raw : String(raw).split(","))
    .map((item) => String(item).trim().toLowerCase())
    .filter(Boolean);
  return /(^|\.)wizard$/i.test(model.value) || (modes.includes("form") && modes.every((mode) => mode === "form"));
});
const fields = computed<FieldSpec[]>(() =>
  resolveListFieldSpecs(contract.value),
);
const visibleFields = computed(() =>
  fields.value.filter(
    (field) =>
      !field.hidden &&
      (!visibleColumnCodes.value.length ||
        visibleColumnCodes.value.includes(field.code)) &&
      (field.defaultVisible !== false || visibleColumnCodes.value.includes(field.code)),
  ),
);
const rights = computed(() => effectiveRights(contract.value));
const canCreate = computed(() => rights.value.create === true);
const canWrite = computed(() => rights.value.write !== false);
const rowActions = computed(() => resolveActions(contract.value, "row"));
function isStatusField(field: FieldSpec) {
  return /(^|_)(state|status|stage|lifecycle_state|workflow_state|approval_state)$/.test(field.code.toLowerCase());
}
function fieldTagType(field: FieldSpec, value: unknown) {
  return isStatusField(field)
    ? statusTagType(displayFieldValue(value, field.code, field.selection, field.type))
    : undefined;
}
const searchContract = computed<Dictionary>(
  () => contract.value.searchContract || {},
);
const selectorStatuses = computed<Dictionary[]>(
  () =>
    contract.value.statusContract.selectorStatus ||
    contract.value.statusContract.selector_status ||
    [],
);
const filterFields = computed(() => {
  const custom = searchContract.value.custom?.filters?.fields || [];
  return custom
    .map((item: Dictionary) => ({
      field: String(item.field || item.name),
      label: fieldLabel(String(item.field || item.name || ''), item.label || item.string || item.field),
      type: String(item.type || "char"),
      operator: String(item.operators?.[0]?.value || "="),
      value: "",
      operators: (item.operators || [{ value: "=", label: "等于" }]).map(
        (op: Dictionary) => ({
          value: String(op.value),
          label: String(op.label || op.value),
        }),
      ),
      choices: (item.choices || []).map((choice: Dictionary) => ({
        value: choice.value,
        label: String(choice.label || choice.value),
      })),
    }))
    .filter((item: any) => item.field);
});
const presetFilters = computed(() =>
  ((searchContract.value.filters || []) as Dictionary[])
    .filter((item) => Array.isArray(item.domain) && item.domain.length)
    .map((item, index) => ({
      key: String(item.key || index),
      label: String(item.label || item.name || "筛选"),
      domain: item.domain as unknown[],
    })),
);
const savedFilters = computed(() =>
  ((searchContract.value.saved_filters || []) as Dictionary[]).map(
    (item, index) => ({
      key: String(item.key || item.name || index),
      label: String(item.label || item.name || "收藏筛选"),
      domain: (item.domain || []) as unknown[],
    }),
  ),
);
const groupOptions = computed(() =>
  ((searchContract.value.group_by || []) as Dictionary[])
    .map((item) => ({
      value: String(item.field || item.name),
      label: fieldLabel(String(item.field || item.name || ''), item.label || item.string || item.field),
    }))
    .filter((item) => item.value),
);
const baseDomain = computed<unknown[]>(
  () =>
    contract.value.dataContract.domain ||
    contract.value.actionContract.domain ||
    contract.value.dataContract.dataSource?.primary?.params?.domain ||
    [],
);
function normalizeOrder(raw: unknown) {
  const allowed = new Set(["id", ...fields.value.map((field) => field.code)]);
  const clauses = String(raw || "")
    .split(",")
    .map((clause) => clause.trim())
    .filter(Boolean)
    .flatMap((clause) => {
      const [field, direction = "asc"] = clause.split(/\s+/);
      const normalizedField = String(field || "").trim();
      const normalizedDirection = String(direction || "asc").toLowerCase();
      if (!allowed.has(normalizedField) || !["asc", "desc"].includes(normalizedDirection)) return [];
      return [`${normalizedField} ${normalizedDirection}`];
    });
  return clauses.join(", ");
}
const defaultOrder = computed(() => {
  const raw =
    contract.value.dataContract.dataSource?.primary?.params?.order ||
    contract.value.dataContract.data_source?.primary?.params?.order ||
    "";
  return normalizeOrder(raw) || "id asc";
});
const activeSortField = computed(() => String(order.value).split(/\s+/)[0] || "");
const activeSortDirection = computed(() =>
  String(order.value).toLowerCase().includes(" desc") ? "desc" : "asc",
);
const activeDomain = computed(() => [
  ...baseDomain.value,
  ...savedDomain.value,
  ...presetFilters.value
    .filter((item) => activePresetKeys.value.includes(item.key))
    .flatMap((item) => item.domain),
  ...activeFilters.value.map((item) => [item.field, item.operator, item.value]),
]);
const hasFilters = computed(() =>
  Boolean(
    search.value ||
    activeFilters.value.length ||
    activePresetKeys.value.length ||
    savedDomain.value.length,
  ),
);
const selectedIds = computed(() =>
  selectedRows.value.map((row) => Number(row.id)).filter(Boolean),
);
const surfacePolicy = computed<Dictionary>(
  () =>
    contract.value.actionContract.surfacePolicies ||
    contract.value.actionContract.surface_policies ||
    {},
);
const batchPolicy = computed<Dictionary>(
  () =>
    surfacePolicy.value.batch_policy || surfacePolicy.value.batchPolicy || {},
);
const batchActions = computed(() => {
  const labels: Dictionary = {
    export: "导出选中",
    archive: "批量归档",
    activate: "批量启用",
    delete: "批量删除",
    assign: "批量指派",
  };
  return (batchPolicy.value.available_actions || []).map((item: any) => {
    const row = typeof item === "object" ? item : {};
    const key = String(row.key || row.action || item);
    return {
      key,
      label: String(row.label || labels[key] || key),
      type: (/delete|reject/.test(key)
        ? "danger"
        : key === "archive"
          ? "warning"
          : "primary") as any,
    };
  });
});
const declaredViews = computed(() => {
  const raw =
    contract.value.actionContract.view_modes ||
    contract.value.pageInfo.view_modes ||
    contract.value.pageInfo.viewType ||
    "list";
  return (Array.isArray(raw) ? raw : String(raw).split(","))
    .map((item) => String(item).toLowerCase())
    .map((item) =>
      item === "tree" ? "list" : item === "card" ? "cards" : item,
    )
    .filter((item) =>
      [
        "list",
        "cards",
        "kanban",
        "pivot",
        "graph",
        "calendar",
        "gantt",
        "activity",
      ].includes(item),
    );
});
const viewOptions = computed(() => [
  ...new Set(declaredViews.value.length ? declaredViews.value : ["list"]),
]);
const viewLabels: Dictionary = {
  list: "列表",
  cards: "卡片",
  kanban: "看板",
  pivot: "透视视图",
  graph: "图表视图",
  calendar: "日历视图",
  gantt: "甘特视图",
  activity: "活动视图",
};
const runtimeContext = computed<Dictionary>(
  () =>
    contract.value.runtimeContract.sourceContext?.context ||
    contract.value.runtimeContract.source_context?.context ||
    {},
);
const hierarchyEnabled = computed(() =>
  Boolean(
    runtimeContext.value.hierarchical_worksheet ||
    (runtimeContext.value.hierarchy_levels || []).length,
  ),
);
const advancedConfig = computed<Dictionary>(
  () =>
    contract.value.layoutContract.views?.[viewMode.value] ||
    contract.value.layoutContract.listProfile ||
    {},
);
const groupedRows = computed(() =>
  groupedRaw.value.map((group, index) => ({
    key: String(group.group_key || index),
    label: String(group.label || displayValue(group.value) || "未分类"),
    count: Number(group.total_count ?? group.count ?? 0),
    rows: group.sample_rows || [],
    aggregates: group.aggregates || {},
  })),
);
const parentField = computed(() =>
  fields.value.find((field) => /parent_id|parent$/.test(field.code)),
);
const treeRows = computed(() => {
  const map = new Map<number, Dictionary>();
  rows.value.forEach((row) =>
    map.set(Number(row.id), { ...row, children: [] }),
  );
  const roots: Dictionary[] = [];
  map.forEach((row) => {
    const raw = parentField.value ? row[parentField.value.code] : null;
    const parentId = Number(Array.isArray(raw) ? raw[0] : raw || 0);
    if (parentId && map.has(parentId)) map.get(parentId)!.children.push(row);
    else roots.push(row);
  });
  return roots;
});
const kanbanLanes = computed(() => {
  const field =
    groupBy.value ||
    fields.value.find((item) => /state|stage|status/.test(item.code))?.code ||
    "";
  const map = new Map<string, Dictionary[]>();
  rows.value.forEach((row) => {
    const key = displayValue(row[field]);
    map.set(key, [...(map.get(key) || []), row]);
  });
  return [...map].map(([key, laneRows]) => ({
    key,
    label: key,
    rows: laneRows,
  }));
});
function selectorEnabled(...keys: string[]) {
  const row = selectorStatuses.value.find((item) =>
    keys.includes(String(item.selector || item.key || "").toLowerCase()),
  );
  return row ? row.visible !== false && row.disabled !== true : true;
}
function recordTitle(row: Dictionary) {
  return String(
    row.display_name ||
      row.name ||
      row.title ||
      row.subject ||
      `记录 #${row.id || ""}`,
  );
}
function searchRows() {
  page.value = 1;
  void loadRows();
}
function togglePreset(key: string) {
  activePresetKeys.value = activePresetKeys.value.includes(key)
    ? activePresetKeys.value.filter((item) => item !== key)
    : [...activePresetKeys.value, key];
  searchRows();
}
function applySavedFilter(key: string) {
  const item = savedFilters.value.find((filter) => filter.key === key);
  savedDomain.value = item?.domain || [];
  searchRows();
}
function resetFilters() {
  search.value = "";
  activeFilters.value = [];
  activePresetKeys.value = [];
  activeSavedFilter.value = "";
  savedDomain.value = [];
  searchRows();
}
function applyFilters() {
  activeFilters.value = filterDraft.value
    .filter((item) => item.value !== "" && item.value != null)
    .map((item) => ({
      id: `${item.field}-${Date.now()}-${Math.random()}`,
      field: item.field,
      label: item.label,
      operator: item.operator,
      value: item.value,
    }));
  filterVisible.value = false;
  searchRows();
}
function removeFilter(id: string) {
  activeFilters.value = activeFilters.value.filter((item) => item.id !== id);
  searchRows();
}
function changeView(mode: string) {
  viewMode.value = mode;
}
function sortChange({ prop, order: direction }: any) {
  const field = fields.value.find((candidate) => candidate.code === String(prop));
  if (!field || field.sortable === false) return;
  order.value = direction
    ? `${prop} ${direction === "ascending" ? "asc" : "desc"}`
    : defaultOrder.value;
  searchRows();
}
function toggleSort(field: FieldSpec) {
  if (field.sortable === false) return;
  const currentField = activeSortField.value;
  const currentDirection = activeSortDirection.value;
  const nextDirection = currentField === field.code && currentDirection === "asc" ? "desc" : "asc";
  order.value = `${field.code} ${nextDirection}`;
  searchRows();
}
function openRecord(id: string, mode: string) {
  void router.push({
    name: "Record",
    params: { model: model.value, id },
    query: {
      ...route.query,
      action_id: String(route.params.actionId || route.query.action_id || ""),
      menu_id: String(route.query.menu_id || ""),
      mode,
    },
  });
}
function aggregateText(aggregates: Dictionary) {
  return Object.entries(aggregates)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${displayValue(value)}`)
    .join(" · ");
}
async function load() {
  loading.value = true;
  error.value = "";
  try {
    contract.value = decodePageContract(
      await loadPageContract({
        actionId:
          Number(route.params.actionId || route.query.action_id || 0) ||
          undefined,
        menuId: Number(route.query.menu_id || 0) || undefined,
        model: String(route.query.model || "") || undefined,
        source: "action",
      }),
    );
    if (formOnlyAction.value) {
      await router.replace({
        name: "Record",
        params: { model: model.value, id: "new" },
        query: {
          ...route.query,
          model: undefined,
          mode: "create",
          action_id: String(route.params.actionId || route.query.action_id || ""),
          wizard: "1",
        },
      });
      return;
    }
    order.value = defaultOrder.value;
    viewMode.value = viewOptions.value.includes(viewMode.value)
      ? viewMode.value
      : viewOptions.value[0];
    filterDraft.value = filterFields.value.map((item: any) => ({ ...item }));
    await loadColumnPreference();
    await loadRows();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "页面加载失败";
    traceId.value = (cause as any)?.traceId || "";
  } finally {
    loading.value = false;
  }
}
async function loadRows() {
  if (!model.value || formOnlyAction.value || /(^|\.)wizard$/i.test(model.value)) return;
  loading.value = true;
  try {
    const request = (requestedOrder: string) => listData({
      model: model.value,
      fields: ["id", ...fields.value.map((field) => field.code)],
      domain: activeDomain.value,
      order: requestedOrder,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
      searchTerm: search.value,
      groupBy: groupBy.value || undefined,
      needAggregates: ["pivot", "graph"].includes(viewMode.value),
    });
    let result;
    try {
      result = await request(normalizeOrder(order.value));
    } catch (cause) {
      // A stale server-side default order must not blank the whole list.
      // Retry once without ordering; user-selected valid sorts still work.
      const message = cause instanceof Error ? cause.message : String(cause || "");
      if (!/order\s*无效|invalid\s+order/i.test(message)) throw cause;
      order.value = "";
      result = await request("");
    }
    rows.value = result.records || result.rows || [];
    groupedRaw.value = result.grouped_rows || [];
    expandedGroups.value = groupedRows.value.map((group) => group.key);
    total.value = Number(result.total || rows.value.length);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "列表数据加载失败";
  } finally {
    loading.value = false;
  }
}
async function loadColumnPreference() {
  const actionId =
    Number(route.params.actionId || route.query.action_id || 0) || undefined;
  try {
    const result = await getUserViewPreference({
      model: model.value,
      actionId,
    });
    const codes =
      result.preference?.visible_columns || result.preference?.columns;
    visibleColumnCodes.value = Array.isArray(codes)
      ? codes.map(String)
      : fields.value.filter((field) => field.defaultVisible !== false && !field.hidden).map((field) => field.code);
  } catch {
    visibleColumnCodes.value = fields.value.filter((field) => field.defaultVisible !== false && !field.hidden).map((field) => field.code);
  }
}
async function saveColumns() {
  await setUserViewPreference({
    model: model.value,
    actionId:
      Number(route.params.actionId || route.query.action_id || 0) || undefined,
    preference: { visible_columns: visibleColumnCodes.value },
  });
  columnVisible.value = false;
  ElMessage.success("列设置已保存");
}
async function saveFavorite() {
  await saveSearchFavorite({
    model: model.value,
    name: favoriteName.value.trim(),
    domain: activeDomain.value,
    actionId:
      Number(route.params.actionId || route.query.action_id || 0) || undefined,
    isDefault: favoriteDefault.value,
  });
  favoriteVisible.value = false;
  favoriteName.value = "";
  ElMessage.success("筛选已收藏");
  await load();
}
async function runRowAction(row: Dictionary, key: string) {
  const action = rowActions.value.find((item) => item.key === key);
  if (!action || action.enabled === false) return;
  if (action.type === "danger")
    await ElMessageBox.confirm(`确定执行“${action.label}”吗？`, "操作确认", {
      type: "warning",
    });
  await executeButton({
    model: model.value,
    recordId: Number(row.id),
    button: action.button,
  });
  ElMessage.success(`${action.label}已完成`);
  await loadRows();
}
async function runBatch(key: string) {
  batchLoading.value = true;
  try {
    if (key === "export") return await exportCurrent(selectedIds.value);
    if (key === "delete") {
      await ElMessageBox.confirm(
        `确定删除选中的 ${selectedIds.value.length} 条记录吗？`,
        "批量删除",
        { type: "warning" },
      );
      await deleteRecords(model.value, selectedIds.value);
    } else
      await batchUpdateRecords({
        model: model.value,
        ids: selectedIds.value,
        action: key,
      });
    ElMessage.success("批量操作已完成");
    selectedRows.value = [];
    await loadRows();
  } finally {
    batchLoading.value = false;
  }
}
async function exportCurrent(ids: number[] = []) {
  const result = await exportCsv({
    model: model.value,
    fields: visibleFields.value.map((field) => field.code),
    domain: activeDomain.value,
    ids,
  });
  downloadText(
    String(result.content || result.csv || ""),
    String(result.filename || `${title.value}.csv`),
  );
  ElMessage.success("导出已生成");
}
watch(
  () => route.fullPath,
  (next, previous) => {
    if (next !== previous) {
      page.value = 1;
      void load();
    }
  },
);
onMounted(load);
</script>

<style scoped>
.action-page {
  display: grid;
  gap: 16px;
}
.page-heading,
.toolbar,
.toolbar-left,
.toolbar-right,
.preset-bar,
.batch-bar,
.active-filters {
  display: flex;
  align-items: center;
}
.page-heading {
  justify-content: space-between;
}
.page-heading h1 {
  margin: 12px 0 4px;
  font-size: 25px;
}
.page-heading p,
.total-count,
.preset-bar > span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.heading-actions,
.toolbar-left,
.toolbar-right,
.preset-bar,
.batch-bar,
.active-filters {
  gap: 8px;
}
.content-card {
  border: 0;
  min-width: 0;
  overflow: hidden;
}
.toolbar {
  justify-content: space-between;
  gap: 14px;
  margin: 14px 0;
  flex-wrap: wrap;
}
.toolbar-left,
.toolbar-right {
  min-width: 0;
  flex-wrap: wrap;
}
.toolbar-right {
  justify-content: flex-end;
}
.content-card :deep(.el-table__body-wrapper) {
  overflow-x: auto;
  scrollbar-width: thin;
}
.content-card :deep(.el-table__header-wrapper),
.content-card :deep(.el-table__footer-wrapper) {
  overflow-x: hidden;
}
.content-card :deep(.el-table__header),
.content-card :deep(.el-table__body),
.content-card :deep(.el-table__footer) {
  min-width: max-content;
}
.search-input {
  width: 260px;
}
.group-select,
.saved-select {
  width: 145px;
}
.sort-header {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.sort-header:disabled {
  cursor: default;
}
.sort-header.is-active {
  color: var(--el-color-primary);
}
.preset-bar,
.active-filters {
  flex-wrap: wrap;
}
.batch-bar {
  padding: 10px;
  background: var(--el-fill-color-light);
}
.pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 18px;
}
.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 24px;
  white-space: nowrap;
}
.row-actions :deep(.el-button),
.row-actions :deep(.el-dropdown) {
  display: inline-flex;
  align-items: center;
  height: 24px;
  margin: 0;
  vertical-align: middle;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}
.card-grid h3 {
  margin: 0 0 12px;
}
.card-grid dl {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 7px;
  font-size: 13px;
}
.card-grid dt {
  color: var(--el-text-color-secondary);
}
.card-grid dd {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kanban-grid {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  overflow-x: auto;
}
.kanban-lane {
  min-width: 270px;
  background: var(--el-fill-color-light);
}
.kanban-card {
  margin-bottom: 8px;
  cursor: pointer;
}
.kanban-card h3 {
  margin: 0 0 8px;
  font-size: 14px;
}
.kanban-card span {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 4px;
}
.grouped-view :deep(.el-collapse-item__title) {
  gap: 10px;
}
.group-total {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.operator-select {
  width: 120px;
  margin-right: 8px;
}
.column-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.error-detail {
  display: flex;
  gap: 12px;
}
@media (max-width: 900px) {
  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .toolbar-left,
  .toolbar-right {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
  .search-input {
    width: 100%;
  }
  .content-card {
    padding-left: 12px;
    padding-right: 12px;
  }
  .pagination {
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>
