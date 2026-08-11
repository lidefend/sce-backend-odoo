<template>
  <div class="sc-hierarchy-table" :aria-label="label" data-ui-engine="tdesign-enhanced-table" tabindex="0">
    <TEnhancedTable
      :data="tableData"
      :columns="tableColumns"
      row-key="__sc_key"
      :active-row-keys="activeRowKeys"
      active-row-type="single"
      :row-class-name="rowClassName"
      :row-attributes="rowAttributes"
      :table-content-width="tableContentWidth"
      table-layout="fixed"
      vertical-align="middle"
      size="medium"
      hover
      keyboard-row-hover
      @row-click="onRowClick"
      @row-dblclick="onRowDoubleClick"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue';
import ScIcon from './ScIcon.vue';
import { TEnhancedTable, type PrimaryTableCol, type TableRowData } from './tdesignAdapter';

export type ScHierarchyTableColumn = {
  key: string;
  label: string;
  width?: string | number;
  minWidth?: string | number;
  align?: 'left' | 'right' | 'center';
};

export type ScHierarchyTableRow = {
  key: string | number;
  depth: number;
  expandable: boolean;
  expanded: boolean;
  values: Record<string, string>;
  tone?: 'default' | 'group' | 'heading' | 'summary';
  cellTones?: Record<string, 'warning'>;
  source?: unknown;
};

type InternalRow = TableRowData & {
  __sc_key: string | number;
  __sc_row: ScHierarchyTableRow;
};

const props = withDefaults(defineProps<{
  label?: string;
  columns: ScHierarchyTableColumn[];
  rows: ScHierarchyTableRow[];
  outlineColumn: string;
  codeColumn?: string;
  selectedKey?: string | number;
  indentSize?: number;
}>(), {
  label: '层级数据表格',
  codeColumn: '',
  selectedKey: undefined,
  indentSize: 20,
});
const emit = defineEmits<{
  select: [row: ScHierarchyTableRow];
  open: [row: ScHierarchyTableRow];
  toggle: [row: ScHierarchyTableRow];
}>();

const tableData = computed<InternalRow[]>(() => props.rows.map((row) => ({
  ...row.values,
  __sc_key: row.key,
  __sc_row: row,
})));

function outlineCell(row: ScHierarchyTableRow, column: ScHierarchyTableColumn) {
  const content = [];
  if (row.expandable) {
    content.push(h('button', {
      type: 'button',
      class: 'sc-hierarchy-table__toggle',
      'aria-label': row.expanded ? '折叠层级' : '展开层级',
      'aria-expanded': row.expanded,
      onClick: (event: MouseEvent) => {
        event.stopPropagation();
        emit('toggle', row);
      },
    }, [h(ScIcon, { name: row.expanded ? 'chevron-down' : 'chevron-right', size: 14 })]));
  } else {
    content.push(h('span', { class: 'sc-hierarchy-table__toggle-spacer', 'aria-hidden': 'true' }));
  }
  content.push(h('span', { class: 'sc-hierarchy-table__value' }, row.values[column.key] || ''));
  return h('div', {
    class: 'sc-hierarchy-table__outline-cell',
    style: { paddingInlineStart: `${row.depth * props.indentSize}px` },
  }, content);
}

function codeCell(row: ScHierarchyTableRow, column: ScHierarchyTableColumn) {
  return h('div', {
    class: 'sc-hierarchy-table__code-cell',
    style: { paddingInlineStart: `${row.depth * props.indentSize}px` },
  }, [
    row.depth ? h('span', { class: 'sc-hierarchy-table__elbow', 'aria-hidden': 'true' }) : null,
    h('span', row.values[column.key] || ''),
  ]);
}

function valueCell(row: ScHierarchyTableRow, column: ScHierarchyTableColumn) {
  return h('span', {
    class: row.cellTones?.[column.key] === 'warning' ? 'sc-hierarchy-table__cell-warning' : '',
  }, row.values[column.key] || '');
}

const tableColumns = computed<PrimaryTableCol<InternalRow>[]>(() => props.columns.map((column) => ({
  colKey: column.key,
  title: column.label,
  width: column.width,
  minWidth: column.minWidth,
  align: column.align,
  ellipsis: true,
  cell: (_render, { row }) => {
    if (column.key === props.outlineColumn) return outlineCell(row.__sc_row, column);
    if (column.key === props.codeColumn) return codeCell(row.__sc_row, column);
    return valueCell(row.__sc_row, column);
  },
})));
const activeRowKeys = computed(() => props.selectedKey === undefined ? [] : [props.selectedKey]);
const tableContentWidth = computed(() => {
  const declaredWidth = props.columns.reduce((sum, column) => {
    const width = typeof column.width === 'number' ? column.width : Number.parseFloat(String(column.width || ''));
    return sum + (Number.isFinite(width) ? width : 150);
  }, 0);
  return `max(100%, ${Math.max(900, declaredWidth)}px)`;
});
const rowClassName = ({ row }: { row: InternalRow }) => [
  'sc-hierarchy-table__row',
  row.__sc_row.expandable ? 'is-parent' : '',
  row.__sc_row.tone && row.__sc_row.tone !== 'default' ? `is-${row.__sc_row.tone}` : '',
  row.__sc_key === props.selectedKey ? 'is-selected' : '',
];
const rowAttributes = ({ row }: { row: InternalRow }) => ({
  tabindex: 0,
  'aria-selected': row.__sc_key === props.selectedKey ? 'true' : 'false',
  onKeydown: (event: KeyboardEvent) => {
    if (event.key === 'Enter') emit('select', row.__sc_row);
  },
});
function onRowClick(context: { row: InternalRow }): void { emit('select', context.row.__sc_row); }
function onRowDoubleClick(context: { row: InternalRow }): void { emit('open', context.row.__sc_row); }
</script>

<style scoped>
.sc-hierarchy-table {
  min-width: 0;
  overflow: auto;
  border-top: 1px solid var(--sc-semantic-border-default);
  background: var(--sc-semantic-surface-panel);
}

.sc-hierarchy-table :deep(.t-table) {
  color: var(--sc-semantic-text-primary);
  background: var(--sc-semantic-surface-panel);
}

.sc-hierarchy-table :deep(.t-table__header th) {
  height: var(--sc-table-header-height);
  background: var(--sc-table-header-bg);
  color: var(--sc-semantic-text-secondary);
  font-size: var(--sc-product-text-sm);
  font-weight: 700;
}

.sc-hierarchy-table :deep(.t-table__body tr) {
  height: var(--sc-product-table-row-height);
}

.sc-hierarchy-table :deep(.t-table__body tr.is-parent td) {
  font-weight: 650;
}

.sc-hierarchy-table :deep(.t-table__body tr.is-group td),
.sc-hierarchy-table :deep(.t-table__body tr.is-heading td) {
  background: var(--sc-semantic-surface-subtle);
  font-weight: 650;
}

.sc-hierarchy-table :deep(.t-table__body tr.is-summary td) {
  background: var(--sc-semantic-surface-selected);
  font-weight: 650;
}

.sc-hierarchy-table :deep(.t-table__body tr.is-selected td) {
  background: var(--sc-semantic-surface-selected);
}

.sc-hierarchy-table :deep(.t-table__body tr:focus-visible) {
  outline: 2px solid var(--sc-semantic-surface-interactive);
  outline-offset: -2px;
}

.sc-hierarchy-table :deep(.sc-hierarchy-table__outline-cell),
.sc-hierarchy-table :deep(.sc-hierarchy-table__code-cell) {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: var(--sc-space-2xs);
}

.sc-hierarchy-table :deep(.sc-hierarchy-table__value) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sc-hierarchy-table :deep(.sc-hierarchy-table__cell-warning) {
  color: var(--sc-semantic-state-warning-text);
  font-weight: 650;
}

.sc-hierarchy-table :deep(.sc-hierarchy-table__toggle),
.sc-hierarchy-table :deep(.sc-hierarchy-table__toggle-spacer) {
  flex: 0 0 var(--sc-touch-target-min);
  width: var(--sc-touch-target-min);
  height: var(--sc-touch-target-min);
}

.sc-hierarchy-table :deep(.sc-hierarchy-table__toggle) {
  display: inline-grid;
  place-items: center;
  border: 0;
  border-radius: var(--sc-product-radius-control);
  background: transparent;
  color: var(--sc-semantic-text-secondary);
  cursor: pointer;
}

.sc-hierarchy-table :deep(.sc-hierarchy-table__toggle:hover),
.sc-hierarchy-table :deep(.sc-hierarchy-table__toggle:focus-visible) {
  background: var(--sc-semantic-surface-hover);
  color: var(--sc-semantic-text-primary);
  outline: none;
}

.sc-hierarchy-table :deep(.sc-hierarchy-table__elbow) {
  width: var(--sc-space-sm);
  height: var(--sc-space-sm);
  border-bottom: 1px solid var(--sc-semantic-border-default);
  border-left: 1px solid var(--sc-semantic-border-default);
}
</style>
