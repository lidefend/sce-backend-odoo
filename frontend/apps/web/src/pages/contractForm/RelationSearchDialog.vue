<template>
  <ScDialog
    :open="dialog.open"
    :title="dialog.title"
    :close-label="dialog.labels.close || '关闭'"
    panel-class="relation-dialog"
    data-professional-relation-lifecycle="search"
    @close="$emit('close')"
  >
      <div class="relation-dialog-search" role="search">
        <ScInput
          ref="searchInputRef"
          class="relation-dialog-search__input"
          type="search"
          autofocus
          :model-value="dialog.keyword"
          :placeholder="dialog.labels.search_placeholder || '输入名称搜索'"
          :loading="dialog.loading"
          :aria-label="dialog.labels.search_placeholder || '输入名称搜索'"
          @update:model-value="$emit('keyword-change', String($event))"
          @keydown.enter.prevent="$emit('search')"
        />
        <ScButton :disabled="dialog.loading" @click="$emit('search')">
          {{ dialog.labels.search || '搜索' }}
        </ScButton>
      </div>
      <p v-if="dialog.error" class="validation-error" role="alert">{{ dialog.error }}</p>
      <div class="relation-dialog-table-wrap">
        <ScLoading :loading="dialog.loading" :label="dialog.labels.loading || '正在加载关系记录'">
        <ScTable class="relation-dialog-table" :aria-busy="dialog.loading || undefined"
          :label="dialog.title" :data="dialog.rows" :columns="relationTableColumns" row-key="id" size="small"
          role="listbox"
          row-selection-type="single" :select-on-row-click="true" :selected-row-keys="selectedRowKeys"
          :row-class-name="relationRowClassName" :row-attributes="relationRowAttributes"
          @select-change="onTableSelectChange" @row-dblclick="onTableConfirm" />
        </ScLoading>
        <ScEmptyState v-if="!dialog.loading && !dialog.rows.length" :title="dialog.labels.empty || '未找到匹配记录'" />
      </div>
      <div class="relation-dialog-mobile-results" role="listbox" :aria-label="dialog.title" :aria-busy="dialog.loading || undefined">
        <label
          v-for="row in dialog.rows"
          :key="`rel-card-${row.id}`"
          class="relation-dialog-result-card"
          :class="{ 'relation-dialog-result-card--active': dialog.selectedId === row.id }"
          data-semantic-component="RelationSearchResult"
          data-semantic-layout="mobile-card"
          :data-record-id="row.id"
          role="option"
          tabindex="0"
          :aria-selected="dialog.selectedId === row.id"
          @dblclick="$emit('confirm', row)"
          @keydown.space.prevent="$emit('select-row', row)"
          @keydown.enter.prevent="$emit('confirm', row)"
        >
          <input
            type="radio"
            name="relation-search-select-mobile"
            :checked="dialog.selectedId === row.id"
            :aria-label="relationSearchPrimaryText(row)"
            tabindex="-1"
            @change="$emit('select-row', row)"
          />
          <span class="relation-dialog-result-content">
            <span class="relation-dialog-result-head">
              <strong>{{ relationSearchPrimaryText(row) }}</strong>
              <span v-if="dialog.selectedId === row.id">已选择</span>
            </span>
            <span v-if="dialog.columns.length > 1" class="relation-dialog-result-facts">
              <span v-for="column in dialog.columns.slice(1)" :key="`${row.id}-card-${column.name}`">
                <small>{{ column.label }}</small>
                <em>{{ relationSearchCell(row, column.name) || '未填写' }}</em>
              </span>
            </span>
          </span>
        </label>
        <ScEmptyState v-if="!dialog.loading && !dialog.rows.length" :title="dialog.labels.empty || '未找到匹配记录'" />
      </div>
      <footer class="relation-dialog-footer">
        <span class="relation-dialog-count">{{ recordCountLabel }}</span>
        <span class="relation-dialog-footer-spacer"></span>
        <span class="relation-dialog-footer-actions">
          <ScButton variant="ghost" :disabled="busy" @click="$emit('close')">
            {{ dialog.labels.cancel || '取消' }}
          </ScButton>
          <ScButton
            v-if="dialog.createMode !== 'none'"
            variant="secondary"
            :disabled="busy || dialog.loading"
            @click="$emit('create')"
          >
            {{ dialog.labels.create || '新建' }}
          </ScButton>
          <ScButton
            variant="primary"
            :disabled="busy || dialog.loading || !dialog.selectedId"
            @click="$emit('confirm')"
          >
            {{ dialog.labels.select || '选择' }}
          </ScButton>
        </span>
      </footer>
  </ScDialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScTable from '../../components/design-system/ScTable.vue';
import ScDialog from '../../components/design-system/ScDialog.vue';
import ScEmptyState from '../../components/design-system/ScEmptyState.vue';
import ScInput from '../../components/design-system/ScInput.vue';
import ScLoading from '../../components/design-system/ScLoading.vue';
import type { RelationOption, RelationSearchColumn, RelationSearchRow, RelationUiLabels } from './types';

export type RelationSearchDialogState = {
  open: boolean;
  fieldName: string;
  title: string;
  keyword: string;
  loading: boolean;
  error: string;
  options: RelationOption[];
  rows: RelationSearchRow[];
  columns: RelationSearchColumn[];
  selectedId: number | null;
  createMode: 'none' | 'quick' | 'page' | 'dialog';
  labels: RelationUiLabels;
};

const props = defineProps<{
  dialog: RelationSearchDialogState;
  busy: boolean;
  recordCountLabel: string;
}>();

const emit = defineEmits<{
  close: [];
  search: [];
  create: [];
  confirm: [row?: RelationSearchRow];
  'select-row': [row: RelationSearchRow];
  'keyword-change': [keyword: string];
}>();

const searchInputRef = ref<{ $el?: HTMLInputElement } | null>(null);
const selectedRowKeys = computed<Array<string | number>>(() => props.dialog.selectedId ? [props.dialog.selectedId] : []);
const relationTableColumns = computed(() => props.dialog.columns.map((column) => ({
  colKey: column.name,
  title: column.label,
  cell: ({ row }: { row: RelationSearchRow }) => relationSearchCell(row, column.name),
})));

function tableRow(context: unknown): RelationSearchRow | null {
  if (!context || typeof context !== 'object') return null;
  const row = (context as { row?: unknown }).row;
  return row && typeof row === 'object' && 'id' in row ? row as RelationSearchRow : null;
}
function relationRowClassName(context: unknown) {
  const row = tableRow(context);
  return row?.id === props.dialog.selectedId ? 'relation-dialog-row--active' : '';
}
function relationRowAttributes(context: unknown): Record<string, unknown> {
  const row = tableRow(context);
  return {
    'data-semantic-component': 'RelationSearchResult',
    'data-semantic-layout': 'table-row',
    'data-record-id': row?.id,
    role: 'option',
    tabindex: 0,
    'aria-selected': row?.id === props.dialog.selectedId,
    onKeydown: (event: KeyboardEvent) => {
      if (!row) return;
      if (event.key === ' ') { event.preventDefault(); emit('select-row', row); }
      if (event.key === 'Enter') { event.preventDefault(); emit('confirm', row); }
    },
  };
}
function onTableSelectChange(keys: Array<string | number>) {
  const selected = props.dialog.rows.find((row) => row.id === Number(keys.at(-1)));
  if (selected) emit('select-row', selected);
}
function onTableConfirm(context: unknown) {
  const row = tableRow(context);
  if (row) emit('confirm', row);
}

watch(
  () => props.dialog.open,
  async (open) => {
    if (!open) return;
    await nextTick();
    searchInputRef.value?.$el?.focus();
  },
);

function relationSearchCell(row: RelationSearchRow, columnName: string) {
  const value = row.values[columnName];
  if (value === null || value === undefined || value === false) return '';
  if (Array.isArray(value)) {
    if (value.length >= 2) return String(value[1] ?? '');
    return value.map((item) => String(item ?? '')).filter(Boolean).join(', ');
  }
  if (typeof value === 'object') {
    const rec = value as Record<string, unknown>;
    return String(rec.display_name || rec.name || rec.id || '');
  }
  if (typeof value === 'boolean') return value ? '是' : '否';
  return String(value);
}

function relationSearchPrimaryText(row: RelationSearchRow) {
  const primaryColumn = props.dialog.columns[0];
  return primaryColumn ? relationSearchCell(row, primaryColumn.name) || `记录 ${row.id}` : `记录 ${row.id}`;
}
</script>

<style scoped src="./RelationSearchDialog.css"></style>
