<template>
  <PageHeaderTemplate
    class="contract-form-command-bar"
    data-semantic-component="ContractFormProductHeader"
    :data-state="busy ? 'loading' : mode"
    :title="title"
    :subtitle="subtitle || undefined"
    :hide-title="hideTitle"
    :presentation-mode="presentationMode"
    :render-profile="mode"
    :dirty-state="headerDirtyState"
    :primary-actions="headerPrimaryActions"
    :overflow-actions="headerOverflowModelActions"
    :exit-action="headerExitAction"
    :data-professional-workflow-component="canonicalWorkflowAuthority.actionCount ? 'action-bar' : undefined"
    :data-workflow-action-count="canonicalWorkflowAuthority.actionCount || undefined"
    :data-workflow-disabled-count="canonicalWorkflowAuthority.disabledCount || undefined"
    :data-workflow-primary-key="canonicalWorkflowAuthority.primaryKey || undefined"
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
        <section
          v-else-if="statusbar.visible"
          class="native-statusbar native-statusbar--header"
          aria-label="业务状态流程"
          data-professional-workflow-component="statusbar"
          :data-workflow-current="workflowStatusAuthority.current"
          :data-workflow-readonly="String(mode === 'readonly' || !statusInteractive || workflowStatusAuthority.readonly)"
          :data-workflow-state-count="workflowStatusAuthority.stateCount"
        >
          <p :class="['native-statusbar-summary', { 'native-statusbar-summary--readonly': mode === 'readonly' || !statusInteractive }]">
            <span>当前状态</span><strong>{{ currentStatusLabel }}</strong>
            <span v-if="statusInteractive && nextActionLabel">下一步 {{ nextActionLabel }}</span>
          </p>
          <ScSteps
            v-if="mode !== 'readonly' && statusInteractive"
            class="native-statusbar-track"
            :current="statusbar.current"
            :readonly="busy || statusbar.readonly"
            :items="statusbar.states.map((item) => ({ value: String(item.value), label: item.label, disabled: busy || statusbar.readonly }))"
            @select="activateStatus(String($event))"
          />
        </section>
      </div>
    </template>
    <template #actions>
      <span v-if="showBack !== false || showReturn" class="form-header-navigation-actions">
        <ScButton
          v-if="showBack !== false"
          class="form-header-back-action"
          variant="ghost"
          size="small"
          :disabled="busy"
          type="button"
          :aria-label="backLabel"
          :data-form-secondary-action="backSemanticIdentity"
          @click="$emit('back')"
        ><ScIcon v-if="backSemanticIdentity === 'return-list'" name="arrow-left" :size="16" /> {{ backLabel }}</ScButton>
        <ScButton v-if="showReturn" variant="ghost" size="small" :disabled="busy" type="button" @click="$emit('return-workbench')">返回工作台</ScButton>
      </span>
      <span v-if="showContinueProcessing || showDraftSave || showPrimaryFormAction || directActions.length || canonicalDirectActions.length || canonicalLocalSavePrimary" class="form-header-primary-actions">
        <ScButton v-if="showContinueProcessing" data-product-primary-action data-form-mode-action="edit" variant="primary" size="small" :disabled="busy" type="button" @click="$emit('continue-processing')">{{ continueProcessingLabel }}</ScButton>
        <ScButton v-if="showDraftSave" variant="ghost" size="small" :disabled="draftSaveDisabled" type="button" @click="$emit('save-draft')">{{ draftSaveLabel }}</ScButton>
        <ScButton v-if="showPrimaryFormAction" data-product-primary-action v-bind="actionEvidenceAttributes(primaryAction)" variant="primary" size="small" :disabled="primaryFormActionDisabled" :title="primaryFormActionHint || undefined" type="button" @click="$emit('run-primary')">{{ submitLabel }}</ScButton>
        <ScButton v-for="action in presentedDirectActions" :key="`hdr-${action.key}`" v-bind="actionEvidenceAttributes(action)" :data-product-primary-action="action.presentationTier === 'primary' || undefined" :variant="buttonVariant(action)" size="small" :disabled="busy || !action.enabled" :title="action.hint" type="button" @click="$emit('run-action', action)">{{ action.label }}</ScButton>
        <ScButton v-if="canonicalLocalSavePrimary" data-product-primary-action data-action-ref="form.save" data-action-tier="primary" :data-action-enabled="String(!busy)" variant="primary" size="small" :disabled="busy" type="button" @click="$emit('canonical-save')">{{ mode === 'create' ? '保存草稿' : '保存修改' }}</ScButton>
        <ScButton v-for="action in canonicalPresentedDirectActions" :key="`canonical-hdr-${action.key}`" v-bind="canonicalActionEvidenceAttributes(action)" :data-product-primary-action="action.tier === 'primary' || undefined" :variant="canonicalButtonVariant(action)" size="small" :disabled="busy || !action.enabled" :title="workflowDisabledReason(action) || undefined" type="button" @click="$emit('canonical-action', action)">{{ action.label }}</ScButton>
      </span>
      <ScDropdown v-if="headerOverflowItems.length" class="form-header-more-actions" :items="headerOverflowItems" @select="selectHeaderOverflow">
        <template #trigger><ScButton variant="ghost" size="small">更多操作</ScButton></template>
      </ScDropdown>
      <span v-if="configActions.length" class="form-header-action-separator" aria-hidden="true" />
      <ScButton v-for="action in configActions" :key="`hdr-config-${action.key}`" v-bind="actionEvidenceAttributes(action)" class="form-header-config-action" appearance="context-action" variant="ghost" size="small" :disabled="busy || !action.enabled" :title="action.hint" type="button" @click="$emit('run-action', action)">{{ action.label }}</ScButton>
      <ScButton v-if="showDiscard" class="form-header-desktop-secondary-action" variant="ghost" size="small" :disabled="busy" type="button" @click="$emit('discard')">{{ discardLabel }}</ScButton>
      <ScButton v-if="showDebug && !intakeMode" class="form-header-desktop-secondary-action" variant="ghost" size="small" :disabled="busy || !contractPresent" type="button" @click="$emit('copy')">复制配置</ScButton>
      <ScButton v-if="showDebug && !intakeMode" class="form-header-desktop-secondary-action" variant="ghost" size="small" :disabled="busy || !contractPresent" type="button" @click="$emit('export')">导出配置</ScButton>
      <ScButton v-if="showDebug && !intakeMode" class="form-header-desktop-secondary-action" variant="ghost" size="small" :disabled="busy" type="button" @click="$emit('reload')">{{ reloadLabel }}</ScButton>
      <ScDropdown v-if="mobileActionAuthority.count && isNarrowViewport" class="form-header-mobile-actions" aria-label="更多页面操作" :data-mobile-action-count="mobileActionAuthority.count" :data-mobile-action-keys="mobileActionAuthority.keys.join(',')" :items="mobileActionItems" @select="selectMobileAction">
        <template #trigger><ScButton variant="secondary" size="small" aria-label="打开更多页面操作">更多</ScButton></template>
      </ScDropdown>
    </template>
  </PageHeaderTemplate>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import PageHeaderTemplate from '../../components/template/PageHeader.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScIcon from '../../components/design-system/ScIcon.vue';
import ScDropdown, { type ScDropdownItem } from '../../components/design-system/ScDropdown.vue';
import ScSteps from '../../components/design-system/ScSteps.vue';
import type { ProductPageHeaderAction, ProductPagePresentationMode } from '../../app/presentation/productPageHeader';
import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import type { BusyKind, ContractAction, NativeStatusbarVm } from './types';
import { nextBusinessActionLabel } from './nativeSectionNavigation';
import { resolveWorkflowActionBarAuthority, resolveWorkflowStatusAuthority, workflowDisabledReason } from './professionalWorkflowModel';
import { resolveMobileFormActionAuthority } from './mobileFormActionSettlement';

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
const workflowStatusAuthority = computed(() => resolveWorkflowStatusAuthority(props.statusbar));

/** 窄屏（<=520px）才展示移动端全收敛「更多」下拉，desktop 由「更多操作」收纳 overflow。 */
const narrowViewportQuery = typeof window !== 'undefined' ? window.matchMedia('(max-width: 520px)') : null;
const isNarrowViewport = ref(Boolean(narrowViewportQuery?.matches));
if (narrowViewportQuery) {
  const applyNarrow = () => { isNarrowViewport.value = Boolean(narrowViewportQuery.matches); };
  narrowViewportQuery.addEventListener('change', applyNarrow);
  onBeforeUnmount(() => narrowViewportQuery.removeEventListener('change', applyNarrow));
}

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
const mobilePresentedDirectActions = computed(() => presentedDirectActions.value.filter((action) => action.presentationTier !== 'primary' && action.semantic !== 'primary_action'));
const mobileCanonicalDirectActions = computed(() => canonicalPresentedDirectActions.value.filter((action) => action.tier !== 'primary'));
const canonicalPresentedOverflowActions = computed(() => [
  ...(props.canonicalLocalSavePrimary ? props.canonicalDirectActions.filter((action) => action.tier === 'primary') : []),
  ...props.canonicalOverflowActions,
]);
const mobileActionAuthority = computed(() => resolveMobileFormActionAuthority({
  showBack: props.showBack !== false,
  showReturn: props.showReturn,
  showDraftSave: props.showDraftSave,
  draftSaveDisabled: props.draftSaveDisabled,
  businessDirect: mobilePresentedDirectActions.value,
  businessOverflow: presentedOverflowActions.value,
  canonicalDirect: mobileCanonicalDirectActions.value,
  canonicalOverflow: canonicalPresentedOverflowActions.value,
  config: props.configActions,
  showDiscard: props.showDiscard,
  busy: props.busy,
}));
const canonicalWorkflowAuthority = computed(() => resolveWorkflowActionBarAuthority(
  canonicalPresentedDirectActions.value,
  canonicalPresentedOverflowActions.value,
  props.canonicalDirectActions.find((action) => action.tier === 'primary')?.key || '',
));
const headerOverflowModelActions = computed<ProductPageHeaderAction[]>(() => [
  ...presentedOverflowActions.value.map((action) => ({ key: action.key, label: action.label, semantic: 'other' as const, enabled: action.enabled })),
  ...canonicalPresentedOverflowActions.value.map((action) => ({ key: action.key, label: action.label, semantic: 'other' as const, enabled: action.enabled })),
]);
const headerOverflowItems = computed<ScDropdownItem[]>(() => [
  ...presentedOverflowActions.value.map((action) => ({ value: `business:${action.key}`, label: action.label, disabled: props.busy || !action.enabled })),
  ...canonicalPresentedOverflowActions.value.map((action) => ({ value: `canonical:${action.key}`, label: action.label, disabled: props.busy || !action.enabled })),
]);
const mobileActionItems = computed<ScDropdownItem[]>(() => [
  ...(props.showBack === false ? [{ value: 'builtin:back', label: props.backLabel, disabled: props.busy }] : []),
  ...(props.showReturn ? [{ value: 'builtin:return', label: '返回工作台', disabled: props.busy }] : []),
  ...(props.showDraftSave ? [{ value: 'builtin:draft', label: props.draftSaveLabel, disabled: props.draftSaveDisabled }] : []),
  ...mobilePresentedDirectActions.value.map((action) => ({ value: `business:${action.key}`, label: action.label, disabled: props.busy || !action.enabled })),
  ...presentedOverflowActions.value.map((action) => ({ value: `business:${action.key}`, label: action.label, disabled: props.busy || !action.enabled })),
  ...mobileCanonicalDirectActions.value.map((action) => ({ value: `canonical:${action.key}`, label: action.label, disabled: props.busy || !action.enabled })),
  ...canonicalPresentedOverflowActions.value.map((action) => ({ value: `canonical:${action.key}`, label: action.label, disabled: props.busy || !action.enabled })),
  ...props.configActions.map((action) => ({ value: `business:${action.key}`, label: action.label, disabled: props.busy || !action.enabled })),
  ...(props.showDiscard ? [{ value: 'builtin:discard', label: props.discardLabel, disabled: props.busy }] : []),
]);
const headerExitAction = computed<ProductPageHeaderAction>(() => ({ key: props.backSemanticIdentity, label: props.backLabel, semantic: 'exit', enabled: !props.busy }));
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

function selectHeaderOverflow(item: ScDropdownItem) {
  dispatchDropdownAction(String(item.value));
}

function selectMobileAction(item: ScDropdownItem) {
  const value = String(item.value);
  if (value === 'builtin:back') return emit('back');
  if (value === 'builtin:return') return emit('return-workbench');
  if (value === 'builtin:draft') return emit('save-draft');
  if (value === 'builtin:discard') return emit('discard');
  dispatchDropdownAction(value);
}

function dispatchDropdownAction(value: string) {
  const [kind, key] = value.split(':', 2);
  if (kind === 'canonical') {
    const action = [...mobileCanonicalDirectActions.value, ...canonicalPresentedOverflowActions.value].find((candidate) => candidate.key === key);
    if (action?.enabled) emit('canonical-action', action);
    return;
  }
  const action = [...mobilePresentedDirectActions.value, ...presentedOverflowActions.value, ...props.configActions].find((candidate) => candidate.key === key);
  if (action?.enabled) emit('run-action', action);
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
  void nextTick(() => {
    const commandBar = document.querySelector<HTMLElement>('.contract-form-command-bar');
    syncCommandBarHeight();
    commandBarResizeObserver = new ResizeObserver(syncCommandBarHeight);
    if (commandBar) commandBarResizeObserver.observe(commandBar);
  });
});
onBeforeUnmount(() => {
  commandBarResizeObserver?.disconnect();
  commandBarShell?.style.removeProperty('--sc-form-command-bar-height');
});

function buttonVariant(action: ContractAction): 'danger' | 'primary' | 'ghost' {
  return action.destructive ? 'danger' : action.presentationTier === 'primary' || action.semantic === 'primary_action' ? 'primary' : 'ghost';
}

function canonicalButtonVariant(action: CanonicalFormAction): 'primary' | 'ghost' {
  return action.tier === 'primary' ? 'primary' : 'ghost';
}
</script>

<style scoped>
.record-header-status { display: flex; align-items: center; justify-content: flex-end; gap: 10px; min-width: 0; }
.record-header-context { display: flex; align-items: center; justify-content: flex-end; gap: 8px; min-height: 30px; color: var(--sc-app-text-secondary); font-size: 12px; white-space: nowrap; }
.record-header-context strong { padding: 4px 8px; border: 1px solid var(--sc-app-border); border-radius: 999px; background: var(--sc-app-panel-muted); color: var(--sc-app-text-primary); font-size: 12px; }
.record-header-context span { font-weight: 600; }
.record-header-intake { display: grid; gap: 2px; }
.form-header-action-separator { align-self: center; width: 1px; height: 16px; background: var(--sc-app-border); }
.form-header-navigation-actions,
.form-header-primary-actions { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.form-header-mobile-actions { display: none; }
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
  .form-header-navigation-actions,
  .form-header-more-actions,
  .form-header-action-separator,
  .form-header-config-action,
  .form-header-desktop-secondary-action { display: none; }
  .form-header-primary-actions { order: 1; flex: 1 1 auto; }
  .form-header-primary-actions > .sc-btn:not([data-product-primary-action]) { display: none; }
  .form-header-mobile-actions { display: block; order: 2; margin-left: auto; }
}
</style>
