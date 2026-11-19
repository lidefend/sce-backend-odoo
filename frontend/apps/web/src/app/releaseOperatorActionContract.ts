import { contractGapError } from './contract/contractGap';

type AnyRecord = Record<string, unknown>;

export interface OperatorActionScope {
  kind: string;
  scope_key: string;
  product_key: string;
  company_ids: number[];
  target_role_codes: string[];
  is_global_product_release: boolean;
  meaning: string;
}

export interface OperatorAction {
  key: string;
  label: string;
  intent: string;
  enabled: boolean;
  reason_code: string;
  params: AnyRecord;
  actor: {
    user_id: number;
    login: string;
    name: string;
    operator_kind: string;
    roles: string[];
  };
  target_scope: OperatorActionScope;
  operation_object: {
    kind: string;
    product_key: string;
    snapshot_id: number;
  };
  prerequisites: {
    satisfied: boolean;
    reason_code: string;
    confirmation_required: boolean;
  };
  readback: {
    source: string;
    mode: string;
    fields: string[];
  };
}

function gap(path: string, message: string): never {
  throw contractGapError({
    kind: 'contract_defect',
    missing: path,
    requiredDeclarationLayer: 'P0:smart_core:release.operator.surface',
  }, message);
}

function record(value: unknown, path: string): AnyRecord {
  if (!value || typeof value !== 'object' || Array.isArray(value)) gap(path, `${path} 缺失`);
  return value as AnyRecord;
}

function text(value: unknown, path: string): string {
  const result = String(value || '').trim();
  if (!result) gap(path, `${path} 缺失`);
  return result;
}

function positiveInt(value: unknown, path: string): number {
  const result = Number(value);
  if (!Number.isInteger(result) || result <= 0) gap(path, `${path} 非法`);
  return result;
}

function boolean(value: unknown, path: string): boolean {
  if (typeof value !== 'boolean') gap(path, `${path} 必须是布尔值`);
  return value;
}

export function decodePromotionAction(value: unknown, expectedProductKey: string): OperatorAction {
  const action = record(value, 'available_actions.promote[]');
  const key = text(action.key, 'available_actions.promote[].key');
  const intent = text(action.intent, 'available_actions.promote[].intent');
  if (intent !== 'release.operator.promote') {
    gap('available_actions.promote[].intent', '候选发布动作意图不匹配');
  }
  const enabled = boolean(action.enabled, `${key}.enabled`);
  const params = record(action.params, `${key}.params`);
  const actor = record(action.actor, `${key}.actor`);
  const target = record(action.target_scope, `${key}.target_scope`);
  const operation = record(action.operation_object, `${key}.operation_object`);
  const prerequisites = record(action.prerequisites, `${key}.prerequisites`);
  const readback = record(action.readback, `${key}.readback`);
  const snapshotId = positiveInt(params.snapshot_id, `${key}.params.snapshot_id`);
  const productKey = text(params.product_key, `${key}.params.product_key`);
  const operationSnapshotId = positiveInt(
    operation.snapshot_id,
    `${key}.operation_object.snapshot_id`,
  );
  const operationProductKey = text(
    operation.product_key,
    `${key}.operation_object.product_key`,
  );
  const targetProductKey = text(target.product_key, `${key}.target_scope.product_key`);
  if (productKey !== expectedProductKey
    || operationProductKey !== productKey
    || targetProductKey !== productKey
    || operationSnapshotId !== snapshotId) {
    gap(`${key}.operation_object`, '候选发布动作身份与参数不一致');
  }
  if (text(operation.kind, `${key}.operation_object.kind`) !== 'release_snapshot') {
    gap(`${key}.operation_object.kind`, '候选发布动作对象类型不匹配');
  }
  const satisfied = boolean(prerequisites.satisfied, `${key}.prerequisites.satisfied`);
  if (satisfied !== enabled) {
    gap(`${key}.prerequisites.satisfied`, '候选发布动作可用状态与前置条件不一致');
  }
  const fields = readback.fields;
  if (!Array.isArray(fields) || !fields.length || fields.some(field => !String(field || '').trim())) {
    gap(`${key}.readback.fields`, '候选发布动作缺少权威回读字段');
  }
  return {
    key,
    label: text(action.label, `${key}.label`),
    intent,
    enabled,
    reason_code: text(action.reason_code, `${key}.reason_code`),
    params,
    actor: {
      user_id: positiveInt(actor.user_id, `${key}.actor.user_id`),
      login: text(actor.login, `${key}.actor.login`),
      name: text(actor.name, `${key}.actor.name`),
      operator_kind: text(actor.operator_kind, `${key}.actor.operator_kind`),
      roles: Array.isArray(actor.roles)
        ? actor.roles.map(role => String(role || '').trim()).filter(Boolean)
        : [],
    },
    target_scope: {
      kind: text(target.kind, `${key}.target_scope.kind`),
      scope_key: text(target.scope_key, `${key}.target_scope.scope_key`),
      product_key: targetProductKey,
      company_ids: Array.isArray(target.company_ids)
        ? target.company_ids.map(Number).filter(Number.isInteger)
        : [],
      target_role_codes: Array.isArray(target.target_role_codes)
        ? target.target_role_codes.map(role => String(role || '').trim()).filter(Boolean)
        : [],
      is_global_product_release: boolean(
        target.is_global_product_release,
        `${key}.target_scope.is_global_product_release`,
      ),
      meaning: text(target.meaning, `${key}.target_scope.meaning`),
    },
    operation_object: {
      kind: String(operation.kind || '').trim(),
      product_key: operationProductKey,
      snapshot_id: operationSnapshotId,
    },
    prerequisites: {
      satisfied,
      reason_code: text(prerequisites.reason_code, `${key}.prerequisites.reason_code`),
      confirmation_required: boolean(
        prerequisites.confirmation_required,
        `${key}.prerequisites.confirmation_required`,
      ),
    },
    readback: {
      source: text(readback.source, `${key}.readback.source`),
      mode: text(readback.mode, `${key}.readback.mode`),
      fields: fields.map(field => String(field)),
    },
  };
}

export function decodeReleaseOperatorSurface<T extends AnyRecord>(value: T): T {
  const surface = record(value, 'release.operator.surface');
  const actions = record(surface.available_actions, 'available_actions');
  const promoteValues = actions.promote;
  if (promoteValues === undefined) return surface as T;
  if (!Array.isArray(promoteValues)) {
    gap('available_actions.promote', '候选发布动作必须是数组');
  }
  const identity = record(surface.identity, 'identity');
  const productKey = text(identity.product_key, 'identity.product_key');
  const actorScope = record(surface.actor_scope, 'actor_scope');
  const actorId = positiveInt(actorScope.user_id, 'actor_scope.user_id');
  const readback = record(surface.operation_readback, 'operation_readback');
  if (text(readback.product_key, 'operation_readback.product_key') !== productKey) {
    gap('operation_readback.product_key', '发布回读产品与当前产品不一致');
  }
  const snapshots = Array.isArray(surface.candidate_snapshots)
    ? surface.candidate_snapshots.map(row => record(row, 'candidate_snapshots[]'))
    : [];
  for (const item of promoteValues) {
    const action = decodePromotionAction(item, productKey);
    if (action.actor.user_id !== actorId) {
      gap(`${action.key}.actor.user_id`, '候选发布动作操作者与发布面不一致');
    }
    const snapshotId = Number(action.params.snapshot_id);
    if (!snapshots.some(snapshot => Number(snapshot.id) === snapshotId)) {
      gap(`${action.key}.params.snapshot_id`, '候选发布动作引用了不存在的候选快照');
    }
  }
  return surface as T;
}
