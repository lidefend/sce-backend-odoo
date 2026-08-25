<template>
  <section class="page sc-page sc-product-workspace-stack" data-product-page-mode="list">
    <PageHeader
      v-if="status === 'error'"
      :title="title"
      :subtitle="subtitle"
      :status="status"
      :status-label="statusLabel"
      :loading="loading"
      :on-reload="onReload"
      :mode-label="modeLabelText"
      :record-count="records.length"
    />

    <ProductLoadingSkeleton
      v-if="loading && !hasRetainedContent"
      :title="title"
      mode="kanban"
      loading-label="正在载入数据"
    />
    <StatusPanel
      v-else-if="status === 'error'"
      :title="errorCopy.title"
      :message="errorCopy.message"
      :trace-id="error?.traceId || traceId"
      :error-code="error?.code || errorCode"
      :reason-code="error?.reasonCode"
      :error-category="error?.errorCategory"
      :error-details="error?.details"
      :retryable="error?.retryable"
      :hint="errorCopy.hint || errorHint"
      :suggested-action="error?.suggestedAction"
      variant="error"
      :on-retry="onReload"
    />
    <StatusPanel
      v-else-if="status === 'empty'"
      :title="emptyCopy.title"
      :message="emptyCopy.message"
      variant="info"
      :on-retry="onReload"
    />

    <template v-else>
      <slot name="toolbar"></slot>

      <section
        class="grid sc-product-main-surface"
        :class="{ 'is-refreshing': loading, 'is-workflow-board': workflowBoard }"
        :data-collection-presentation="workflowBoard ? 'workflow_board' : 'explicit_card'"
        :aria-busy="loading || undefined"
      >
        <span v-if="loading" class="refresh-status">正在刷新数据</span>
        <CollectionKanbanLane
          v-for="lane in displayLanes"
          :key="lane.key"
          :lane-key="lane.key"
          :label="lane.label"
          :record-count="lane.records.length"
          :show-header="workflowBoard"
        >
            <CollectionKanbanRecordCard
              v-for="(row, index) in lane.records"
              :key="String(row.id ?? index)"
              :record-key="String(row.id ?? index)"
              :title="rowTitle(row)"
              :tone="rowTone(row)"
              :statuses="cardStatuses(row)"
              :primary-facts="cardFacts(row, primaryMetaFields)"
              :secondary-facts="cardFacts(row, secondaryMetaFields)"
              open-label="打开记录"
              @open="handleCard(row)"
            />
        </CollectionKanbanLane>
      </section>

      <CollectionPaginationFooter
        :mode="showPagination ? 'paged' : 'count'"
        :record-count-text="paginationTotalText"
        :loading="loading"
        :can-previous="canPagePrev"
        :can-next="canPageNext"
        :page-text="`第 ${currentPage} / ${totalPages} 页`"
        :page-jump-value="pageJumpInput"
        page-limit-value=""
        :list-limit="listLimit"
        :total-pages="totalPages"
        :page-limit-options="[]"
        :show-page-size="false"
        :labels="paginationLabels"
        @previous="pagePrev"
        @next="pageNext"
        @page-jump-input="pageJumpInput = $event"
        @page-jump="jumpPage"
      />
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import StatusPanel from '../components/StatusPanel.vue';
import PageHeader from '../components/page/PageHeader.vue';
import ProductLoadingSkeleton from '../components/product-list/ProductLoadingSkeleton.vue';
import CollectionKanbanRecordCard, { type CollectionKanbanFact, type CollectionKanbanStatus } from '../components/product-list/CollectionKanbanRecordCard.vue';
import CollectionPaginationFooter from '../components/product-list/CollectionPaginationFooter.vue';
import CollectionKanbanLane from '../components/product-list/CollectionKanbanLane.vue';
import { resolveEmptyCopy, resolveErrorCopy, type StatusError } from '../composables/useStatus';
import { pageModeLabel } from '../app/pageMode';
import { semanticStatus, semanticValueByField } from '../utils/semantic';
import { groupCollectionRecords } from '../app/runtime/collectionViewRuntime';

const props = defineProps<{
  title: string;
  status: 'loading' | 'ok' | 'empty' | 'error';
  loading: boolean;
  errorMessage?: string;
  traceId?: string;
  errorCode?: number | null;
  errorHint?: string;
  error?: StatusError | null;
  records: Array<Record<string, unknown>>;
  fields: string[];
  primaryFields?: string[];
  secondaryFields?: string[];
  statusFields?: string[];
  fieldLabels?: Record<string, string>;
  titleField: string;
  onReload: () => void;
  onCardClick: (row: Record<string, unknown>) => void;
  subtitle: string;
  statusLabel: string;
  pageMode?: string;
  sceneKey?: string;
  listTotalCount?: number | null;
  listOffset?: number;
  listLimit?: number;
  onPageChange?: (offset: number) => void;
  presentationSemantic?: 'card' | 'workflow_board' | string;
  groupField?: string;
}>();
const errorCopy = computed(() =>
  resolveErrorCopy(
    props.error || null,
    props.errorMessage || 'Card load failed',
  ),
);
const emptyCopy = computed(() => resolveEmptyCopy('card'));
const hasRetainedContent = computed(() => props.records.length > 0 && props.fields.length > 0);
const workflowBoard = computed(() => props.presentationSemantic === 'workflow_board' && Boolean(props.groupField));
const displayLanes = computed(() => {
  if (!workflowBoard.value || !props.groupField) {
    return groupCollectionRecords(props.records, '');
  }
  return groupCollectionRecords(props.records, props.groupField);
});

function normalizedFieldName(raw: unknown): string {
  if (typeof raw === 'string' || typeof raw === 'number') {
    const text = String(raw || '').trim();
    if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(text)) return text;
    return text.match(/(?:^|[,{])\s*name\s*[:.]\s*\.?([A-Za-z_][A-Za-z0-9_]*)/i)?.[1] || '';
  }
  const row = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw as Record<string, unknown> : {};
  for (const candidate of [row.name, row.field_name, row.field_code, row.fieldCode, row.field]) {
    const name = candidate === raw ? '' : normalizedFieldName(candidate);
    if (name) return name;
  }
  return '';
}
const normalizedFields = computed(() => props.fields.map(normalizedFieldName).filter(Boolean));
const technicalFields = new Set(['id', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update']);
const businessMetaField = (field: string) => field && field !== props.titleField && !technicalFields.has(field);
const fallbackMetaFields = computed(() => normalizedFields.value.filter(businessMetaField));
const statusMetaFields = computed(() => {
  const preferred = (props.statusFields || []).map(normalizedFieldName).filter(businessMetaField);
  if (preferred.length) return preferred.slice(0, 2);
  return [];
});
const primaryMetaFields = computed(() => {
  const preferred = (props.primaryFields || []).map(normalizedFieldName).filter(
    (field) => businessMetaField(field) && !statusMetaFields.value.includes(field),
  );
  if (preferred.length) return preferred.slice(0, 2);
  return fallbackMetaFields.value.filter((field) => !statusMetaFields.value.includes(field)).slice(0, 2);
});
const secondaryMetaFields = computed(() => {
  const preferred = (props.secondaryFields || []).map(normalizedFieldName).filter(
    (field) =>
      businessMetaField(field)
      && !statusMetaFields.value.includes(field)
      && !primaryMetaFields.value.includes(field),
  );
  if (preferred.length) return preferred.slice(0, 3);
  return fallbackMetaFields.value
    .filter((field) => !statusMetaFields.value.includes(field) && !primaryMetaFields.value.includes(field))
    .slice(0, 3);
});

const modeLabelText = computed(() => pageModeLabel(props.pageMode || 'workspace'));
const paginationLabels = {
  region: '卡片分页', previous: '上一页', next: '下一页', groupPrevious: '上一组', groupNext: '下一组',
  pageInput: '输入页码', jump: '跳转', pageSize: '每页', pageSizeInput: '输入每页条数', pageSizeSelect: '选择每页条数',
};
const pageJumpInput = ref('');
const observedListLimit = ref(0);
const listLimit = computed(() => {
  if (observedListLimit.value > 0) return observedListLimit.value;
  const limit = Number(props.listLimit || 40);
  return Number.isFinite(limit) && limit > 0 ? Math.trunc(limit) : 40;
});
const listTotal = computed(() => {
  if (props.listTotalCount === null || typeof props.listTotalCount === 'undefined') return null;
  const raw = Number(props.listTotalCount);
  if (!Number.isFinite(raw) || raw < 0) return null;
  return Math.trunc(raw);
});
const listOffset = computed(() => {
  const offset = Number(props.listOffset || 0);
  if (!Number.isFinite(offset) || offset <= 0) return 0;
  return Math.trunc(offset);
});
const totalPages = computed(() => {
  const total = listTotal.value || 0;
  return Math.max(1, Math.ceil(total / listLimit.value));
});
const currentPage = computed(() => Math.min(totalPages.value, Math.floor(listOffset.value / listLimit.value) + 1));
const showPagination = computed(() => listTotal.value !== null && props.status !== 'empty');
const canPagePrev = computed(() => listOffset.value > 0);
const canPageNext = computed(() => {
  const total = listTotal.value || 0;
  return listOffset.value + listLimit.value < total;
});
const paginationTotalText = computed(() => `共 ${listTotal.value ?? props.records.length} 条`);
function semanticCell(field: string, value: unknown) {
  return semanticValueByField(field, value);
}

function rowTone(row: Record<string, unknown>) {
  const state = row.state || row.stage_id || row.status;
  return semanticStatus(state).tone;
}

function rowTitle(row: Record<string, unknown>): string {
  return formatValue(row[props.titleField]) || formatValue(row.name) || formatValue(row.display_name) || String(row.id ?? '');
}

function cardFacts(row: Record<string, unknown>, fields: string[]): CollectionKanbanFact[] {
  return fields.map((field) => ({ key: field, label: fieldLabel(field), value: semanticCell(field, row[field]).text }));
}

function cardStatuses(row: Record<string, unknown>): CollectionKanbanStatus[] {
  return statusMetaFields.value.map((field) => {
    const cell = semanticCell(field, row[field]);
    return {
      key: field,
      label: fieldLabel(field),
      value: cell.text,
      semantic: cell.tone === 'neutral' ? 'default' : cell.tone,
    };
  });
}

function fieldLabel(name: string) {
  const labels = props.fieldLabels || {};
  return labels[name] || name;
}

function handleCard(row: Record<string, unknown>) {
  props.onCardClick(row);
}

function emitPageOffset(offset: number) {
  if (!props.onPageChange) return;
  const total = listTotal.value || 0;
  const maxOffset = total > 0 ? Math.floor((total - 1) / listLimit.value) * listLimit.value : 0;
  const normalized = Math.min(Math.max(Math.trunc(offset || 0), 0), maxOffset);
  props.onPageChange(normalized);
}

function pagePrev() {
  emitPageOffset(listOffset.value - listLimit.value);
}

function pageNext() {
  emitPageOffset(listOffset.value + listLimit.value);
}

function jumpPage() {
  const page = Number(pageJumpInput.value || currentPage.value);
  if (!Number.isFinite(page)) return;
  const normalizedPage = Math.min(Math.max(Math.trunc(page), 1), totalPages.value);
  pageJumpInput.value = String(normalizedPage);
  emitPageOffset((normalizedPage - 1) * listLimit.value);
}

watch(
  currentPage,
  (page) => {
    pageJumpInput.value = String(page);
  },
  { immediate: true },
);

watch(
  [() => props.records.length, listTotal],
  ([length, totalRaw]) => {
    const total = totalRaw || 0;
    if (length <= 0 || total <= 0) return;
    if (length > observedListLimit.value) {
      observedListLimit.value = length;
      return;
    }
    if (listOffset.value === 0) {
      observedListLimit.value = length;
    }
  },
  { immediate: true },
);

function formatValue(value: unknown) {
  if (Array.isArray(value)) {
    if (value.length > 1 && value[1] !== null && value[1] !== undefined) {
      return String(value[1]);
    }
    if (value.length > 0 && value[0] !== null && value[0] !== undefined) {
      return String(value[0]);
    }
    return '';
  }
  if (value && typeof value === 'object') {
    const maybeName = (value as Record<string, unknown>).name;
    if (maybeName !== null && maybeName !== undefined && String(maybeName).trim()) {
      return String(maybeName);
    }
    return '';
  }
  if (value === null || value === undefined) {
    return '';
  }
  return String(value);
}
</script>

<style scoped>
.page {
  display: grid;
  gap: var(--sc-product-workspace-stack-gap);
}


.grid {
  position: relative;
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.grid:not(.is-workflow-board) :deep(.collection-kanban-lane__cards) {
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.grid.is-workflow-board {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  align-items: start;
}

.grid.is-refreshing {
  pointer-events: none;
}

.grid.is-refreshing::before {
  position: absolute;
  z-index: 2;
  top: 0;
  right: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent 0%, var(--sc-semantic-surface-interactive) 45%, transparent 100%);
  background-size: 45% 100%;
  content: '';
  animation: kanban-refresh-progress 1.15s ease-in-out infinite;
}

.refresh-status {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

@keyframes kanban-refresh-progress {
  from { background-position: -80% 0; }
  to { background-position: 180% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .grid.is-refreshing::before {
    animation: none;
    background: var(--sc-semantic-surface-interactive);
  }
}

</style>
