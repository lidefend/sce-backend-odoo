<template>
  <div v-if="field.type === 'many2many'" class="relation-editor">
    <div v-if="field.readonly" class="relation-readonly" data-readonly-relation>
      <span
        v-for="option in adapter.selectedRelationOptions(field.name)"
        :key="`${field.name}-readonly-${option.id}`"
        class="relation-readonly-item"
      >{{ option.label }}</span>
      <span
        v-if="!adapter.selectedRelationOptions(field.name).length && adapter.relationIds(field.name).length"
        class="relation-readonly-summary"
      >已关联 {{ adapter.relationIds(field.name).length }} 条</span>
      <ScInlineState
        v-else-if="!adapter.selectedRelationOptions(field.name).length"
        class="relation-readonly-empty"
        state="empty"
        label="暂无记录"
      />
    </div>
    <div v-else-if="isMany2manyTags(field)" class="relation-tag-picker">
      <div class="relation-tags-control">
        <div v-if="adapter.selectedRelationOptions(field.name).length" class="relation-tag-list">
          <ScButton
            v-for="option in adapter.selectedRelationOptions(field.name)"
            :key="`${field.name}-tag-${option.id}`"
            type="button"
            class="relation-tag"
            appearance="relation-tag"
            variant="ghost"
            size="small"
            :style="tagColorStyle(option.color)"
            :disabled="adapter.busy"
            :title="`移除${option.label}`"
            @click="toggleRelationId(field.name, option.id, false)"
          >
            {{ option.label }}
            <ScIcon name="close" :size="14" />
          </ScButton>
        </div>
        <ScInput
          class="relation-tags-input"
          appearance="relation-tag-entry"
          type="text"
          :model-value="adapter.relationKeyword(field.name)"
          :placeholder="field.inputPlaceholder || adapter.inputPlaceholder(field.label)"
          @update:model-value="adapter.setRelationKeyword(field.name, $event)"
          @keydown.enter.prevent="commitTagKeyword(field.name)"
        />
        <div v-if="hasTagDropdown(field.name)" class="relation-tag-dropdown">
          <ScButton
            v-for="option in adapter.filteredRelationOptions(field.name).slice(0, 8)"
            :key="`${field.name}-tag-option-${option.id}`"
            type="button"
            class="relation-tag-option"
            appearance="menu-item"
            variant="ghost"
            size="small"
            @mousedown.prevent
            @click="toggleRelationId(field.name, option.id, true)"
          >
            <span class="relation-tag-swatch" :style="tagColorStyle(option.color)" aria-hidden="true"></span>
            <span>{{ option.label }}</span>
          </ScButton>
          <div v-if="hasTagCreateActions(field.name)" class="relation-tag-actions">
            <div
              v-if="adapter.canInlineCreateRelation(field.name)"
              class="relation-tag-hint"
              role="note"
            >
              {{ adapter.relationInlineCreateLabel(field.name) }}
            </div>
            <ScButton
              v-if="adapter.relationCreateMode(field.name) === 'page'"
              type="button"
              class="relation-tag-action"
              variant="secondary"
              size="small"
              @mousedown.prevent
              @click="adapter.openRelationCreate(field.name)"
            >
              {{ adapter.relationCreateLabel(field.name) }}
            </ScButton>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="isAttachmentField(field)" class="relation-attachment-editor" data-semantic-component="RelationAttachmentEditor">
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
            variant="ghost"
            size="small"
            :disabled="adapter.busy"
            :aria-label="`移除${att.label}`"
            @click="toggleRelationId(field.name, att.id, false)"
          >移除</ScButton>
        </div>
      </div>
      <ScFileField
        :key="uploadTick"
        class="attachment-upload"
        :disabled="adapter.busy"
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
    <div v-else class="relation-select-editor">
      <ScInput
        class="relation-search"
        type="text"
        :model-value="adapter.relationKeyword(field.name)"
        :placeholder="field.inputPlaceholder || adapter.inputPlaceholder(field.label)"
        @update:model-value="adapter.setRelationKeyword(field.name, $event)"
      />
      <div
        v-if="adapter.filteredRelationOptions(field.name).length"
        class="relation-multi-options"
        role="listbox"
        aria-multiselectable="true"
        :aria-label="field.label || `${field.name} 选项列表`"
      >
        <ScCheckbox
          v-for="option in adapter.filteredRelationOptions(field.name)"
          :key="`${field.name}-${option.id}`"
          :checked="relationIdSet(field.name).has(option.id)"
          :disabled="adapter.busy"
          :label="option.label"
          @change="toggleRelationId(field.name, option.id, $event)"
        />
      </div>
    </div>
  </div>
  <div v-else-if="field.type === 'one2many'" class="relation-editor">
    <div v-if="field.readonly" class="o2m-readonly" data-readonly-relation>
      <div v-if="adapter.visibleOne2manyRows(field.name).length" class="o2m-readonly-list">
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
      <ScInlineState v-else class="relation-readonly-empty" state="empty" label="暂无记录" data-readonly-relation-empty />
    </div>
        <template v-else>
    <div class="o2m-card">
      <div class="o2m-toolbar">
        <span class="o2m-title">{{ field.label }}</span>
        <span v-if="adapter.visibleOne2manyRows(field.name).length" class="o2m-count">共 {{ adapter.visibleOne2manyRows(field.name).length }} 条</span>
        <span v-if="adapter.one2manySummary(field.name)" class="o2m-summary">{{ adapter.one2manySummary(field.name) }}</span>
        <span class="o2m-spacer" />
        <ScButton
          v-if="isSettlementIntroduceField(field)"
          class="o2m-introduce"
          type="button"
          variant="secondary"
          size="small"
          :disabled="adapter.busy || introduceBusy"
          @click="openSettlementIntroduce"
        >
          <ScIcon name="clipboard" :size="14" />
          从结算单引入
        </ScButton>
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
        <div role="table" class="o2m-table">
          <thead>
            <tr>
              <th class="o2m-th-state">状态</th>
              <th
                v-for="column in adapter.one2manyColumns(field.name)"
                :key="`${field.name}-th-${column.name}`"
                :class="o2mThClass(column)"
              >{{ column.label }}</th>
              <th class="o2m-th-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in paginatedOne2manyRows" :key="row.key">
              <tr class="o2m-tr">
                <td class="o2m-td-state">
                  <span class="o2m-state-badge">{{ adapter.one2manyRowStateLabel(row) }}</span>
                </td>
                <td
                  v-for="column in adapter.one2manyColumns(field.name)"
                  :key="`${row.key}-td-${column.name}`"
                  :class="o2mTdClass(column)"
                >
                  <ScCheckbox
                    v-if="column.ttype === 'boolean'"
                    class="input-checkbox"
                    :disabled="column.readonly || adapter.busy"
                    :checked="Boolean(row.values[column.name])"
                    :label="column.label"
                    @change="adapter.setOne2manyRowField(field.name, row.key, column, $event)"
                  />
                  <ScSelect
                    v-else-if="column.ttype === 'selection'"
                    :disabled="column.readonly || adapter.busy"
                    :model-value="String(row.values[column.name] ?? '')"
                    :placeholder="adapter.selectPlaceholder(column.label)"
                    :options="(column.selection || []).map((option) => ({ value: String(option[0]), label: String(option[1]) }))"
                    @update:model-value="adapter.setOne2manyRowField(field.name, row.key, column, $event)"
                  />
                  <ScInput
                    v-else
                    :class="o2mInputClass(column)"
                    :type="adapter.one2manyColumnInputType(column)"
                    :disabled="column.readonly || adapter.busy"
                    :model-value="adapter.one2manyColumnDisplayValue(column, row.values[column.name])"
                    :placeholder="column.label"
                    @update:model-value="adapter.setOne2manyRowField(field.name, row.key, column, $event)"
                  />
                </td>
                <td class="o2m-td-action">
                  <ScButton
                    class="o2m-row-remove"
                    type="button"
                    variant="danger"
                    size="small"
                    :aria-label="`移除${adapter.one2manyRowLabel(field.name, row)}`"
                    :disabled="adapter.busy"
                    @click="adapter.removeOne2manyRow(field.name, row.key)"
                  >移除</ScButton>
                </td>
              </tr>
              <tr v-if="o2mRowHasMessages(row)" class="o2m-tr-msgs">
                <td :colspan="o2mColSpan">
                  <ScInlineState
                    v-for="message in o2mRowMessages(row)"
                    :key="`${row.key}-${message.state}-${message.label}`"
                    class="o2m-row-message"
                    :state="message.state"
                    :label="message.label"
                  />
                </td>
              </tr>
            </template>
          </tbody>
        </div>
      </div>

      <div v-else-if="adapter.one2manyColumns(field.name).length" class="o2m-empty" data-o2m-empty>
        <ScIcon name="file-text" :size="24" />
        <p class="o2m-empty-title">暂无明细</p>
        <p class="o2m-empty-hint">点击「{{ adapter.one2manyCreateLabel(field.name, field.label) }}」新增明细</p>
      </div>

      <div v-if="adapter.visibleOne2manyRows(field.name).length" class="o2m-total">
        <span class="o2m-total-label">明细金额合计</span>
        <span class="o2m-total-value">{{ o2mAmountTotalText }}</span>
      </div>

      <div v-if="adapter.removedOne2manyRows(field.name).length" class="o2m-removed">
        <p class="meta">已移除 {{ adapter.removedOne2manyRows(field.name).length }} 行</p>
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
  <ScDialog
    v-if="isSettlementIntroduceField(field)"
    :open="settleDialogOpen"
    title="从结算单引入明细"
    description="选择结算单，勾选结算行并设置申请金额，确认后引入为付款申请明细"
    size="wide"
    dismissible
    :busy="introduceBusy || previewLoading"
    @close="settleDialogOpen = false"
  >
    <div class="settle-introduce" data-settle-introduce>
      <div class="settle-search">
        <ScInput
          class="settle-search-input"
          :model-value="settleKeyword"
          placeholder="搜索结算单号 / 名称"
          @update:model-value="settleKeyword = $event"
          @keydown.enter.prevent="searchSettlements"
        />
        <ScButton
          type="button"
          variant="secondary"
          size="small"
          :disabled="settleSearching"
          @click="searchSettlements"
        >搜索</ScButton>
      </div>
      <div v-if="introduceError" class="settle-error" role="alert">{{ introduceError }}</div>

      <div v-if="!previewData" class="settle-results" data-settle-results>
        <div v-if="settleSearching" class="settle-hint">搜索中…</div>
        <div v-else-if="!settleResults.length" class="settle-hint">未找到结算单，请输入关键词搜索</div>
        <div
          v-for="s in settleResults"
          :key="s.id"
          role="button"
          tabindex="0"
          class="settle-option"
          :class="{ 'is-active': selectedSettlementId === s.id }"
          @click="loadSettlementPreview(s.id)"
          @keydown.enter.prevent="loadSettlementPreview(s.id)"
        >
          <span class="settle-option-name">{{ s.display_name || s.name }}</span>
          <span class="settle-option-meta">
            <span v-if="s.contract_name">合同：{{ s.contract_name }}</span>
            <span v-if="s.amount_total">金额：{{ fmtMoney(s.amount_total) }}</span>
            <span>明细 {{ s.line_count }} 行</span>
          </span>
        </div>
      </div>

      <div v-else class="settle-preview" data-settle-preview>
        <div class="settle-preview-head">
          <div class="settle-preview-title">
            <strong>{{ previewData.settlement.display_name }}</strong>
            <span class="settle-preview-sub" v-if="previewData.settlement.contract_name">合同：{{ previewData.settlement.contract_name }}</span>
          </div>
          <ScButton type="button" variant="ghost" size="small" @click="backToSettlementSearch">换一个结算单</ScButton>
        </div>
        <div class="settle-preview-toolbar">
          <ScCheckbox
            :model-value="allLinesSelected"
            :disabled="!selectableLines.length"
            @update:model-value="toggleAllLines"
          />
          <span class="settle-select-hint">全选未完全申请的行</span>
          <span class="settle-spacer" />
          <span class="settle-total-hint">选中 {{ selectedLines.length }} 行 · 结算金额 {{ fmtMoney(selectedLinesAmount) }} · 可申请 {{ fmtMoney(selectedLinesRemaining) }}</span>
        </div>
        <div class="settle-lines" data-settle-lines>
          <div v-if="!previewLoading" class="settle-lines-head">
            <span class="settle-col-check"></span>
            <span class="settle-col-name">名称</span>
            <span class="settle-col-contract">合同</span>
            <span class="settle-col-amount">结算金额</span>
            <span class="settle-col-applied">已申请</span>
            <span class="settle-col-remaining">可申请</span>
            <span class="settle-col-state">状态</span>
          </div>
          <div
            v-for="line in previewData.lines"
            :key="line.id"
            class="settle-line"
            :class="{ 'is-disabled': line.is_fully_applied }"
          >
            <span class="settle-col-check">
              <ScCheckbox
                :model-value="selectedLineIds.has(line.id)"
                :disabled="line.is_fully_applied"
                @update:model-value="toggleLine(line.id)"
              />
            </span>
            <span class="settle-col-name" :title="line.name">{{ line.name }}</span>
            <span class="settle-col-contract" :title="line.contract_name">{{ line.contract_name || '—' }}</span>
            <span class="settle-col-amount">{{ fmtMoney(line.amount) }}</span>
            <span class="settle-col-applied">{{ fmtMoney(line.applied) }}</span>
            <span class="settle-col-remaining">{{ fmtMoney(line.remaining) }}</span>
            <span class="settle-col-state">
              <span v-if="line.is_fully_applied" class="settle-state-done">已申请完</span>
              <span v-else class="settle-state-open">可申请</span>
            </span>
          </div>
          <div v-if="!previewLoading && !selectableLines.length" class="settle-hint">该结算单所有明细均已申请完毕</div>
        </div>

        <div v-if="relatedPaymentRequests.length" class="settle-history" data-settle-history>
          <div class="settle-history-head" @click="historyExpanded = !historyExpanded">
            <span class="settle-history-title">历史申请记录</span>
            <span class="settle-history-count">{{ relatedPaymentRequests.length }} 笔</span>
            <span class="settle-history-toggle">{{ historyExpanded ? '收起' : '展开' }}</span>
          </div>
          <div v-if="historyExpanded" class="settle-history-body">
            <div v-for="req in relatedPaymentRequests" :key="req.id" class="settle-history-row">
              <span class="settle-history-name" :title="req.name">{{ req.name }}</span>
              <span class="settle-history-state" :class="'is-' + req.state">{{ req.state_label }}</span>
              <span class="settle-history-amount">{{ fmtMoney(req.applied_to_settlement || req.amount) }}</span>
              <span class="settle-history-date">{{ req.date_request || '—' }}</span>
            </div>
          </div>
        </div>

        <div class="settle-apply" data-settle-apply>
          <div class="settle-apply-mode">
            <ScButton
              type="button"
              variant="ghost"
              size="small"
              :class="{ 'is-active': applyMode === 'ratio' }"
              @click="applyMode = 'ratio'"
            >按比例</ScButton>
            <ScButton
              type="button"
              variant="ghost"
              size="small"
              :class="{ 'is-active': applyMode === 'amount' }"
              @click="applyMode = 'amount'"
            >按总金额</ScButton>
          </div>
          <div class="settle-apply-fields">
            <template v-if="applyMode === 'ratio'">
              <ScInput
                class="settle-apply-input"
                :model-value="String(applyRatio)"
                type="number"
                min="0"
                max="100"
                placeholder="申请比例 %"
                @update:model-value="applyRatio = Number($event)"
              />
              <span class="settle-apply-suffix">%</span>
              <span class="settle-apply-hint">每行申请 = 可申请 * 比例</span>
            </template>
            <template v-else>
              <ScInput
                class="settle-apply-input"
                :model-value="String(applyTotal)"
                type="number"
                min="0"
                placeholder="总申请金额"
                @update:model-value="applyTotal = Number($event)"
              />
              <span class="settle-apply-suffix">元</span>
              <span class="settle-apply-hint">按各结算行可申请占比分配</span>
            </template>
            <span class="settle-apply-total">本次申请合计：<strong>{{ fmtMoney(selectedLinesApply) }}</strong></span>
          </div>
        </div>
      </div>
    </div>
    <template #actions>
      <ScButton type="button" variant="ghost" :disabled="introduceBusy" @click="settleDialogOpen = false">取消</ScButton>
      <ScButton
        type="button"
        variant="primary"
        :disabled="!canConfirmIntroduce || introduceBusy"
        @click="confirmIntroduce"
      >确认引入</ScButton>
    </template>
  </ScDialog>
  <ScInput
  v-else
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
import ScDialog from '../design-system/ScDialog.vue';
import { downloadFile, fileToBase64, uploadFile } from '../../api/files';
import { intentRequest } from '../../api/intents';
import type { RelationFieldColumn, RelationFieldRow, X2ManyRelationRendererProps } from './relationField.types';

const props = defineProps<X2ManyRelationRendererProps>();
const emit = defineEmits<{ (e: 'reload-requested'): void }>();
const one2manyPage = ref(1);
const one2manyPageSize = 20;
const one2manyRows = computed(() => props.field.type === 'one2many' ? props.adapter.visibleOne2manyRows(props.field.name) : []);
const one2manyPageCount = computed(() => Math.max(1, Math.ceil(one2manyRows.value.length / one2manyPageSize)));
const paginatedOne2manyRows = computed(() => {
  const start = (one2manyPage.value - 1) * one2manyPageSize;
  return one2manyRows.value.slice(start, start + one2manyPageSize);
});
watch(one2manyPageCount, (count) => {
  if (one2manyPage.value > count) one2manyPage.value = count;
});

function isMany2manyTags(field: FormSectionFieldSchema) {
  return String(field.widget || '').trim().toLowerCase() === 'many2many_tags';
}

const O2M_AMOUNT_FIELDS = new Set(['amount', 'paid_before_amount', 'remaining_amount', 'current_pay_amount']);

function isO2mAmountColumn(column: RelationFieldColumn) {
  return O2M_AMOUNT_FIELDS.has(column.name) || String(column.ttype).toLowerCase().includes('monet');
}

function o2mThClass(column: RelationFieldColumn) {
  return { 'o2m-th-amount': isO2mAmountColumn(column) };
}

function o2mTdClass(column: RelationFieldColumn) {
  return { 'o2m-td-amount': isO2mAmountColumn(column) };
}

function o2mInputClass(column: RelationFieldColumn) {
  return { 'o2m-input-amount': isO2mAmountColumn(column) };
}

const o2mColSpan = computed(() => props.adapter.one2manyColumns(props.field.name).length + 2);

const o2mAmountTotal = computed(() => {
  const columns = props.adapter.one2manyColumns(props.field.name);
  if (!columns.some((column) => column.name === 'amount')) return 0;
  return paginatedOne2manyRows.value.reduce((sum, row) => {
    const value = Number(row.values.amount);
    return sum + (Number.isFinite(value) ? value : 0);
  }, 0);
});

const o2mAmountTotalText = computed(() => {
  const total = o2mAmountTotal.value;
  const text = total.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `¥ ${text}`;
});

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

// ===== 从结算单引入明细 =====
type SettleLineItem = {
  id: number;
  name: string;
  contract_id?: number;
  contract_name?: string;
  qty?: number;
  price_unit?: number;
  amount: number;
  applied: number;
  remaining: number;
  is_fully_applied: boolean;
};

type SettleRelatedPaymentRequest = {
  id: number;
  name: string;
  state: string;
  state_label: string;
  amount: number;
  applied_to_settlement: number;
  date_request?: string | null;
};

type SettlePreviewData = {
  settlement: {
    id: number;
    name: string;
    display_name: string;
    contract_id?: number;
    contract_name?: string;
    partner_id?: number;
    partner_name?: string;
    amount_total: number;
  };
  lines: SettleLineItem[];
  related_payment_requests?: SettleRelatedPaymentRequest[];
  totals: { settlement_amount: number; line_amount_total: number; applied_total: number; remaining_total: number };
};

const settleDialogOpen = ref(false);
const settleKeyword = ref('');
const settleSearching = ref(false);
const settleResults = ref<Array<{ id: number; name: string; display_name: string; amount_total: number; contract_name: string; partner_name: string; line_count: number }>>([]);
const selectedSettlementId = ref<number | null>(null);
const previewData = ref<SettlePreviewData | null>(null);
const historyExpanded = ref(false);
const previewLoading = ref(false);
const selectedLineIds = ref<Set<number>>(new Set());
const applyMode = ref<'ratio' | 'amount'>('ratio');
const applyRatio = ref(100);
const applyTotal = ref(0);
const introduceBusy = ref(false);
const introduceError = ref('');

function isSettlementIntroduceField(field: FormSectionFieldSchema) {
  if (field.type !== 'one2many') return false;
  const relation = (field as { descriptor?: { relation?: string } }).descriptor?.relation;
  return String(relation || '').trim().toLowerCase() === 'payment.request.line';
}

function fmtMoney(value: number | string | undefined | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '¥ 0.00';
  return `¥ ${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

async function openSettlementIntroduce() {
  introduceError.value = '';
  settleDialogOpen.value = true;
  settleKeyword.value = '';
  settleResults.value = [];
  selectedSettlementId.value = null;
  previewData.value = null;
  selectedLineIds.value = new Set();
  applyMode.value = 'ratio';
  applyRatio.value = 100;
  applyTotal.value = 0;
  await searchSettlements();
}

async function searchSettlements() {
  introduceError.value = '';
  settleSearching.value = true;
  try {
    const res = await intentRequest<{ settlements: Array<{ id: number; name: string; display_name: string; amount_total: number; contract_name: string; partner_name: string; line_count: number }> }>({
      intent: 'payment.request.settlement.search',
      params: {
        keyword: settleKeyword.value || '',
        payment_request_id: props.adapter.currentRecordId || 0,
      },
    });
    settleResults.value = res?.settlements || [];
  } catch (error) {
    introduceError.value = String(error instanceof Error ? error.message : error);
  } finally {
    settleSearching.value = false;
  }
}

async function loadSettlementPreview(id: number) {
  introduceError.value = '';
  selectedSettlementId.value = id;
  previewData.value = null;
  selectedLineIds.value = new Set();
  previewLoading.value = true;
  try {
    const res = await intentRequest<SettlePreviewData>({
      intent: 'payment.request.settlement.preview',
      params: { settlement_id: id },
    });
    previewData.value = res;
    // 默认全选未完全申请的行
    selectedLineIds.value = new Set(
      (res?.lines || []).filter((line) => !line.is_fully_applied).map((line) => line.id),
    );
  } catch (error) {
    introduceError.value = String(error instanceof Error ? error.message : error);
  } finally {
    previewLoading.value = false;
  }
}

function backToSettlementSearch() {
  previewData.value = null;
  selectedSettlementId.value = null;
  selectedLineIds.value = new Set();
  void searchSettlements();
}

function toggleLine(id: number) {
  const next = new Set(selectedLineIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  selectedLineIds.value = next;
}

const selectableLines = computed(() => (previewData.value?.lines || []).filter((line) => !line.is_fully_applied));
const relatedPaymentRequests = computed(() => previewData.value?.related_payment_requests || []);
const allLinesSelected = computed(() => {
  const selectable = selectableLines.value;
  return selectable.length > 0 && selectable.every((line) => selectedLineIds.value.has(line.id));
});

function toggleAllLines() {
  const selectable = selectableLines.value;
  if (allLinesSelected.value) {
    selectedLineIds.value = new Set();
  } else {
    selectedLineIds.value = new Set(selectable.map((line) => line.id));
  }
}

const selectedLines = computed(() => (previewData.value?.lines || []).filter((line) => selectedLineIds.value.has(line.id)));

const selectedLinesAmount = computed(() => selectedLines.value.reduce((sum, line) => sum + (Number(line.amount) || 0), 0));
const selectedLinesRemaining = computed(() => selectedLines.value.reduce((sum, line) => sum + (Number(line.remaining) || 0), 0));

const selectedLinesApply = computed(() => {
  if (applyMode.value === 'amount') {
    const total = Number(applyTotal.value) || 0;
    return Math.min(total, selectedLinesRemaining.value);
  }
  const ratio = Math.min(Math.max(Number(applyRatio.value) || 0, 0), 100);
  return selectedLinesRemaining.value * ratio / 100;
});

const canConfirmIntroduce = computed(() => {
  if (!selectedSettlementId.value || selectedLineIds.value.size === 0) return false;
  if (applyMode.value === 'amount' && (!(Number(applyTotal.value) > 0))) return false;
  if (applyMode.value === 'ratio' && (!(Number(applyRatio.value) > 0))) return false;
  return selectedLinesApply.value > 0;
});

async function confirmIntroduce() {
  if (!canConfirmIntroduce.value) return;
  const recordId = props.adapter.currentRecordId;
  if (!recordId) {
    introduceError.value = '请先保存付款申请后再引入明细';
    return;
  }
  introduceBusy.value = true;
  introduceError.value = '';
  try {
    await intentRequest({
      intent: 'payment.request.add.settlement.lines',
      params: {
        payment_request_id: recordId,
        settlement_id: selectedSettlementId.value,
        settlement_line_ids: Array.from(selectedLineIds.value),
        apply_mode: applyMode.value,
        ratio: applyRatio.value,
        total_amount: applyTotal.value,
      },
    });
    settleDialogOpen.value = false;
    emit('reload-requested');
  } catch (error) {
    introduceError.value = String(error instanceof Error ? error.message : error);
  } finally {
    introduceBusy.value = false;
  }
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

async function handleAttachmentUpload(field: FormSectionFieldSchema, file: File | null) {
  attachmentError.value = '';
  if (!file) return;
  const model = props.adapter.currentModel;
  const resId = props.adapter.currentRecordId;
  if (!model || !resId) {
    attachmentError.value = '请先保存单据后再上传附件';
    return;
  }
  try {
    const { data, mimetype } = await fileToBase64(file);
    const created = await uploadFile({ model, res_id: resId, name: file.name, mimetype, data });
    const current = props.adapter.relationIds(field.name);
    props.adapter.setRelationIds(field.name, Array.from(new Set([...current, created.id])));
    attachmentNameMap.value = { ...attachmentNameMap.value, [created.id]: created.name || file.name };
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

function hasTagCreateActions(name: string) {
  const keyword = props.adapter.relationKeyword(name).trim();
  return Boolean(keyword) && (
    props.adapter.canInlineCreateRelation(name) || props.adapter.relationCreateMode(name) === 'page'
  );
}

function hasTagDropdown(name: string) {
  return props.adapter.filteredRelationOptions(name).length > 0 || hasTagCreateActions(name);
}

function commitTagKeyword(name: string) {
  const options = props.adapter.filteredRelationOptions(name);
  if (options.length === 1) {
    toggleRelationId(name, options[0].id, true);
  }
}

function tagColorStyle(color: unknown) {
  const idx = Number(color);
  if (!Number.isFinite(idx)) return {};
  const palette = [
    'var(--sc-app-muted-bg)',
    'var(--sc-app-danger-bg)',
    'var(--sc-app-warning-bg)',
    'var(--sc-app-info-bg)',
    'var(--sc-app-success-bg)',
    'var(--sc-app-subtle-bg)',
    'var(--sc-app-hover-bg)',
    'var(--sc-app-info-bg)',
    'var(--sc-app-muted-bg)',
    'var(--sc-app-warning-bg)',
    'var(--sc-app-danger-bg)',
    'var(--sc-app-border)',
  ];
  const bg = palette[Math.abs(Math.trunc(idx)) % palette.length];
  return { '--tag-bg': bg };
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

.o2m-input-amount input {
  text-align: right;
  font-variant-numeric: tabular-nums;
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

/* ===== 从结算单引入明细 ===== */
.o2m-introduce {
  margin-right: 8px;
}

.settle-introduce {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settle-search {
  display: flex;
  gap: 8px;
  align-items: center;
}

.settle-search-input {
  flex: 1;
}

.settle-error {
  color: var(--sc-color-error);
  font-size: 13px;
  background: color-mix(in srgb, var(--sc-color-error) 8%, transparent);
  border-radius: 6px;
  padding: 8px 12px;
}

.settle-hint {
  color: var(--sc-color-text-3);
  font-size: 13px;
  padding: 12px;
  text-align: center;
}

.settle-results {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 360px;
  overflow-y: auto;
}

.settle-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid var(--sc-color-border);
  border-radius: 8px;
  background: var(--sc-color-bg-1);
  cursor: pointer;
  transition: border-color .15s, box-shadow .15s;
}

.settle-option:hover,
.settle-option.is-active {
  border-color: var(--sc-color-primary);
  box-shadow: 0 0 0 1px var(--sc-color-primary);
}

.settle-option-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--sc-color-text-1);
}

.settle-option-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--sc-color-text-3);
}

.settle-preview {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.settle-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.settle-preview-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.settle-preview-title strong {
  font-size: 15px;
  color: var(--sc-color-text-1);
}

.settle-preview-sub {
  font-size: 12px;
  color: var(--sc-color-text-3);
}

.settle-preview-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--sc-color-text-3);
}

.settle-spacer {
  flex: 1;
}

.settle-total-hint {
  font-size: 12px;
  color: var(--sc-color-text-2);
}

.settle-lines {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--sc-color-border);
  border-radius: 8px;
  overflow: hidden;
  max-height: 320px;
  overflow-y: auto;
}

.settle-lines-head,
.settle-line {
  display: grid;
  grid-template-columns: 32px minmax(120px, 2fr) minmax(100px, 1.2fr) 110px 100px 100px 84px;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
}

.settle-lines-head {
  background: var(--sc-color-bg-2);
  color: var(--sc-color-text-3);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: var(--sc-component-sticky-header-z-index);
}

.settle-line {
  border-top: 1px solid var(--sc-color-border);
}

.settle-line:hover {
  background: var(--sc-color-bg-2);
}

.settle-line.is-disabled {
  opacity: .55;
}

.settle-col-check {
  display: flex;
  align-items: center;
}

.settle-col-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--sc-color-text-1);
}

.settle-col-contract {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--sc-color-text-2);
}

.settle-col-amount,
.settle-col-applied,
.settle-col-remaining {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.settle-col-state {
  display: flex;
  justify-content: center;
}

.settle-state-open,
.settle-state-done {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.settle-state-open {
  color: var(--sc-color-success);
  background: color-mix(in srgb, var(--sc-color-success) 12%, transparent);
}

.settle-state-done {
  color: var(--sc-color-text-3);
  background: var(--sc-color-bg-2);
}

.settle-history {
  margin-top: 12px;
  border: 1px solid var(--sc-color-border-2);
  border-radius: 6px;
  overflow: hidden;
}

.settle-history-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  background: var(--sc-color-bg-2);
}

.settle-history-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--sc-color-text-1);
}

.settle-history-count {
  font-size: 12px;
  color: var(--sc-color-text-3);
}

.settle-history-toggle {
  margin-left: auto;
  font-size: 12px;
  color: var(--sc-color-brand);
}

.settle-history-body {
  border-top: 1px solid var(--sc-color-border-2);
}

.settle-history-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  font-size: 12px;
}

.settle-history-row + .settle-history-row {
  border-top: 1px solid var(--sc-color-border-3);
}

.settle-history-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--sc-color-text-1);
}

.settle-history-state {
  min-width: 52px;
  text-align: center;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  background: var(--sc-color-bg-2);
  color: var(--sc-color-text-3);
}

.settle-history-state.is-approved,
.settle-history-state.is-done {
  background: color-mix(in srgb, var(--sc-color-success) 10%, transparent);
  color: var(--sc-color-success);
}

.settle-history-state.is-draft,
.settle-history-state.is-submit {
  background: color-mix(in srgb, var(--sc-color-brand) 10%, transparent);
  color: var(--sc-color-brand);
}

.settle-history-amount {
  min-width: 84px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--sc-color-text-1);
}

.settle-history-date {
  min-width: 92px;
  text-align: right;
  color: var(--sc-color-text-3);
}

.settle-apply {
  display: flex;  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 12px;
  background: var(--sc-color-bg-2);
  border-radius: 8px;
}

.settle-apply-mode {
  display: flex;
  gap: 4px;
}

.settle-apply-mode .is-active {
  background: color-mix(in srgb, var(--sc-color-primary) 12%, transparent);
  color: var(--sc-color-primary);
}

.settle-apply-fields {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  flex-wrap: wrap;
}

.settle-apply-input {
  width: 140px;
}

.settle-apply-suffix {
  font-size: 13px;
  color: var(--sc-color-text-2);
}

.settle-apply-hint {
  font-size: 12px;
  color: var(--sc-color-text-3);
}

.settle-apply-total {
  margin-left: auto;
  font-size: 13px;
  color: var(--sc-color-text-2);
}

.settle-apply-total strong {
  font-size: 15px;
  color: var(--sc-color-primary);
  font-variant-numeric: tabular-nums;
}

</style>
