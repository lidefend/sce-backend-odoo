/**
 * 契约缺口的唯一停机原语（P0 前端渲染机制）。
 *
 * 最高职责界限（AGENTS.md / ARCHITECTURE_GUARD.md / ARCH-DECISION-002）：
 * 前端只做渲染与交互，其余一切输入必须来自契约。前端一旦需要做没有契约依据的
 * 判断，这个缺口本身就是契约缺陷 —— 必须立即停机并回到声明层要结果，
 * 不得由前端默认值、夹取或特判兜底。
 *
 * 因此本模块提供唯一入口：任何消费契约声明的地方，声明缺失或非法即抛
 * `ContractGapError`，把缺口作为契约缺陷暴露给声明层，而不是猜一个值继续。
 */

/** 契约缺陷引用。绑定缺失字段路径与应补齐该声明的归属层。 */
export type ContractDefectRef = {
  kind: 'contract_defect';
  /** 缺失或非法的契约字段路径，例如 `config.sheet.page_size`。 */
  missing: string;
  /** 应补齐该声明的归属层与载体，例如 `P0:smart_core:page_assembler`。 */
  requiredDeclarationLayer: string;
};

/**
 * 契约缺口停机错误。抛出即表示「前端判断出现 → 立即停机 → 回契约要结果」。
 */
export class ContractGapError extends Error {
  readonly defect: ContractDefectRef;

  constructor(defect: ContractDefectRef, message: string) {
    super(message);
    this.name = 'ContractGapError';
    this.defect = defect;
  }
}

/**
 * 消费一个必须由契约声明的数值参数。声明缺失、非数值或非法（<= min）时立即
 * 停机：前端不提供默认值、不夹取范围，缺口以 `ContractGapError` 暴露。
 *
 * @param value 契约声明的原始值
 * @param spec.missing 缺失字段路径
 * @param spec.requiredDeclarationLayer 应补齐声明的归属层
 * @param spec.min 合法下界（含），用于判定「非法声明」
 */
export function requireDeclaredNumber(
  value: unknown,
  spec: { missing: string; requiredDeclarationLayer: string; min?: number; integer?: boolean },
): number {
  const numeric = Number(value);
  const declared = (spec.integer ?? true) ? Math.trunc(numeric) : numeric;
  const min = spec.min ?? 1;
  if (!Number.isFinite(declared) || declared < min) {
    throw new ContractGapError(
      {
        kind: 'contract_defect',
        missing: spec.missing,
        requiredDeclarationLayer: spec.requiredDeclarationLayer,
      },
      `契约缺少合法声明 ${spec.missing}：前端不停机兜底，等待声明层补齐`,
    );
  }
  return declared;
}

/**
 * 消费一个必须由契约声明的数值列表（例如列表页可选的每页条数）。
 * 声明缺失、非数组、空数组或含非法项时立即停机。
 */
export function requireDeclaredNumberList(
  value: unknown,
  spec: { missing: string; requiredDeclarationLayer: string; min?: number },
): number[] {
  const min = spec.min ?? 1;
  const rows = Array.isArray(value) ? value : null;
  const declared = rows
    ? rows.map((item) => Math.trunc(Number(item))).filter((item) => Number.isFinite(item) && item >= min)
    : [];
  if (!rows || !declared.length || declared.length !== rows.length) {
    throw new ContractGapError(
      {
        kind: 'contract_defect',
        missing: spec.missing,
        requiredDeclarationLayer: spec.requiredDeclarationLayer,
      },
      `契约缺少合法声明 ${spec.missing}：前端不停机兜底，等待声明层补齐`,
    );
  }
  return declared;
}

/**
 * 消费一个「契约声明为可选」的数值参数。声明缺失（undefined/null/空串）时返回
 * `undefined`，表示调用方按声明语义走「未声明」分支；一旦声明存在但非法，立即
 * 停机（与 `requireDeclaredNumber` 同口径），前端不补默认值、不夹取。
 */
export function optionalDeclaredNumber(
  value: unknown,
  spec: { missing: string; requiredDeclarationLayer: string },
): number | undefined {
  if (value === undefined || value === null || value === '') return undefined;
  return requireDeclaredNumber(value, spec);
}

/** 判定一个错误是否为契约缺口停机错误（供停机态渲染与诊断使用）。 */
export function isContractGapError(error: unknown): error is ContractGapError {
  return error instanceof ContractGapError
    || (typeof error === 'object' && error !== null && (error as { name?: string }).name === 'ContractGapError');
}
