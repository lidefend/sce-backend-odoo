<template>
  <ScPanel class="product-work" aria-label="我的工作事项" data-semantic-component="MyWorkApprovalWorkspace" :data-state="busy ? 'loading' : 'ready'" :aria-busy="busy || undefined">
    <div class="product-work__counts" aria-label="工作项汇总">
      <ScButton
        v-for="section in workspace.sections"
        :key="section.key"
        appearance="metric"
        variant="ghost"
        type="button"
        class="count-card"
        :data-section-key="section.key"
        :class="{ active: activeSection === section.key }"
        :aria-pressed="activeSection === section.key"
        @click="activeSection = section.key"
      >
        <span>{{ section.label }}</span>
        <strong>{{ section.count }}</strong>
      </ScButton>
    </div>

    <section class="product-work__filters" aria-label="筛选和排序工作事项">
      <ScField v-slot="{ controlId, describedBy }" :label="workspace.presentation.search_label" field-key="my-work-search">
        <ScInput :id="controlId" v-model="searchText" appearance="form-field" type="search" :described-by="describedBy" :placeholder="workspace.presentation.search_placeholder" />
      </ScField>
      <ScField v-slot="{ controlId, describedBy }" label="排序方式" field-key="my-work-sort">
        <ScSelect :id="controlId" v-model="sortMode" appearance="form-field" :described-by="describedBy" :options="workspace.presentation.sort_options.map((option) => ({ value: option.key, label: option.label }))" />
      </ScField>
      <ScButton v-if="searchText" variant="ghost" @click="searchText = ''">清除查找</ScButton>
    </section>

    <p v-if="feedback" class="feedback" :class="{ error: feedbackError }" role="status">{{ feedback }}</p>

    <ScSection v-for="section in visibleSections" :key="section.key" class="work-section" :title="`${section.label} ${section.count}`" :data-section-key="section.key">
      <ScEmptyState v-if="!section.items.length" :title="searchText ? '没有符合当前查找条件的事项。' : `当前范围内没有${section.label}事项。`" />
      <ScCard v-for="item in section.items" :key="item.key" appearance="record" class="work-card" :data-work-item-key="item.key" :data-record-id="item.target.record_id" :data-work-item-state="item.state.key">
        <div class="work-card__main">
          <div class="work-card__identity">
            <span class="business-type">{{ item.business_type }}</span>
            <ScStatusBadge :value="item.state.key" :label="item.state.label" :semantic="statusSemantic(item.state.key)" />
          </div>
          <h3 :title="item.record.label">{{ item.record.label }}</h3>
          <dl class="work-card__summary" aria-label="关键事实">
            <div v-for="entry in primaryFacts(item)" :key="entry.key" :data-primary-fact-key="entry.fact.key">
              <dt>{{ entry.fact.label }}</dt>
              <dd><ScMoney v-if="entry.fact.display_role === 'money'" :display="entry.display" :label="entry.fact.label" /><template v-else>{{ entry.display }}</template></dd>
            </div>
          </dl>
          <ScDisclosure v-if="supplementaryFacts(item).length" class="work-card__disclosure" :title="`查看其余 ${supplementaryFacts(item).length} 项信息`">
            <dl class="work-card__supplementary">
              <div v-for="entry in supplementaryFacts(item)" :key="entry.key" :data-supplementary-fact-key="entry.fact.key">
                <dt>{{ entry.fact.label }}</dt>
                <dd><ScMoney v-if="entry.fact.display_role === 'money'" :display="entry.display" :label="entry.fact.label" /><template v-else>{{ entry.display }}</template></dd>
              </div>
            </dl>
          </ScDisclosure>
        </div>
        <ScActionBar class="work-card__actions" :label="`${item.record.label}操作`">
          <ScButton variant="ghost" @click="openItem(item)">打开详情</ScButton>
          <ScButton
            v-if="primaryAction(item)"
            variant="primary"
            :disabled="busy"
            @click="beginAction(item, primaryAction(item)!)"
          >
            {{ primaryAction(item)?.label }}
          </ScButton>
          <ScButton
            v-for="action in secondaryActions(item)"
            :key="action.key"
            variant="secondary"
            :disabled="busy"
            @click="beginAction(item, action)"
          >{{ action.label }}</ScButton>
          <ScDropdown
            v-if="overflowActions(item).length"
            class="more-actions"
            :items="overflowActions(item).map((action) => ({ value: action.key, label: action.label, disabled: busy }))"
            @select="(selected) => selectOverflowAction(item, selected.value)"
          >
            <template #trigger><ScButton variant="ghost" :disabled="busy">更多操作</ScButton></template>
          </ScDropdown>
        </ScActionBar>
      </ScCard>
    </ScSection>

    <ScDialog :open="dialogOpen" :title="pendingAction?.label || '确认操作'" appearance="workspace" panel-class="intent-dialog" @close="closeDialog">
      <form method="dialog" @submit.prevent>
        <p v-if="pendingItem">{{ confirmationSummary(pendingItem) }}</p>
        <label v-if="pendingAction?.requires_reason">
          {{ pendingAction.reason_label || '操作原因' }}
          <ScTextarea ref="reasonRef" v-model="reason" :rows="3" required described-by="reason-help" />
          <small id="reason-help">{{ pendingAction.reason_help || '请说明本次操作原因。' }}</small>
        </label>
        <p v-if="dialogError" class="feedback error" role="alert">{{ dialogError }}</p>
        <ScActionBar class="dialog-actions" label="确认操作">
          <ScButton variant="ghost" :disabled="busy" @click="closeDialog">取消</ScButton>
          <ScButton variant="primary" :disabled="busy" :loading="busy" autofocus @click="confirmAction">
            {{ busy ? '提交中…' : `确认${pendingAction?.label || ''}` }}
          </ScButton>
        </ScActionBar>
      </form>
    </ScDialog>
  </ScPanel>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { executeProductMyWorkAction, type ProductMyWorkAction, type ProductMyWorkFact, type ProductMyWorkItem, type ProductMyWorkWorkspace } from '../../api/myWork';
import { formatProductMyWorkFact, partitionProductMyWorkFacts } from '../../app/presentation/productMyWorkPresentation';
import ScActionBar from '../design-system/ScActionBar.vue';
import ScButton from '../design-system/ScButton.vue';
import ScDialog from '../design-system/ScDialog.vue';
import ScDisclosure from '../design-system/ScDisclosure.vue';
import ScDropdown, { type ScDropdownItem } from '../design-system/ScDropdown.vue';
import ScEmptyState from '../design-system/ScEmptyState.vue';
import ScField from '../design-system/ScField.vue';
import ScMoney from '../design-system/ScMoney.vue';
import ScCard from '../design-system/ScCard.vue';
import ScPanel from '../design-system/ScPanel.vue';
import ScSection from '../design-system/ScSection.vue';
import ScSelect from '../design-system/ScSelect.vue';
import ScStatusBadge from '../design-system/ScStatusBadge.vue';
import ScInput from '../design-system/ScInput.vue';
import ScTextarea from '../design-system/ScTextarea.vue';

const props = defineProps<{ workspace: ProductMyWorkWorkspace }>();
const emit = defineEmits<{ refresh: [] }>();
const router = useRouter();
const activeSection = ref('todo');
const searchText = ref('');
const sortMode = ref(props.workspace.presentation.default_sort);
const busy = ref(false);
const feedback = ref('');
const feedbackError = ref(false);
const dialogError = ref('');
const reason = ref('');
const pendingItem = ref<ProductMyWorkItem | null>(null);
const pendingAction = ref<ProductMyWorkAction | null>(null);
const dialogOpen = ref(false);
const reasonRef = ref<{ focus: () => void } | null>(null);
let actionTrigger: HTMLElement | null = null;

function selectOverflowAction(item: ProductMyWorkItem, value: ScDropdownItem['value']) {
  const action = overflowActions(item).find((candidate) => candidate.key === String(value));
  if (action) beginAction(item, action);
}

const visibleSections = computed(() => {
  const selected = props.workspace.sections.find((row) => row.key === activeSection.value);
  const sections = selected ? [selected] : props.workspace.sections;
  const query = searchText.value.toLocaleLowerCase('zh-CN');
  return sections.map((section) => {
    const items = section.items.filter((item) => {
      if (!query) return true;
      return String(item.search_text || '').toLocaleLowerCase('zh-CN').includes(query);
    });
    const option = props.workspace.presentation.sort_options.find((row) => row.key === sortMode.value);
    items.sort((left, right) => {
      const leftValue = left.sort_values?.[sortMode.value];
      const rightValue = right.sort_values?.[sortMode.value];
      if (option?.kind === 'number_desc') return Number(rightValue || 0) - Number(leftValue || 0);
      if (option?.kind === 'number_asc') return Number(leftValue || 0) - Number(rightValue || 0);
      if (option?.kind === 'text_asc') return String(leftValue || '').localeCompare(String(rightValue || ''));
      return String(rightValue || '').localeCompare(String(leftValue || ''));
    });
    return { ...section, items };
  });
});

watch(
  () => props.workspace.query_scope,
  () => {
    searchText.value = '';
    sortMode.value = props.workspace.presentation.default_sort;
    const first = props.workspace.sections.find((section) => section.key === 'todo') || props.workspace.sections[0];
    activeSection.value = first?.key || 'todo';
  },
  { deep: true },
);

function formatFact(fact: ProductMyWorkFact) {
  return formatProductMyWorkFact(fact);
}

function primaryFacts(item: ProductMyWorkItem) {
  return partitionProductMyWorkFacts(item.facts, 1).primary;
}

function supplementaryFacts(item: ProductMyWorkItem) {
  return partitionProductMyWorkFacts(item.facts, 1).supplementary;
}

function statusSemantic(value?: string) {
  const semantic = String(value || '').toLowerCase();
  if (semantic === 'success' || semantic === 'warning' || semantic === 'danger' || semantic === 'info') return semantic;
  return 'default';
}

function confirmationSummary(item: ProductMyWorkItem) {
  const highlighted = item.facts.find((fact) => fact.display_role === 'money');
  return highlighted ? `${item.record.label} · ${formatFact(highlighted)}` : item.record.label;
}

function primaryAction(item: ProductMyWorkItem) {
  return item.actions.find((action) => action.presentation?.tier === 'primary');
}

function secondaryActions(item: ProductMyWorkItem) {
  return item.actions
    .filter((action) => action.presentation?.tier === 'secondary')
    .slice(0, 2);
}

function overflowActions(item: ProductMyWorkItem) {
  const primary = primaryAction(item);
  const secondary = new Set(secondaryActions(item).map((action) => action.key));
  return item.actions.filter((action) => action.key !== primary?.key && !secondary.has(action.key));
}

function openItem(item: ProductMyWorkItem) {
  void router.push(item.target.route);
}

async function beginAction(item: ProductMyWorkItem, action: ProductMyWorkAction) {
  if (busy.value) return;
  actionTrigger = document.activeElement as HTMLElement | null;
  pendingItem.value = item;
  pendingAction.value = action;
  reason.value = '';
  dialogError.value = '';
  dialogOpen.value = true;
  await nextTick();
  if (action.requires_reason) reasonRef.value?.focus();
  else document.querySelector<HTMLButtonElement>('.intent-dialog .dialog-actions button:last-child')?.focus();
}

function closeDialog() {
  dialogOpen.value = false;
  restoreFocus();
}

function restoreFocus() {
  actionTrigger?.focus();
  actionTrigger = null;
}

async function confirmAction() {
  const item = pendingItem.value;
  const action = pendingAction.value;
  if (!item || !action || busy.value) return;
  if (action.requires_reason && !reason.value) {
    dialogError.value = `请填写${action.reason_label || '操作原因'}。`;
    reasonRef.value?.focus();
    return;
  }
  busy.value = true;
  dialogError.value = '';
  try {
    const result = await executeProductMyWorkAction(action, reason.value);
    if (result.success === false) throw new Error(result.message || '操作失败');
    feedback.value = `${item.record.label}已${action.label}，工作项已同步刷新。`;
    feedbackError.value = false;
    closeDialog();
    emit('refresh');
  } catch (error) {
    dialogError.value = error instanceof Error ? error.message : '操作失败，请稍后重试。';
    feedback.value = dialogError.value;
    feedbackError.value = true;
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.product-work { display: grid; align-content: start; gap: 18px; }
.product-work__counts { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
.product-work__filters { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(180px, auto) auto; gap: 12px; align-items: end; padding: var(--sc-product-space-2); border: 1px solid var(--sc-app-border); border-radius: var(--sc-product-radius-panel); background: var(--sc-app-panel); }
.product-work__filters label { display: grid; gap: 6px; color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-sm); }
.product-work__filters :deep(.sc-input), .product-work__filters :deep(.sc-select) { width: 100%; min-height: var(--sc-product-control-height); }
.work-section { display: grid; gap: 12px; }
.work-section h2 { margin: 0; font-size: 20px; }
.work-section h2 span { color: var(--sc-app-text-secondary); font-weight: 500; }
.work-card { min-width: 0; }
.work-card__main { display: grid; grid-template-columns: auto minmax(220px, 1.2fr) minmax(270px, 1fr) auto; grid-template-areas: 'identity title summary disclosure'; align-items: center; min-width: 0; flex: 1; gap: 6px 16px; }
.work-card__identity { grid-area: identity; display: flex; gap: 8px; align-items: center; }
.business-type, .status-badge { display: inline-flex; padding: 3px 8px; border-radius: var(--sc-component-tag-radius); background: var(--sc-app-info-bg); color: var(--sc-app-info-text); font-size: var(--sc-product-text-sm); }
.status-badge { background: var(--sc-app-subtle-bg); color: var(--sc-app-text-primary); }
.work-card h3 { grid-area: title; min-width: 0; margin: 2px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.work-card :deep(.t-card__body) { grid-template-columns: minmax(0, 1fr) auto; align-items: start; }
.work-card dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 20px; margin: 0; }
.work-card__summary { grid-area: summary; }
.work-card dl div { min-width: 0; }
.work-card dt { color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-sm); }
.work-card dd { margin: 3px 0 0; overflow-wrap: anywhere; }
.work-card__disclosure { grid-area: disclosure; margin-top: 0; }
.work-card__supplementary { padding-top: 8px; border-top: 1px solid var(--sc-app-border); }
.work-card__actions { display: flex; flex-wrap: wrap; gap: 8px; align-content: flex-start; }
.more-actions { position: relative; }
.more-actions summary { cursor: pointer; min-height: var(--sc-product-control-height); display: inline-flex; align-items: center; padding: 0 12px; border: 1px solid var(--sc-app-border); border-radius: var(--sc-product-radius-control); }
.more-actions[open] { display: grid; gap: 8px; }
.empty { padding: var(--sc-product-space-3); border: 1px dashed var(--sc-app-border); border-radius: var(--sc-product-radius-panel); color: var(--sc-app-text-secondary); }
.feedback { margin: 0; padding: 10px 12px; border-radius: var(--sc-product-radius-control); background: var(--sc-app-success-bg); color: var(--sc-app-success-text); }
.feedback.error { background: var(--sc-app-danger-bg); color: var(--sc-app-danger-text); }
:deep(.intent-dialog) { width: min(480px, calc(100vw - 32px)); max-height: calc(100dvh - 32px); overflow: auto; }
:deep(.intent-dialog label) { display: grid; gap: 6px; }
:deep(.intent-dialog .sc-textarea) { width: 100%; box-sizing: border-box; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
@media (max-width: 640px) {
  .product-work { gap: 14px; }
  .product-work__counts { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .product-work__filters { grid-template-columns: 1fr; padding: 12px; --sc-component-input-form-height: 44px; }
  .work-card__main { grid-template-columns: minmax(0, 1fr); grid-template-areas: 'identity' 'title' 'summary' 'disclosure'; gap: 8px; }
  .work-card h3 { display: -webkit-box; margin: 9px 0 12px; overflow: hidden; font-size: 17px; line-height: 1.3; white-space: normal; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
  .work-card dl { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 14px; }
  .work-card :deep(.t-card__body) { grid-template-columns: minmax(0, 1fr); }
  .work-card dt { font-size: 11px; }
  .work-card dd { font-size: 13px; }
  .work-card__actions { width: 100%; }
  .work-card__actions :deep(.sc-btn) { flex: 1 1 auto; }
}
</style>
