<template>
  <div v-if="field.type === 'many2many'" class="relation-editor">
    <div
      v-if="isAttachmentField(field)"
      class="relation-attachment-editor"
      data-semantic-component="RelationAttachmentEditor"
      :data-control-state="field.readonly ? 'readonly' : 'editable'"
    >
      <div v-if="adapter.selectedRelationOptions(field.name).length" class="attachment-list">
        <div
          v-for="att in adapter.selectedRelationOptions(field.name)"
          :key="`${field.name}-att-${att.id}`"
          class="attachment-item"
        >
          <ScIcon name="file-text" :size="16" />
          <span class="attachment-name" :title="attachmentDisplayName(att)">{{ attachmentDisplayName(att) }}</span>
          <ScButton variant="ghost" size="small" @click="downloadAttachment(att)">下载</ScButton>
          <ScButton
            v-if="!field.readonly"
            variant="ghost"
            size="small"
            :disabled="adapter.busy"
            :aria-label="`移除${att.label}`"
            @click="toggleRelationId(field.name, att.id, false)"
          >移除</ScButton>
        </div>
      </div>
      <ScInlineState
        v-else-if="field.readonly"
        class="attachment-empty"
        state="empty"
        label="暂无附件"
      />
      <ScFileField
        v-if="!field.readonly"
        :key="uploadTick"
        class="attachment-upload"
        :disabled="adapter.busy"
        :multiple="true"
        choose-label="上传附件"
        empty-label="未选择文件"
        @change="handleAttachmentUpload(field, $event)"
      />
      <ScInlineState
        v-if="attachmentError"
        class="attachment-error"
        state="error"
        :label="attachmentError"
      />
    </div>
    <ProfessionalManyToManySelect
      v-else
      :field="field"
      :adapter="adapter"
    />
  </div>
  <div v-else-if="field.type === 'one2many'" class="relation-editor">
    <div v-if="field.readonly" class="o2m-readonly" data-readonly-relation>
      <div v-if="one2manyRows.length" class="o2m-readonly-list">
        <article
          v-for="row in paginatedOne2manyRows"
          :key="row.key"
          class="o2m-readonly-row"
        >
          <p v-if="adapter.one2manyRowStateLabel(row)" class="o2m-readonly-state">
            {{ adapter.one2manyRowStateLabel(row) }}
          </p>
          <dl class="o2m-readonly-facts">
            <div
              v-for="column in adapter.one2manyColumns(field.name)"
              :key="`${row.key}-readonly-${column.name}`"
              class="o2m-readonly-fact"
            >
              <dt>{{ column.label }}</dt>
              <dd>{{ adapter.one2manyColumnDisplayValue(column, row.values[column.name]) || '—' }}</dd>
            </div>
          </dl>
        </article>
      </div>
      <ScInlineState
        v-else-if="adapter.isOne2manyHydrating(field.name)"
        class="relation-readonly-loading"
        state="loading"
        label="正在加载关系记录"
        data-readonly-relation-loading
      />
      <ScInlineState v-else class="relation-readonly-empty" state="empty" label="暂无可展示记录" data-readonly-relation-empty />
    </div>
        <template v-else>
    <div class="o2m-card">
      <div class="o2m-toolbar">
        <span class="o2m-title">{{ field.label }}</span>
        <span v-if="adapter.visibleOne2manyRows(field.name).length" class="o2m-count">共 {{ adapter.visibleOne2manyRows(field.name).length }} 条</span>
        <span v-if="adapter.one2manySummary(field.name)" class="o2m-summary">{{ adapter.one2manySummary(field.name) }}</span>
        <span class="o2m-spacer" />
        <slot name="collection-actions" />
        <ScButton
          v-if="adapter.one2manyCanCreate(field.name)"
          class="o2m-create"
          type="button"
          variant="primary"
          size="small"
          :disabled="adapter.busy"
          @click="adapter.addOne2manyRow(field.name)"
        >
          {{ adapter.one2manyCreateLabel(field.name, field.label) }}
        </ScButton>
      </div>

      <div
        v-if="adapter.one2manyColumns(field.name).length && adapter.visibleOne2manyRows(field.name).length"
        class="o2m-table-scroll"
      >
        <ScTable
          :data="o2mTableData"
          :columns="o2mTableColumns"
          row-key="id"
          size="small"
          :hover="true"
          :stripe="false"
          :foot-data="o2mTableFootData"
          appearance="relation-detail"
          label="明细列表"
        >
          <template #_state="{ row }">
            <div class="o2m-state-cell">
              <span class="o2m-state-badge">{{ row._stateLabel }}</span>
              <ScInlineState
                v-for="message in row._messages"
                :key="`${row._key}-${message.state}-${message.label}`"
                class="o2m-row-message"
                :state="message.state"
                :label="message.label"
              />
            </div>
          </template>
          <template
            v-for="column in adapter.one2manyColumns(field.name)"
            :key="`cell-${column.name}`"
            #[column.name]="{ row }"
          >
            <ScCheckbox
              v-if="column.ttype === 'boolean'"
              class="input-checkbox"
              :disabled="column.readonly || adapter.busy"
              :checked="Boolean(row._row.values[column.name])"
              :label="column.label"
              @change="adapter.setOne2manyRowField(field.name, row._key, column, $event)"
            />
            <ScSelect
              v-else-if="column.ttype === 'selection'"
              :disabled="column.readonly || adapter.busy"
              :model-value="String(row._row.values[column.name] ?? '')"
              :placeholder="adapter.selectPlaceholder(column.label)"
              :options="(column.selection || []).map((option) => ({ value: String(option[0]), label: String(option[1]) }))"
              @update:model-value="adapter.setOne2manyRowField(field.name, row._key, column, $event)"
            />
            <ScInput
              v-else
              :appearance="isO2mAmountColumn(column) ? 'numeric-entry' : 'default'"
              :align="isO2mAmountColumn(column) ? 'right' : 'left'"
              :type="adapter.one2manyColumnInputType(column)"
              :disabled="column.readonly || adapter.busy"
              :model-value="adapter.one2manyColumnDisplayValue(column, row._row.values[column.name])"
              :placeholder="column.label"
              @update:model-value="adapter.setOne2manyRowField(field.name, row._key, column, $event)"
            />
          </template>
          <template #_action="{ row }">
            <ScButton
              class="o2m-row-remove"
              type="button"
              variant="danger"
              size="small"
              :aria-label="`移除${adapter.one2manyRowLabel(field.name, row._row)}`"
              :disabled="adapter.busy"
              @click="adapter.removeOne2manyRow(field.name, row._key)"
            >移除</ScButton>
          </template>
        </ScTable>
      </div>

      <ScInlineState
        v-else-if="adapter.one2manyColumns(field.name).length"
        class="o2m-empty"
        state="empty"
        :label="`暂无明细，点击「${adapter.one2manyCreateLabel(field.name, field.label)}」新增`"
        data-o2m-empty
      />

      <div v-if="adapter.removedOne2manyRows(field.name).length" class="o2m-removed">
        <ScInlineState
          class="meta"
          state="info"
          :label="`已移除 ${adapter.removedOne2manyRows(field.name).length} 行，提交前可撤销`"
        />
        <div class="chips">
          <ScButton
            v-for="row in adapter.removedOne2manyRows(field.name)"
            :key="`rm-${row.key}`"
            class="o2m-row-restore"
            type="button"
            variant="ghost"
            size="small"
            :disabled="adapter.busy"
            @click="adapter.restoreOne2manyRow(field.name, row.key)"
          >
            撤销移除 · {{ adapter.one2manyRowLabel(field.name, row) }} · 待删除
          </ScButton>
        </div>
      </div>
    </div>
    </template>
    <nav v-if="one2manyPageCount > 1" class="o2m-pagination" aria-label="明细分页" data-detail-collection-pagination>
      <ScButton type="button" class="o2m-page-action" variant="ghost" size="small" :disabled="one2manyPage <= 1" @click="one2manyPage -= 1">上一页</ScButton>
      <span>第 {{ one2manyPage }} / {{ one2manyPageCount }} 页</span>
      <ScButton type="button" class="o2m-page-action" variant="ghost" size="small" :disabled="one2manyPage >= one2manyPageCount" @click="one2manyPage += 1">下一页</ScButton>
    </nav>
  </div>
  <ScInput
  v-else-if="field.type !== 'many2many' && field.type !== 'one2many'"
    :model-value="adapter.inputFieldValue(field.name)"
    :type="adapter.fieldInputType(field.type)"
    :placeholder="adapter.inputPlaceholder(field.label)"
    @update:model-value="adapter.setTextField(field.name, $event)"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { FormSectionFieldSchema } from './formSection.types';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScFileField from '../design-system/ScFileField.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScInput from '../design-system/ScInput.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import ScSelect from '../design-system/ScSelect.vue';
import ScTable from '../design-system/ScTable.vue';
import ProfessionalManyToManySelect from '../professional-fields/ProfessionalManyToManySelect.vue';
import { downloadFile, fileToBase64, uploadFile } from '../../api/files';
import type { RelationFieldColumn, RelationFieldRow, X2ManyRelationRendererProps } from './relationField.types';

const props = defineProps<X2ManyRelationRendererProps>();
const one2manyPage = ref(1);
const one2manyPageSize = 20;
const one2manyRows = computed(() => {
  if (props.field.type !== 'one2many') return [];
  const rows = props.adapter.visibleOne2manyRows(props.field.name);
  if (!props.field.readonly) return rows;
  const columns = props.adapter.one2manyColumns(props.field.name);
  return rows.filter((row) => columns.some((column) => (
    Boolean(props.adapter.one2manyColumnDisplayValue(column, row.values[column.name]))
  )));
});
const one2manyPageCount = computed(() => Math.max(1, Math.ceil(one2manyRows.value.length / one2manyPageSize)));
const paginatedOne2manyRows = computed(() => {
  const start = (one2manyPage.value - 1) * one2manyPageSize;
  return one2manyRows.value.slice(start, start + one2manyPageSize);
});
watch(one2manyPageCount, (count) => {
  if (one2manyPage.value > count) one2manyPage.value = count;
});


function isO2mAmountColumn(column: RelationFieldColumn) {
  return String(column.ttype).toLowerCase() === 'monetary';
}


// ===== TDesign Table 列定义与行数据 =====
const o2mTableColumns = computed(() => {
  const fieldColumns = props.adapter.one2manyColumns(props.field.name).map((column) => ({
    colKey: column.name,
    width: isO2mAmountColumn(column) ? 140 : undefined,
    align: isO2mAmountColumn(column) ? 'right' : 'left',
    ellipsis: true,
  }));
  return [
    { colKey: '_state', title: '状态', width: 90, fixed: 'left' },
    ...fieldColumns,
    { colKey: '_action', title: '操作', width: 80, fixed: 'right' },
  ];
});

const o2mTableData = computed(() => paginatedOne2manyRows.value.map((row) => {
  const rowData: Record<string, unknown> = {
    id: String(row.key),
    _row: row,
    _key: row.key,
    _stateLabel: props.adapter.one2manyRowStateLabel(row),
    _hasMessages: o2mRowHasMessages(row),
    _messages: o2mRowMessages(row),
  };
  // 展开字段值到行对象，供 TDesign Table 普通列渲染
  const columns = props.adapter.one2manyColumns(props.field.name);
  columns.forEach((column) => {
    rowData[column.name] = props.adapter.one2manyColumnDisplayValue(column, row.values[column.name]);
  });
  return rowData;
}));

const o2mTableFootData = computed(() => {
  const footRow: Record<string, unknown> = {
    id: '__total__',
    _stateLabel: `全部 ${one2manyRows.value.length} 条合计`,
    _messages: [],
  };
  const amountCol = aggregateAmountColumn.value;
  if (!amountCol || !one2manyRows.value.length) return [];
  footRow[amountCol.name] = o2mAmountTotalText.value;
  return [footRow];
});

const o2mAmountTotal = computed(() => {
  const amountCol = aggregateAmountColumn.value;
  if (!amountCol) return 0;
  // The footer is the collection total, so pagination must not narrow the
  // authoritative business amount to the currently visible window.
  return one2manyRows.value.reduce((sum, row) => {
    const value = Number(row.values[amountCol.name]);
    return sum + (Number.isFinite(value) ? value : 0);
  }, 0);
});

const o2mAmountTotalText = computed(() => {
  const amountCol = aggregateAmountColumn.value;
  return amountCol ? props.adapter.one2manyColumnDisplayValue(amountCol, o2mAmountTotal.value) : '';
});

const aggregateAmountColumn = computed(() => (
  props.adapter.one2manyColumns(props.field.name).find(isO2mAmountColumn)
));

function o2mRowHasMessages(row: RelationFieldRow) {
  const name = props.field.name;
  const errors = props.adapter.showOne2manyErrors ? props.adapter.one2manyRowErrors(name, row.key) : [];
  const hints = props.adapter.one2manyRowHints(name, row);
  return errors.length > 0 || hints.length > 0;
}

function o2mRowMessages(row: RelationFieldRow) {
  const name = props.field.name;
  const errors = props.adapter.showOne2manyErrors ? props.adapter.one2manyRowErrors(name, row.key) : [];
  const hints = props.adapter.one2manyRowHints(name, row);
  return [
    ...errors.map((label) => ({ state: 'error' as const, label })),
    ...hints.map((label) => ({ state: 'info' as const, label })),
  ];
}

const attachmentError = ref('');
const uploadTick = ref(0);
const attachmentNameMap = ref<Record<number, string>>({});
const attachmentNameLoading = ref<Set<number>>(new Set());

function attachmentDisplayName(option: { id: number; label: string }) {
  const cached = attachmentNameMap.value[option.id];
  if (cached) return cached;
  const label = String(option.label || '');
  // label 不是 "#id" 形式（附件名已由选项携带）时直接使用
  if (!/^#\d+$/.test(label)) return label;
  void lazyLoadAttachmentName(option.id);
  return label;
}

async function lazyLoadAttachmentName(id: number) {
  if (attachmentNameLoading.value.has(id)) return;
  attachmentNameLoading.value.add(id);
  try {
    const res = await downloadFile({ id });
    if (res?.name) {
      attachmentNameMap.value = { ...attachmentNameMap.value, [id]: res.name };
    }
  } catch {
    // 下载失败时保留原 label（#id），不阻塞展示
  } finally {
    attachmentNameLoading.value.delete(id);
  }
}

function isAttachmentField(field: FormSectionFieldSchema) {
  const relation = (field as { descriptor?: { relation?: string } }).descriptor?.relation;
  return String(relation || '').trim().toLowerCase() === 'ir.attachment';
}

async function handleAttachmentUpload(field: FormSectionFieldSchema, files: File[]) {
  attachmentError.value = '';
  if (field.readonly) return;
  if (!files || files.length === 0) return;
  const model = props.adapter.currentModel;
  const resId = props.adapter.currentRecordId;
  if (!model || !resId) {
    attachmentError.value = '请先保存单据后再上传附件';
    return;
  }
  try {
    const current = props.adapter.relationIds(field.name);
    const newIds: number[] = [];
    const newNames: Record<number, string> = {};
    for (const file of files) {
      const { data, mimetype } = await fileToBase64(file);
      const created = await uploadFile({ model, res_id: resId, name: file.name, mimetype, data });
      newIds.push(created.id);
      newNames[created.id] = created.name || file.name;
    }
    props.adapter.setRelationIds(field.name, Array.from(new Set([...current, ...newIds])));
    attachmentNameMap.value = { ...attachmentNameMap.value, ...newNames };
    uploadTick.value += 1;
  } catch (err) {
    attachmentError.value = err instanceof Error ? err.message : '附件上传失败';
  }
}

async function downloadAttachment(att: { id?: number; name?: string }) {
  if (!att?.id) return;
  attachmentError.value = '';
  try {
    const res = await downloadFile({ id: att.id });
    if (res?.url && !String(res.url).startsWith('legacy-file')) {
      window.open(res.url, '_blank', 'noopener');
      return;
    }
    if (res?.datas) {
      const binary = atob(res.datas);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: res.mimetype || 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = res.name || att.name || 'attachment';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  } catch (err) {
    attachmentError.value = err instanceof Error ? err.message : '附件下载失败';
  }
}

function relationIdSet(name: string) {
  return new Set(props.adapter.relationIds(name));
}

function toggleRelationId(name: string, id: number, checked: boolean) {
  const current = relationIdSet(name);
  if (checked) {
    current.add(id);
  } else {
    current.delete(id);
  }
  props.adapter.setRelationIds(name, Array.from(current));
  props.adapter.setRelationKeyword(name, '');
}

</script>

<style scoped>
.relation-editor {
  display: grid;
  gap: 6px;
}

.relation-readonly {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 24px;
  align-items: center;
  color: var(--sc-app-text-primary);
}

.relation-readonly-item {
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--sc-app-muted-bg);
}

.relation-readonly-summary,
.relation-readonly-empty {
  color: var(--sc-app-text-secondary);
}

.relation-readonly-empty {
  margin: 0;
  padding: 10px 12px;
  border: 1px dashed var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-muted-bg);
  font-size: 13px;
}

.o2m-readonly-list {
  display: grid;
  gap: 0;
  border: 1px solid var(--sc-app-border);
  border-radius: 6px;
  overflow: hidden;
}

.o2m-readonly-row {
  display: grid;
  grid-template-columns: minmax(72px, max-content) minmax(0, 1fr);
  gap: 12px;
  padding: 8px 12px;
  border: 0;
  border-bottom: 1px solid var(--sc-app-border);
  border-radius: 0;
  background: var(--sc-app-panel);
}

.o2m-readonly-row:last-child { border-bottom: 0; }

.o2m-readonly-state {
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.o2m-readonly-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 6px 18px;
  margin: 0;
}

.o2m-readonly-fact {
  min-width: 0;
}

.o2m-readonly-fact dt,
.o2m-readonly-fact dd {
  margin: 0;
}

.o2m-readonly-fact dt {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.o2m-readonly-fact dd {
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--sc-app-text-primary);
  font-size: 14px;
}

@media (max-width: 760px) {
  .o2m-readonly-row { grid-template-columns: 1fr; gap: 6px; }
  .o2m-readonly-facts { grid-template-columns: 1fr; }
  .o2m-readonly-fact dd { white-space: normal; overflow-wrap: anywhere; }
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.relation-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.relation-tag-picker,
.relation-select-editor,
.relation-attachment-editor {
  display: grid;
  gap: 8px;
}

.attachment-list {
  display: grid;
  gap: 6px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--sc-app-border-default);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-input-bg);
}

.attachment-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--sc-app-text-primary);
  font-size: 14px;
}

.attachment-upload {
  width: 100%;
}

.attachment-error {
  margin-top: 4px;
}

.relation-multi-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--sc-space-xs);
  max-height: 240px;
  overflow: auto;
  padding: var(--sc-space-sm);
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-input-bg);
}

.relation-select-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  padding: 6px 8px;
  border: 1px dashed var(--sc-app-border-strong);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-subtle-bg, var(--sc-app-panel));
}

.relation-select-hint {
  flex: 1 1 160px;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.relation-tags-control {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 5px 8px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-input-bg);
}

.relation-tags-input {
  flex: 1 1 140px;
  min-width: 120px;
  line-height: 1.4;
}

.relation-tag-dropdown {
  position: absolute;
  z-index: var(--sc-component-relation-dropdown-z-index);
  top: calc(100% + 2px);
  left: 0;
  right: 0;
  display: none;
  max-height: var(--sc-component-relation-dropdown-max-height);
  overflow: auto;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-panel);
  box-shadow: var(--sc-component-relation-dropdown-shadow);
}

.relation-tags-control:focus-within .relation-tag-dropdown {
  display: grid;
}

.relation-tag-hint {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  border: 0;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  padding: 6px 10px;
  color: var(--sc-app-text-primary);
  text-align: left;
  cursor: pointer;
  font-size: 12px;
  line-height: 1.25;
}

.relation-tag-actions {
  display: grid;
  border-top: 1px solid var(--sc-app-border);
}

.relation-tag-action {
  width: 100%;
  justify-content: flex-start;
}

.relation-tag-hint {
  color: var(--sc-app-text-secondary);
  cursor: default;
}

.relation-tag-swatch {
  flex: 0 0 auto;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--tag-bg, var(--sc-app-muted-bg));
  border: 1px solid var(--sc-app-border);
}

.relation-choice-panel {
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-panel);
}

.relation-choice-panel > summary {
  min-height: 32px;
  padding: 7px 10px;
  color: var(--sc-app-text-primary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.relation-choice-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 10px;
  max-height: 220px;
  overflow: auto;
  padding: 0 8px 8px;
}

.relation-choice {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-height: 28px;
  padding: 5px 8px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: 6px;
  background: var(--sc-app-input-bg);
  color: var(--sc-app-text-primary);
  font-size: 12px;
  line-height: 1.35;
}

.relation-choice-check {
  margin-top: 1px;
  flex: 0 0 auto;
}

.relation-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  line-height: 1.35;
}

.meta {
  margin: 1px 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}

.required {
  color: var(--sc-app-danger-text);
  margin-left: 2px;
}

.o2m-card {
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--sc-app-panel);
}

.o2m-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.o2m-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--sc-app-text-primary);
}

.o2m-spacer {
  flex: 1;
}

.o2m-count {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}

.o2m-summary {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}

/* o2m-table renders as a semantic grid: the wrapper uses role="table" and the
 * native thead/tbody/tr/th/td children keep table display via explicit CSS so
 * the markup stays free of a raw native table element. */
.o2m-table thead { display: table-header-group; }
.o2m-table tbody { display: table-row-group; }
.o2m-table tr { display: table-row; }
.o2m-table th,
.o2m-table td { display: table-cell; }
.o2m-table-scroll {
  overflow-x: auto;
  border-top: 1px solid var(--sc-app-border);
}

.o2m-table {
  display: table;
  width: 100%;
  border-collapse: collapse;
  width: 100%;
  min-width: 1120px;
  border-collapse: collapse;
  font-size: 13px;
}

.o2m-table thead th {
  padding: 8px 10px;
  background: var(--sc-app-muted-bg);
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  font-weight: 600;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--sc-app-border);
}

.o2m-table tbody td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--sc-app-border);
  vertical-align: middle;
}

.o2m-table tbody tr:hover td {
  background: var(--sc-app-hover-bg);
}

.o2m-table tbody tr:last-child td {
  border-bottom: 0;
}

.o2m-th-state {
  width: 84px;
}

.o2m-th-action {
  width: 72px;
  text-align: center;
}

.o2m-td-action {
  text-align: center;
}

.o2m-th-amount,
.o2m-td-amount {
  text-align: right;
}

.o2m-state-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
  font-size: 12px;
  white-space: nowrap;
}

.o2m-state-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.o2m-tr-msgs td {
  background: var(--sc-app-panel);
}

.o2m-row-message {
  margin: 2px 0;
}

.o2m-empty {
  padding: 24px 12px;
  text-align: center;
  color: var(--sc-app-text-secondary);
  border-top: 1px solid var(--sc-app-border);
}

.o2m-empty-title {
  margin: 8px 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: var(--sc-app-text-primary);
}

.o2m-empty-hint {
  margin: 0;
  font-size: 12px;
}

.o2m-total {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid var(--sc-app-border);
  background: var(--sc-app-muted-bg);
  font-size: 13px;
}

.o2m-total-label {
  color: var(--sc-app-text-secondary);
}

.o2m-total-value {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.o2m-removed {
  display: grid;
  gap: 4px;
  padding: 8px 12px;
  border-top: 1px solid var(--sc-app-border);
}


.relation-search {
  font-size: 14px;
}

@media (max-width: 760px) {
  .o2m-header {
    display: none;
  }

  .o2m-row {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--sc-app-border);
    border-radius: 8px;
    background: var(--sc-app-panel);
  }

  .o2m-row-state {
    grid-column: 1 / -1;
    padding-bottom: 7px;
    border-bottom: 1px solid var(--sc-app-border);
    font-weight: 600;
  }

  .o2m-row-remove {
    align-self: start;
    min-height: 44px;
    white-space: nowrap;
  }

  .o2m-create,
  .o2m-row-restore,
  .o2m-page-action {
    min-height: 44px;
  }

  .o2m-fields {
    grid-template-columns: 1fr;
  }

  .o2m-field {
    gap: 4px;
  }

  .o2m-field .meta {
    display: block;
  }
}

</style>
