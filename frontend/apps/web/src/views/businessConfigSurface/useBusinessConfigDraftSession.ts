import { computed, ref, watch } from 'vue';
import {
  discardBusinessConfigChangeSet,
  openBusinessConfigChangeSet,
  resumeBusinessConfigChangeSet,
  previewBusinessConfigChangeSet,
  publishBusinessConfigChangeSet,
  rollbackBusinessConfigChangeSet,
  stageBusinessConfigChangeSetItem,
  validateBusinessConfigChangeSet,
  type BusinessConfigChangeSet,
  type StageBusinessConfigChangeSetItemParams,
} from '../../api/businessConfig';

function requestId(prefix: string) {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function publishFailureMessage(changeSet: BusinessConfigChangeSet) {
  const firstError = changeSet.items
    .flatMap((item) => item.validation_result?.errors || [])
    .find((message) => String(message || '').trim());
  return String(firstError || changeSet.failure_message || '变更集校验未通过，请修正后重试');
}

function requestFailureMessage(cause: unknown) {
  return cause instanceof Error && cause.message.trim() ? cause.message : '待发布变更读取失败，请重试。';
}

export function useBusinessConfigDraftSession(roleKey: () => string, targetScope?: () => { model: string; actionId?: number; companyId?: number }) {
  const changeSet = ref<BusinessConfigChangeSet | null>(null);
  const loading = ref(false);
  const publishing = ref(false);
  const previewing = ref(false);
  const error = ref('');
  const busy = ref(false);

  const changeSetToken = computed(() => changeSet.value?.token || '');
  const changeSetItemCount = computed(() => Number(changeSet.value?.item_count || 0));
  const hasUnifiedDraft = computed(() => changeSetItemCount.value > 0 && !['published', 'discarded', 'superseded'].includes(changeSet.value?.state || ''));

  let scopeRequest = 0;
  const scopeIdentity = () => JSON.stringify([roleKey(), targetScope?.()]);
  type Operation = { epoch: number; identity: string; role: string; target: ReturnType<typeof scopeParams> };
  function assertCurrent(op: Operation) {
    if (op.epoch !== scopeRequest || op.identity !== scopeIdentity()) throw new Error('配置对象已变化，已停止原对象操作；请检查当前草稿。');
  }
  async function operate<T>(task: (op: Operation) => Promise<T>, flag?: typeof busy): Promise<T> {
    if (busy.value) throw new Error('配置操作正在进行，请等待完成。');
    const op = { epoch: scopeRequest, identity: scopeIdentity(), role: roleKey(), target: scopeParams() };
    busy.value = true; if (flag) flag.value = true; error.value = '';
    try { return await task(op); }
    catch (cause) { if (op.epoch === scopeRequest && op.identity === scopeIdentity()) error.value = requestFailureMessage(cause); throw cause; }
    finally { busy.value = false; if (flag) flag.value = false; }
  }
  function accept(op: Operation, result: BusinessConfigChangeSet) { assertCurrent(op); changeSet.value = result; return result; }

  const scopeParams = () => ({ target_model: targetScope?.().model || undefined, target_action_id: targetScope?.().actionId });
  async function resumeScope() {
    const request = ++scopeRequest;
    changeSet.value = null; error.value = ''; loading.value = false;
    if (!targetScope?.().model || !targetScope?.().actionId) return;
    loading.value = true;
    try {
      const result = await resumeBusinessConfigChangeSet({ role_key: roleKey(), ...scopeParams() });
      if (request === scopeRequest && 'token' in result) changeSet.value = result;
    } catch (cause) { if (request === scopeRequest) error.value = requestFailureMessage(cause); }
    finally { if (request === scopeRequest) loading.value = false; }
  }
  if (targetScope) watch(() => [roleKey(), targetScope().model, targetScope().actionId, targetScope().companyId], () => void resumeScope(), { immediate: true, flush: 'sync' });

  async function ensureFor(op: Operation) {
    assertCurrent(op);
    if (changeSet.value && !['published', 'discarded', 'superseded'].includes(changeSet.value.state)) return changeSet.value;
    return accept(op, await openBusinessConfigChangeSet({ role_key: op.role || undefined, ...op.target }));
  }
  async function validateFor(op: Operation) {
    const current = await ensureFor(op); assertCurrent(op);
    return accept(op, await validateBusinessConfigChangeSet({ change_set_token: current.token, role_key: op.role || undefined }));
  }
  const ensureChangeSet = () => operate(ensureFor);
  const validateDraft = () => operate(validateFor);
  async function stageItem(params: Omit<StageBusinessConfigChangeSetItemParams, 'change_set_token'>) {
    return operate(async (op) => {
      const current = await ensureFor(op); assertCurrent(op);
      return accept(op, await stageBusinessConfigChangeSetItem({ ...params, change_set_token: current.token }));
    });
  }
  async function previewDraft(device = 'desktop') {
    return operate(async (op) => {
      const current = await ensureFor(op); assertCurrent(op);
      return accept(op, await previewBusinessConfigChangeSet({ change_set_token: current.token, role_key: op.role || undefined, device }));
    }, previewing);
  }
  async function publishDraft() {
    return operate(async (op) => {
      const validated = await validateFor(op); assertCurrent(op);
      if (validated.state !== 'ready') throw new Error(publishFailureMessage(validated));
      const published = accept(op, await publishBusinessConfigChangeSet({
        change_set_token: validated.token, role_key: op.role || undefined, request_id: requestId('publish'),
      }));
      const publishResult = published.publish_result || {};
      if (published.state !== 'published' || publishResult.ok !== true || publishResult.published_content_verified !== true) {
        throw new Error(published.failure_message || '发布内容回读未通过');
      }
      return published;
    }, publishing);
  }
  async function rollbackPublished() {
    return operate(async (op) => {
      const current = changeSet.value; if (!current) return null;
      return accept(op, await rollbackBusinessConfigChangeSet({ change_set_token: current.token, role_key: op.role || undefined, request_id: requestId('rollback') }));
    });
  }
  async function discardDraft() {
    return operate(async (op) => {
      const current = changeSet.value; if (!current) return null;
      return accept(op, await discardBusinessConfigChangeSet({ change_set_token: current.token, role_key: op.role || undefined }));
    });
  }

  function resetScope() {
    scopeRequest += 1;
    changeSet.value = null;
    error.value = '';
  }

  return {
    changeSet,
    changeSetToken,
    changeSetItemCount,
    hasUnifiedDraft,
    loading,
    busy,
    publishing,
    previewing,
    error,
    ensureChangeSet,
    resumeScope,
    stageItem,
    validateDraft,
    previewDraft,
    publishDraft,
    rollbackPublished,
    discardDraft,
    resetScope,
  };
}
