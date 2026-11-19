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
    action_id?: number;
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
  accepted_fields: string[];
  editable_fields?: Array<{
    key: string;
    type: string;
    options?: Array<{ value: string; label: string }>;
  }>;
}

export interface ProductCenterEditorCenter {
  center_key: string;
  label: string;
  sequence: number;
  entry_count: number;
  editable_fields: string[];
  config_ref: AnyRecord;
  published_label: string;
  published_sequence: number;
  changed_from_published: boolean;
}

export interface ProductCenterEditorEntry {
  menu_xmlid: string;
  label: string;
  center_key: string;
  center_label: string;
  center_sequence: number;
  published_center_key: string;
  published_center_label: string;
  changed_from_published: boolean;
}

export interface ProductCenterEditableField {
  key: string;
  label: string;
  type: 'text' | 'integer' | 'select';
  required: boolean;
  max_length?: number;
  minimum?: number;
  maximum?: number;
  options_source?: string;
}

export interface ProductCenterSaveAction {
  key: string;
  intent: string;
  enabled: boolean;
  reason_code: string;
  params: AnyRecord;
  accepted_fields: string[];
  readback: string[];
  confirmation_required: boolean;
}

export interface ProductCenterEditor {
  contract_version: 'product_center_editor.v1';
  product_key: string;
  operation_scope: AnyRecord;
  editable_fields: ProductCenterEditableField[];
  centers: ProductCenterEditorCenter[];
  entries: ProductCenterEditorEntry[];
  published: AnyRecord;
  change_summary: AnyRecord;
  save_action: ProductCenterSaveAction;
  config_ref: AnyRecord;
}

export interface BusinessSceneCompositionEntry {
  entry_id: number;
  menu_key: string;
  menu_id: number;
  intent: string;
  intent_label: string;
  sequence: number;
  center_key: string;
  center_name: string;
  center_sequence: number;
  source_db: string;
}

export interface BusinessSceneCompositionScenario {
  key: string;
  name: string;
  active: boolean;
  sequence: number;
  source_db: string;
  entries: BusinessSceneCompositionEntry[];
}

export interface BusinessSceneCompositionState {
  contract_version: 'business_scene_composition_management.v1';
  status: 'draft' | 'candidate' | 'active' | 'not_frozen' | 'no_active_release';
  status_label: string;
  available: boolean;
  reason_code: string;
  identity: AnyRecord;
  source_db: string;
  runtime_scope: string;
  scenario_count: number;
  entry_count: number;
  empty: boolean;
  digest: string;
  scenarios: BusinessSceneCompositionScenario[];
}

export interface BusinessSceneCompositionDiff {
  state: 'changed' | 'identical' | 'unavailable';
  changed_scenario_keys: string[];
  changed_entry_keys: string[];
  change_count: number;
}

export interface BusinessSceneCompositionStates {
  contract_version: 'business_scene_composition_management.v1';
  product_key: string;
  scope: string;
  draft: BusinessSceneCompositionState;
  candidate: BusinessSceneCompositionState;
  active: BusinessSceneCompositionState;
  comparisons: {
    draft_vs_candidate: BusinessSceneCompositionDiff;
    draft_vs_active: BusinessSceneCompositionDiff;
    candidate_vs_active: BusinessSceneCompositionDiff;
  };
}

export interface BusinessScenarioMaintenance {
  contract_version: 'business_scenario_maintenance_entry.v1';
  product_key: string;
  applicable: boolean;
  provider: string;
  enabled: boolean;
  reason_code: string;
  blockers: string[];
  action: {
    xmlid: string;
    id: number;
    name: string;
    res_model: string;
    view_mode: string;
  };
  menu: {
    xmlid: string;
    id: number;
    name: string;
  };
  scope: {
    kind: 'shared_maintenance_library' | 'not_applicable';
    label: string;
    model: string;
    has_product_key: boolean;
    has_company_id: boolean;
    applies_to: string;
    filter_by_current_product: boolean;
  };
  future_freeze_product_key: string;
  access: {
    read_allowed: boolean;
    write_allowed: boolean;
  };
  return_readback: {
    intent: string;
    product_key: string;
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
  const result = integer(value, path);
  if (result <= 0) gap(path, `${path} 非法`);
  return result;
}

function boolean(value: unknown, path: string): boolean {
  if (typeof value !== 'boolean') gap(path, `${path} 必须是布尔值`);
  return value;
}

function integer(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || !Number.isInteger(value)) {
    gap(path, `${path} 必须是数字整数`);
  }
  return value;
}

function nonNegativeInt(value: unknown, path: string): number {
  const result = integer(value, path);
  if (result < 0) gap(path, `${path} 必须是非负整数`);
  return result;
}

function optionalText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function signedInt(value: unknown, path: string): number {
  return integer(value, path);
}

function textList(value: unknown, path: string, required = false): string[] {
  if (!Array.isArray(value)) gap(path, `${path} 缺失`);
  const rows = value.map((row, index) => text(row, `${path}[${index}]`));
  if (required && !rows.length) gap(path, `${path} 缺失`);
  return rows;
}

function stringList(value: unknown, path: string): string[] {
  if (!Array.isArray(value) || !value.length) gap(path, `${path} 缺失`);
  const rows = value.map((row, index) => text(row, `${path}[${index}]`));
  if (new Set(rows).size !== rows.length) gap(path, `${path} 不能重复`);
  return rows;
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
  const acceptedFields = stringList(
    action.accepted_fields,
    `${key}.accepted_fields`,
  );
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
    accepted_fields: acceptedFields,
  };
}

export function decodeConfiguredOperatorAction(
  value: unknown,
  expectedIntent: string,
  expectedProductKey: string,
  path: string,
): OperatorAction {
  const action = record(value, path);
  const key = text(action.key, `${path}.key`);
  const intent = text(action.intent, `${path}.intent`);
  if (intent !== expectedIntent) {
    gap(`${path}.intent`, `${path} 意图与平台动作定义不一致`);
  }
  const enabled = boolean(action.enabled, `${path}.enabled`);
  const params = record(action.params, `${path}.params`);
  if (text(params.product_key, `${path}.params.product_key`) !== expectedProductKey) {
    gap(`${path}.params.product_key`, `${path} 产品范围与当前产品不一致`);
  }
  const actor = record(action.actor, `${path}.actor`);
  const target = record(action.target_scope, `${path}.target_scope`);
  const operation = record(action.operation_object, `${path}.operation_object`);
  if (text(target.product_key, `${path}.target_scope.product_key`) !== expectedProductKey
    || text(operation.product_key, `${path}.operation_object.product_key`) !== expectedProductKey) {
    gap(`${path}.operation_object`, `${path} 执行对象与当前产品不一致`);
  }
  const prerequisites = record(action.prerequisites, `${path}.prerequisites`);
  const satisfied = boolean(prerequisites.satisfied, `${path}.prerequisites.satisfied`);
  if (satisfied !== enabled) {
    gap(`${path}.prerequisites.satisfied`, `${path} 可用状态与前置条件不一致`);
  }
  const readback = record(action.readback, `${path}.readback`);
  const fields = readback.fields;
  if (!Array.isArray(fields) || !fields.length || fields.some(field => !String(field || '').trim())) {
    gap(`${path}.readback.fields`, `${path} 缺少权威回读字段`);
  }
  const acceptedFields = stringList(
    action.accepted_fields,
    `${path}.accepted_fields`,
  );
  const editableFields = Array.isArray(action.editable_fields)
    ? action.editable_fields.map((value, index) => {
      const field = record(value, `${path}.editable_fields[${index}]`);
      return {
        key: text(field.key, `${path}.editable_fields[${index}].key`),
        type: text(field.type, `${path}.editable_fields[${index}].type`),
        ...(field.options === undefined
          ? {}
          : {
            options: Array.isArray(field.options)
              ? field.options.map((option, optionIndex) => {
                const row = record(
                  option,
                  `${path}.editable_fields[${index}].options[${optionIndex}]`,
                );
                return {
                  value: text(
                    row.value,
                    `${path}.editable_fields[${index}].options[${optionIndex}].value`,
                  ),
                  label: text(
                    row.label,
                    `${path}.editable_fields[${index}].options[${optionIndex}].label`,
                  ),
                };
              })
              : gap(
                `${path}.editable_fields[${index}].options`,
                `${path} 字段选项声明非法`,
              ),
          }),
      };
    })
    : undefined;
  const requiredEditableFields: Record<string, string[]> = {
    'release.operator.update_policy': ['state', 'access_level'],
    'release.operator.update_page_policy': ['release_state', 'access_level'],
  };
  for (const fieldKey of requiredEditableFields[intent] || []) {
    const field = editableFields?.find(row => row.key === fieldKey);
    if (!field) {
      gap(`${path}.editable_fields.${fieldKey}`, `${path} 缺少可编辑字段声明`);
    }
    if (field.type !== 'select' || !field.options?.length) {
      gap(`${path}.editable_fields.${fieldKey}.options`, `${path} 缺少字段选项声明`);
    }
  }
  return {
    key,
    label: text(action.label, `${path}.label`),
    intent,
    enabled,
    reason_code: text(action.reason_code, `${path}.reason_code`),
    params,
    actor: {
      user_id: positiveInt(actor.user_id, `${path}.actor.user_id`),
      login: text(actor.login, `${path}.actor.login`),
      name: text(actor.name, `${path}.actor.name`),
      operator_kind: text(actor.operator_kind, `${path}.actor.operator_kind`),
      roles: Array.isArray(actor.roles)
        ? actor.roles.map(role => String(role || '').trim()).filter(Boolean)
        : [],
    },
    target_scope: {
      kind: text(target.kind, `${path}.target_scope.kind`),
      scope_key: text(target.scope_key, `${path}.target_scope.scope_key`),
      product_key: expectedProductKey,
      company_ids: Array.isArray(target.company_ids)
        ? target.company_ids.map(Number).filter(Number.isInteger)
        : [],
      target_role_codes: Array.isArray(target.target_role_codes)
        ? target.target_role_codes.map(role => String(role || '').trim()).filter(Boolean)
        : [],
      is_global_product_release: boolean(
        target.is_global_product_release,
        `${path}.target_scope.is_global_product_release`,
      ),
      meaning: text(target.meaning, `${path}.target_scope.meaning`),
    },
    operation_object: {
      kind: text(operation.kind, `${path}.operation_object.kind`),
      product_key: expectedProductKey,
      snapshot_id: operation.snapshot_id === undefined ? 0 : integer(
        operation.snapshot_id,
        `${path}.operation_object.snapshot_id`,
      ),
      ...(operation.action_id === undefined
        ? {}
        : {
          action_id: integer(
            operation.action_id,
            `${path}.operation_object.action_id`,
          ),
        }),
    },
    prerequisites: {
      satisfied,
      reason_code: text(prerequisites.reason_code, `${path}.prerequisites.reason_code`),
      confirmation_required: boolean(
        prerequisites.confirmation_required,
        `${path}.prerequisites.confirmation_required`,
      ),
    },
    readback: {
      source: text(readback.source, `${path}.readback.source`),
      mode: text(readback.mode, `${path}.readback.mode`),
      fields: fields.map(field => String(field || '').trim()),
    },
    accepted_fields: acceptedFields,
    ...(editableFields ? { editable_fields: editableFields } : {}),
  };
}

export function buildConfiguredOperatorParams(
  action: OperatorAction,
  overrides: AnyRecord,
): AnyRecord {
  const accepted = new Set(action.accepted_fields);
  for (const field of Object.keys(overrides)) {
    if (!accepted.has(field)) {
      gap(`${action.key}.accepted_fields.${field}`, `平台动作未声明输入字段 ${field}`);
    }
  }
  for (const field of action.editable_fields || []) {
    if (field.options && Object.hasOwn(overrides, field.key)) {
      const value = String(overrides[field.key] ?? '');
      if (!field.options.some(option => option.value === value)) {
        gap(
          `${action.key}.editable_fields.${field.key}.options`,
          `平台动作 ${field.key} 的值不在后端声明中`,
        );
      }
    }
  }
  return { ...action.params, ...overrides };
}

export function decodeConfiguredActionResult(
  value: unknown,
  action: OperatorAction,
  expectedProductKey: string,
): {
  surface: AnyRecord;
  readback: Record<string, AnyRecord>;
} {
  const result = record(value, `${action.key}.write_result`);
  const readback: Record<string, AnyRecord> = {};
  for (const field of action.readback.fields) {
    readback[field] = record(
      result[field],
      `${action.key}.write_result.${field}`,
    );
  }
  const surface = record(
    result.surface,
    `${action.key}.write_result.surface`,
  );
  const surfaceIdentity = record(
    surface.identity,
    `${action.key}.write_result.surface.identity`,
  );
  if (text(
    surfaceIdentity.product_key,
    `${action.key}.write_result.surface.identity.product_key`,
  ) !== expectedProductKey) {
    gap(`${action.key}.write_result.surface.product_key`, '执行回读页面属于另一产品');
  }
  if (action.intent === 'release.operator.freeze') {
    const snapshot = readback.snapshot;
    if (text(snapshot.product_key, `${action.key}.readback.snapshot.product_key`) !== expectedProductKey) {
      gap(`${action.key}.readback.snapshot.product_key`, '冻结快照属于另一产品');
    }
    positiveInt(snapshot.id, `${action.key}.readback.snapshot.id`);
  }
  if ([
    'release.operator.sync_policy',
    'release.operator.set_page_enabled',
    'release.operator.update_page_policy',
    'release.operator.update_policy',
  ].includes(action.intent)) {
    const policy = readback.policy;
    if (text(policy.product_key, `${action.key}.readback.policy.product_key`) !== expectedProductKey) {
      gap(`${action.key}.readback.policy.product_key`, '策略回读属于另一产品');
    }
  }
  if (action.intent === 'release.operator.update_policy') {
    const operationReadback = readback.readback;
    if (text(
      operationReadback.product_key,
      `${action.key}.readback.readback.product_key`,
    ) !== expectedProductKey) {
      gap(`${action.key}.readback.readback.product_key`, '策略回读身份属于另一产品');
    }
    text(
      operationReadback.draft_policy_sha256,
      `${action.key}.readback.readback.draft_policy_sha256`,
    );
    text(
      operationReadback.draft_fingerprint,
      `${action.key}.readback.readback.draft_fingerprint`,
    );
  }
  if (['release.operator.approve', 'release.operator.rollback'].includes(action.intent)) {
    const actionResult = readback.action;
    if (text(
      actionResult.product_key,
      `${action.key}.readback.action.product_key`,
    ) !== expectedProductKey) {
      gap(`${action.key}.readback.action.product_key`, '审批或回滚动作属于另一产品');
    }
    const resultActionId = positiveInt(
      actionResult.id,
      `${action.key}.readback.action.id`,
    );
    if (
      action.intent === 'release.operator.approve'
      && resultActionId !== Number(action.params.action_id)
    ) {
      gap(`${action.key}.readback.action.id`, '审批回读动作与本次审批对象不一致');
    }
  }
  return { surface, readback };
}

export function decodeProductCenterEditor(
  value: unknown,
  expectedProductKey: string,
): ProductCenterEditor {
  const editor = record(value, 'product_center_editor');
  if (text(editor.contract_version, 'product_center_editor.contract_version') !== 'product_center_editor.v1') {
    gap('product_center_editor.contract_version', '产品中心编辑契约版本不支持');
  }
  if (text(editor.product_key, 'product_center_editor.product_key') !== expectedProductKey) {
    gap('product_center_editor.product_key', '产品中心编辑契约产品与当前产品不一致');
  }
  const scope = record(editor.operation_scope, 'product_center_editor.operation_scope');
  if (text(scope.product_key, 'product_center_editor.operation_scope.product_key') !== expectedProductKey) {
    gap('product_center_editor.operation_scope.product_key', '产品中心编辑范围与当前产品不一致');
  }
  const centers = editor.centers;
  if (!Array.isArray(centers)) {
    gap('product_center_editor.centers', '产品中心编辑契约缺少中心选项');
  }
  const editableFields = Array.isArray(editor.editable_fields)
    ? editor.editable_fields.map((value, index) => {
      const field = record(value, `product_center_editor.editable_fields[${index}]`);
      const key = text(field.key, `product_center_editor.editable_fields[${index}].key`);
      const type = text(field.type, `product_center_editor.editable_fields[${index}].type`);
      if (!['text', 'integer', 'select'].includes(type)) {
        gap(`product_center_editor.editable_fields[${index}].type`, '中心字段类型未支持');
      }
      const decoded: ProductCenterEditableField = {
        key,
        label: text(field.label, `product_center_editor.editable_fields[${index}].label`),
        type: type as ProductCenterEditableField['type'],
        required: boolean(
          field.required,
          `product_center_editor.editable_fields[${index}].required`,
        ),
      };
      if (type === 'text') {
        decoded.max_length = positiveInt(
          field.max_length,
          `product_center_editor.editable_fields[${index}].max_length`,
        );
      }
      if (type === 'integer') {
        decoded.minimum = integer(
          field.minimum,
          `product_center_editor.editable_fields[${index}].minimum`,
        );
        decoded.maximum = integer(
          field.maximum,
          `product_center_editor.editable_fields[${index}].maximum`,
        );
        if (decoded.maximum < decoded.minimum) {
          gap(`product_center_editor.editable_fields[${index}].maximum`, '中心字段范围非法');
        }
      }
      if (type === 'select') {
        decoded.options_source = text(
          field.options_source,
          `product_center_editor.editable_fields[${index}].options_source`,
        );
      }
      return decoded;
    })
    : gap('product_center_editor.editable_fields', '产品中心编辑契约缺少字段声明');
  const editableFieldByKey = new Map(editableFields.map(field => [field.key, field]));
  for (const field of ['label', 'sequence', 'center_key']) {
    if (!editableFieldByKey.has(field)) {
      gap(`product_center_editor.editable_fields.${field}`, '产品中心编辑契约缺少必需字段');
    }
  }
  const sequenceField = editableFieldByKey.get('sequence')!;
  const centerRows = centers.map((value, index) => {
    const center = record(value, `product_center_editor.centers[${index}]`);
    const centerEditableFields = Array.isArray(center.editable_fields)
      ? center.editable_fields.map((field, fieldIndex) => text(
        field,
        `product_center_editor.centers[${index}].editable_fields[${fieldIndex}]`,
      ))
      : gap(
        `product_center_editor.centers[${index}].editable_fields`,
        '产品中心缺少可编辑字段声明',
      );
    if (centerEditableFields.some(field => !editableFieldByKey.has(field))) {
      gap(
        `product_center_editor.centers[${index}].editable_fields`,
        '产品中心声明了未登记的编辑字段',
      );
    }
    const sequence = integer(
      center.sequence,
      `product_center_editor.centers[${index}].sequence`,
    );
    if (sequence < sequenceField.minimum! || sequence > sequenceField.maximum!) {
      gap(`product_center_editor.centers[${index}].sequence`, '产品中心顺序超出声明范围');
    }
    return {
      center_key: text(center.center_key, `product_center_editor.centers[${index}].center_key`),
      label: text(center.label, `product_center_editor.centers[${index}].label`),
      sequence,
      entry_count: integer(center.entry_count, `product_center_editor.centers[${index}].entry_count`),
      editable_fields: centerEditableFields,
      config_ref: record(center.config_ref, `product_center_editor.centers[${index}].config_ref`),
      published_label: String(center.published_label || ''),
      published_sequence: Number(center.published_sequence || 0),
      changed_from_published: Boolean(center.changed_from_published),
    };
  });
  const entries = editor.entries;
  if (!Array.isArray(entries)) {
    gap('product_center_editor.entries', '产品中心编辑契约缺少入口放置列表');
  }
  const entryRows = entries.map((value, index) => {
    const entry = record(value, `product_center_editor.entries[${index}]`);
    return {
      menu_xmlid: text(entry.menu_xmlid, `product_center_editor.entries[${index}].menu_xmlid`),
      label: text(entry.label, `product_center_editor.entries[${index}].label`),
      center_key: text(entry.center_key, `product_center_editor.entries[${index}].center_key`),
      center_label: text(entry.center_label, `product_center_editor.entries[${index}].center_label`),
      center_sequence: integer(entry.center_sequence, `product_center_editor.entries[${index}].center_sequence`),
      published_center_key: String(entry.published_center_key || ''),
      published_center_label: String(entry.published_center_label || ''),
      changed_from_published: Boolean(entry.changed_from_published),
    };
  });
  const saveAction = record(editor.save_action, 'product_center_editor.save_action');
  const saveIntent = text(saveAction.intent, 'product_center_editor.save_action.intent');
  if (saveIntent !== 'release.operator.update_policy') {
    gap('product_center_editor.save_action.intent', '产品中心保存动作意图不匹配');
  }
  const acceptedFields = stringList(
    saveAction.accepted_fields,
    'product_center_editor.save_action.accepted_fields',
  );
  for (const field of ['center_updates', 'entry_placements']) {
    if (!acceptedFields.includes(field)) {
      gap('product_center_editor.save_action.accepted_fields', '中心保存动作缺少必需参数声明');
    }
  }
  const readbackFields = stringList(
    saveAction.readback,
    'product_center_editor.save_action.readback',
  );
  for (const field of ['policy', 'surface', 'readback']) {
    if (!readbackFields.includes(field)) {
      gap('product_center_editor.save_action.readback', '中心保存动作缺少权威回读声明');
    }
  }
  const saveParams = record(saveAction.params, 'product_center_editor.save_action.params');
  if (text(saveParams.product_key, 'product_center_editor.save_action.params.product_key') !== expectedProductKey) {
    gap('product_center_editor.save_action.params.product_key', '中心保存动作产品范围不匹配');
  }
  return {
    contract_version: 'product_center_editor.v1',
    product_key: expectedProductKey,
    operation_scope: scope,
    editable_fields: editableFields,
    centers: centerRows,
    entries: entryRows,
    published: record(editor.published, 'product_center_editor.published'),
    change_summary: record(editor.change_summary, 'product_center_editor.change_summary'),
    save_action: {
      key: text(saveAction.key, 'product_center_editor.save_action.key'),
      intent: saveIntent,
      enabled: boolean(saveAction.enabled, 'product_center_editor.save_action.enabled'),
      reason_code: text(saveAction.reason_code, 'product_center_editor.save_action.reason_code'),
      params: saveParams,
      accepted_fields: acceptedFields,
      readback: readbackFields,
      confirmation_required: boolean(
        saveAction.confirmation_required,
        'product_center_editor.save_action.confirmation_required',
      ),
    },
    config_ref: record(editor.config_ref, 'product_center_editor.config_ref'),
  };
}

export function decodeProductCenterWriteEnvelope(
  value: unknown,
  editor: ProductCenterEditor,
): {
  policy: AnyRecord;
  surface: AnyRecord;
  readback: AnyRecord;
} {
  const result = record(value, 'product_center_write');
  for (const field of editor.save_action.readback) {
    if (!Object.hasOwn(result, field)) {
      gap(`product_center_write.${field}`, `产品中心保存缺少 ${field}`);
    }
  }
  const policy = record(result.policy, 'product_center_write.policy');
  const surface = record(result.surface, 'product_center_write.surface');
  const readback = record(result.readback, 'product_center_write.readback');
  if (text(policy.product_key, 'product_center_write.policy.product_key') !== editor.product_key) {
    gap('product_center_write.policy.product_key', '产品中心保存返回的草案属于另一产品');
  }
  if (text(readback.product_key, 'product_center_write.readback.product_key') !== editor.product_key) {
    gap('product_center_write.readback.product_key', '产品中心保存回读属于另一产品');
  }
  const publishedSnapshotId = integer(
    readback.published_snapshot_id,
    'product_center_write.readback.published_snapshot_id',
  );
  if (publishedSnapshotId < 0) {
    gap(
      'product_center_write.readback.published_snapshot_id',
      '产品中心保存回读的发布快照身份不能为负数',
    );
  }
  const surfaceIdentity = record(
    surface.identity,
    'product_center_write.surface.identity',
  );
  if (text(surfaceIdentity.product_key, 'product_center_write.surface.identity.product_key') !== editor.product_key) {
    gap('product_center_write.surface.identity.product_key', '产品中心保存返回页面属于另一产品');
  }
  return { policy, surface, readback };
}

function decodeBusinessSceneCompositionEntry(
  value: unknown,
  path: string,
): BusinessSceneCompositionEntry {
  const entry = record(value, path);
  const intent = text(entry.intent, `${path}.intent`);
  return {
    entry_id: nonNegativeInt(entry.entry_id, `${path}.entry_id`),
    menu_key: text(entry.menu_key, `${path}.menu_key`),
    menu_id: nonNegativeInt(entry.menu_id, `${path}.menu_id`),
    intent,
    intent_label: text(entry.intent_label, `${path}.intent_label`),
    sequence: signedInt(entry.sequence, `${path}.sequence`),
    center_key: optionalText(entry.center_key),
    center_name: optionalText(entry.center_name),
    center_sequence: signedInt(
      entry.center_sequence,
      `${path}.center_sequence`,
    ),
    source_db: optionalText(entry.source_db),
  };
}

function decodeBusinessSceneCompositionScenario(
  value: unknown,
  path: string,
): BusinessSceneCompositionScenario {
  const scenario = record(value, path);
  if (!Array.isArray(scenario.entries)) {
    gap(`${path}.entries`, '业务场景入口必须是数组');
  }
  return {
    key: text(scenario.key, `${path}.key`),
    name: text(scenario.name, `${path}.name`),
    active: boolean(scenario.active, `${path}.active`),
    sequence: signedInt(scenario.sequence, `${path}.sequence`),
    source_db: optionalText(scenario.source_db),
    entries: scenario.entries.map((row, index) => (
      decodeBusinessSceneCompositionEntry(row, `${path}.entries[${index}]`)
    )),
  };
}

function decodeBusinessSceneCompositionState(
  value: unknown,
  path: string,
): BusinessSceneCompositionState {
  const state = record(value, path);
  const status = text(state.status, `${path}.status`);
  const allowed = new Set([
    'draft',
    'candidate',
    'active',
    'not_frozen',
    'no_active_release',
  ]);
  if (!allowed.has(status)) gap(`${path}.status`, '业务组合状态未声明');
  if (!Array.isArray(state.scenarios)) {
    gap(`${path}.scenarios`, '业务组合场景必须是数组');
  }
  const scenarios = state.scenarios.map((row, index) => (
    decodeBusinessSceneCompositionScenario(row, `${path}.scenarios[${index}]`)
  ));
  const scenarioCount = nonNegativeInt(
    state.scenario_count,
    `${path}.scenario_count`,
  );
  const entryCount = nonNegativeInt(state.entry_count, `${path}.entry_count`);
  if (scenarioCount !== scenarios.length) {
    gap(`${path}.scenario_count`, '业务组合场景数量与投影不一致');
  }
  if (entryCount !== scenarios.reduce((sum, row) => sum + row.entries.length, 0)) {
    gap(`${path}.entry_count`, '业务组合入口数量与投影不一致');
  }
  return {
    contract_version: 'business_scene_composition_management.v1',
    status: status as BusinessSceneCompositionState['status'],
    status_label: text(state.status_label, `${path}.status_label`),
    available: boolean(state.available, `${path}.available`),
    reason_code: text(state.reason_code, `${path}.reason_code`),
    identity: record(state.identity, `${path}.identity`),
    source_db: optionalText(state.source_db),
    runtime_scope: optionalText(state.runtime_scope),
    scenario_count: scenarioCount,
    entry_count: entryCount,
    empty: boolean(state.empty, `${path}.empty`),
    digest: optionalText(state.digest),
    scenarios,
  };
}

function decodeBusinessSceneCompositionDiff(
  value: unknown,
  path: string,
): BusinessSceneCompositionDiff {
  const diff = record(value, path);
  const state = text(diff.state, `${path}.state`);
  if (!['changed', 'identical', 'unavailable'].includes(state)) {
    gap(`${path}.state`, '业务组合差异状态未声明');
  }
  const changedScenarioKeys = textList(
    diff.changed_scenario_keys,
    `${path}.changed_scenario_keys`,
  );
  const changedEntryKeys = textList(
    diff.changed_entry_keys,
    `${path}.changed_entry_keys`,
  );
  const changeCount = nonNegativeInt(diff.change_count, `${path}.change_count`);
  if (changeCount !== changedScenarioKeys.length + changedEntryKeys.length) {
    gap(`${path}.change_count`, '业务组合差异数量与明细不一致');
  }
  return {
    state: state as BusinessSceneCompositionDiff['state'],
    changed_scenario_keys: changedScenarioKeys,
    changed_entry_keys: changedEntryKeys,
    change_count: changeCount,
  };
}

export function decodeBusinessSceneCompositionStates(
  value: unknown,
  expectedProductKey: string,
): BusinessSceneCompositionStates {
  const root = record(value, 'business_scene_composition_states');
  if (text(
    root.contract_version,
    'business_scene_composition_states.contract_version',
  ) !== 'business_scene_composition_management.v1') {
    gap(
      'business_scene_composition_states.contract_version',
      '业务组合管理契约版本不支持',
    );
  }
  if (text(
    root.product_key,
    'business_scene_composition_states.product_key',
  ) !== expectedProductKey) {
    gap(
      'business_scene_composition_states.product_key',
      '业务组合管理契约属于另一产品',
    );
  }
  const comparisons = record(
    root.comparisons,
    'business_scene_composition_states.comparisons',
  );
  const draft = decodeBusinessSceneCompositionState(
    root.draft,
    'business_scene_composition_states.draft',
  );
  const candidate = decodeBusinessSceneCompositionState(
    root.candidate,
    'business_scene_composition_states.candidate',
  );
  const active = decodeBusinessSceneCompositionState(
    root.active,
    'business_scene_composition_states.active',
  );
  for (const [key, state] of Object.entries({ draft, candidate, active })) {
    if (text(
      state.identity.product_key,
      `business_scene_composition_states.${key}.identity.product_key`,
    ) !== expectedProductKey) {
      gap(
        `business_scene_composition_states.${key}.identity.product_key`,
        '业务组合状态身份属于另一产品',
      );
    }
  }
  return {
    contract_version: 'business_scene_composition_management.v1',
    product_key: expectedProductKey,
    scope: text(root.scope, 'business_scene_composition_states.scope'),
    draft,
    candidate,
    active,
    comparisons: {
      draft_vs_candidate: decodeBusinessSceneCompositionDiff(
        comparisons.draft_vs_candidate,
        'business_scene_composition_states.comparisons.draft_vs_candidate',
      ),
      draft_vs_active: decodeBusinessSceneCompositionDiff(
        comparisons.draft_vs_active,
        'business_scene_composition_states.comparisons.draft_vs_active',
      ),
      candidate_vs_active: decodeBusinessSceneCompositionDiff(
        comparisons.candidate_vs_active,
        'business_scene_composition_states.comparisons.candidate_vs_active',
      ),
    },
  };
}

export function decodeBusinessScenarioMaintenance(
  value: unknown,
  expectedProductKey: string,
): BusinessScenarioMaintenance {
  const root = record(value, 'business_scenario_maintenance');
  if (text(
    root.contract_version,
    'business_scenario_maintenance.contract_version',
  ) !== 'business_scenario_maintenance_entry.v1') {
    gap(
      'business_scenario_maintenance.contract_version',
      '共享业务场景维护契约版本不支持',
    );
  }
  if (text(
    root.product_key,
    'business_scenario_maintenance.product_key',
  ) !== expectedProductKey) {
    gap(
      'business_scenario_maintenance.product_key',
      '共享业务场景维护上下文属于另一产品',
    );
  }
  const action = record(root.action, 'business_scenario_maintenance.action');
  const menu = record(root.menu, 'business_scenario_maintenance.menu');
  const scope = record(root.scope, 'business_scenario_maintenance.scope');
  const enabled = boolean(root.enabled, 'business_scenario_maintenance.enabled');
  const applicable = boolean(
    root.applicable,
    'business_scenario_maintenance.applicable',
  );
  const scopeKind = text(
    scope.kind,
    'business_scenario_maintenance.scope.kind',
  );
  if (!['shared_maintenance_library', 'not_applicable'].includes(scopeKind)) {
    gap(
      'business_scenario_maintenance.scope.kind',
      '业务场景维护作用域未声明',
    );
  }
  if (enabled && (!applicable || scopeKind !== 'shared_maintenance_library')) {
    gap(
      'business_scenario_maintenance.enabled',
      '不可适用的业务场景维护契约不能声明可执行',
    );
  }
  if (applicable && boolean(
    scope.filter_by_current_product,
    'business_scenario_maintenance.scope.filter_by_current_product',
  )) {
    gap(
      'business_scenario_maintenance.scope.filter_by_current_product',
      '共享维护库不能被伪装成当前产品私有过滤',
    );
  }
  const access = record(root.access, 'business_scenario_maintenance.access');
  const readback = record(
    root.return_readback,
    'business_scenario_maintenance.return_readback',
  );
  const returnIntent = text(
    readback.intent,
    'business_scenario_maintenance.return_readback.intent',
  );
  if (text(
    readback.product_key,
    'business_scenario_maintenance.return_readback.product_key',
  ) !== expectedProductKey) {
    gap(
      'business_scenario_maintenance.return_readback',
      '共享业务场景维护返回回读契约不匹配',
    );
  }
  return {
    contract_version: 'business_scenario_maintenance_entry.v1',
    product_key: expectedProductKey,
    applicable,
    provider: optionalText(root.provider),
    enabled,
    reason_code: text(
      root.reason_code,
      'business_scenario_maintenance.reason_code',
    ),
    blockers: textList(
      root.blockers,
      'business_scenario_maintenance.blockers',
    ),
    action: {
      xmlid: optionalText(action.xmlid),
      id: nonNegativeInt(
        action.id,
        'business_scenario_maintenance.action.id',
      ),
      name: optionalText(action.name),
      res_model: optionalText(action.res_model),
      view_mode: optionalText(action.view_mode),
    },
    menu: {
      xmlid: optionalText(menu.xmlid),
      id: nonNegativeInt(menu.id, 'business_scenario_maintenance.menu.id'),
      name: optionalText(menu.name),
    },
    scope: {
      kind: scopeKind as BusinessScenarioMaintenance['scope']['kind'],
      label: text(scope.label, 'business_scenario_maintenance.scope.label'),
      model: optionalText(scope.model),
      has_product_key: boolean(
        scope.has_product_key,
        'business_scenario_maintenance.scope.has_product_key',
      ),
      has_company_id: boolean(
        scope.has_company_id,
        'business_scenario_maintenance.scope.has_company_id',
      ),
      applies_to: optionalText(scope.applies_to),
      filter_by_current_product: false,
    },
    future_freeze_product_key: optionalText(root.future_freeze_product_key),
    access: {
      read_allowed: boolean(
        access.read_allowed,
        'business_scenario_maintenance.access.read_allowed',
      ),
      write_allowed: boolean(
        access.write_allowed,
        'business_scenario_maintenance.access.write_allowed',
      ),
    },
    return_readback: {
      intent: returnIntent,
      product_key: expectedProductKey,
      fields: textList(
        readback.fields,
        'business_scenario_maintenance.return_readback.fields',
        true,
      ),
    },
  };
}

export function decodeReleaseOperatorSurface<T extends AnyRecord>(value: T): T {
  const surface = record(value, 'release.operator.surface');
  const actions = record(surface.available_actions, 'available_actions');
  const promoteValues = actions.promote;
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
  const productCenterEditor = decodeProductCenterEditor(
    surface.product_center_editor,
    productKey,
  );
  const businessSceneCompositionStates = decodeBusinessSceneCompositionStates(
    surface.business_scene_composition_states,
    productKey,
  );
  const businessScenarioMaintenance = decodeBusinessScenarioMaintenance(
    surface.business_scenario_maintenance,
    productKey,
  );
  if (businessScenarioMaintenance.enabled
    && (businessScenarioMaintenance.action.id <= 0
      || businessScenarioMaintenance.menu.id <= 0
      || !businessScenarioMaintenance.access.read_allowed
      || !businessScenarioMaintenance.access.write_allowed)) {
    gap(
      'business_scenario_maintenance',
      '共享业务场景维护入口已启用但缺少原生目标或写权限',
    );
  }
  const decodedActions: AnyRecord = { ...actions };
  for (const [key, intent] of Object.entries({
    freeze: 'release.operator.freeze',
    sync_policy: 'release.operator.sync_policy',
    set_page_enabled: 'release.operator.set_page_enabled',
    update_page_policy: 'release.operator.update_page_policy',
    update_policy: 'release.operator.update_policy',
    runtime_probe: 'release.operator.runtime_probe',
    rollback: 'release.operator.rollback',
  })) {
    decodedActions[key] = decodeConfiguredOperatorAction(
      actions[key],
      intent,
      productKey,
      `available_actions.${key}`,
    );
  }
  const updatePolicy = record(actions.update_policy, 'available_actions.update_policy');
  if (text(updatePolicy.editor_contract, 'available_actions.update_policy.editor_contract') !== 'product_center_editor.v1') {
    gap('available_actions.update_policy.editor_contract', '保存产品草案未声明产品中心编辑契约');
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
  const pending = surface.pending_approval
    ? record(surface.pending_approval, 'pending_approval')
    : null;
  const pendingActions = pending && Array.isArray(pending.actions)
    ? pending.actions.map((value, index) => {
      const row = record(value, `pending_approval.actions[${index}]`);
      const rowId = positiveInt(
        row.id,
        `pending_approval.actions[${index}].id`,
      );
      const approveAction = decodeConfiguredOperatorAction(
        row.approve_action,
        'release.operator.approve',
        productKey,
        `pending_approval.actions[${index}].approve_action`,
      );
      if (
        Number(approveAction.params.action_id) !== rowId
        || approveAction.operation_object.action_id !== rowId
      ) {
        gap(
          `pending_approval.actions[${index}].approve_action.operation_object.action_id`,
          '审批动作对象与待审批行不一致',
        );
      }
      return {
        ...row,
        approve_action: approveAction,
      };
    })
    : [];
  return {
    ...surface,
    available_actions: decodedActions,
    ...(pending
      ? { pending_approval: { ...pending, actions: pendingActions } }
      : {}),
    product_center_editor: productCenterEditor,
    business_scene_composition_states: businessSceneCompositionStates,
    business_scenario_maintenance: businessScenarioMaintenance,
  } as unknown as T;
}
