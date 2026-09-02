<template>
  <ScDialog
    data-semantic-component="PaymentSettlementIntroduceDialog"
    :open="open"
    title="从结算单引入明细"
    description="选择结算单，勾选结算行并设置申请金额，确认后引入为付款申请明细"
    size="wide"
    dismissible
    :busy="introduceBusy || previewLoading"
    @close="$emit('close')"
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
      <ScInlineState v-if="introduceError" class="settle-error" state="error" :label="introduceError" />

      <div v-if="!previewData" class="settle-results" data-settle-results>
        <ScInlineState v-if="settleSearching" class="settle-hint" state="loading" label="正在搜索结算单" />
        <ScInlineState v-else-if="!settleResults.length" class="settle-hint" state="empty" label="未找到结算单，请输入关键词搜索" />
        <div
          v-for="s in settleResults"
          :key="s.id"
          role="button"
          tabindex="0"
          class="settle-option"
          :class="{ 'sc-settle-option-active': selectedSettlementId === s.id }"
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
          <ScInlineState
            v-if="!previewLoading && !selectableLines.length"
            class="settle-hint"
            state="info"
            label="该结算单所有明细均已申请完毕"
          />
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
              :class="{ 'sc-apply-mode-active': applyMode === 'ratio' }"
              @click="applyMode = 'ratio'"
            >按比例</ScButton>
            <ScButton
              type="button"
              variant="ghost"
              size="small"
              :class="{ 'sc-apply-mode-active': applyMode === 'amount' }"
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
      <ScButton type="button" variant="ghost" :disabled="introduceBusy" @click="$emit('close')">取消</ScButton>
      <ScButton
        type="button"
        variant="primary"
        :disabled="!canConfirmIntroduce || introduceBusy"
        @click="confirmIntroduce"
      >确认引入</ScButton>
    </template>
  </ScDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScInput from '../design-system/ScInput.vue';
import ScDialog from '../design-system/ScDialog.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import { intentRequest } from '../../api/intents';

const props = defineProps<{ field: FormSectionFieldSchema; adapter: RelationFieldAdapter; open: boolean }>();
const emit = defineEmits<{ close: []; introduced: []; 'busy-change': [busy: boolean] }>();

const actionRefs = computed(() => {
  const raw = props.field.componentConfig?.actionRefs;
  const refs = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw as Record<string, unknown> : {};
  return {
    search: String(refs.search || '').trim(),
    preview: String(refs.preview || '').trim(),
    introduce: String(refs.introduce || '').trim(),
  };
});

function requiredActionRef(key: 'search' | 'preview' | 'introduce') {
  const value = actionRefs.value[key];
  if (!value) throw new Error(`PAYMENT_SETTLEMENT_ACTION_REF_MISSING:${key}`);
  return value;
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

function fmtMoney(value: number | string | undefined | null) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '¥ 0.00';
  return `¥ ${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

watch(() => props.open, (opened) => {
  if (!opened) return;
  introduceError.value = '';
  settleKeyword.value = '';
  settleResults.value = [];
  selectedSettlementId.value = null;
  previewData.value = null;
  selectedLineIds.value = new Set();
  applyMode.value = 'ratio';
  applyRatio.value = 100;
  applyTotal.value = 0;
  void searchSettlements();
});

async function searchSettlements() {
  introduceError.value = '';
  settleSearching.value = true;
  try {
    const res = await intentRequest<{ settlements: Array<{ id: number; name: string; display_name: string; amount_total: number; contract_name: string; partner_name: string; line_count: number }> }>({
      intent: requiredActionRef('search'),
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
      intent: requiredActionRef('preview'),
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
  emit('busy-change', true);
  introduceError.value = '';
  try {
    await intentRequest({
      intent: requiredActionRef('introduce'),
      params: {
        payment_request_id: recordId,
        settlement_id: selectedSettlementId.value,
        settlement_line_ids: Array.from(selectedLineIds.value),
        apply_mode: applyMode.value,
        ratio: applyRatio.value,
        total_amount: applyTotal.value,
      },
    });
    emit('introduced');
    emit('close');
  } catch (error) {
    introduceError.value = String(error instanceof Error ? error.message : error);
  } finally {
    introduceBusy.value = false;
    emit('busy-change', false);
  }
}
</script>

<style scoped>
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
.settle-option.sc-settle-option-active {
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

.settle-apply-mode .sc-apply-mode-active {
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
