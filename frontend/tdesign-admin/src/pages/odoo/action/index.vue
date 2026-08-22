<template>
  <div class="odoo-action-page">
    <section class="page-card">
      <div class="page-heading">
        <div>
          <t-breadcrumb>
            <t-breadcrumb-item>业务菜单</t-breadcrumb-item>
            <t-breadcrumb-item>{{ title }}</t-breadcrumb-item>
          </t-breadcrumb>
          <h2>{{ title }}</h2>
        </div>
        <div class="page-actions">
          <t-button variant="outline" :loading="loading" @click="load">
            <template #icon><t-icon name="refresh" /></template>
            刷新
          </t-button>
          <t-button v-if="canCreate" theme="primary" :disabled="!targetModel" @click="openCreate">
            <template #icon><t-icon name="add" /></template>
            新建
          </t-button>
        </div>
      </div>

      <t-alert v-if="error" class="page-error" theme="error" :message="error" />
      <suggested-action-bar
        v-if="error"
        :action="suggestedAction"
        :trace-id="errorTraceId"
        :reason-code="errorReasonCode"
        :message="error"
        :on-retry="load"
      />
      <div v-else-if="loading && !contractReady" class="loading-state" aria-live="polite" aria-label="正在加载页面">
        <div class="loading-state__context"><t-skeleton animation="gradient" :row-col="loadingContextRows" /></div>
        <div class="loading-state__table"><t-skeleton animation="gradient" :row-col="loadingTableRows" /></div>
        <div class="loading-state__caption"><t-icon name="loading" /> 正在加载页面配置和数据</div>
      </div>

      <template v-else>
        <section class="control-panel" aria-label="列表控制面板">
          <div v-if="presetFilters.length" class="preset-filter-bar">
            <span class="toolbar-label">快捷筛选</span>
            <div class="preset-filter-list">
              <t-tag
                v-for="filter in presetFilters"
                :key="filter.key"
                class="filter-tag"
                :theme="activePresetKeys.includes(filter.key) ? 'primary' : 'default'"
                :variant="activePresetKeys.includes(filter.key) ? 'light' : 'outline'"
                @click="togglePresetFilter(filter.key)"
              >
                {{ filter.label }}
              </t-tag>
            </div>
          </div>

          <t-alert
            v-for="diagnostic in unsupportedViewDiagnostics"
            :key="diagnostic.requestedRendererKey"
            class="surface-diagnostic"
            theme="warning"
            :message="diagnostic.message"
          />

          <div class="list-toolbar">
            <div class="list-toolbar__search">
              <t-input
                v-model="searchTerm"
                class="keyword-input"
                clearable
                placeholder="搜索当前列表"
                @enter="onSearch"
                @clear="onSearch"
              >
                <template #suffix-icon><t-icon name="search" /></template>
              </t-input>
              <t-button theme="primary" @click="onSearch">查询</t-button>
              <t-button v-if="customFilterFields.length" variant="outline" @click="openFilterDialog">
                <template #icon><t-icon name="filter" /></template>
                筛选
                <t-badge v-if="appliedCustomFilters.length" :count="appliedCustomFilters.length" :offset="[8, -8]" />
              </t-button>
              <t-button v-if="hasActiveFilters" variant="text" @click="resetFilters">重置</t-button>
            </div>
            <div class="list-toolbar__tools">
              <span class="result-count">共 {{ total }} 条</span>
              <t-select
                v-if="groupByOptions.length"
                v-model="activeGroupByField"
                class="group-select"
                :options="groupByOptions"
                clearable
                placeholder="分组依据"
                @change="onGroupByChange"
                @clear="onGroupByChange('')"
              />
              <t-select
                v-if="savedFilterOptions.length"
                class="saved-filter-select"
                :options="savedFilterOptions"
                clearable
                placeholder="已保存筛选"
                @change="applySavedFilter"
              />
              <t-button v-if="favoriteSaveEnabled" variant="outline" @click="openFavoriteDialog">
                <template #icon><t-icon name="star" /></template>
                收藏
              </t-button>
              <t-dropdown :options="viewOptions" @click="onViewOption">
                <t-button variant="outline">
                  <template #icon><t-icon name="view-list" /></template>
                  {{ viewModeLabel }}
                  <template #suffix><t-icon name="chevron-down" /></template>
                </t-button>
              </t-dropdown>
              <t-button variant="outline" shape="square" title="列设置" @click="columnDialogVisible = true">
                <template #icon><t-icon name="setting" /></template>
              </t-button>
              <t-button
                variant="outline"
                shape="square"
                title="导出"
                :disabled="!rows.length"
                :loading="exporting"
                @click="exportCurrent"
              >
                <template #icon><t-icon name="download" /></template>
              </t-button>
            </div>
          </div>

          <div v-if="appliedCustomFilters.length" class="active-filter-list">
            <t-tag
              v-for="filter in appliedCustomFilters"
              :key="filter.id"
              closable
              theme="primary"
              variant="light"
              @close="removeCustomFilter(filter.id)"
            >
              {{ customFilterLabel(filter) }}
            </t-tag>
          </div>

          <div v-if="selectedRowKeys.length" class="batch-toolbar">
            <span>已选 {{ selectedRowKeys.length }} 条</span>
            <t-button
              v-for="action in batchActions"
              :key="action.key"
              size="small"
              variant="outline"
              :theme="action.theme"
              :loading="batchBusy"
              @click="runContractBatchAction(action.key)"
              >{{ action.label }}</t-button
            >
            <t-button size="small" variant="text" @click="selectedRowKeys = []">清除选择</t-button>
          </div>
        </section>

        <hierarchy-runtime
          v-if="hierarchyRuntimeEnabled"
          :model="targetModel"
          :config="hierarchyRuntimeConfig"
          :fields="hierarchyFields"
          :domain="activeDomain"
          :can-create="canCreate"
          @open-record="(row) => openRecord(Number(row.id), 'view')"
          @create-record="openCreate"
        />

        <section v-else-if="activeGroupByField" class="grouped-results">
          <header class="grouped-results__toolbar">
            <div>
              <strong>{{ activeGroupByLabel }}分组</strong>
              <span v-if="groupWindowText">{{ groupWindowText }}</span>
            </div>
            <t-space>
              <t-button
                size="small"
                variant="outline"
                :disabled="!canPreviousGroupWindow"
                @click="changeGroupWindow(-1)"
                >上一组</t-button
              >
              <t-button size="small" variant="outline" :disabled="!canNextGroupWindow" @click="changeGroupWindow(1)"
                >下一组</t-button
              >
              <t-button size="small" variant="text" @click="setAllGroupsCollapsed(false)">全部展开</t-button>
              <t-button size="small" variant="text" @click="setAllGroupsCollapsed(true)">全部收起</t-button>
            </t-space>
          </header>
          <article v-for="group in groupedRows" :key="group.key" class="group-block">
            <button class="group-block__header" type="button" @click="toggleGroup(group.key)">
              <t-icon :name="collapsedGroupKeys.includes(group.key) ? 'chevron-right' : 'chevron-down'" />
              <strong>{{ group.label }}</strong>
              <t-tag size="small" theme="primary" variant="light">{{ group.count }} 条</t-tag>
              <span v-if="groupAggregateText(group)" class="group-aggregate">{{ groupAggregateText(group) }}</span>
            </button>
            <template v-if="!collapsedGroupKeys.includes(group.key)">
              <t-table row-key="id" :columns="columns" :data="group.sampleRows" bordered stripe hover>
                <template #operation="{ row }">
                  <t-space size="small">
                    <t-link theme="primary" hover="color" @click="openRecord(Number(row.id), 'view')">详情</t-link>
                    <t-link v-if="canWrite" theme="warning" hover="color" @click="openRecord(Number(row.id), 'edit')"
                      >编辑</t-link
                    >
                  </t-space>
                </template>
              </t-table>
              <footer v-if="group.pageTotal > 1" class="group-block__pagination">
                <span
                  >第 {{ group.pageCurrent }} / {{ group.pageTotal }} 页，显示 {{ group.pageRangeStart }}-{{
                    group.pageRangeEnd
                  }}
                  条</span
                >
                <t-space>
                  <t-button
                    size="small"
                    variant="outline"
                    :disabled="!group.pageHasPrev"
                    @click="changeGroupPage(group, -1)"
                    >上一页</t-button
                  >
                  <t-button
                    size="small"
                    variant="outline"
                    :disabled="!group.pageHasNext"
                    @click="changeGroupPage(group, 1)"
                    >下一页</t-button
                  >
                </t-space>
              </footer>
            </template>
          </article>
          <t-empty v-if="!groupedRows.length" description="当前条件下没有分组数据" />
        </section>

        <div v-else-if="viewMode === 'cards'" class="record-card-grid">
          <t-card v-for="row in displayRows" :key="String(row.id)" class="record-card" hover-shadow>
            <div class="record-card__title">{{ recordTitle(row) }}</div>
            <div class="record-card__fields">
              <div v-for="field in fieldSpecs.slice(0, 6)" :key="field.code" class="record-card__field">
                <span>{{ field.label }}</span>
                <field-display
                  :value="row[field.code]"
                  :field-code="field.code"
                  :field-label="field.label"
                  :field-type="field.type"
                  :config="field.config"
                />
              </div>
            </div>
            <div class="record-card__actions">
              <t-link theme="primary" @click="openRecord(Number(row.id), 'view')">详情</t-link>
              <t-link v-if="canWrite" theme="warning" @click="openRecord(Number(row.id), 'edit')">编辑</t-link>
              <t-link
                v-for="action in rowActions"
                :key="action.key"
                :theme="action.theme"
                @click="runRowAction(row, action)"
                >{{ action.label }}</t-link
              >
            </div>
          </t-card>
          <t-empty v-if="!displayRows.length" description="暂无符合当前条件的数据" />
        </div>

        <div v-else-if="viewMode === 'kanban'" class="kanban-board">
          <section v-for="lane in kanbanLanes" :key="lane.key" class="kanban-lane">
            <header class="kanban-lane__header">
              <strong>{{ lane.label }}</strong
              ><t-tag size="small" theme="primary" variant="light">{{ lane.rows.length }}</t-tag>
            </header>
            <div class="kanban-lane__cards">
              <t-card
                v-for="row in lane.rows"
                :key="String(row.id)"
                class="record-card"
                hover-shadow
                @click="openRecord(Number(row.id), 'view')"
              >
                <div class="record-card__title">{{ recordTitle(row) }}</div>
                <div class="record-card__fields">
                  <div v-for="field in kanbanFields" :key="field.code" class="record-card__field">
                    <span>{{ field.label }}</span>
                    <field-display
                      :value="row[field.code]"
                      :field-code="field.code"
                      :field-label="field.label"
                      :field-type="field.type"
                      :config="field.config"
                    />
                  </div>
                </div>
                <div class="record-card__actions" @click.stop>
                  <t-link theme="primary" @click="openRecord(Number(row.id), 'view')">详情</t-link
                  ><t-link v-if="canWrite" theme="warning" @click="openRecord(Number(row.id), 'edit')">编辑</t-link
                  ><t-link
                    v-for="action in rowActions"
                    :key="action.key"
                    :theme="action.theme"
                    @click="runRowAction(row, action)"
                    >{{ action.label }}</t-link
                  >
                </div>
              </t-card>
            </div>
          </section>
          <t-empty v-if="!displayRows.length" description="暂无符合当前条件的数据" />
        </div>

        <action-surface-renderer-host
          v-else-if="['pivot', 'graph', 'calendar', 'gantt', 'activity'].includes(viewMode)"
          :mode="viewMode"
          :rows="displayRows"
          :fields="fieldSpecs"
          :config="advancedViewConfig"
          :aggregates="serverAggregates"
          :grouped-rows="advancedGroupedRowsRaw"
          @activity-action="runAdvancedActivityAction"
          @timeline-change="runTimelineChange"
          @open="(row) => openRecord(Number(row.id), 'view')"
        />

        <t-table
          v-else
          row-key="id"
          :columns="columns"
          :data="displayRows"
          :pagination="pagination"
          :selected-row-keys="selectedRowKeys"
          :row-selection="rowSelection"
          :loading="loading"
          bordered
          stripe
          hover
          resizable
          @page-change="onPageChange"
          @sort-change="onSortChange"
          @select-change="onSelectChange"
        >
          <template #operation="{ row }">
            <t-space size="small">
              <t-link theme="primary" hover="color" @click="openRecord(Number(row.id), 'view')">详情</t-link>
              <t-link v-if="canWrite" theme="warning" hover="color" @click="openRecord(Number(row.id), 'edit')"
                >编辑</t-link
              >
              <t-link
                v-for="action in rowActions"
                :key="action.key"
                :theme="action.theme"
                hover="color"
                @click="runRowAction(row, action)"
                >{{ action.label }}</t-link
              >
            </t-space>
          </template>
          <template #empty><t-empty description="暂无符合当前条件的数据" /></template>
        </t-table>
      </template>
    </section>

    <record-drawer
      v-model:visible="drawerVisible"
      :model="targetModel"
      :record-id="drawerRecordId"
      :action-id="actionId || undefined"
      :menu-id="menuId || undefined"
      :initial-mode="drawerMode"
      :title="title"
      presentation="drawer"
      @saved="onDrawerSaved"
      @deleted="onDrawerDeleted"
    />

    <t-dialog
      v-model:visible="assignDialogVisible"
      header="批量指派"
      width="480px"
      :confirm-btn="{ content: '确认指派', theme: 'primary', loading: batchBusy }"
      @confirm="confirmBatchAssign"
    >
      <t-form label-align="top">
        <t-form-item label="指派给" required>
          <t-select
            v-model="assigneeId"
            :options="assigneeOptions"
            :loading="assigneeLoading"
            filterable
            clearable
            placeholder="搜索协作用户"
            @search="searchAssignees"
          />
        </t-form-item>
        <t-alert theme="info" :message="`将指派当前选中的 ${selectedRowKeys.length} 条记录`" />
      </t-form>
    </t-dialog>

    <t-dialog
      v-model:visible="batchReasonDialogVisible"
      header="填写批量操作原因"
      width="520px"
      :confirm-btn="{ content: '确认执行', theme: 'danger', disabled: !batchReason.trim(), loading: batchBusy }"
      @confirm="confirmReasonedBatchAction"
    >
      <t-textarea v-model="batchReason" placeholder="请输入驳回或拒绝原因" :autosize="{ minRows: 4, maxRows: 8 }" />
    </t-dialog>

    <t-dialog
      v-model:visible="filterDialogVisible"
      header="自定义筛选"
      width="760px"
      :confirm-btn="{ content: '应用筛选', theme: 'primary' }"
      @confirm="applyCustomFilters"
    >
      <div class="filter-dialog-body">
        <div v-for="(condition, index) in draftCustomFilters" :key="condition.id" class="filter-condition">
          <t-select
            v-model="condition.field"
            :options="customFilterFieldOptions"
            filterable
            placeholder="选择字段"
            @change="onCustomFieldChange(condition)"
          />
          <t-select v-model="condition.operator" :options="operatorOptions(condition)" placeholder="运算符" />
          <t-select
            v-if="selectedCustomField(condition)?.type === 'selection'"
            v-model="condition.value"
            :options="choiceOptions(condition)"
            clearable
            placeholder="选择值"
          />
          <t-select
            v-else-if="selectedCustomField(condition)?.type === 'boolean'"
            v-model="condition.value"
            :options="booleanOptions"
            placeholder="选择值"
          />
          <t-date-picker
            v-else-if="selectedCustomField(condition)?.type === 'date'"
            v-model="condition.value"
            clearable
            format="YYYY-MM-DD"
            value-type="YYYY-MM-DD"
          />
          <t-date-picker
            v-else-if="selectedCustomField(condition)?.type === 'datetime'"
            v-model="condition.value"
            clearable
            enable-time-picker
            format="YYYY-MM-DD HH:mm:ss"
            value-type="YYYY-MM-DD HH:mm:ss"
          />
          <t-input-number
            v-else-if="isNumericCustomField(condition)"
            v-model="condition.value"
            theme="normal"
            placeholder="输入数值"
          />
          <t-input v-else v-model="condition.value" clearable placeholder="输入筛选值" />
          <t-button shape="square" variant="text" theme="danger" title="删除条件" @click="removeDraftFilter(index)">
            <template #icon><t-icon name="delete" /></template>
          </t-button>
        </div>
        <t-empty v-if="!draftCustomFilters.length" description="尚未添加筛选条件" />
        <t-button variant="dashed" block @click="addDraftFilter">
          <template #icon><t-icon name="add" /></template>
          添加条件
        </t-button>
      </div>
    </t-dialog>

    <t-dialog
      v-model:visible="favoriteDialogVisible"
      header="保存当前筛选"
      width="480px"
      :confirm-btn="{ content: '保存收藏', theme: 'primary', loading: favoriteSaving }"
      @confirm="saveFavorite"
    >
      <t-form label-align="top">
        <t-form-item label="收藏名称" required><t-input v-model="favoriteName" maxlength="80" clearable /></t-form-item>
        <t-form-item label="使用方式"><t-checkbox v-model="favoriteDefault">设为默认筛选</t-checkbox></t-form-item>
      </t-form>
    </t-dialog>

    <t-dialog
      v-model:visible="columnDialogVisible"
      header="列设置"
      width="520px"
      :confirm-btn="{ content: '保存', theme: 'primary' }"
      @confirm="saveColumnPreference"
    >
      <t-checkbox-group v-model="draftVisibleColumns" class="column-settings">
        <t-checkbox v-for="field in fieldSpecs" :key="field.code" :value="field.code">{{ field.label }}</t-checkbox>
      </t-checkbox-group>
    </t-dialog>
  </div>
</template>
<script setup lang="ts">
import type { PrimaryTableCol, TableSort } from 'tdesign-vue-next';
import { DialogPlugin, MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import type { GroupedDataRow } from '@/api/odoo';
import {
  batchUpdateRecords,
  deleteRecords,
  executeButton,
  exportRecordsCsv,
  getUserViewPreference,
  listData,
  OdooApiError,
  saveSearchFavorite,
  searchCollaborationUsers,
  setUserViewPreference,
  updateChatterActivity,
  updateRecord,
} from '@/api/odoo';
import SuggestedActionBar from '@/components/result/SuggestedActionBar.vue';
import { ContractDecodeError, loadActionContract } from '@/runtime/contract';
import { normalizeFieldType } from '@/runtime/fieldType';

import ActionSurfaceRendererHost from './components/ActionSurfaceRendererHost.vue';
import FieldDisplay from './components/FieldDisplay.vue';
import HierarchyRuntime from './components/HierarchyRuntime.vue';
import RecordDrawer from './components/RecordDrawer.vue';
import type { ActionSurfaceViewMode } from './runtime/actionSurfaceRegistry';
import { actionSurfaceDiagnostics, actionSurfaceViewOptions } from './runtime/actionSurfaceRegistry';

type Dict = Record<string, any>;
interface FieldSpec {
  code: string;
  label: string;
  type: string;
  config: Dict;
  capabilities: string[];
}
interface PresetFilter {
  key: string;
  label: string;
  help: string;
  domain: unknown[];
}
interface FilterOperator {
  value: string;
  label: string;
  needsValue: boolean;
}
interface CustomFilterField {
  field: string;
  label: string;
  type: string;
  operators: FilterOperator[];
  choices: Array<{ label: string; value: unknown }>;
}
interface CustomFilterCondition {
  id: number;
  field: string;
  operator: string;
  value: any;
}
interface GroupByOption {
  value: string;
  label: string;
  isDefault: boolean;
}
interface SavedFilterOption {
  value: string;
  label: string;
  domain: unknown[];
  context: Dict;
}
interface BatchAction {
  key: string;
  label: string;
  theme: 'primary' | 'warning' | 'danger';
  requiresReason?: boolean;
}
interface GroupRowView {
  key: string;
  label: string;
  count: number;
  sampleRows: Dict[];
  pageOffset: number;
  pageSize: number;
  pageCurrent: number;
  pageTotal: number;
  pageRangeStart: number;
  pageRangeEnd: number;
  pageHasPrev: boolean;
  pageHasNext: boolean;
  aggregates: Dict;
}
interface SkeletonRowColObj {
  type?: 'text' | 'circle' | 'rect';
  width?: string;
  height?: string;
  marginLeft?: string;
}
type SkeletonRowCol = Array<number | SkeletonRowColObj | SkeletonRowColObj[]>;
type DrawerMode = 'view' | 'edit' | 'create';
type ViewMode = ActionSurfaceViewMode;

const route = useRoute();
const loading = ref(false);
const error = ref('');
const errorReasonCode = ref('');
const errorTraceId = ref('');
const suggestedAction = ref('');
const contract = ref<Dict>({});
const rows = ref<Dict[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const searchTerm = ref('');
const order = ref('');
const activePresetKeys = ref<string[]>([]);
const appliedCustomFilters = ref<CustomFilterCondition[]>([]);
const draftCustomFilters = ref<CustomFilterCondition[]>([]);
const filterDialogVisible = ref(false);
const columnDialogVisible = ref(false);
const selectedRowKeys = ref<Array<string | number>>([]);
const draftVisibleColumns = ref<string[]>([]);
const viewMode = ref<ViewMode>('list');
const exporting = ref(false);
const batchBusy = ref(false);
const batchReasonDialogVisible = ref(false);
const batchReason = ref('');
const pendingBatchActionKey = ref('');
const assignDialogVisible = ref(false);
const assigneeId = ref<number>();
const assigneeLoading = ref(false);
const assigneeOptions = ref<Array<{ value: number; label: string }>>([]);
const activeGroupByField = ref('');
const groupWindowOffset = ref(0);
const groupPageOffsets = ref<Record<string, number>>({});
const groupedRowsRaw = ref<GroupedDataRow[]>([]);
const advancedGroupedRowsRaw = ref<GroupedDataRow[]>([]);
const serverAggregates = ref<Record<string, Record<string, unknown>>>({});
const groupPaging = ref<Dict>({});
const collapsedGroupKeys = ref<string[]>([]);
const activeSavedFilterDomain = ref<unknown[]>([]);
const favoriteDialogVisible = ref(false);
const favoriteName = ref('');
const favoriteDefault = ref(false);
const favoriteSaving = ref(false);
const rowActionBusy = ref('');
const drawerVisible = ref(false);
const drawerRecordId = ref<number | null>(null);
const drawerMode = ref<DrawerMode>('view');
let filterSequence = 0;
let loadSequence = 0;
let dataRequestSequence = 0;
let loadingSequence = 0;

const meta = computed(() => (route.meta || {}) as Dict);
const title = computed(() => {
  const raw = meta.value.title;
  return typeof raw === 'string'
    ? raw
    : raw && typeof raw === 'object'
      ? String((raw as Dict).zh_CN || (raw as Dict).en_US || '业务页面')
      : '业务页面';
});
const actionId = computed(() => Number(meta.value.actionId || 0));
const menuId = computed(() => Number(meta.value.menuId || 0));
const model = computed(() => String(meta.value.model || ''));
const targetModel = computed(() => String((contract.value.pageInfo as Dict | undefined)?.model || model.value));
const contractReady = computed(() => Boolean(Object.keys(contract.value).length));
const globalStatus = computed(
  () => ((contract.value.statusContract || contract.value.status_contract || {}) as Dict).globalStatus || {},
);
const modelRights = computed(() => (globalStatus.value.modelRights || globalStatus.value.model_rights || {}) as Dict);
const canCreate = computed(() => modelRights.value.create !== false);
const canWrite = computed(() => modelRights.value.write !== false);
const fieldSpecs = computed(() => resolveFieldSpecs(contract.value));
const runtimeSourceContext = computed(() => {
  const runtime = (contract.value.runtimeContract || contract.value.runtime_contract || {}) as Dict;
  const source = (runtime.sourceContext || runtime.source_context || {}) as Dict;
  return (source.context || {}) as Dict;
});
const hierarchyRuntimeConfig = computed(() => ({
  hierarchy_levels: runtimeSourceContext.value.hierarchy_levels,
  hierarchy_create: runtimeSourceContext.value.hierarchy_create,
  hierarchy_commands: runtimeSourceContext.value.hierarchy_commands,
  hierarchical_worksheet: runtimeSourceContext.value.hierarchical_worksheet,
}));
const hierarchyRuntimeEnabled = computed(
  () =>
    (Array.isArray(runtimeSourceContext.value.hierarchy_levels) &&
      runtimeSourceContext.value.hierarchy_levels.length > 0) ||
    Boolean(runtimeSourceContext.value.hierarchical_worksheet),
);
const hierarchyFields = computed(() =>
  fieldSpecs.value.map((field) => ({
    code: field.code,
    label: field.label,
    type: field.type,
    relation: String(field.config.relation || field.config.fieldInfo?.relation || ''),
  })),
);
const requestFields = computed(() =>
  ['id', ...fieldSpecs.value.map((field) => field.code)].filter((field, index, list) => list.indexOf(field) === index),
);
const searchContract = computed(() => (contract.value.searchContract || contract.value.search_contract || {}) as Dict);
const customFilterFields = computed<CustomFilterField[]>(() => {
  const custom = (searchContract.value.custom || {}) as Dict;
  const filterConfig = (custom.filters || {}) as Dict;
  const fields = Array.isArray(filterConfig.fields) ? filterConfig.fields : [];
  return fields
    .map((item: Dict) => {
      const field = String(item.field || item.name || '');
      return {
        field,
        label: resolveFieldLabel(field, [item.label, item.string], fieldSpecs.value),
        type: String(item.type || fieldSpecs.value.find((spec) => spec.code === field)?.type || 'char'),
        operators: (Array.isArray(item.operators) ? item.operators : []).map((operator: Dict) => ({
          value: String(operator.value || '='),
          label: String(operator.label || operator.value || '='),
          needsValue: operator.needs_value !== false,
        })),
        choices: (Array.isArray(item.choices) ? item.choices : []).map((choice: Dict) => ({
          value: choice.value,
          label: String(choice.label || choice.value || ''),
        })),
      };
    })
    .filter((field: CustomFilterField) => field.field);
});
const presetFilters = computed<PresetFilter[]>(() => {
  const filters = Array.isArray(searchContract.value.filters) ? searchContract.value.filters : [];
  return filters.flatMap((item: Dict, index: number) => {
    const domain = Array.isArray(item.domain) ? item.domain : [];
    if (!domain.length) return [];
    const field = String(item.field || item.name || item.key || '');
    return [
      {
        key: String(item.key || `preset-${index}`),
        label: resolveFieldLabel(
          field,
          [item.label, item.string, item.title],
          fieldSpecs.value,
          customFilterFields.value,
        ),
        help: String(item.help || ''),
        domain,
      },
    ];
  });
});
const groupByOptions = computed<GroupByOption[]>(() => {
  const seen = new Set<string>();
  const rows = [
    ...(Array.isArray(searchContract.value.group_by) ? searchContract.value.group_by : []),
    ...(((searchContract.value.custom || {}) as Dict).group_by?.fields || []),
  ];
  return rows.flatMap((item: Dict) => {
    const field = String(item.field || item.name || item.key || '').trim();
    if (!field || seen.has(field) || !fieldSpecs.value.some((spec) => spec.code === field)) return [];
    seen.add(field);
    return [
      {
        value: field,
        label: resolveFieldLabel(field, [item.label, item.string], fieldSpecs.value),
        isDefault: item.default === true || item.is_default === true,
      },
    ];
  });
});
const savedFilterOptions = computed<SavedFilterOption[]>(() => {
  const rows = Array.isArray(searchContract.value.saved_filters) ? searchContract.value.saved_filters : [];
  return rows.flatMap((item: Dict, index: number) => {
    const name = String(item.key || item.name || `saved-${index}`).trim();
    const label = String(item.label || item.name || name).trim();
    return name && label
      ? [
          {
            value: name,
            label,
            domain: Array.isArray(item.domain) ? item.domain : [],
            context: (item.context || {}) as Dict,
          },
        ]
      : [];
  });
});
const activeGroupByLabel = computed(
  () => groupByOptions.value.find((item) => item.value === activeGroupByField.value)?.label || activeGroupByField.value,
);
const groupedRows = computed<GroupRowView[]>(() => {
  const backendGroups = groupedRowsRaw.value.map((row) => ({
    key: String(row.group_key || `${row.field}:${String(row.value ?? '')}`),
    label: String(row.label || row.value || '未分类'),
    count: Number(row.total_count ?? row.count ?? 0),
    sampleRows: Array.isArray(row.sample_rows) ? row.sample_rows : [],
    pageOffset: Number(row.page_applied_offset ?? row.page_offset ?? 0),
    pageSize: Number(row.page_applied_size ?? row.page_size ?? 3),
    pageCurrent: Number(row.page_current ?? 1),
    pageTotal: Number(row.page_total ?? 1),
    pageRangeStart: Number(row.page_range_start ?? 0),
    pageRangeEnd: Number(row.page_range_end ?? 0),
    pageHasPrev: row.page_has_prev === true,
    pageHasNext: row.page_has_next === true,
    aggregates: (row.aggregates || {}) as Dict,
  }));
  if (backendGroups.length || !activeGroupByField.value || !rows.value.length) return backendGroups;

  const groups = new Map<string, Dict[]>();
  rows.value.forEach((row) => {
    const value = row[activeGroupByField.value];
    const key = Array.isArray(value) ? String(value[0] ?? '') : String(value ?? '');
    groups.set(key, [...(groups.get(key) || []), row]);
  });
  return [...groups].map(([key, sampleRows]) => {
    const value = sampleRows[0]?.[activeGroupByField.value];
    const label = Array.isArray(value) ? String(value[1] ?? value[0] ?? '未分类') : String(value || '未分类');
    return {
      key: `${activeGroupByField.value}:${key}`,
      label,
      count: sampleRows.length,
      sampleRows,
      pageOffset: 0,
      pageSize: sampleRows.length,
      pageCurrent: 1,
      pageTotal: 1,
      pageRangeStart: sampleRows.length ? 1 : 0,
      pageRangeEnd: sampleRows.length,
      pageHasPrev: false,
      pageHasNext: false,
      aggregates: {},
    };
  });
});
const groupWindowText = computed(() => {
  const start = Number(groupPaging.value.group_window_start || groupPaging.value.window_start || 0);
  const end = Number(groupPaging.value.group_window_end || groupPaging.value.window_end || 0);
  const totalGroups = Number(groupPaging.value.group_total || 0);
  return start && end && totalGroups ? `第 ${start}-${end} 组 / 共 ${totalGroups} 组` : '';
});
const canPreviousGroupWindow = computed(
  () => Number(groupPaging.value.group_offset || 0) > 0 || groupPaging.value.has_prev === true,
);
const canNextGroupWindow = computed(
  () =>
    groupPaging.value.has_next === true ||
    groupPaging.value.has_more === true ||
    (groupPaging.value.next_group_offset !== null && groupPaging.value.next_group_offset !== undefined),
);
const favoriteSaveEnabled = computed(
  () => ((searchContract.value.custom || {}) as Dict).favorites?.save_enabled !== false,
);
const rowActions = computed(() => {
  const source = (contract.value.actionContract || contract.value.action_contract || {}) as Dict;
  const rows = Array.isArray(source.actionRuleList) ? source.actionRuleList : [];
  return rows.flatMap((item: Dict) => {
    const scope = [item.targetScope, item.target_scope, item.sourceWidgetId, item.source_widget_id, item.sourceChannel]
      .map((value) => String(value || '').toLowerCase())
      .join(' ');
    const key = String(item.actionKey || item.key || item.name || '').trim();
    if (!key || !scope.includes('row')) return [];
    const button = (item.button || {}) as Dict;
    const intentName = String(item.intent || '').toLowerCase();
    if (intentName === 'open' && !Object.keys(button).length) return [];
    if (!Object.keys(button).length && !item.name) return [];
    const semantic = String(item.presentation?.tier || item.semantic || '').toLowerCase();
    const theme: 'danger' | 'warning' | 'primary' =
      semantic.includes('danger') || semantic.includes('cancel')
        ? 'danger'
        : semantic.includes('warning')
          ? 'warning'
          : 'primary';
    return [
      {
        key,
        label: String(item.label || key),
        theme,
        button: (Object.keys(button).length ? button : { name: item.name || key, type: 'object' }) as Dict,
      },
    ];
  });
});
const batchActions = computed<BatchAction[]>(() => {
  const source = (contract.value.actionContract || contract.value.action_contract || {}) as Dict;
  const policy = (source.surfacePolicies || source.surface_policies || {}) as Dict;
  const batch = (policy.batch_policy || policy.batchPolicy || {}) as Dict;
  const labels: Record<string, string> = {
    archive: '批量归档',
    activate: '批量激活',
    delete: '批量删除',
    assign: '批量指派',
    export: '导出选中',
  };
  const available = Array.isArray(batch.available_actions) ? batch.available_actions : [];
  return available.flatMap((value) => {
    const row = value && typeof value === 'object' ? (value as Dict) : {};
    const key = String(row.key || row.action || value || '')
      .trim()
      .toLowerCase();
    if (!key) return [];
    const label = String(row.label || labels[key] || key);
    const danger = row.theme === 'danger' || /delete|reject|cancel|删除|驳回|拒绝/.test(`${key} ${label}`);
    return [
      {
        key,
        label,
        theme: danger ? 'danger' : key === 'archive' ? 'warning' : 'primary',
        requiresReason:
          row.requires_reason === true || row.requiresReason === true || /reject|驳回|拒绝/.test(`${key} ${label}`),
      },
    ];
  });
});
const customFilterFieldOptions = computed(() =>
  customFilterFields.value.map((field) => ({ value: field.field, label: field.label })),
);
const booleanOptions = [
  { value: true, label: '是' },
  { value: false, label: '否' },
];
const baseDomain = computed<unknown[]>(() => {
  const data = (contract.value.dataContract || contract.value.data_contract || {}) as Dict;
  const action = (contract.value.actionContract || contract.value.action_contract || {}) as Dict;
  if (Array.isArray(data.domain)) return data.domain;
  if (Array.isArray(action.domain)) return action.domain;
  return [];
});
const activeDomain = computed<unknown[]>(() => {
  const domains: unknown[] = [...baseDomain.value, ...activeSavedFilterDomain.value];
  activePresetKeys.value.forEach((key) => {
    const filter = presetFilters.value.find((item) => item.key === key);
    if (filter) domains.push(...filter.domain);
  });
  appliedCustomFilters.value.forEach((condition) => {
    const field = customFilterFields.value.find((item) => item.field === condition.field);
    const operator = field?.operators.find((item) => item.value === condition.operator);
    if (!field || !operator || (operator.needsValue && isBlank(condition.value))) return;
    domains.push([condition.field, condition.operator, normalizeFilterValue(condition.value, field)]);
  });
  return domains;
});
const hasActiveFilters = computed(() =>
  Boolean(searchTerm.value || activePresetKeys.value.length || appliedCustomFilters.value.length),
);
const columns = computed<PrimaryTableCol[]>(() => [
  ...fieldSpecs.value
    .filter((field) => draftVisibleColumns.value.length === 0 || draftVisibleColumns.value.includes(field.code))
    .map((field) => ({
      colKey: field.code,
      title: field.label || field.code,
      ellipsis: true,
      minWidth: field.type === 'text' || field.type === 'html' ? 220 : 140,
      sorter: field.capabilities.includes('sort') || field.capabilities.includes('sortable'),
      cell: (h: any, { row }: { row?: Dict }) =>
        h(FieldDisplay, {
          value: row?.[field.code],
          fieldCode: field.code,
          fieldLabel: field.label,
          fieldType: field.type,
          config: field.config,
        }),
    })),
  { colKey: 'operation', title: '操作', width: 120, fixed: 'right' },
]);
const rowSelection = computed(() => ({ type: 'multiple' as const, reserveSelectedRowKeys: true }));
const declaredViewModes = computed(() => {
  const action = (contract.value.actionContract || contract.value.action_contract || {}) as Dict;
  const page = (contract.value.pageInfo || contract.value.page_info || {}) as Dict;
  const layout = (contract.value.layoutContract || contract.value.layout_contract || {}) as Dict;
  const raw =
    action.view_modes || action.viewModes || page.view_modes || page.viewModes || meta.value.action?.view_modes;
  const fallback =
    page.viewType || page.view_type || page.layoutType || page.layout_type || layout.layoutType || layout.layout_type;
  const declared = raw || fallback || [];
  return Array.isArray(declared)
    ? declared.map((item) => String(item).toLowerCase())
    : String(declared)
        .split(',')
        .map((item) => item.trim().toLowerCase());
});
const viewOptions = computed(() => {
  return actionSurfaceViewOptions(declaredViewModes.value);
});
const unsupportedViewDiagnostics = computed(() => actionSurfaceDiagnostics(declaredViewModes.value));
const advancedViewConfig = computed(() => {
  const layout = (contract.value.layoutContract || contract.value.layout_contract || {}) as Dict;
  const action = (contract.value.actionContract || contract.value.action_contract || {}) as Dict;
  const views = (layout.views || action.views || contract.value.viewConfig || contract.value.view_config || {}) as Dict;
  return (views[viewMode.value] || views.default || layout.listProfile || layout.list_profile || {}) as Dict;
});
const advancedViewActive = computed(() => ['pivot', 'graph', 'calendar', 'gantt', 'activity'].includes(viewMode.value));
const advancedGroupingFields = computed(() => {
  const source = advancedViewConfig.value as Dict;
  const raw = source.dimensions || source.dimension_fields || source.group_by;
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => String(item?.field || item?.code || item || '').trim()).filter(Boolean);
});
const displayRows = computed(() => rows.value.map((row) => ({ ...row })));
const viewModeLabel = computed(
  () => viewOptions.value.find((item) => item.value === viewMode.value)?.content || '列表视图',
);
const kanbanGroupField = computed(() => {
  const runtime = (contract.value.runtimeContract || contract.value.runtime_contract || {}) as Dict;
  const explicit = String(
    runtime.kanbanGroupField || runtime.kanban_group_field || runtime.groupField || runtime.group_field || '',
  );
  if (explicit && fieldSpecs.value.some((field) => field.code === explicit)) return explicit;
  return (
    fieldSpecs.value.find((field) =>
      /(?:^|_)(?:state|status|stage|approval_state|workflow_state)(?:_|$)/.test(field.code),
    )?.code || ''
  );
});
const kanbanFields = computed(() =>
  fieldSpecs.value.filter((field) => field.code !== kanbanGroupField.value).slice(0, 5),
);
const kanbanLanes = computed(() => {
  const field = fieldSpecs.value.find((item) => item.code === kanbanGroupField.value);
  const labels = new Map(
    selectionPairs(
      field?.config?.selection || field?.config?.fieldInfo?.selection || field?.config?.node?.fieldInfo?.selection,
    ).map(([value, label]) => [String(value), String(label)]),
  );
  const lanes = new Map<string, { key: string; label: string; rows: Dict[] }>();
  displayRows.value.forEach((row) => {
    const raw = row[kanbanGroupField.value];
    const key = Array.isArray(raw) ? String(raw[0] ?? '') : String(raw ?? '');
    const label = labels.get(key) || (Array.isArray(raw) ? String(raw[1] ?? raw[0] ?? '未分类') : key || '未分类');
    const lane = lanes.get(key) || { key, label, rows: [] };
    lane.rows.push(row);
    lanes.set(key, lane);
  });
  return [...lanes.values()];
});
const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50, 100],
}));

const loadingContextRows: SkeletonRowCol = [
  [
    { type: 'text', width: '21%', height: '18px' },
    { type: 'text', width: '13%', height: '18px', marginLeft: '12px' },
    { type: 'text', width: '10%', height: '18px', marginLeft: 'auto' },
  ],
  { type: 'text', width: '45%', height: '14px' },
  [
    { type: 'rect', width: '62%', height: '36px' },
    { type: 'rect', width: '76px', height: '36px', marginLeft: '12px' },
    { type: 'rect', width: '84px', height: '36px', marginLeft: 'auto' },
  ],
];
const loadingTableRows: SkeletonRowCol = [
  [
    { type: 'rect', width: '22%', height: '38px' },
    { type: 'rect', width: '14%', height: '38px', marginLeft: '10px' },
    { type: 'rect', width: '14%', height: '38px', marginLeft: '10px' },
  ],
  ...Array.from({ length: 5 }, () => [{ type: 'rect' as const, width: '100%', height: '42px' }]),
];

async function load() {
  const sequence = ++loadSequence;
  const currentLoadingSequence = ++loadingSequence;
  loading.value = true;
  error.value = '';
  errorReasonCode.value = '';
  errorTraceId.value = '';
  suggestedAction.value = '';
  try {
    const nextContract = await loadActionContract({
      actionId: actionId.value,
      menuId: menuId.value,
    });
    if (sequence !== loadSequence) return;
    contract.value = nextContract;
    draftVisibleColumns.value = fieldSpecs.value.map((field) => field.code);
    await loadColumnPreference();
    const defaults = (searchContract.value.defaults || {}) as Dict;
    order.value = String(defaults.order || '');
    if (Number(defaults.limit) > 0) pageSize.value = Number(defaults.limit);
    const availableViews = viewOptions.value;
    if (!availableViews.some((item) => item.value === viewMode.value)) {
      viewMode.value = (availableViews[0]?.value || 'list') as ViewMode;
    }
    const defaultGroup = groupByOptions.value.find((item) => item.isDefault);
    activeGroupByField.value = viewMode.value === 'list' ? activeGroupByField.value || defaultGroup?.value || '' : '';
    groupWindowOffset.value = 0;
    groupPageOffsets.value = {};
    await loadData(sequence);
  } catch (cause) {
    if (sequence === loadSequence) capturePageError(cause, '页面数据加载失败');
  } finally {
    if (sequence === loadSequence && currentLoadingSequence === loadingSequence) loading.value = false;
  }
}

function capturePageError(cause: unknown, fallback: string) {
  error.value = cause instanceof Error ? cause.message : fallback;
  if (cause instanceof OdooApiError) {
    errorReasonCode.value = cause.reasonCode || cause.code;
    errorTraceId.value = cause.traceId;
    suggestedAction.value = cause.suggestedAction;
  } else if (cause instanceof ContractDecodeError) {
    errorReasonCode.value = cause.runtimeMeta.reasonCode || cause.issues[0]?.code || 'CONTRACT_INVALID';
    errorTraceId.value = cause.runtimeMeta.traceId;
    suggestedAction.value = cause.runtimeMeta.suggestedAction || 'retry';
  }
}

async function loadData(sequence = loadSequence) {
  if (!targetModel.value || !requestFields.value.length) return;
  const requestSequence = ++dataRequestSequence;
  const requestedGroupBy = activeGroupByField.value;
  const requestedAdvancedGroupBy = !requestedGroupBy && advancedViewActive.value ? advancedGroupingFields.value : [];
  const serverGroupBy = requestedGroupBy || requestedAdvancedGroupBy;
  let result: Awaited<ReturnType<typeof listData>>;
  try {
    result = await listData({
      model: targetModel.value,
      fields: requestFields.value,
      domain: activeDomain.value,
      order: order.value,
      limit: pageSize.value,
      offset: serverGroupBy ? 0 : (page.value - 1) * pageSize.value,
      search_term: searchTerm.value,
      group_by: serverGroupBy || undefined,
      group_offset: groupWindowOffset.value,
      need_group_total: Boolean(serverGroupBy),
      group_sample_limit: 3,
      group_limit: 10,
      group_page_size: 3,
      group_page_offsets: groupPageOffsets.value,
      need_aggregates: Boolean(serverGroupBy || advancedViewActive.value),
    });
  } catch (cause) {
    if (sequence !== loadSequence || requestSequence !== dataRequestSequence) return;
    throw cause;
  }
  if (sequence !== loadSequence || requestSequence !== dataRequestSequence) return;
  rows.value = result.records || result.rows || [];
  total.value = Number(result.total ?? rows.value.length);
  groupedRowsRaw.value = requestedGroupBy ? result.grouped_rows || [] : [];
  advancedGroupedRowsRaw.value = requestedAdvancedGroupBy.length ? result.grouped_rows || [] : [];
  serverAggregates.value = result.aggregates || {};
  groupPaging.value = (result.group_paging || {}) as Dict;
}

async function loadColumnPreference() {
  if (!targetModel.value) return;
  try {
    const result = await getUserViewPreference({ model: targetModel.value, actionId: actionId.value });
    const preference = result.preference || {};
    const visible = Array.isArray(preference.visible_columns)
      ? preference.visible_columns.map(String).filter((field) => fieldSpecs.value.some((spec) => spec.code === field))
      : [];
    if (visible.length) draftVisibleColumns.value = visible;
  } catch {
    // View preferences are optional; the contract columns remain the fallback.
  }
}

async function saveColumnPreference() {
  if (!targetModel.value) return;
  const visible = draftVisibleColumns.value.length
    ? draftVisibleColumns.value
    : fieldSpecs.value.map((field) => field.code);
  draftVisibleColumns.value = visible;
  columnDialogVisible.value = false;
  try {
    await setUserViewPreference({
      model: targetModel.value,
      actionId: actionId.value,
      preference: { visible_columns: visible },
    });
    MessagePlugin.success('列设置已保存');
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '列设置保存失败');
  }
}

function onSelectChange(keys: Array<string | number>) {
  selectedRowKeys.value = keys;
}

async function onViewOption(info: any) {
  const next = String(info?.value || '');
  const nextView = (
    viewOptions.value.some((item) => item.value === next) ? next : viewOptions.value[0]?.value || 'list'
  ) as ViewMode;
  viewMode.value = nextView;

  // Grouped responses contain paged group samples, so cards and kanban must reload
  // the normal record set instead of rendering an incomplete grouped payload.
  if (nextView !== 'list' && activeGroupByField.value) {
    activeGroupByField.value = '';
    groupWindowOffset.value = 0;
    groupPageOffsets.value = {};
    groupedRowsRaw.value = [];
    collapsedGroupKeys.value = [];
    page.value = 1;
    await fetchCurrentPage();
  }
}

async function runAdvancedActivityAction(payload: Dict) {
  const row = (payload.row || {}) as Dict;
  const activityId = Number(payload.activityId || row.activity_id || row.activityId || row.activity?.id || 0);
  if (!activityId) {
    openRecord(Number(row.id), 'view');
    return;
  }
  if (payload.action === 'reschedule') {
    openRecord(Number(row.id), 'edit');
    return;
  }
  try {
    await updateChatterActivity({
      model: targetModel.value,
      recordId: Number(row.id),
      activityId,
      action: payload.action,
    });
    MessagePlugin.success(payload.action === 'done' ? '活动已完成' : '活动已取消');
    await loadData();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '活动操作失败');
  }
}

async function runTimelineChange(payload: Dict) {
  const row = (payload.row || {}) as Dict;
  const startField = String(advancedViewConfig.value.start_field || advancedViewConfig.value.startField || '');
  const endField = String(advancedViewConfig.value.end_field || advancedViewConfig.value.endField || '');
  if (!row.id || !startField || !endField) {
    MessagePlugin.info('当前甘特 Contract 未提供可写入的时间字段');
    return;
  }
  try {
    await updateRecord(targetModel.value, Number(row.id), { [startField]: payload.start, [endField]: payload.end });
    MessagePlugin.success('计划时间已更新');
    await loadData();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '计划时间更新失败');
  }
}

function selectionPairs(value: unknown): Array<[unknown, unknown]> {
  return Array.isArray(value)
    ? value.flatMap((item) =>
        Array.isArray(item) && item.length >= 2 ? [[item[0], item[1]] as [unknown, unknown]] : [],
      )
    : [];
}

function recordTitle(row: Dict) {
  return String(row.name || row.display_name || row.code || row.id || '记录');
}

async function exportCurrent() {
  if (!targetModel.value) return;
  exporting.value = true;
  try {
    const result = await exportRecordsCsv({
      model: targetModel.value,
      fields: requestFields.value,
      domain: activeDomain.value,
      ids: selectedRowKeys.value.map(Number).filter((id) => Number.isFinite(id)),
      order: order.value,
      columnLabels: Object.fromEntries(fieldSpecs.value.map((field) => [field.code, field.label])),
    });
    const content = result.content_b64 ? decodeBase64(result.content_b64) : String(result.content || '');
    if (!content) throw new Error('后端未返回可下载内容');
    const blob = new Blob([content], { type: result.mime_type || 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = result.file_name || result.filename || `${targetModel.value.replace(/\W+/g, '_')}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
    MessagePlugin.success(`已导出 ${result.count ?? ''} 条记录`);
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '导出失败');
  } finally {
    exporting.value = false;
  }
}

async function runBatch(action: 'archive' | 'activate') {
  if (!targetModel.value || !selectedRowKeys.value.length) return;
  batchBusy.value = true;
  try {
    const ids = selectedRowKeys.value.map(Number).filter((id) => Number.isFinite(id));
    const result = await batchUpdateRecords({ model: targetModel.value, ids, action });
    const count = Number((result as Dict).succeeded ?? (result as Dict).deleted_count ?? ids.length);
    MessagePlugin.success(`${action === 'archive' ? '归档' : '激活'}完成${count ? `：${count} 条` : ''}`);
    selectedRowKeys.value = [];
    await fetchCurrentPage();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '批量操作失败');
  } finally {
    batchBusy.value = false;
  }
}

async function runContractBatchAction(action: string, reason = '', confirmedReason = false) {
  if (!targetModel.value || !selectedRowKeys.value.length) return;
  const specification = batchActions.value.find((item) => item.key === action);
  if (specification?.requiresReason && !confirmedReason) {
    pendingBatchActionKey.value = action;
    batchReason.value = '';
    batchReasonDialogVisible.value = true;
    return;
  }
  if (['delete', 'archive', 'activate', 'assign'].includes(action) && !confirmedReason) {
    const confirmed = await confirmBatchAction(action);
    if (!confirmed) return;
  }
  if (action === 'archive' || action === 'activate') {
    await runBatch(action);
    return;
  }
  if (action === 'assign') {
    assigneeId.value = undefined;
    assignDialogVisible.value = true;
    await searchAssignees('');
    return;
  }
  const ids = selectedRowKeys.value.map(Number).filter((id) => Number.isFinite(id));
  batchBusy.value = true;
  try {
    if (action === 'delete') {
      await deleteRecords(targetModel.value, ids);
      MessagePlugin.success(`批量删除完成：${ids.length} 条`);
    } else if (action === 'export') {
      await exportCurrent();
      return;
    } else {
      await batchUpdateRecords({ model: targetModel.value, ids, action, reason });
      MessagePlugin.success('批量操作已完成');
    }
    selectedRowKeys.value = [];
    await fetchCurrentPage();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '批量操作失败');
  } finally {
    batchBusy.value = false;
  }
}

async function confirmReasonedBatchAction() {
  if (!pendingBatchActionKey.value || !batchReason.value.trim()) return;
  const action = pendingBatchActionKey.value;
  batchReasonDialogVisible.value = false;
  await runContractBatchAction(action, batchReason.value.trim(), true);
  pendingBatchActionKey.value = '';
}

function confirmBatchAction(action: string) {
  const labels: Record<string, string> = {
    delete: '删除选中记录',
    archive: '归档选中记录',
    activate: '激活选中记录',
    assign: '指派选中记录',
  };
  return new Promise<boolean>((resolve) => {
    const dialog = DialogPlugin.confirm({
      header: '确认批量操作',
      body: `即将${labels[action] || '执行批量操作'}，共 ${selectedRowKeys.value.length} 条记录。`,
      confirmBtn: { content: '确认', theme: action === 'delete' ? 'danger' : 'primary' },
      cancelBtn: '取消',
      onConfirm: () => {
        dialog.destroy();
        resolve(true);
      },
      onClose: () => {
        dialog.destroy();
        resolve(false);
      },
    });
  });
}

async function searchAssignees(query: string) {
  assigneeLoading.value = true;
  try {
    const result = await searchCollaborationUsers(String(query || '').trim(), 30);
    assigneeOptions.value = (result.items || []).map((user) => ({
      value: Number(user.id),
      label: String(user.name || user.login || user.id),
    }));
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '协作用户加载失败');
  } finally {
    assigneeLoading.value = false;
  }
}

async function confirmBatchAssign() {
  if (!targetModel.value || !assigneeId.value) {
    MessagePlugin.warning('请选择指派人');
    return;
  }
  const ids = selectedRowKeys.value.map(Number).filter((id) => Number.isFinite(id));
  batchBusy.value = true;
  try {
    const result = await batchUpdateRecords({
      model: targetModel.value,
      ids,
      action: 'assign',
      assigneeId: assigneeId.value,
    });
    const count = Number((result as Dict).succeeded ?? ids.length);
    MessagePlugin.success(`批量指派完成：${count} 条`);
    assignDialogVisible.value = false;
    selectedRowKeys.value = [];
    await fetchCurrentPage();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '批量指派失败');
  } finally {
    batchBusy.value = false;
  }
}

function decodeBase64(value: string) {
  try {
    const binary = atob(value);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return value;
  }
}

async function fetchCurrentPage() {
  const currentLoadingSequence = ++loadingSequence;
  loading.value = true;
  error.value = '';
  try {
    await loadData();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '查询失败';
  } finally {
    if (currentLoadingSequence === loadingSequence) loading.value = false;
  }
}

async function onSearch() {
  page.value = 1;
  await fetchCurrentPage();
}

async function onGroupByChange(value: unknown) {
  activeGroupByField.value = String(value || '');
  if (activeGroupByField.value) viewMode.value = 'list';
  groupWindowOffset.value = 0;
  groupPageOffsets.value = {};
  collapsedGroupKeys.value = [];
  page.value = 1;
  await fetchCurrentPage();
}

async function changeGroupWindow(direction: number) {
  const next = direction < 0 ? groupPaging.value.prev_group_offset : groupPaging.value.next_group_offset;
  if (next === null || next === undefined) return;
  groupWindowOffset.value = Math.max(0, Number(next) || 0);
  groupPageOffsets.value = {};
  collapsedGroupKeys.value = [];
  await fetchCurrentPage();
}

async function changeGroupPage(group: GroupRowView, direction: number) {
  const nextOffset = Math.max(0, group.pageOffset + direction * group.pageSize);
  groupPageOffsets.value = { ...groupPageOffsets.value, [group.key]: nextOffset };
  await fetchCurrentPage();
}

function toggleGroup(key: string) {
  collapsedGroupKeys.value = collapsedGroupKeys.value.includes(key)
    ? collapsedGroupKeys.value.filter((item) => item !== key)
    : [...collapsedGroupKeys.value, key];
}

function setAllGroupsCollapsed(collapsed: boolean) {
  collapsedGroupKeys.value = collapsed ? groupedRows.value.map((group) => group.key) : [];
}

function groupAggregateText(group: GroupRowView) {
  const entries = Object.entries(group.aggregates || {}).slice(0, 2);
  return entries
    .map(([key, value]) => `${key}: ${String((value as Dict).sum ?? (value as Dict).value ?? '')}`)
    .filter((item) => !item.endsWith(': '))
    .join(' · ');
}

function openFavoriteDialog() {
  favoriteName.value = '';
  favoriteDefault.value = false;
  favoriteDialogVisible.value = true;
}

async function saveFavorite() {
  const name = favoriteName.value.trim();
  if (!name || !targetModel.value) return;
  favoriteSaving.value = true;
  try {
    await saveSearchFavorite({
      model: targetModel.value,
      name,
      domain: activeDomain.value,
      order: order.value,
      actionId: actionId.value,
      isDefault: favoriteDefault.value,
    });
    favoriteDialogVisible.value = false;
    MessagePlugin.success('筛选已保存，将从后端配置重新加载');
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '保存筛选失败');
  } finally {
    favoriteSaving.value = false;
  }
}

async function applySavedFilter(value: unknown) {
  const saved = savedFilterOptions.value.find((item) => item.value === String(value || ''));
  activePresetKeys.value = [];
  appliedCustomFilters.value = [];
  activeSavedFilterDomain.value = saved?.domain || [];
  const contextGroup = saved?.context?.group_by;
  if (contextGroup)
    activeGroupByField.value = Array.isArray(contextGroup) ? String(contextGroup[0] || '') : String(contextGroup);
  page.value = 1;
  groupWindowOffset.value = 0;
  groupPageOffsets.value = {};
  await fetchCurrentPage();
}

async function onPageChange(info: { current: number; pageSize: number }) {
  page.value = info.current;
  pageSize.value = info.pageSize;
  await fetchCurrentPage();
}

async function onSortChange(sort: TableSort) {
  const current = Array.isArray(sort) ? sort[0] : sort;
  if (!current?.sortBy || current.descending === undefined)
    order.value = String((searchContract.value.defaults as Dict | undefined)?.order || '');
  else order.value = `${String(current.sortBy)} ${current.descending === true ? 'desc' : 'asc'}`;
  page.value = 1;
  await fetchCurrentPage();
}

async function togglePresetFilter(key: string) {
  activePresetKeys.value = activePresetKeys.value.includes(key)
    ? activePresetKeys.value.filter((item) => item !== key)
    : [...activePresetKeys.value, key];
  page.value = 1;
  await fetchCurrentPage();
}

function openFilterDialog() {
  draftCustomFilters.value = appliedCustomFilters.value.map((item) => ({ ...item }));
  if (!draftCustomFilters.value.length) addDraftFilter();
  filterDialogVisible.value = true;
}

function addDraftFilter() {
  const field = customFilterFields.value[0];
  draftCustomFilters.value.push({
    id: ++filterSequence,
    field: field?.field || '',
    operator: field?.operators[0]?.value || '=',
    value: '',
  });
}

function removeDraftFilter(index: number) {
  draftCustomFilters.value.splice(index, 1);
}

function onCustomFieldChange(condition: CustomFilterCondition) {
  const field = selectedCustomField(condition);
  condition.operator = field?.operators[0]?.value || '=';
  condition.value = field?.type === 'boolean' ? true : '';
}

function selectedCustomField(condition: CustomFilterCondition) {
  return customFilterFields.value.find((field) => field.field === condition.field);
}

function operatorOptions(condition: CustomFilterCondition) {
  return (selectedCustomField(condition)?.operators || []).map((operator) => ({
    value: operator.value,
    label: operator.label,
  }));
}

function choiceOptions(condition: CustomFilterCondition) {
  return selectedCustomField(condition)?.choices || [];
}

function isNumericCustomField(condition: CustomFilterCondition) {
  return ['integer', 'float', 'monetary'].includes(selectedCustomField(condition)?.type || '');
}

async function applyCustomFilters() {
  appliedCustomFilters.value = draftCustomFilters.value
    .filter((condition) => {
      const field = selectedCustomField(condition);
      const operator = field?.operators.find((item) => item.value === condition.operator);
      return Boolean(field && operator && (!operator.needsValue || !isBlank(condition.value)));
    })
    .map((condition) => ({ ...condition }));
  filterDialogVisible.value = false;
  page.value = 1;
  await fetchCurrentPage();
}

async function removeCustomFilter(id: number) {
  appliedCustomFilters.value = appliedCustomFilters.value.filter((item) => item.id !== id);
  page.value = 1;
  await fetchCurrentPage();
}

async function resetFilters() {
  searchTerm.value = '';
  activePresetKeys.value = [];
  appliedCustomFilters.value = [];
  activeSavedFilterDomain.value = [];
  groupWindowOffset.value = 0;
  groupPageOffsets.value = {};
  groupedRowsRaw.value = [];
  page.value = 1;
  await fetchCurrentPage();
}

function customFilterLabel(condition: CustomFilterCondition) {
  const field = selectedCustomField(condition);
  const operator = field?.operators.find((item) => item.value === condition.operator);
  const choice = field?.choices.find((item) => String(item.value) === String(condition.value));
  const value = field?.type === 'boolean' ? (condition.value ? '是' : '否') : choice?.label || String(condition.value);
  return `${field?.label || condition.field} ${operator?.label || condition.operator} ${value}`;
}

function openCreate() {
  drawerRecordId.value = null;
  drawerMode.value = 'create';
  drawerVisible.value = true;
}

function openRecord(recordId: number, nextMode: DrawerMode) {
  if (!Number.isFinite(recordId) || recordId <= 0) return;
  drawerRecordId.value = recordId;
  drawerMode.value = nextMode;
  drawerVisible.value = true;
}

async function onDrawerSaved() {
  await fetchCurrentPage();
}

async function onDrawerDeleted() {
  drawerVisible.value = false;
  await fetchCurrentPage();
}

async function runRowAction(row: Dict, action: (typeof rowActions.value)[number]) {
  const id = Number(row.id || 0);
  if (!id || rowActionBusy.value) return;
  rowActionBusy.value = `${id}:${action.key}`;
  try {
    await executeButton({ model: targetModel.value, recordId: id, button: action.button, context: {} });
    MessagePlugin.success(`${action.label}已执行`);
    await fetchCurrentPage();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : `${action.label}执行失败`);
  } finally {
    rowActionBusy.value = '';
  }
}

function resetForRouteChange() {
  loadSequence += 1;
  dataRequestSequence += 1;
  loadingSequence += 1;
  drawerVisible.value = false;
  drawerRecordId.value = null;
  drawerMode.value = 'view';
  contract.value = {};
  rows.value = [];
  total.value = 0;
  page.value = 1;
  searchTerm.value = '';
  order.value = '';
  activePresetKeys.value = [];
  appliedCustomFilters.value = [];
  selectedRowKeys.value = [];
  draftVisibleColumns.value = [];
  viewMode.value = 'list';
  void load();
}

function resolveFieldSpecs(payload: Dict): FieldSpec[] {
  const layout = (payload.layoutContract || payload.layout_contract) as Dict | undefined;
  const fields: FieldSpec[] = [];
  const walk = (items: unknown) => {
    if (!Array.isArray(items)) return;
    items.forEach((item) => {
      if (!item || typeof item !== 'object') return;
      const row = item as Dict;
      const explicitFieldCode = String(row.fieldCode || row.field_code || '');
      const nodeType = String(row.type || row.kind || '').toLowerCase();
      const code = explicitFieldCode || (nodeType === 'field' ? String(row.name || '') : '');
      const config = (row.componentConfig || row.component_config || row.fieldInfo || {}) as Dict;
      if (code && code !== 'id' && !fields.some((field) => field.code === code)) {
        fields.push({
          code,
          label: String(row.label || row.string || config.label || config.string || code),
          type: normalizeFieldType(
            config.fieldType || config.field_type || config.type || row.fieldType || row.field_type || 'char',
          ),
          config,
          capabilities: Array.isArray(row.capabilities) ? row.capabilities.map(String) : [],
        });
      }
      walk(row.children);
      walk(row.widgetList);
    });
  };
  walk(layout?.containerTree || layout?.container_tree);
  walk(layout?.widgetList || layout?.widget_list);
  if (fields.length) return fields;
  return resolveFallbackFieldSpecs(payload);
}

function resolveFallbackFieldSpecs(payload: Dict): FieldSpec[] {
  const rawFields =
    payload.fields || (payload.data_contract && (payload.data_contract as Dict).fields) || payload.columns;
  if (!Array.isArray(rawFields)) {
    return resolveFields(payload)
      .filter((field) => field !== 'id')
      .map((code) => ({ code, label: code, type: 'char', config: {}, capabilities: [] }));
  }
  return rawFields
    .map((item): FieldSpec | null => {
      if (typeof item === 'string') {
        return item === 'id' ? null : { code: item, label: item, type: 'char', config: {}, capabilities: [] };
      }
      const row = (item || {}) as Dict;
      const code = String(row.fieldCode || row.field_code || row.name || row.field || '');
      if (!code || code === 'id') return null;
      const config = (row.componentConfig || row.component_config || row.fieldInfo || {}) as Dict;
      return {
        code,
        label: String(row.label || row.string || config.label || config.string || code),
        type: normalizeFieldType(
          row.fieldType || row.field_type || config.fieldType || config.field_type || config.type || 'char',
        ),
        config,
        capabilities: Array.isArray(row.capabilities) ? row.capabilities.map(String) : [],
      };
    })
    .filter((field): field is FieldSpec => Boolean(field))
    .filter((field, index, list) => list.findIndex((item) => item.code === field.code) === index);
}

function resolveFieldLabel(
  code: string,
  candidates: unknown[],
  specs: FieldSpec[],
  customFields: CustomFilterField[] = [],
) {
  const direct = candidates.map((value) => String(value || '').trim()).find(Boolean);
  if (direct && direct !== code) return direct;
  const customLabel = customFields.find((field) => field.field === code)?.label;
  if (customLabel && customLabel !== code) return customLabel;
  const fieldLabel = specs.find((field) => field.code === code)?.label;
  if (fieldLabel && fieldLabel !== code) return fieldLabel;
  return direct || code || '未命名字段';
}

function resolveFields(payload: Dict): string[] {
  const fields = payload.fields || (payload.data_contract && (payload.data_contract as Dict).fields) || payload.columns;
  if (Array.isArray(fields)) {
    return fields
      .map((item) => (typeof item === 'string' ? item : String((item as Dict)?.name || (item as Dict)?.field || '')))
      .filter(Boolean)
      .slice(0, 30);
  }
  const first = rows.value[0];
  return first ? Object.keys(first).slice(0, 30) : ['id', 'name'];
}

function normalizeFilterValue(value: unknown, field: CustomFilterField) {
  if (field.type === 'boolean') return Boolean(value);
  if (['integer', 'float', 'monetary'].includes(field.type)) return Number(value);
  return value;
}

function isBlank(value: unknown) {
  return value === '' || value === null || value === undefined;
}

watch([() => route.fullPath, actionId, menuId, model], resetForRouteChange);
onMounted(load);
</script>
<style scoped>
.odoo-action-page {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.page-card {
  width: 100%;
  min-height: calc(100vh - 144px);
  box-sizing: border-box;
}

.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 22px;
}

.page-heading h2 {
  margin: 18px 0 0;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 0;
}

.page-actions,
.preset-filter-bar,
.preset-filter-list,
.active-filter-list {
  display: flex;
  align-items: center;
  gap: 8px;
}
.control-panel {
  display: grid;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  background: var(--td-bg-color-container);
}

.surface-diagnostic {
  margin: 0;
}

.group-select,
.saved-filter-select {
  min-width: 150px;
  max-width: 210px;
}
.grouped-results {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}
.grouped-results__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  background: var(--td-bg-color-secondarycontainer);
}
.grouped-results__toolbar > div {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.grouped-results__toolbar span,
.group-aggregate {
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.group-block {
  overflow: hidden;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
}
.group-block__header {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
  padding: 12px 14px;
  border: 0;
  background: var(--td-bg-color-container);
  color: var(--td-text-color-primary);
  cursor: pointer;
  text-align: left;
}
.group-block__header:hover {
  background: var(--td-bg-color-secondarycontainer);
}
.group-block__header .group-aggregate {
  margin-left: auto;
}
.group-block :deep(.t-table) {
  border: 0;
  border-top: 1px solid var(--td-border-level-1-color);
  border-radius: 0;
}
.group-block__pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-top: 1px solid var(--td-border-level-1-color);
  color: var(--td-text-color-secondary);
  font-size: 12px;
}

.page-error {
  margin-bottom: 16px;
}

.preset-filter-bar {
  align-items: flex-start;
  padding: 0 0 12px;
  border-bottom: 1px solid var(--td-border-level-1-color);
}

.toolbar-label {
  flex: 0 0 auto;
  padding-top: 3px;
  color: var(--td-text-color-secondary);
  font-size: 13px;
}

.preset-filter-list,
.active-filter-list {
  flex-wrap: wrap;
}

.filter-tag {
  cursor: pointer;
  user-select: none;
}

.list-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  min-width: 0;
}

.list-toolbar__search,
.list-toolbar__tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.list-toolbar__tools {
  justify-content: flex-end;
}

.keyword-input {
  width: min(360px, 100%);
}

.result-count {
  flex: 0 0 auto;
  margin-left: 0;
  white-space: nowrap;
  color: var(--td-text-color-secondary);
  font-size: 13px;
}

.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin: -2px 0 14px;
  color: var(--td-text-color-secondary);
  background: var(--td-bg-color-secondarycontainer);
  border: 1px solid var(--td-brand-color-3);
  border-radius: 4px;
}

.record-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.kanban-board {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  align-items: start;
  gap: 16px;
}

.kanban-lane {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-secondarycontainer);
}

.kanban-lane__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.kanban-lane__cards {
  display: grid;
  gap: 10px;
}

.record-card {
  min-width: 0;
}

.record-card__title {
  margin-bottom: 16px;
  overflow: hidden;
  color: var(--td-text-color-primary);
  font-size: 16px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-card__fields {
  display: grid;
  gap: 10px;
}

.record-card__field {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 8px;
  min-width: 0;
  font-size: 13px;
}

.record-card__field > span {
  color: var(--td-text-color-secondary);
}

.record-card__actions {
  display: flex;
  gap: 16px;
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--td-border-level-1-color);
}

.column-settings {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.active-filter-list {
  margin: -2px 0 14px;
}

.filter-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 56vh;
  overflow-y: auto;
  padding: 2px;
}

.filter-condition {
  display: grid;
  grid-template-columns: minmax(150px, 1.2fr) minmax(100px, 0.75fr) minmax(180px, 1.4fr) 32px;
  gap: 10px;
  align-items: center;
}

.loading-state {
  padding: 8px 0 18px;
}

.loading-state__context {
  padding: 8px 0 26px;
  border-bottom: 1px solid var(--td-border-level-1-color);
}

.loading-state__table {
  padding-top: 22px;
}

.loading-state__caption {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 22px;
  color: var(--td-text-color-secondary);
  font-size: 13px;
}

.loading-state__caption .t-icon {
  color: var(--td-brand-color);
}

@media (width <= 720px) {
  .page-heading {
    flex-direction: column;
  }

  .page-actions {
    width: 100%;
  }

  .page-actions .t-button {
    flex: 1;
  }
  .grouped-results__toolbar,
  .group-block__pagination {
    align-items: flex-start;
    flex-direction: column;
  }
  .group-select,
  .saved-filter-select {
    width: 100%;
    max-width: none;
  }

  .control-panel {
    padding: 12px;
  }

  .list-toolbar {
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
  }

  .list-toolbar__search,
  .list-toolbar__tools {
    width: 100%;
  }

  .list-toolbar__tools {
    justify-content: flex-start;
  }

  .preset-filter-bar {
    flex-direction: column;
  }

  .keyword-input {
    width: 100%;
  }

  .result-count {
    width: 100%;
    margin-left: 0;
  }

  .batch-toolbar {
    flex-wrap: wrap;
  }

  .column-settings {
    grid-template-columns: minmax(0, 1fr);
  }

  .filter-condition {
    grid-template-columns: minmax(0, 1fr) 32px;
  }

  .filter-condition > :deep(*) {
    grid-column: 1;
  }

  .filter-condition > :last-child {
    grid-column: 2;
    grid-row: 1;
  }
}
</style>
