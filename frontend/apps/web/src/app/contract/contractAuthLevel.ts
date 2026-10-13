/**
 * 契约权限级别（auth）的唯一枚举与语义（P0 契约语义层）。
 *
 * `statusContract.globalStatus.pageAuth` 的取值域来自后端 `permission_auth_level`
 * （addons/smart_core/core/unified_page_contract_v2_permissions.py）：none < read <
 * edit < admin。其中 `admin` 由后端 admin 权限位显式派生并蕴含 write/edit，
 * 是「已声明的枚举语义」，不是前端就地猜测；前端只消费这一枚枚举，
 * 不得再用 `['edit','admin'].includes(x)` 之类散落判断，也不得把非法取值
 * 静默合并进 read/edit 分支（T5：明确权限枚举）。
 *
 * 语义分工（T5：分开「明确禁止」与「声明缺失」）：
 * - `none`  = 契约显式禁止访问（明确禁止，消费点据此只读/拒绝），
 * - `null`  = 未声明或非法（声明缺失），消费点须按契约缺口处理，不得当作 readonly 兜底，
 * - `read`/`edit`/`admin` = 逐级放行。
 */
import { ContractGapError } from './contractGap';

export const CONTRACT_AUTH_LEVELS = ['none', 'read', 'edit', 'admin'] as const;

export type ContractAuthLevel = typeof CONTRACT_AUTH_LEVELS[number];

/**
 * 严格归一化：仅接受已声明枚举，非法/缺失一律返回 `null`（声明缺失），
 * 由调用方决定是停机还是走「未声明」分支；此处绝不夹取、不默认。
 */
export function normalizeContractAuthLevel(raw: unknown): ContractAuthLevel | null {
  const value = typeof raw === 'string' ? raw.trim().toLowerCase() : '';
  return (CONTRACT_AUTH_LEVELS as readonly string[]).includes(value)
    ? value as ContractAuthLevel
    : null;
}

/** 是否允许读取：read/edit/admin 放行；none 显式禁止；null 未声明。 */
export function contractAuthLevelGrantsRead(level: ContractAuthLevel | null): boolean {
  return level === 'read' || level === 'edit' || level === 'admin';
}

/** 是否允许编辑：edit/admin 放行（admin 由后端枚举语义显式蕴含 edit）。 */
export function contractAuthLevelGrantsEdit(level: ContractAuthLevel | null): boolean {
  return level === 'edit' || level === 'admin';
}

/** 是否为契约显式禁止访问（仅 none；null 表示未声明而非禁止）。 */
export function contractAuthLevelDeniesAccess(level: ContractAuthLevel | null): boolean {
  return level === 'none';
}

/**
 * 消费一个必须由契约声明的权限级别：非法/缺失即停机（ContractGapError），
 * 把缺口交回声明层，而不是让前端猜一个级别继续。
 */
export function requireContractAuthLevel(
  raw: unknown,
  spec: { missing: string; requiredDeclarationLayer: string },
): ContractAuthLevel {
  const level = normalizeContractAuthLevel(raw);
  if (!level) {
    throw new ContractGapError(
      {
        kind: 'contract_defect',
        missing: spec.missing,
        requiredDeclarationLayer: spec.requiredDeclarationLayer,
      },
      `契约缺少合法声明 ${spec.missing}：前端不停机兜底，等待声明层补齐`,
    );
  }
  return level;
}

export type OccurrenceAuthVerdict = {
  level: ContractAuthLevel | null;
  /** true when a widget verdict declares no legal auth level (contract gap). */
  gap: boolean;
  readonly: boolean;
  /** true when the occurrence must stop (not render as a normal live widget). */
  blocked: boolean;
};

/**
 * 消费一个字段 occurrence 的权限判定（T5 落地到实际只读路径）。
 *
 * - 非字段 verdict（按钮/容器）不携带 auth，不得据它判只读；
 * - 字段 verdict 必须携带已声明枚举：none/read 只读，edit/admin 可编辑；
 * - 缺失或非法 = 契约缺口，fail closed（不可静默变只读）。
 */
export function resolveOccurrenceAuthVerdict(input: {
  hasWidgetVerdict: boolean;
  auth: unknown;
  statusDisabled?: boolean;
  unresolved?: boolean;
}): OccurrenceAuthVerdict {
  const hasWidgetVerdict = input.hasWidgetVerdict === true;
  const unresolved = input.unresolved === true;
  const level = hasWidgetVerdict ? normalizeContractAuthLevel(input.auth) : null;
  const gap = hasWidgetVerdict && level === null;
  // An unresolved occurrence cannot be a normal live widget either: it is
  // blocked and must read as read-only, never as writable.
  const readonly = gap
    || unresolved
    || (hasWidgetVerdict && !contractAuthLevelGrantsEdit(level));
  return { level, gap, readonly, blocked: unresolved || gap };
}
