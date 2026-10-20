/**
 * 受控系统参数的 fail-closed 消费投影。
 *
 * 参数目录、影响预览与变更记录全部原样消费后端声明；声明面存在但形状非法即
 * 抛 ContractGapError 停机，空集合是合法投影，前端不推导取值合法性、影响范围
 * 或回滚语义。
 */
import type {
  ProductSystemParameter,
  ProductSystemParameterCatalog,
  ProductSystemParameterChange,
  ProductSystemParameterImpact,
  ProductSystemParameterPreview,
} from '../api/productSystemParameter';
import { contractGapError, type ContractGapError } from './contract/contractGap';

const REQUIRED_DECLARATION_LAYER = 'P1:smart_construction_core:sc.product.system_parameter';

function raiseGap(missing: string): never {
  throw contractGapError(
    { kind: 'contract_defect', missing, requiredDeclarationLayer: REQUIRED_DECLARATION_LAYER },
    `契约缺少合法声明 ${missing}：前端不停机兜底，等待声明层补齐`,
  );
}

function asObject(value: unknown, missing: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) raiseGap(missing);
  return value as Record<string, unknown>;
}

function asList(value: unknown, missing: string): unknown[] {
  if (!Array.isArray(value)) raiseGap(missing);
  return value;
}

function requiredText(value: unknown, missing: string): string {
  if (typeof value !== 'string' || !value.trim()) raiseGap(missing);
  return value;
}

function optionalText(value: unknown, missing: string): string {
  if (value === undefined || value === null) return '';
  if (typeof value !== 'string') raiseGap(missing);
  return value;
}

function declaredBoolean(value: unknown, missing: string): boolean {
  if (typeof value !== 'boolean') raiseGap(missing);
  return value;
}

function optionalNumber(value: unknown, missing: string): number | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value !== 'number' || !Number.isFinite(value)) raiseGap(missing);
  return value;
}

function impactObject(value: unknown, missing: string): ProductSystemParameterImpact {
  if (value === undefined || value === null) raiseGap(missing);
  const row = asObject(value, missing);
  const surfaces = asList(row.surfaces, missing).map((item, index) =>
    requiredText(item, `${missing}.surfaces[${index}]`),
  );
  return {
    surfaces,
    summary: requiredText(row.summary, `${missing}.summary`),
    risk_level: optionalText(row.risk_level, `${missing}.risk_level`),
  };
}

export function projectSystemParameterCatalog(catalog: unknown): {
  categories: ProductSystemParameterCatalog['categories'];
  parameters: ProductSystemParameter[];
  guardrails: string[];
} {
  if (catalog === undefined || catalog === null) raiseGap('sc.product.system_parameter.catalog');
  const root = asObject(catalog, 'sc.product.system_parameter.catalog');
  const categories = asList(root.categories, 'sc.product.system_parameter.catalog.categories').map((item, index) => {
    const row = asObject(item, `sc.product.system_parameter.catalog.categories[${index}]`);
    return {
      key: requiredText(row.key, `sc.product.system_parameter.catalog.categories[${index}].key`),
      label: requiredText(row.label, `sc.product.system_parameter.catalog.categories[${index}].label`),
    };
  });
  const parameters = asList(root.parameters, 'sc.product.system_parameter.catalog.parameters').map((item, index) => {
    const row = asObject(item, `sc.product.system_parameter.catalog.parameters[${index}]`);
    return {
      key: requiredText(row.key, `sc.product.system_parameter.catalog.parameters[${index}].key`),
      category: requiredText(row.category, `sc.product.system_parameter.catalog.parameters[${index}].category`),
      label: requiredText(row.label, `sc.product.system_parameter.catalog.parameters[${index}].label`),
      description: optionalText(row.description, `sc.product.system_parameter.catalog.parameters[${index}].description`),
      type: requiredText(row.type, `sc.product.system_parameter.catalog.parameters[${index}].type`),
      default: row.default,
      allowed_values: Array.isArray(row.allowed_values) ? row.allowed_values : [],
      min: optionalNumber(row.min, `sc.product.system_parameter.catalog.parameters[${index}].min`),
      max: optionalNumber(row.max, `sc.product.system_parameter.catalog.parameters[${index}].max`),
      scope: optionalText(row.scope, `sc.product.system_parameter.catalog.parameters[${index}].scope`),
      maintainer_role: optionalText(row.maintainer_role, `sc.product.system_parameter.catalog.parameters[${index}].maintainer_role`),
      status: requiredText(row.status, `sc.product.system_parameter.catalog.parameters[${index}].status`),
      available: declaredBoolean(row.available, `sc.product.system_parameter.catalog.parameters[${index}].available`),
      authority: optionalText(row.authority, `sc.product.system_parameter.catalog.parameters[${index}].authority`),
      impact: impactObject(row.impact, `sc.product.system_parameter.catalog.parameters[${index}].impact`),
      current_value: row.current_value,
    };
  });
  const guardrails = Array.isArray(root.guardrails)
    ? root.guardrails.filter((item): item is string => typeof item === 'string')
    : [];
  return { categories, parameters, guardrails };
}

export function projectImpactPreview(preview: unknown): ProductSystemParameterPreview {
  const root = asObject(preview, 'sc.product.system_parameter.preview');
  const ok = declaredBoolean(root.ok, 'sc.product.system_parameter.preview.ok');
  const parameter = requiredText(root.parameter, 'sc.product.system_parameter.preview.parameter');
  if (ok) {
    return {
      ok: true,
      parameter,
      status: optionalText(root.status, 'sc.product.system_parameter.preview.status'),
      proposed_value: root.proposed_value,
      impact: impactObject(root.impact, 'sc.product.system_parameter.preview.impact'),
      audit_required: declaredBoolean(root.audit_required, 'sc.product.system_parameter.preview.audit_required'),
      rollback_required: declaredBoolean(root.rollback_required, 'sc.product.system_parameter.preview.rollback_required'),
      change_set_required: declaredBoolean(root.change_set_required, 'sc.product.system_parameter.preview.change_set_required'),
    };
  }
  return {
    ok: false,
    parameter,
    reason: optionalText(root.reason, 'sc.product.system_parameter.preview.reason'),
    status: optionalText(root.status, 'sc.product.system_parameter.preview.status'),
    impact: root.impact && typeof root.impact === 'object' ? root.impact as ProductSystemParameterPreview['impact'] : undefined,
    allowed_values: Array.isArray(root.allowed_values) ? root.allowed_values : undefined,
    min: optionalNumber(root.min, 'sc.product.system_parameter.preview.min'),
    max: optionalNumber(root.max, 'sc.product.system_parameter.preview.max'),
  };
}

export function projectChangeRecord(change: unknown): ProductSystemParameterChange {
  const root = asObject(change, 'sc.product.system_parameter.change');
  const id = root.id;
  if (typeof id !== 'number' || !Number.isInteger(id) || id <= 0) {
    raiseGap('sc.product.system_parameter.change.id');
  }
  return {
    id,
    parameter_key: requiredText(root.parameter_key, 'sc.product.system_parameter.change.parameter_key'),
    proposed_value: root.proposed_value,
    previous_value: root.previous_value,
    state: requiredText(root.state, 'sc.product.system_parameter.change.state'),
    company_id: Number(root.company_id || 0),
    change_reason: optionalText(root.change_reason, 'sc.product.system_parameter.change.change_reason'),
    risk_level: optionalText(root.risk_level, 'sc.product.system_parameter.change.risk_level'),
    published_at: typeof root.published_at === 'string' ? root.published_at : false,
    rolled_back_at: typeof root.rolled_back_at === 'string' ? root.rolled_back_at : false,
    audit_json: root.audit_json && typeof root.audit_json === 'object' && !Array.isArray(root.audit_json)
      ? root.audit_json as Record<string, unknown>
      : {},
  };
}

export function isProductSystemParameterGap(error: unknown): error is ContractGapError {
  return typeof error === 'object' && error !== null
    && (error as { name?: string }).name === 'ContractGapError';
}

/** 渲染层对已声明的参数状态/风险等级的展示文案映射（renderer dispatch）。 */
export function parameterStatusLabel(status: string): string {
  if (status === 'available') return '可用';
  if (status === 'planned') return '未发布';
  return status;
}
