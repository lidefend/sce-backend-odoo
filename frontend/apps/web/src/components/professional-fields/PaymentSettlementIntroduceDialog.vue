<template>
  <ScDialog
    :data-dialog-purpose="contract.purpose"
    :open="open"
    :title="contract.title"
    :description="contract.description"
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
          :placeholder="contract.searchPlaceholder"
          @update:model-value="settleKeyword = $event"
          @keydown.enter.prevent="searchSettlements"
        />
        <ScButton
          type="button"
          variant="secondary"
          size="small"
          :disabled="settleSearching"
          @click="searchSettlements"
        >{{ contract.searchActionLabel }}</ScButton>
      </div>
      <ScInlineState v-if="introduceError" class="settle-error" state="error" :label="introduceError" />

      <div v-if="!previewData" class="settle-results" data-settle-results>
        <ScInlineState v-if="settleSearching" class="settle-hint" state="loading" :label="contract.searchLoadingLabel" />
        <ScInlineState v-else-if="!settleResults.length" class="settle-hint" state="empty" :label="contract.searchEmptyLabel" />
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
            <span v-if="s.contract_name">{{ contract.resultContractLabel }}：{{ s.contract_name }}</span>
            <span v-if="s.amount_total">{{ contract.resultAmountLabel }}：{{ fmtMoney(s.amount_total, s.currency) }}</span>
            <span>{{ contract.resultLineCountLabel }} {{ s.line_count }} {{ contract.resultLineCountSuffix }}</span>
          </span>
        </div>
      </div>

      <div v-else class="settle-preview" data-settle-preview>
        <div class="settle-preview-head">
          <div class="settle-preview-title">
            <strong>{{ previewData.settlement.display_name }}</strong>
            <span class="settle-preview-sub" v-if="previewData.settlement.contract_name">{{ contract.resultContractLabel }}：{{ previewData.settlement.contract_name }}</span>
          </div>
          <ScButton type="button" variant="ghost" size="small" @click="backToSettlementSearch">{{ contract.switchSourceLabel }}</ScButton>
        </div>
        <div class="settle-preview-toolbar">
          <ScCheckbox
            :model-value="allLinesSelected"
            :disabled="!selectableLines.length"
            @update:model-value="toggleAllLines"
          />
          <span class="settle-select-hint">{{ contract.selectAllLabel }}</span>
          <span class="settle-spacer" />
          <span class="settle-total-hint">{{ contract.summarySelectedPrefix }} {{ selectedLines.length }} {{ contract.summaryLineCountSuffix }} · {{ contract.summarySettlementAmountLabel }} {{ fmtMoney(selectedLinesAmount) }} · {{ contract.summaryApplicableAmountLabel }} {{ fmtMoney(selectedLinesRemaining) }}</span>
        </div>
        <div class="settle-lines" data-settle-lines>
          <div v-if="!previewLoading" class="settle-lines-head">
            <span class="settle-col-check"></span>
            <span class="settle-col-name">{{ contract.columnLabels.name }}</span>
            <span class="settle-col-contract">{{ contract.columnLabels.contract }}</span>
            <span class="settle-col-amount">{{ contract.columnLabels.settlementAmount }}</span>
            <span class="settle-col-applied">{{ contract.columnLabels.applied }}</span>
            <span class="settle-col-remaining">{{ contract.columnLabels.remaining }}</span>
            <span class="settle-col-state">{{ contract.columnLabels.state }}</span>
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
              <span v-if="line.is_fully_applied" class="settle-state-done">{{ contract.stateAppliedLabel }}</span>
              <span v-else class="settle-state-open">{{ contract.stateApplicableLabel }}</span>
            </span>
          </div>
          <ScInlineState
            v-if="!previewLoading && !selectableLines.length"
            class="settle-hint"
            state="info"
            :label="contract.allAppliedLabel"
          />
        </div>

        <div v-if="relatedPaymentRequests.length" class="settle-history" data-settle-history>
          <div class="settle-history-head" @click="historyExpanded = !historyExpanded">
            <span class="settle-history-title">{{ contract.historyTitle }}</span>
            <span class="settle-history-count">{{ relatedPaymentRequests.length }} {{ contract.historyCountSuffix }}</span>
            <span class="settle-history-toggle">{{ historyExpanded ? contract.historyCollapseLabel : contract.historyExpandLabel }}</span>
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
            >{{ contract.ratioModeLabel }}</ScButton>
            <ScButton
              type="button"
              variant="ghost"
              size="small"
              :class="{ 'sc-apply-mode-active': applyMode === 'amount' }"
              @click="applyMode = 'amount'"
            >{{ contract.amountModeLabel }}</ScButton>
          </div>
          <div class="settle-apply-fields">
            <template v-if="applyMode === 'ratio'">
              <ScInput
                class="settle-apply-input"
                :model-value="String(applyRatio)"
                type="number"
                min="0"
                max="100"
                :placeholder="contract.ratioPlaceholder"
                @update:model-value="applyRatio = Number($event)"
              />
              <span class="settle-apply-suffix">%</span>
              <span class="settle-apply-hint">{{ contract.ratioHint }}</span>
            </template>
            <template v-else>
              <ScInput
                class="settle-apply-input"
                :model-value="String(applyTotal)"
                type="number"
                min="0"
                :step="currencyInputStep"
                :placeholder="contract.totalPlaceholder"
                @update:model-value="applyTotal = Number($event)"
              />
              <span class="settle-apply-suffix">{{ currencyUnit }}</span>
              <span class="settle-apply-hint">{{ contract.amountHint }}</span>
            </template>
            <span class="settle-apply-total">{{ contract.applyTotalLabel }}：<strong>{{ fmtMoney(selectedLinesApply) }}</strong></span>
          </div>
        </div>
      </div>
    </div>
    <template #actions>
      <ScButton type="button" variant="ghost" :disabled="introduceBusy" @click="$emit('close')">{{ contract.cancelLabel }}</ScButton>
      <ScButton
        type="button"
        variant="primary"
        :disabled="!canConfirmIntroduce || introduceBusy"
        @click="confirmIntroduce"
      >{{ contract.confirmLabel }}</ScButton>
    </template>
  </ScDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { SettlementIntroduceContract } from './paymentSettlementIntroduceDialogModel';
import type { RelationFieldAdapter } from '../template/relationField.types';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScInput from '../design-system/ScInput.vue';
import ScDialog from '../design-system/ScDialog.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import { intentRequest } from '../../api/intents';
import { formatMonetaryDisplayValue } from '../template/formSection.mapper';
import {
  ratioSettlementApplyAmounts,
  ratioSettlementApplyTotal,
  roundSettlementCurrencyAmount,
} from './paymentSettlementIntroduceModel';

const props = defineProps<{ contract: SettlementIntroduceContract; adapter: RelationFieldAdapter; open: boolean }>();
const emit = defineEmits<{ close: []; introduced: []; 'busy-change': [busy: boolean] }>();

// The dialog renders resolved contract semantics only: every term, action
// identity and payload key was validated before the dialog was mounted.
type SettleLineItem = {
  id: number;
  name: string;
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
  currency: SettleCurrencyIdentity;
  settlement: {
    id: number;
    name: string;
    display_name: string;
    contract_name?: string;
    partner_id?: number;
    partner_name?: string;
    amount_total: number;
  };
  lines: SettleLineItem[];
  related_payment_requests?: SettleRelatedPaymentRequest[];
  totals: { settlement_amount: number; line_amount_total: number; applied_total: number; remaining_total: number };
};

type SettleCurrencyIdentity = {
  id: number;
  name: string;
  symbol: string;
  decimal_places: number;
  rounding: number;
};

const settleKeyword = ref('');
const settleSearching = ref(false);
const settleResults = ref<Array<{ id: number; name: string; display_name: string; amount_total: number; currency: SettleCurrencyIdentity; contract_name: string; partner_name: string; line_count: number }>>([]);
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

function fmtMoney(
  value: number | string | undefined | null,
  currency: SettleCurrencyIdentity | undefined = previewData.value?.currency,
) {
  return formatMonetaryDisplayValue(
    Number(value || 0),
    currency ? [20, currency.decimal_places] as [number, number] : undefined,
    currency?.name || currency?.symbol || '',
  );
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
    const res = await intentRequest<{ settlements: Array<{ id: number; name: string; display_name: string; amount_total: number; currency: SettleCurrencyIdentity; contract_name: string; partner_name: string; line_count: number }> }>({
      intent: props.contract.actions.search,
      params: {
        [props.contract.payloadFields.searchKeyword]: settleKeyword.value || '',
        [props.contract.payloadFields.record]: props.adapter.currentRecordId || 0,
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
      intent: props.contract.actions.preview,
      params: { [props.contract.payloadFields.source]: id },
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
const currencyUnit = computed(() => previewData.value?.currency.symbol || previewData.value?.currency.name || '金额');
const currencyInputStep = computed(() => String(previewData.value?.currency.rounding || 'any'));

function roundPreviewAmount(value: number) {
  return roundSettlementCurrencyAmount(
    value,
    Number(previewData.value?.currency.rounding || 0),
  );
}

const selectedLinesApply = computed(() => {
  if (applyMode.value === 'amount') {
    const total = Number(applyTotal.value) || 0;
    return roundPreviewAmount(Math.min(total, selectedLinesRemaining.value));
  }
  const ratio = Math.min(Math.max(Number(applyRatio.value) || 0, 0), 100);
  return ratioSettlementApplyTotal(
    selectedLines.value,
    ratio,
    Number(previewData.value?.currency.rounding || 0),
  );
});

const canConfirmIntroduce = computed(() => {
  if (!selectedSettlementId.value || selectedLineIds.value.size === 0) return false;
  if (applyMode.value === 'amount' && (!(Number(applyTotal.value) > 0))) return false;
  if (applyMode.value === 'ratio' && (!(Number(applyRatio.value) > 0))) return false;
  if (applyMode.value === 'ratio' && ratioSettlementApplyAmounts(
    selectedLines.value,
    applyRatio.value,
    Number(previewData.value?.currency.rounding || 0),
  ).some((amount) => !(amount > 0))) return false;
  return selectedLinesApply.value > 0;
});

async function confirmIntroduce() {
  if (!canConfirmIntroduce.value) return;
  const recordId = props.adapter.currentRecordId;
  if (!recordId) {
    introduceError.value = props.contract.recordRequiredMessage;
    return;
  }
  introduceBusy.value = true;
  emit('busy-change', true);
  introduceError.value = '';
  try {
    await intentRequest({
      intent: props.contract.actions.introduce,
      params: {
        [props.contract.payloadFields.record]: recordId,
        [props.contract.payloadFields.source]: selectedSettlementId.value,
        [props.contract.payloadFields.sourceLines]: Array.from(selectedLineIds.value),
        [props.contract.payloadFields.applyMode]: applyMode.value,
        [props.contract.payloadFields.ratio]: applyRatio.value,
        [props.contract.payloadFields.totalAmount]: applyTotal.value,
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
/* Introduce settlement lines; every semantic is contract supplied. */
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
  font: var(--sc-font-body-medium);
  color: var(--sc-color-error);
  background: color-mix(in srgb, var(--sc-color-error) 8%, transparent);
  border-radius: 6px;
  padding: 8px 12px;
}

.settle-hint {
  font: var(--sc-font-body-medium);
  color: var(--sc-color-text-3);
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
  font: var(--sc-font-mark-medium);

  color: var(--sc-color-text-1);
}

.settle-option-meta {
  font: var(--sc-font-body-small);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
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
  font: var(--sc-font-title-medium);
  color: var(--sc-color-text-1);
}

.settle-preview-sub {
  font: var(--sc-font-body-small);
  color: var(--sc-color-text-3);
}

.settle-preview-toolbar {
  font: var(--sc-font-body-small);
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--sc-color-text-3);
}

.settle-spacer {
  flex: 1;
}

.settle-total-hint {
  font: var(--sc-font-body-small);
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
  font: var(--sc-font-body-medium);
  display: grid;
  grid-template-columns: 32px minmax(120px, 2fr) minmax(100px, 1.2fr) 110px 100px 100px 84px;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
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
  font: var(--sc-font-body-small);
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
  font: var(--sc-font-mark-medium);

  color: var(--sc-color-text-1);
}

.settle-history-count {
  font: var(--sc-font-body-small);
  color: var(--sc-color-text-3);
}

.settle-history-toggle {
  font: var(--sc-font-body-small);
  margin-left: auto;
  color: var(--sc-color-brand);
}

.settle-history-body {
  border-top: 1px solid var(--sc-color-border-2);
}

.settle-history-row {
  font: var(--sc-font-body-small);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
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
  font: var(--sc-font-body-small);
  min-width: 52px;
  text-align: center;
  padding: 1px 6px;
  border-radius: 4px;
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
  font: var(--sc-font-body-medium);
  color: var(--sc-color-text-2);
}

.settle-apply-hint {
  font: var(--sc-font-body-small);
  color: var(--sc-color-text-3);
}

.settle-apply-total {
  font: var(--sc-font-body-medium);
  margin-left: auto;
  color: var(--sc-color-text-2);
}

.settle-apply-total strong {
  font: var(--sc-font-title-medium);
  color: var(--sc-color-primary);
  font-variant-numeric: tabular-nums;
}

</style>
