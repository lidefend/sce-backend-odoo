import { contractGapError } from '../contract/contractGap';

export type ActionViewFieldFilter = {
  identity: string;
  field: string;
  label: string;
  type: string;
  relation: string;
  operator: string;
  value: unknown;
  domain?: unknown[];
  queryMode: 'domain';
};

export type ActionViewFieldFilterPayload = {
  field: string;
  occurrenceKey?: string;
  label: string;
  type: string;
  relation?: string;
  operator: string;
  value: unknown;
  domain?: unknown[];
  queryMode?: string;
};

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function validValue(value: unknown): boolean {
  return value === false || value === 0 || value === '' || Boolean(value);
}

export function buildActionViewFieldFilter(payload: ActionViewFieldFilterPayload): ActionViewFieldFilter {
  const field = text(payload.field);
  const operator = text(payload.operator);
  const type = text(payload.type);
  const label = text(payload.label);
  const queryMode = text(payload.queryMode);
  const value = payload.value;
  if (!field || !label || !operator || !type || !queryMode || !validValue(value)) {
    throw contractGapError(
      {
        kind: 'contract_defect',
        missing: 'searchContract.fields[].field/label/operator/type/query_mode/value',
        requiredDeclarationLayer: 'P0:smart_core:app_search_config native field projection',
      },
      '字段查询声明不完整，前端不允许猜测查询语义',
    );
  }
  if (queryMode !== 'domain') {
    throw contractGapError(
      {
        kind: 'contract_defect',
        missing: 'searchContract.fields[].query_mode',
        requiredDeclarationLayer: 'P0:smart_core:api_data native field query execution',
      },
      '字段查询声明需要后端绑定输入后执行，当前前端消费路径不得自行求值',
    );
  }
  const identity = text(payload.occurrenceKey) || `custom:${field}`;
  return {
    identity,
    field,
    label,
    type,
    relation: text(payload.relation),
    operator,
    value,
    domain: [[field, operator, value]],
    queryMode: 'domain',
  };
}

export function serializeActionViewFieldFilter(filter: ActionViewFieldFilter | null): string {
  if (!filter) return '';
  return JSON.stringify({
    identity: filter.identity,
    field: filter.field,
    label: filter.label,
    type: filter.type,
    relation: filter.relation,
    operator: filter.operator,
    value: filter.value,
    queryMode: filter.queryMode,
  });
}

export function parseActionViewFieldFilter(raw: unknown): ActionViewFieldFilter | null {
  const source = text(Array.isArray(raw) ? raw[0] : raw);
  if (!source) return null;
  let parsed: Record<string, unknown>;
  try {
    const candidate = JSON.parse(source);
    if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) return null;
    parsed = candidate as Record<string, unknown>;
  } catch {
    return null;
  }
  try {
    return buildActionViewFieldFilter({
      field: text(parsed.field),
      occurrenceKey: text(parsed.identity),
      label: text(parsed.label),
      type: text(parsed.type),
      relation: text(parsed.relation),
      operator: text(parsed.operator),
      value: parsed.value,
      queryMode: text(parsed.queryMode),
    });
  } catch {
    return null;
  }
}

export function sameActionViewFieldFilter(
  left: ActionViewFieldFilter | null,
  right: ActionViewFieldFilter | null,
): boolean {
  return serializeActionViewFieldFilter(left) === serializeActionViewFieldFilter(right);
}
