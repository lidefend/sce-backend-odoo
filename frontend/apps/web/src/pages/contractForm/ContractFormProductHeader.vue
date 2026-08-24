<template>
  <PageHeaderTemplate
    class="contract-form-command-bar"
    :title="title"
    :subtitle="subtitle || undefined"
    :hide-title="hideTitle"
    :presentation-mode="presentationMode"
    :render-profile="mode"
    :dirty-state="headerDirtyState"
    :primary-actions="headerPrimaryActions"
    :overflow-actions="headerOverflowModelActions"
    :exit-action="headerExitAction"
  >
    <template #meta>
      <p v-if="showHud" class="meta">model={{ model }} · id={{ recordIdDisplay }} · action={{ actionId || '-' }}</p>
      <p v-if="showHud && contractMetaLine" class="meta">{{ contractMetaLine }}</p>
    </template>
    <template #status>
      <div class="record-header-status">
        <div class="record-header-context" aria-label="页面模式与保存状态" aria-live="polite">
          <strong>{{ modeLabel }}</strong>
          <span v-if="busyKind === 'save'">正在保存…</span>
          <span v-else-if="busy">正在处理…</span>
          <span v-else-if="dirty">{{ changedFieldCount > 0 ? `已修改 ${changedFieldCount} 项` : '有未保存修改' }}</span>
          <span v-else-if="mode !== 'readonly'">尚未修改</span>
        </div>
        <div v-if="intakeMode" class="record-header-intake">
          <p class="header-status-item">当前进度：{{ intakeRequiredSummary }}</p>
          <p class="header-status-item" :class="{ 'header-status-item--danger': intakeMissingSummary !== '无' }">缺少：{{ intakeMissingSummary }}</p>
        </div>
        <section v-else-if="statusbar.visible" class="native-statusbar native-statusbar--header" aria-label="业务状态流程">
          <p :class="['native-statusbar-summary', { 'native-statusbar-summary--readonly': mode === 'readonly' || !statusInteractive }]">
            <span>当前状态</span><strong>{{ currentStatusLabel }}</strong>
            <span v-if="statusInteractive && nextActionLabel">下一步 {{ nextActionLabel }}</span>
          </p>
          <ol
            v-if="mode !== 'readonly' && statusInteractive"
            ref="statusTrackRef"
            class="native-statusbar-track"
            :data-has-more-before="workflowHasMoreBefore || undefined"
            :data-has-more-after="workflowHasMoreAfter || undefined"
            @scroll="updateWorkflowOverflow"
          >
            <li v-for="(item, index) in statusbar.states" :key="String(item.value)">
              <button
                type="button"
                class="native-statusbar-step"
                :class="{ 'native-statusbar-step--active': statusbar.current === String(item.value), 'native-statusbar-step--done': statusbar.reachedValues.includes(String(item.value)) && statusbar.current !== String(item.value) }"
                :aria-current="statusbar.current === String(item.value) ? 'step' : undefined"
                :aria-label="`第 ${index + 1} 步，共 ${statusbar.states.length} 步：${item.label}`"
                :aria-disabled="busy || statusbar.readonly"
                :disabled="busy || statusbar.readonly"
                @click="activateStatus(String(item.value))"
              ><span class="native-statusbar-step-index" aria-hidden="true">{{ index + 1 }}</span><span>{{ item.label }}</span></button>
            </li>
          </ol>
        </section>
      </div>
    </template>
    <template #actions>
      <span v-if="showBack !== false || showReturn" class="form-header-navigation-actions">
        <button
          v-if="showBack !== false"
          class="sc-btn sc-btn-ghost sc-btn-sm form-header-back-action"
          :disabled="busy"
          type="button"
          :aria-label="backLabel"
          :data-form-secondary-action="backSemanticIdentity"
          @click="$emit('back')"
        ><ScIcon v-if="backSemanticIdentity === 'return-list'" name="arrow-left" :size="16" /> {{ backLabel }}</button>
        <button v-if="showReturn" class="sc-btn sc-btn-ghost sc-btn-sm" :disabled="busy" type="button" @click="$emit('return-workbench')">返回工作台</button>
      </span>
      <span v-if="showContinueProcessing || showDraftSave || showPrimaryFormAction || directActions.length || canonicalDirectActions.length || canonicalLocalSavePrimary" class="form-header-primary-actions">
        <button v-if="showContinueProcessing" data-product-primary-action data-form-mode-action="edit" class="sc-btn sc-btn-primary sc-btn-sm" :disabled="busy" type="button" @click="$emit('continue-processing')">{{ continueProcessingLabel }}</button>
        <button v-if="showDraftSave" class="sc-btn sc-btn-ghost sc-btn-sm" :disabled="draftSaveDisabled" type="button" @click="$emit('save-draft')">{{ draftSaveLabel }}</button>
        <button v-if="showPrimaryFormAction" data-product-primary-action v-bind="actionEvidenceAttributes(primaryAction)" class="sc-btn sc-btn-primary sc-btn-sm" :disabled="primaryFormActionDisabled" :title="primaryFormActionHint || undefined" type="button" @click="$emit('run-primary')">{{ submitLabel }}</button>
        <button v-for="action in presentedDirectActions" :key="`hdr-${action.key}`" v-bind="actionEvidenceAttributes(action)" :data-product-primary-action="action.presentationTier === 'primary' || undefined" :class="buttonClass(action)" :disabled="busy || !action.enabled" :title="action.hint" type="button" @click="$emit('run-action', action)">{{ action.label }}</button>
        <button v-if="canonicalLocalSavePrimary" data-product-primary-action data-action-ref="form.save" class="sc-btn sc-btn-primary sc-btn-sm" :disabled="busy" type="button" @click="$emit('canonical-save')">{{ mode === 'create' ? '保存草稿' : '保存修改' }}</button>
        <button v-for="action in canonicalPresentedDirectActions" :key="`canonical-hdr-${action.key}`" v-bind="canonicalActionEvidenceAttributes(action)" :data-product-primary-action="action.tier === 'primary' || undefined" :class="canonicalButtonClass(action)" :disabled="busy || !action.enabled" :title="action.reasonCode || undefined" type="button" @click="$emit('canonical-action', action)">{{ action.label }}</button>
      </span>
      <details v-if="presentedOverflowActions.length || canonicalPresentedOverflowActions.length" class="form-header-more-actions">
        <summary class="sc-btn sc-btn-ghost sc-btn-sm">更多操作</summary>
        <div>
          <button v-for="action in presentedOverflowActions" :key="`hdr-more-${action.key}`" v-bind="actionEvidenceAttributes(action)" :class="buttonClass(action)" :disabled="busy || !action.enabled" :title="action.hint" type="button" @click="$emit('run-action', action)">{{ action.label }}</button>
          <button v-for="action in canonicalPresentedOverflowActions" :key="`canonical-hdr-more-${action.key}`" v-bind="canonicalActionEvidenceAttributes(action)" class="sc-btn sc-btn-ghost sc-btn-sm" :disabled="busy || !action.enabled" :title="action.reasonCode || undefined" type="button" @click="$emit('canonical-action', action)">{{ action.label }}</button>
        </div>
      </details>
      <span v-if="configActions.length" class="form-header-action-separator" aria-hidden="true" />
      <button v-for="action in configActions" :key="`hdr-config-${action.key}`" v-bind="actionEvidenceAttributes(action)" class="sc-btn sc-btn-ghost sc-btn-sm form-header-config-action" :disabled="busy || !action.enabled" :title="action.hint" type="button" @click="$emit('run-action', action)">{{ action.label }}</button>
      <button v-if="showDiscard" class="sc-btn sc-btn-ghost sc-btn-sm" :disabled="busy" type="button" @click="$emit('discard')">{{ discardLabel }}</button>
      <button v-if="showDebug && !intakeMode" class="sc-btn sc-btn-ghost sc-btn-sm" :disabled="busy || !contractPresent" type="button" @click="$emit('copy')">复制配置</button>
      <button v-if="showDebug && !intakeMode" class="sc-btn sc-btn-ghost sc-btn-sm" :disabled="busy || !contractPresent" type="button" @click="$emit('export')">导出配置</button>
      <button v-if="showDebug && !intakeMode" class="sc-btn sc-btn-ghost sc-btn-sm" :disabled="busy" type="button" @click="$emit('reload')">{{ reloadLabel }}</button>
    </template>
  </PageHeaderTemplate>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import PageHeaderTemplate from '../../components/template/PageHeader.vue';
import ScIcon from '../../components/design-system/ScIcon.vue';
import type { ProductPageHeaderAction, ProductPagePresentationMode } from '../../app/presentation/productPageHeader';
import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import type { BusyKind, ContractAction, NativeStatusbarVm } from './types';
import { nextBusinessActionLabel } from './nativeSectionNavigation';

const props = defineProps<{
  title: string; subtitle: string; hideTitle: boolean; showHud: boolean; model: string; recordIdDisplay: string;
  actionId: number | null; contractMetaLine: string; intakeMode: boolean; intakeRequiredSummary: string;
  intakeMissingSummary: string; statusbar: NativeStatusbarVm; busy: boolean; busyKind: BusyKind; showReturn: boolean;
  mode: 'create' | 'edit' | 'readonly'; modeLabel: string; dirty: boolean; changedFieldCount: number;
  presentationMode: ProductPagePresentationMode;
  showContinueProcessing: boolean;
  showBack?: boolean;
  backLabel: string;
  backSemanticIdentity: 'return-list' | 'cancel-edit';
  statusInteractive?: boolean;
  continueProcessingLabel: string;
  showDraftSave: boolean; draftSaveDisabled: boolean; draftSaveLabel: string; showPrimaryFormAction: boolean;
  primaryFormActionDisabled: boolean; primaryFormActionHint: string; submitLabel: string; primaryAction: ContractAction | null;
  directActions: ContractAction[]; overflowActions: ContractAction[];
  canonicalDirectActions: CanonicalFormAction[]; canonicalOverflowActions: CanonicalFormAction[]; canonicalLocalSavePrimary: boolean;
  configActions: ContractAction[]; showDiscard: boolean; showDebug: boolean; contractPresent: boolean;
  discardLabel: string; reloadLabel: string;
}>();

const currentStatusIndex = computed(() => props.statusbar.states.findIndex((item) => String(item.value) === props.statusbar.current));
const currentStatusLabel = computed(() => props.statusbar.states[currentStatusIndex.value]?.label || '未设置');
const nextActionLabel = computed(() => nextBusinessActionLabel(props.primaryAction, props.directActions));
const headerDirtyState = computed(() => props.busyKind === 'save' ? 'saving' : props.dirty ? 'dirty' : 'clean');
const builtInPrimaryClaimed = computed(() => props.showContinueProcessing || props.showPrimaryFormAction);
const presentedDirectActions = computed(() => builtInPrimaryClaimed.value
  ? props.directActions.filter((action) => action.presentationTier !== 'primary' && action.semantic !== 'primary_action')
  : props.directActions);
const presentedOverflowActions = computed(() => {
  const displaced = builtInPrimaryClaimed.value
    ? props.directActions.filter((action) => action.presentationTier === 'primary' || action.semantic === 'primary_action')
    : [];
  return [...displaced, ...props.overflowActions];
});
const headerPrimaryActions = computed<ProductPageHeaderAction[]>(() => {
  if (props.showContinueProcessing) return [{ key: 'continue-processing', label: props.continueProcessingLabel, semantic: 'other', enabled: !props.busy }];
  if (props.showPrimaryFormAction) return [{ key: props.primaryAction?.key || 'save', label: props.submitLabel, semantic: props.primaryAction ? 'submit' : 'save', enabled: !props.primaryFormActionDisabled }];
  const action = presentedDirectActions.value.find((item) => item.presentationTier === 'primary' || item.semantic === 'primary_action');
  if (action) return [{ key: action.key, label: action.label, semantic: 'submit', enabled: action.enabled }];
  if (props.canonicalLocalSavePrimary) return [{ key: 'form.save', label: props.mode === 'create' ? '保存草稿' : '保存修改', semantic: 'save', enabled: !props.busy }];
  const canonical = props.canonicalDirectActions.find((item) => item.tier === 'primary');
  return canonical ? [{ key: canonical.key, label: canonical.label, semantic: 'submit', enabled: canonical.enabled }] : [];
});
const canonicalPresentedDirectActions = computed(() => props.canonicalLocalSavePrimary ? props.canonicalDirectActions.filter((action) => action.tier !== 'primary') : props.canonicalDirectActions);
const canonicalPresentedOverflowActions = computed(() => [
  ...(props.canonicalLocalSavePrimary ? props.canonicalDirectActions.filter((action) => action.tier === 'primary') : []),
  ...props.canonicalOverflowActions,
]);
const headerOverflowModelActions = computed<ProductPageHeaderAction[]>(() => [
  ...presentedOverflowActions.value.map((action) => ({ key: action.key, label: action.label, semantic: 'other' as const, enabled: action.enabled })),
  ...canonicalPresentedOverflowActions.value.map((action) => ({ key: action.key, label: action.label, semantic: 'other' as const, enabled: action.enabled })),
]);
const headerExitAction = computed<ProductPageHeaderAction>(() => ({ key: props.backSemanticIdentity, label: props.backLabel, semantic: 'exit', enabled: !props.busy }));
const statusTrackRef = ref<HTMLOListElement | null>(null);
const workflowHasMoreBefore = ref(false);
const workflowHasMoreAfter = ref(false);
let commandBarResizeObserver: ResizeObserver | null = null;
let commandBarShell: HTMLElement | null = null;

const emit = defineEmits<{
  back: []; 'continue-processing': []; 'set-status': [value: string]; 'return-workbench': []; 'save-draft': []; 'run-primary': [];
  'run-action': [action: ContractAction]; discard: []; copy: []; export: []; reload: [];
  'canonical-action': [action: CanonicalFormAction]; 'canonical-save': [];
}>();

function actionEvidenceAttributes(action: ContractAction | null) {
  if (!action) return {};
  return {
    'data-action-key': action.key,
    'data-backend-identity': action.backendIdentity || '',
    'data-action-method': action.methodName || '',
    'data-action-enabled': String(action.enabled),
    'data-action-allowed': String(action.authorizationAllowed !== false),
    'data-visible-profiles': action.visibleProfiles.join(','),
  };
}

function canonicalActionEvidenceAttributes(action: CanonicalFormAction) {
  return {
    'data-action-ref': action.actionRef.actionId,
    'data-action-key': action.key,
    'data-backend-identity': action.actionRef.backendIdentity,
    'data-action-method': action.actionRef.button?.name || action.actionRef.button?.method || '',
    'data-action-enabled': String(action.enabled),
    'data-action-allowed': String(action.actionRef.allowed === true),
  };
}

function updateWorkflowOverflow() {
  const track = statusTrackRef.value;
  if (!track) return;
  workflowHasMoreBefore.value = track.scrollLeft > 2;
  workflowHasMoreAfter.value = track.scrollLeft + track.clientWidth < track.scrollWidth - 2;
}

function revealCurrentStatus(smooth = false) {
  const track = statusTrackRef.value;
  const active = track?.querySelector<HTMLElement>('[aria-current="step"]');
  if (!track || !active) return;
  const left = Math.max(0, active.offsetLeft - (track.clientWidth - active.offsetWidth) / 2);
  track.scrollTo({ left, behavior: smooth ? 'smooth' : 'auto' });
  window.setTimeout(updateWorkflowOverflow, smooth ? 220 : 0);
}

function activateStatus(value: string) {
  if (props.busy || props.statusbar.readonly) return;
  emit('set-status', value);
}

function syncCommandBarHeight() {
  const commandBar = document.querySelector<HTMLElement>('.contract-form-command-bar');
  if (!commandBar) return;
  commandBarShell = commandBar.closest<HTMLElement>('.contract-form-native-shell');
  commandBarShell?.style.setProperty('--sc-form-command-bar-height', `${Math.ceil(commandBar.getBoundingClientRect().height)}px`);
}

onMounted(() => {
  void nextTick(() => revealCurrentStatus(false));
  void nextTick(() => {
    const commandBar = document.querySelector<HTMLElement>('.contract-form-command-bar');
    syncCommandBarHeight();
    commandBarResizeObserver = new ResizeObserver(syncCommandBarHeight);
    if (commandBar) commandBarResizeObserver.observe(commandBar);
  });
  window.addEventListener('resize', updateWorkflowOverflow);
});
watch(() => [props.statusbar.current, props.statusbar.states.length], () => void nextTick(() => revealCurrentStatus(true)));
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateWorkflowOverflow);
  commandBarResizeObserver?.disconnect();
  commandBarShell?.style.removeProperty('--sc-form-command-bar-height');
});

function buttonClass(action: ContractAction) {
  return ['sc-btn', 'sc-btn-sm', action.destructive ? 'sc-btn-danger' : action.presentationTier === 'primary' || action.semantic === 'primary_action' ? 'sc-btn-primary' : 'sc-btn-ghost'];
}

function canonicalButtonClass(action: CanonicalFormAction) {
  return ['sc-btn', 'sc-btn-sm', action.tier === 'primary' ? 'sc-btn-primary' : 'sc-btn-ghost'];
}
</script>

<style scoped>
.record-header-status { display: flex; align-items: center; justify-content: flex-end; gap: 10px; min-width: 0; }
.record-header-context { display: flex; align-items: center; justify-content: flex-end; gap: 8px; min-height: 30px; color: var(--sc-app-text-secondary); font-size: 12px; white-space: nowrap; }
.record-header-context strong { padding: 4px 8px; border: 1px solid var(--sc-app-border); border-radius: 999px; background: var(--sc-app-panel-muted); color: var(--sc-app-text-primary); font-size: 12px; }
.record-header-context span { font-weight: 600; }
.record-header-intake { display: grid; gap: 2px; }
.form-header-action-separator { align-self: center; width: 1px; height: 16px; background: var(--sc-app-border); }
.form-header-more-actions { position: relative; }
.form-header-more-actions > summary { list-style: none; cursor: pointer; }
.form-header-more-actions > summary::-webkit-details-marker { display: none; }
.form-header-more-actions > div { position: absolute; z-index: 30; top: calc(100% + 6px); right: 0; display: grid; min-width: 180px; gap: 6px; padding: 8px; border: 1px solid var(--sc-app-border); border-radius: var(--sc-component-panel-radius); background: var(--sc-app-panel); box-shadow: var(--sc-product-shadow-overlay); }
.form-header-config-action { color: var(--sc-semantic-text-muted); }
.form-header-navigation-actions,
.form-header-primary-actions { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.native-statusbar--header {
  position: relative;
  max-width: 100%;
  min-width: 0;
}
.native-statusbar-track {
  display: flex;
  align-items: stretch;
  margin: 0;
  padding: 0;
  list-style: none;
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: thin;
}
.native-statusbar-track > li { display: flex; flex: 0 0 auto; }
.native-statusbar-summary { display: none; }
.native-statusbar-summary--readonly {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.native-statusbar-summary--readonly strong { color: var(--sc-app-info-text); font-size: 13px; }
.native-statusbar-step-index {
  display: none;
  width: 18px;
  height: 18px;
  place-items: center;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 10px;
  line-height: 1;
}
.native-statusbar--header .native-statusbar-step {
  flex: 0 0 auto;
  width: max-content;
  min-width: 68px;
  min-height: 30px;
  margin: 0 0 0 -1px;
  padding: 0 10px;
  border: 1px solid var(--sc-app-border);
  border-radius: 0;
  background: var(--sc-app-subtle-bg);
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: default;
  white-space: nowrap;
}
.native-statusbar--header .native-statusbar-step:first-child {
  margin-left: 0;
  border-radius: 4px 0 0 4px;
}
.native-statusbar--header .native-statusbar-step:last-child {
  border-radius: 0 4px 4px 0;
}
.native-statusbar--header .native-statusbar-step--done {
  background: var(--sc-app-success-bg);
  color: var(--sc-app-success-text);
}
.native-statusbar--header .native-statusbar-step--active {
  position: relative;
  z-index: 1;
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
  font-weight: 600;
}
@media (max-width: 860px) {
  .record-header-status { align-items: flex-start; flex-direction: column; width: 100%; }
  .record-header-context { justify-content: flex-start; }
  .native-statusbar--header { width: 100%; }
}
@media (max-width: 520px) {
  .record-header-status { gap: 6px; }
  .record-header-context { min-height: 24px; }
  .record-header-context strong { padding: 3px 7px; }
  .native-statusbar-summary {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0 0 6px;
    color: var(--sc-app-text-secondary);
    font-size: 11px;
  }
  .native-statusbar-summary strong { color: var(--sc-app-info-text); font-size: 13px; }
  .native-statusbar-summary > span:nth-child(3) { margin-left: auto; }
  .native-statusbar-track {
    display: none;
  }
  .native-statusbar--header .native-statusbar-step,
  .native-statusbar--header .native-statusbar-step:first-child,
  .native-statusbar--header .native-statusbar-step:last-child {
    width: auto;
    min-width: 92px;
    min-height: 32px;
    margin: 0 0 0 -1px;
    padding: 0 9px;
    border-radius: 0;
    gap: 6px;
  }
  .native-statusbar--header .native-statusbar-step:first-child { margin-left: 0; border-radius: 5px 0 0 5px; }
  .native-statusbar--header .native-statusbar-step:last-child { border-radius: 0 5px 5px 0; }
  .native-statusbar-step-index { display: grid; }
  .form-header-navigation-actions { order: 2; }
  .form-header-primary-actions { order: 1; }
}
</style>
