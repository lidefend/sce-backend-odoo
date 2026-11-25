<template>
  <section
    v-if="stateResolution.gap"
    class="panel sc-state-panel error state-unknown"
    role="alert"
    data-semantic-state-surface="page"
    :data-contract-gap="stateResolution.gap"
    :data-contract-gap-kind="contractDefect?.kind || 'contract_defect'"
    :data-contract-gap-layer="contractDefectOwnerLayer || undefined"
    :data-contract-semantic-type="contractDefect?.kind === 'frontend_capability_gap' ? contractDefect.semanticType : undefined"
    :data-consumer-error-name="contractConsumerContext?.errorName || undefined"
    :data-consumer-error-stage="contractConsumerContext?.stage || undefined"
    :data-consumer-component-trace="consumerComponentTraceText || undefined"
  >
    <h2>{{ contractGapTitle }}</h2>
    <p>{{ contractGapStopMessage }}</p>
    <p v-if="message" class="trace">{{ message }}</p>
    <p class="trace">错误类型：{{ contractGapErrorType }}</p>
    <p class="trace">失败分类：{{ contractGapFailureLabel }}</p>
    <p v-if="contractConsumerContext?.stage" class="trace">
      失败阶段：{{ contractConsumerContext.stage }}
    </p>
    <p v-if="consumerComponentTraceText" class="trace">
      组件链：{{ consumerComponentTraceText }}
    </p>
    <p class="trace">{{ contractGapLocationLabel }}：{{ stateResolution.gap }}</p>
    <p v-if="contractDefect?.kind === 'frontend_capability_gap'" class="trace">
      语义：{{ contractDefect.semanticType }}
      <span v-if="contractDefect.fieldType"> · 字段类型：{{ contractDefect.fieldType }}</span>
      <span v-if="contractDefect.presentationMode"> · 模式：{{ contractDefect.presentationMode }}</span>
    </p>
    <p v-if="contractDefectOwnerLayer" class="trace">
      责任层：{{ contractDefectOwnerLayer }}
    </p>
  </section>
  <section
    v-else
    class="panel sc-state-panel"
    :class="[variant, `state-${productState?.kind}`]"
    data-semantic-state-surface="page"
    :data-error-kind="productState?.kind"
    :data-state="busy ? 'loading' : variant === 'error' ? 'error' : productState?.kind"
    :data-contract-gap="contractDefect?.missing || undefined"
    :data-contract-gap-kind="contractDefect?.kind || undefined"
    :data-contract-gap-layer="contractDefectOwnerLayer || undefined"
    :role="variant === 'error' ? 'alert' : 'status'"
    :aria-live="variant === 'error' ? 'assertive' : 'polite'"
    :aria-busy="busy || undefined"
  >
    <h2 v-if="!hideTitle">{{ displayTitle }}</h2>
    <p v-if="displayMessage">{{ displayMessage }}</p>
    <div v-if="busy" class="state-skeleton" aria-hidden="true"><span /><span /><span /></div>
    <div v-if="variant === 'error' && showHudMeta" class="error-meta">
      <p class="trace">Error code: {{ errorCode ?? 'N/A' }}</p>
      <p class="trace">Trace: {{ traceId || 'N/A' }}</p>
      <p v-if="reasonCode" class="trace">Reason: {{ reasonCode }}</p>
      <p v-if="errorCategory" class="trace">Category: {{ errorCategory }}</p>
      <p v-if="errorModel" class="trace">Model: {{ errorModel }}</p>
      <p v-if="errorOp" class="trace">Operation: {{ errorOp }}</p>
      <p v-if="retryable !== undefined" class="trace">Retryable: {{ retryable ? 'yes' : 'no' }}</p>
      <p v-if="hint" class="trace">Hint: {{ hint }}</p>
      <ScButton v-if="traceId" class="trace-copy" variant="ghost" size="small" @click="copyTrace">复制诊断编号</ScButton>
      <ScButton v-if="canRunSuggestedAction && suggestedActionLabel" class="trace-copy" variant="ghost" size="small" @click="runSuggestedAction">
        {{ suggestedActionLabel }}
      </ScButton>
    </div>
    <ScButton
      v-else-if="variant === 'error' && canRunSuggestedAction && suggestedActionLabel"
      class="trace-copy"
      variant="ghost"
      @click="runSuggestedAction"
    >
      {{ suggestedActionLabel }}
    </ScButton>
    <p v-if="actionRunFeedback" class="action-feedback" role="status" aria-live="polite">{{ actionRunFeedback }}</p>
    <ScButton v-if="props.variant === 'error' ? Boolean(productState?.action && productState.action.kind !== 'none') : Boolean(onRetry)" :data-recovery-action="productState?.action.kind" variant="primary" :disabled="retrying || busy" :loading="retrying" loading-label="正在重试" @click="retry">
      {{ retrying ? '正在重试…' : (props.variant === 'error' ? productState?.action.label : retryLabel) }}
    </ScButton>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { contractGapError } from '../app/contract/contractGap';
import type { ContractConsumerDefectRef } from '../app/contract/contractGap';
import { useSessionStore } from '../stores/session';
import { useSuggestedAction } from '../composables/useSuggestedAction';
import { isHudEnabled } from '../config/debug';
import { resolveProductErrorState } from '../app/productErrorState';
import ScButton from './design-system/ScButton.vue';

const props = defineProps<{
  title: string;
  message?: string;
  traceId?: string;
  errorCode?: number | string | null;
  reasonCode?: string;
  errorCategory?: string;
  errorDetails?: Record<string, unknown>;
  contractDefect?: ContractConsumerDefectRef | null;
  retryable?: boolean;
  hint?: string;
  suggestedAction?: string;
  variant?: 'error' | 'info' | 'forbidden_capability';
  onRetry?: () => void;
  onSuggestedAction?: (action: string) => boolean | void;
  hideTitle?: boolean;
  retryLabel?: string;
  busy?: boolean;
}>();
const emit = defineEmits<{
  (event: 'action-executed', payload: { action: string; success: boolean }): void;
}>();
const actionRunFeedback = ref('');
const retrying = ref(false);
const route = useRoute();
const router = useRouter();
const session = useSessionStore();

watch(
  () => [props.suggestedAction, props.message, props.reasonCode, props.traceId],
  () => {
    actionRunFeedback.value = '';
  },
);

const suggestedActionRuntime = useSuggestedAction(
  () => props.suggestedAction,
  computed(() => ({
    hasRetryHandler: typeof props.onRetry === 'function',
    hasActionHandler: typeof props.onSuggestedAction === 'function',
    traceId: props.traceId,
    reasonCode: props.reasonCode,
    message: props.message,
  })),
);

const canRunSuggestedAction = computed(() => suggestedActionRuntime.canRun.value);
const suggestedActionLabel = computed(() => suggestedActionRuntime.label.value);
const showHudMeta = computed(() => isHudEnabled(route));
const errorModel = computed(() => String(props.errorDetails?.model || '').trim());
const errorOp = computed(() => String(props.errorDetails?.op || '').trim().toLowerCase());
const stateResolution = computed(() => {
  if (props.variant !== 'error') return { state: null, gap: false };
  if (props.contractDefect) return { state: null, gap: props.contractDefect.missing };
  try {
    const state = resolveProductErrorState({ status: props.errorCode, reasonCode: props.reasonCode }, session.errorStateContract);
    if (state.action.kind === 'retry' && !props.onRetry) throw contractGapError({ kind: 'contract_defect', missing: 'error_states.action.retry.executor', requiredDeclarationLayer: 'P0:frontend:StatusPanel consumer' }, 'ContractGapError: error_states.action.retry.executor');
    return { state, gap: false };
  }
  catch (error) {
    if ((error as Error).name !== 'ContractGapError') throw error;
    return { state: null, gap: (error as { defect?: { missing?: string } }).defect?.missing || 'page_contracts.error_states' };
  }
});
const productState = computed(() => stateResolution.value.state);
const contractGapTitle = computed(() => {
  if (props.contractDefect?.kind === 'frontend_capability_gap') return '前端渲染能力缺失';
  const failureClass = props.contractDefect?.failureClass || 'contract_missing';
  if (failureClass === 'contract_mismatch') return '生产契约与平台解码规则不一致';
  if (failureClass === 'consumer_error') return '前端实现异常已停机';
  return '业务契约声明缺失';
});
const contractGapStopMessage = computed(() => (
  props.contractDefect?.kind === 'frontend_capability_gap'
    ? '契约语义合法，但当前前端没有可用实现，系统已停止继续操作。'
    : props.contractDefect?.failureClass === 'consumer_error'
    ? '系统已停止继续操作，以避免在错误的前端实现状态下执行业务。'
    : '系统已停止继续操作，以避免在不完整或错误的契约上执行业务。'
));
const contractGapErrorType = computed(() => (
  contractConsumerContext.value?.errorName
    || (props.contractDefect?.kind === 'frontend_capability_gap' ? 'FrontendCapabilityGapError' : 'ContractGapError')
));
const contractGapLocationLabel = computed(() => (
  props.contractDefect?.kind === 'frontend_capability_gap'
    ? '缺失能力'
    : contractConsumerContext.value ? '失败位置' : '契约路径'
));
const contractGapFailureLabel = computed(() => {
  if (props.contractDefect?.kind === 'frontend_capability_gap') {
    return 'frontend_capability_gap（前端实现注册表缺失）';
  }
  const failureClass = props.contractDefect?.failureClass || 'contract_missing';
  if (failureClass === 'contract_mismatch') return 'contract_mismatch（等待 P0 契约/解码裁定）';
  if (failureClass === 'consumer_error') return 'consumer_error（前端实现错误）';
  return 'contract_missing（声明层缺失）';
});
const consumerComponentTraceText = computed(() => (
  (contractConsumerContext.value?.componentTrace || []).join(' > ')
));
const contractConsumerContext = computed(() => (
  props.contractDefect?.kind === 'contract_defect' ? props.contractDefect.consumerContext : undefined
));
const contractDefectOwnerLayer = computed(() => (
  props.contractDefect?.kind === 'frontend_capability_gap'
    ? props.contractDefect.requiredImplementationLayer
    : props.contractDefect?.requiredDeclarationLayer
));
const displayTitle = computed(() => props.variant === 'error' ? productState.value?.title : props.title);
const displayMessage = computed(() => props.variant === 'error' ? productState.value?.message : props.message);

function runSuggestedAction() {
  const ran = suggestedActionRuntime.run({
    onRetry: props.onRetry,
    onSuggestedAction: props.onSuggestedAction,
    traceId: props.traceId,
    reasonCode: props.reasonCode,
    message: props.message,
    onExecuted: (result) => {
      actionRunFeedback.value = result.success ? '恢复操作已执行。' : '当前无法执行恢复操作。';
      emit('action-executed', { action: result.raw || result.kind, success: result.success });
    },
  });
  if (!ran && !actionRunFeedback.value) {
    actionRunFeedback.value = '当前状态无法执行此恢复操作。';
  }
}

async function retry() {
  if (retrying.value || props.busy) return;
  retrying.value = true;
  try {
    const action = productState.value?.action;
    if (props.variant === 'error' && action?.kind === 'route') await router.push(action.path!);
    else if (props.onRetry) await props.onRetry();
  } finally { retrying.value = false; }
}

function copyTrace() {
  if (!props.traceId) {
    return;
  }
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(props.traceId).catch(() => {});
  }
}
</script>

<style scoped>
.panel {
  padding: 24px;
  border-radius: var(--sc-product-radius-panel);
  background: var(--sc-app-muted-bg);
  border: 1px solid var(--sc-app-border);
  color: var(--sc-app-text-primary);
  display: grid;
  gap: 8px;
}

.panel.error {
  border-color: var(--sc-app-danger-border);
  background: var(--sc-app-danger-bg);
}

.panel.forbidden_capability {
  border-color: var(--sc-app-warning-border);
  background: var(--sc-app-warning-bg);
}

.error-meta {
  display: grid;
  gap: 4px;
}

.trace {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}

.panel > :deep(button) { justify-self: start; }

.trace-copy {
  justify-self: start;
}

.action-feedback {
  color: var(--sc-app-text-primary);
}

.state-skeleton { display: grid; gap: var(--sc-product-space-1); width: min(520px, 100%); }
.state-skeleton span { display: block; height: 12px; border-radius: var(--sc-product-radius-control); background: var(--sc-app-border); animation: state-pulse 1.2s ease-in-out infinite alternate; }
.state-skeleton span:nth-child(2) { width: 82%; }
.state-skeleton span:nth-child(3) { width: 64%; }
@keyframes state-pulse { to { opacity: .45; } }
@media (prefers-reduced-motion: reduce) { .state-skeleton span { animation: none; } }
</style>
