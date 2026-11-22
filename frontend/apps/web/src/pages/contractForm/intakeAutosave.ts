import {
  contractGapError,
  requireDeclaredBoolean,
  requireDeclaredNumber,
  requireDeclaredText,
} from '../../app/contract/contractGap';

type Dict = Record<string, unknown>;

export type IntakeAutosaveInputKind =
  | 'text'
  | 'integer'
  | 'decimal'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'selection'
  | 'relation';

export type IntakeAutosaveIdentityScope =
  | 'tenant'
  | 'user'
  | 'company'
  | 'menu'
  | 'action'
  | 'form_view'
  | 'entry_scope'
  | 'form_instance';

export type IntakeAutosaveIdentity = Partial<Record<IntakeAutosaveIdentityScope, string | number>>;

export type IntakeAutosaveField = {
  name: string;
  label: string;
  type: string;
  relation: string;
  inputKind: IntakeAutosaveInputKind;
  required: boolean;
  readonly: false;
  allowEmpty: true;
  source: 'effective_create_form';
  constraints: Dict;
};

export type IntakeAutosavePolicy = {
  schemaVersion: 'intake_autosave_policy.v1';
  policyVersion: number;
  enabled: true;
  appliesTo: ['create'];
  scope: string;
  storage: {
    kind: 'browser_local_storage';
    keyPrefix: string;
    payloadVersion: number;
  };
  retention: {
    seconds: number;
    basis: 'last_valid_input';
  };
  recovery: {
    strategy: 'prompt_restore_or_discard';
    actions: ['restore', 'discard'];
  };
  identity: {
    requiredScopes: IntakeAutosaveIdentityScope[];
  };
  fields: IntakeAutosaveField[];
  coverage: {
    fields: true;
    attachments: false;
    binary: false;
    unsavedChildRecords: false;
    workflowState: false;
    serverDefaults: false;
  };
};

export type IntakeAutosaveCandidate = {
  key: string;
  draftToken: string;
  savedAt: number;
  values: Record<string, unknown>;
  fields: IntakeAutosaveField[];
  policy: IntakeAutosavePolicy;
};

export type IntakeAutosaveReadResult =
  | { status: 'none' | 'unavailable' | 'expired' | 'invalid'; message?: string }
  | { status: 'recoverable'; candidate: IntakeAutosaveCandidate };

export type IntakeAutosavePersistResult = 'saved' | 'skipped' | 'unavailable' | 'failed';

const POLICY_PATH = 'runtimeContract.intakeAutosave';
const POLICY_LAYER = 'P1:smart_construction_core:project intake autosave policy';
const INPUT_KINDS = new Set<IntakeAutosaveInputKind>([
  'text', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'selection', 'relation',
]);
const IDENTITY_SCOPES = new Set<IntakeAutosaveIdentityScope>([
  'tenant', 'user', 'company', 'menu', 'action', 'form_view', 'entry_scope', 'form_instance',
]);

function dictionary(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Dict : {};
}

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function gap(missing: string, message: string): never {
  throw contractGapError(
    { kind: 'contract_defect', missing, requiredDeclarationLayer: POLICY_LAYER },
    message,
  );
}

function declaredBoolean(value: unknown, missing: string): boolean {
  return requireDeclaredBoolean(value, { missing, requiredDeclarationLayer: POLICY_LAYER });
}

function declaredNumber(value: unknown, missing: string): number {
  return requireDeclaredNumber(value, { missing, requiredDeclarationLayer: POLICY_LAYER });
}

function declaredText(value: unknown, missing: string): string {
  return requireDeclaredText(value, { missing, requiredDeclarationLayer: POLICY_LAYER });
}

export function resolveIntakeAutosavePolicy(runtimeContract: unknown): IntakeAutosavePolicy | null {
  const raw = dictionary(dictionary(runtimeContract).intakeAutosave);
  if (!Object.keys(raw).length) return null;
  if (!declaredBoolean(raw.enabled, `${POLICY_PATH}.enabled`)) return null;
  const schemaVersion = declaredText(raw.schemaVersion, `${POLICY_PATH}.schemaVersion`);
  if (schemaVersion !== 'intake_autosave_policy.v1') {
    gap(`${POLICY_PATH}.schemaVersion`, '项目立项本地草稿策略版本不受支持');
  }
  const appliesTo = array(raw.appliesTo);
  if (appliesTo.length !== 1 || appliesTo[0] !== 'create') {
    gap(`${POLICY_PATH}.appliesTo`, '项目立项本地草稿只能声明用于新建输入');
  }
  const storage = dictionary(raw.storage);
  if (declaredText(storage.kind, `${POLICY_PATH}.storage.kind`) !== 'browser_local_storage') {
    gap(`${POLICY_PATH}.storage.kind`, '前端不支持契约声明的本地草稿存储方式');
  }
  const retention = dictionary(raw.retention);
  if (declaredText(retention.basis, `${POLICY_PATH}.retention.basis`) !== 'last_valid_input') {
    gap(`${POLICY_PATH}.retention.basis`, '项目立项本地草稿保留期限基准不受支持');
  }
  const recovery = dictionary(raw.recovery);
  const recoveryActions = array(recovery.actions).map(String);
  if (declaredText(recovery.strategy, `${POLICY_PATH}.recovery.strategy`) !== 'prompt_restore_or_discard'
      || recoveryActions.length !== 2
      || !recoveryActions.includes('restore')
      || !recoveryActions.includes('discard')) {
    gap(`${POLICY_PATH}.recovery`, '项目立项本地草稿恢复策略声明不完整');
  }
  const requiredScopes = array(dictionary(raw.identity).requiredScopes).map(String);
  if (!requiredScopes.length
      || requiredScopes.some((scope) => !IDENTITY_SCOPES.has(scope as IntakeAutosaveIdentityScope))) {
    gap(`${POLICY_PATH}.identity.requiredScopes`, '项目立项本地草稿身份作用域声明不完整');
  }
  const fields = array(raw.fields).map((value, index): IntakeAutosaveField => {
    const row = dictionary(value);
    const name = declaredText(row.name, `${POLICY_PATH}.fields[${index}].name`);
    const inputKind = declaredText(row.inputKind, `${POLICY_PATH}.fields[${index}].inputKind`);
    if (!INPUT_KINDS.has(inputKind as IntakeAutosaveInputKind)) {
      gap(`${POLICY_PATH}.fields[${index}].inputKind`, `字段 ${name} 的本地草稿输入类型不受支持`);
    }
    if (row.readonly !== false || row.allowEmpty !== true) {
      gap(`${POLICY_PATH}.fields[${index}]`, `字段 ${name} 的本地草稿许可声明不完整`);
    }
    if (row.source !== 'effective_create_form') {
      gap(`${POLICY_PATH}.fields[${index}].source`, `字段 ${name} 不是有效创建表单声明`);
    }
    const type = declaredText(row.type, `${POLICY_PATH}.fields[${index}].type`);
    if (type === 'one2many') {
      gap(`${POLICY_PATH}.fields[${index}].type`, '尚未创建的子记录命令不能进入本地草稿');
    }
    return {
      name,
      label: declaredText(row.label, `${POLICY_PATH}.fields[${index}].label`),
      type,
      relation: String(row.relation || '').trim(),
      inputKind: inputKind as IntakeAutosaveInputKind,
      required: declaredBoolean(row.required, `${POLICY_PATH}.fields[${index}].required`),
      readonly: false,
      allowEmpty: true,
      source: 'effective_create_form',
      constraints: dictionary(row.constraints),
    };
  });
  if (!fields.length || new Set(fields.map((field) => field.name)).size !== fields.length) {
    gap(`${POLICY_PATH}.fields`, '项目立项本地草稿允许字段为空或重复');
  }
  const coverage = dictionary(raw.coverage);
  if (coverage.fields !== true
      || ['attachments', 'binary', 'unsavedChildRecords', 'workflowState', 'serverDefaults']
        .some((key) => coverage[key] !== false)) {
    gap(`${POLICY_PATH}.coverage`, '项目立项本地草稿覆盖范围声明不合法');
  }
  return {
    schemaVersion: 'intake_autosave_policy.v1',
    policyVersion: declaredNumber(raw.policyVersion, `${POLICY_PATH}.policyVersion`),
    enabled: true,
    appliesTo: ['create'],
    scope: declaredText(raw.scope, `${POLICY_PATH}.scope`),
    storage: {
      kind: 'browser_local_storage',
      keyPrefix: declaredText(storage.keyPrefix, `${POLICY_PATH}.storage.keyPrefix`),
      payloadVersion: declaredNumber(storage.payloadVersion, `${POLICY_PATH}.storage.payloadVersion`),
    },
    retention: {
      seconds: declaredNumber(retention.seconds, `${POLICY_PATH}.retention.seconds`),
      basis: 'last_valid_input',
    },
    recovery: {
      strategy: 'prompt_restore_or_discard',
      actions: ['restore', 'discard'],
    },
    identity: {
      requiredScopes: requiredScopes as IntakeAutosaveIdentityScope[],
    },
    fields,
    coverage: {
      fields: true,
      attachments: false,
      binary: false,
      unsavedChildRecords: false,
      workflowState: false,
      serverDefaults: false,
    },
  };
}

export function buildIntakeAutosaveKey(
  policy: IntakeAutosavePolicy,
  identity: IntakeAutosaveIdentity,
): string {
  const resolved = policy.identity.requiredScopes.map((scope) => [
    scope,
    scope === 'entry_scope' ? policy.scope : identity[scope],
  ] as const);
  if (resolved.some(([, value]) => String(value ?? '').trim() === '')) return '';
  return [
    policy.storage.keyPrefix,
    `schema=${encodeURIComponent(policy.schemaVersion)}`,
    `policy=${policy.policyVersion}`,
    `payload=${policy.storage.payloadVersion}`,
    ...resolved.map(([scope, value]) => `${scope}=${encodeURIComponent(String(value).trim())}`),
  ].join(':');
}

export function intakeAutosaveCoverageText(policy: IntakeAutosavePolicy): string {
  const labels = policy.fields.map((field) => field.label).join('、');
  const seconds = policy.retention.seconds;
  const retention = seconds % 3600 === 0
    ? `${seconds / 3600} 小时`
    : seconds % 60 === 0
      ? `${seconds / 60} 分钟`
      : `${seconds} 秒`;
  return `仅暂存本机允许字段：${labels}；不含附件、明细和流程状态，保留 ${retention}。`;
}

function storage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function normalizedStoredValue(field: IntakeAutosaveField, value: unknown): { accepted: boolean; value?: unknown } {
  if (value === undefined || value === null) return { accepted: false };
  if (field.inputKind === 'text') {
    const maxLength = Number(field.constraints.maxLength || 0);
    return typeof value === 'string'
      && (!(maxLength > 0) || value.length <= maxLength)
      ? { accepted: true, value } : { accepted: false };
  }
  if (field.inputKind === 'date') {
    return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? { accepted: true, value } : { accepted: false };
  }
  if (field.inputKind === 'datetime') {
    return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value)
      ? { accepted: true, value } : { accepted: false };
  }
  if (field.inputKind === 'boolean') {
    return typeof value === 'boolean' ? { accepted: true, value } : { accepted: false };
  }
  if (field.inputKind === 'integer') {
    return typeof value === 'number' && Number.isSafeInteger(value)
      ? { accepted: true, value } : { accepted: false };
  }
  if (field.inputKind === 'decimal') {
    return typeof value === 'number' && Number.isFinite(value)
      ? { accepted: true, value } : { accepted: false };
  }
  if (field.inputKind === 'selection') {
    const allowedValues = Array.isArray(field.constraints.allowedValues)
      ? field.constraints.allowedValues : [];
    return ['string', 'number', 'boolean'].includes(typeof value)
      && (!allowedValues.length || allowedValues.some((allowed) => Object.is(allowed, value)))
      ? { accepted: true, value } : { accepted: false };
  }
  if (field.type === 'many2many') {
    return Array.isArray(value)
      && value.every((item) => typeof item === 'number' && Number.isSafeInteger(item) && item > 0)
      ? { accepted: true, value: [...new Set(value as number[])] }
      : { accepted: false };
  }
  return value === false
    || (typeof value === 'number' && Number.isSafeInteger(value) && value > 0)
    ? { accepted: true, value } : { accepted: false };
}

export function persistIntakeAutosavePayload(options: {
  policy: IntakeAutosavePolicy;
  key: string;
  identity: IntakeAutosaveIdentity;
  draftToken: string;
  values: Record<string, unknown>;
  now?: number;
}): IntakeAutosavePersistResult {
  if (!options.key) return 'unavailable';
  const target = storage();
  if (!target) return 'unavailable';
  const values: Record<string, unknown> = {};
  for (const field of options.policy.fields) {
    if (!Object.prototype.hasOwnProperty.call(options.values, field.name)) continue;
    const normalized = normalizedStoredValue(field, options.values[field.name]);
    if (normalized.accepted) values[field.name] = normalized.value;
  }
  if (!Object.keys(values).length) return 'skipped';
  const identity = Object.fromEntries(options.policy.identity.requiredScopes.map((scope) => [
    scope,
    scope === 'entry_scope' ? options.policy.scope : String(options.identity[scope] ?? ''),
  ]));
  try {
    target.setItem(options.key, JSON.stringify({
      schema_version: options.policy.schemaVersion,
      policy_version: options.policy.policyVersion,
      payload_version: options.policy.storage.payloadVersion,
      scope: options.policy.scope,
      identity,
      draft_token: options.draftToken,
      saved_at: options.now ?? Date.now(),
      values,
    }));
    return 'saved';
  } catch {
    return 'failed';
  }
}

export function restoreIntakeAutosavePayload(options: {
  policy: IntakeAutosavePolicy;
  key: string;
  identity: IntakeAutosaveIdentity;
  now?: number;
}): IntakeAutosaveReadResult {
  if (!options.key) return { status: 'unavailable' };
  const target = storage();
  if (!target) return { status: 'unavailable' };
  let raw = '';
  try {
    raw = target.getItem(options.key) || '';
  } catch {
    return { status: 'unavailable' };
  }
  if (!raw) return { status: 'none' };
  let payload: Dict;
  try {
    payload = dictionary(JSON.parse(raw));
  } catch {
    return { status: 'invalid', message: '本机暂存内容已损坏，不能恢复。' };
  }
  if (payload.schema_version !== options.policy.schemaVersion
      || payload.policy_version !== options.policy.policyVersion
      || payload.payload_version !== options.policy.storage.payloadVersion
      || payload.scope !== options.policy.scope) {
    return { status: 'invalid', message: '本机暂存来自不兼容的输入策略，不能恢复。' };
  }
  const savedAt = Number(payload.saved_at || 0);
  if (!Number.isFinite(savedAt) || savedAt <= 0) {
    return { status: 'invalid', message: '本机暂存时间无效，不能恢复。' };
  }
  if ((options.now ?? Date.now()) - savedAt > options.policy.retention.seconds * 1000) {
    return { status: 'expired', message: '本机暂存已超过策略允许的恢复期限。' };
  }
  const identity = dictionary(payload.identity);
  const expectedIdentity = Object.fromEntries(options.policy.identity.requiredScopes.map((scope) => [
    scope,
    scope === 'entry_scope' ? options.policy.scope : String(options.identity[scope] ?? ''),
  ]));
  if (JSON.stringify(identity) !== JSON.stringify(expectedIdentity)) {
    return { status: 'invalid', message: '本机暂存不属于当前用户、公司或表单实例。' };
  }
  const draftToken = String(payload.draft_token || '').trim();
  if (!draftToken) {
    return { status: 'invalid', message: '本机暂存缺少草稿版本身份，不能恢复。' };
  }
  const sourceValues = dictionary(payload.values);
  const values: Record<string, unknown> = {};
  for (const field of options.policy.fields) {
    if (!Object.prototype.hasOwnProperty.call(sourceValues, field.name)) continue;
    const normalized = normalizedStoredValue(field, sourceValues[field.name]);
    if (normalized.accepted) values[field.name] = normalized.value;
  }
  return {
    status: 'recoverable',
    candidate: {
      key: options.key,
      draftToken,
      savedAt,
      values,
      fields: options.policy.fields,
      policy: options.policy,
    },
  };
}

export function clearIntakeAutosavePayload(
  key: string,
  expected?: { policyVersion: number; scope: string; draftToken?: string },
): boolean {
  if (!key) return true;
  if (expected && (
    !key.includes(`:policy=${expected.policyVersion}:`)
    || !key.includes(`:entry_scope=${encodeURIComponent(expected.scope)}`)
  )) {
    return false;
  }
  const target = storage();
  if (!target) return false;
  try {
    if (expected?.draftToken) {
      const raw = target.getItem(key);
      if (!raw) return true;
      const payload = dictionary(JSON.parse(raw));
      if (String(payload.draft_token || '') !== expected.draftToken) return false;
    }
    target.removeItem(key);
    return true;
  } catch {
    return false;
  }
}
