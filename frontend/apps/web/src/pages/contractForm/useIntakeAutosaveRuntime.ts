import { computed, ref, type Ref } from 'vue';
import {
  buildIntakeAutosaveKey,
  clearIntakeAutosavePayload,
  intakeAutosaveCoverageText,
  persistIntakeAutosavePayload,
  restoreIntakeAutosavePayload,
  type IntakeAutosaveCandidate,
  type IntakeAutosaveIdentity,
  type IntakeAutosavePolicy,
} from './intakeAutosave';

export type IntakeAutosaveNotice = {
  kind: 'info' | 'success' | 'warn' | 'error';
  message: string;
};

export type IntakeAutosaveCapture = {
  key: string;
  policyVersion: number;
  scope: string;
  draftToken: string;
};

export function useIntakeAutosaveRuntime(options: {
  policy: Ref<IntakeAutosavePolicy | null>;
  identity: Ref<IntakeAutosaveIdentity>;
  hasRecord: Ref<unknown>;
  formData: Record<string, unknown>;
  isActive: Ref<boolean>;
  isDirty: Ref<boolean>;
  paused: Ref<boolean>;
  applyRestoredValues: (candidate: IntakeAutosaveCandidate) => Promise<void> | void;
  onNotice: (notice: IntakeAutosaveNotice | null) => void;
}) {
  const candidate = ref<IntakeAutosaveCandidate | null>(null);
  let lastSavedSignature = '';
  let lastSavedToken = '';
  let draftSequence = 0;

  const key = computed(() => options.policy.value
    ? buildIntakeAutosaveKey(options.policy.value, options.identity.value)
    : '');
  const coverageText = computed(() => options.policy.value
    ? intakeAutosaveCoverageText(options.policy.value)
    : '');

  const capture = (): IntakeAutosaveCapture | null => {
    if (!options.policy.value || !key.value) return null;
    if (options.isDirty.value && !options.paused.value && !candidate.value) persist();
    return {
      key: key.value,
      policyVersion: options.policy.value.policyVersion,
      scope: options.policy.value.scope,
      draftToken: lastSavedToken,
    };
  };

  const inspect = () => {
    candidate.value = null;
    options.onNotice(null);
    options.paused.value = true;
    const policy = options.policy.value;
    if (!policy || options.hasRecord.value) {
      options.paused.value = false;
      return 'none' as const;
    }
    if (!key.value) {
      options.onNotice({ kind: 'error', message: '本机暂存不可用：表单身份尚未就绪。' });
      return 'unavailable' as const;
    }
    const result = restoreIntakeAutosavePayload({
      policy,
      key: key.value,
      identity: options.identity.value,
    });
    if (result.status === 'recoverable') {
      candidate.value = result.candidate;
      // A successful create while the prompt is still visible must retire the
      // exact draft that produced the prompt, even if the user did not restore.
      lastSavedToken = result.candidate.draftToken;
      options.onNotice({ kind: 'info', message: `发现可恢复的新建输入。${coverageText.value}` });
      return result.status;
    }
    if (result.status === 'expired' || result.status === 'invalid') {
      clearIntakeAutosavePayload(key.value);
      options.onNotice({
        kind: 'warn',
        message: result.message || (result.status === 'expired' ? '本机暂存已过期。' : '本机暂存不可恢复。'),
      });
    } else if (result.status === 'unavailable') {
      options.onNotice({ kind: 'error', message: '本机暂存不可用，当前输入仍可正常手动创建。' });
      return result.status;
    }
    options.paused.value = false;
    return result.status;
  };

  const restore = async () => {
    const selected = candidate.value;
    if (!selected) return false;
    await options.applyRestoredValues(selected);
    candidate.value = null;
    lastSavedSignature = JSON.stringify(Object.fromEntries(
      selected.fields.map((field) => [field.name, options.formData[field.name]]),
    ));
    lastSavedToken = selected.draftToken;
    options.paused.value = false;
    options.onNotice({ kind: 'success', message: `已恢复本机暂存的新建输入。${coverageText.value}` });
    return true;
  };

  const discard = () => {
    const hadCandidate = Boolean(candidate.value);
    const expected = capture();
    if (key.value) clearIntakeAutosavePayload(key.value, expected || undefined);
    candidate.value = null;
    lastSavedSignature = '';
    lastSavedToken = '';
    options.paused.value = false;
    if (hadCandidate) options.onNotice({ kind: 'info', message: '已丢弃本机暂存的新建输入。' });
  };

  const persist = () => {
    const policy = options.policy.value;
    if (!policy || !options.isActive.value || options.hasRecord.value || options.paused.value
        || candidate.value || !options.isDirty.value || !key.value) {
      return;
    }
    const signature = JSON.stringify(policy.fields.map((field) => [field.name, options.formData[field.name]]));
    if (signature === lastSavedSignature) return;
    draftSequence += 1;
    const draftToken = `${Date.now()}:${draftSequence}`;
    const result = persistIntakeAutosavePayload({
      policy,
      key: key.value,
      identity: options.identity.value,
      draftToken,
      values: options.formData,
    });
    if (result === 'saved') {
      lastSavedSignature = signature;
      lastSavedToken = draftToken;
      options.onNotice({ kind: 'success', message: `已在本机暂存允许恢复的输入。${coverageText.value}` });
    } else if (result === 'failed' || result === 'unavailable') {
      options.onNotice({ kind: 'error', message: '本机暂存失败；当前输入仍保留，可继续手动创建。' });
    }
  };

  const clear = (expected: IntakeAutosaveCapture | null = capture()) => {
    if (!expected) return false;
    if (!expected.draftToken) return true;
    const currentKey = key.value;
    const cleared = clearIntakeAutosavePayload(expected.key, expected);
    if (cleared && currentKey === expected.key) {
      candidate.value = null;
      lastSavedSignature = '';
      lastSavedToken = '';
      options.paused.value = true;
    }
    return cleared;
  };

  return {
    key,
    coverageText,
    candidate,
    capture,
    inspect,
    restore,
    discard,
    persist,
    clear,
  };
}
