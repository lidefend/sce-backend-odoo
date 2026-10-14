/**
 * 契约缺陷的唯一停机原语（P0 前端渲染机制）。
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
 * 契约缺陷停机错误的对外形状。抛出即表示「前端判断出现 → 立即停机 → 回契约要结果」。
 *
 * 这里只有**类型别名 + 工厂函数**，没有 class：本模块位于协作权威
 * （`pages/contractForm/contractRuntimeVm.ts`）的受复核加载闭包内，闭包成员在模块加载期
 * 不得求值任何东西，而 `class ContractGapError extends Error` 的 `extends` 子句在定义时就
 * 要求值 `Error`（`frontend_scene_component_bridge_guard` 的
 * `collaboration_import_closure_failures` 因此拒绝闭包成员里的 class、enum、namespace 以及
 * 任何模块级绑定）。停机原语的**身份**由 `name` 与 `defect` 两个事实定义，而不是由原型
 * 决定：`contractGapError()` 造出的就是真正的 `Error` 实例，`isContractGapError()` 按同一
 * 口径判定。
 */
export type ContractGapError = Error & { readonly defect: ContractDefectRef };

/** 构造唯一的停机错误。前端不夹取、不默认、不改写，缺口以 `ContractGapError` 交给声明层。 */
export function contractGapError(defect: ContractDefectRef, message: string): ContractGapError {
  const error = new Error(message) as Error & { defect: ContractDefectRef };
  error.name = 'ContractGapError';
  error.defect = defect;
  return error;
}

/**
 * 契约声明缺失或非法时的唯一停机出口：前端不夹取、不默认、不改写，缺口以
 * `ContractGapError` 暴露给声明层。
 */
function raiseGap(spec: { missing: string; requiredDeclarationLayer: string }): never {
  throw contractGapError(
    {
      kind: 'contract_defect',
      missing: spec.missing,
      requiredDeclarationLayer: spec.requiredDeclarationLayer,
    },
    `契约缺少合法声明 ${spec.missing}：前端不停机兜底，等待声明层补齐`,
  );
}

/**
 * 消费一个必须由契约声明的数值参数。
 *
 * 校验口径（严格、无夹取、无改写）：
 * - 必须是真正的数值类型（`typeof === 'number'` 且有限）；布尔、字符串、数组、对象、
 *   空串等一律视为非法声明。旧实现用 `Number(value)` 会把 `true` 变成 `1`、把 `'20'`
 *   当成 `20`，等于前端替声明层补语义，已被禁止。
 * - `integer` 默认为真：声明必须本身是整数，不再用 `Math.trunc` 把 `1.9` 截成 `1`。
 * - `min`（含）与可选 `max` 越界即停机。
 * - 合法声明以原始值原样返回，前端绝不修改契约事实。
 *
 * @param value 契约声明的原始值
 * @param spec.missing 缺失字段路径
 * @param spec.requiredDeclarationLayer 应补齐声明的归属层
 * @param spec.min 合法下界（含），默认 1
 * @param spec.max 合法上界（含），可选
 * @param spec.integer 是否要求整数，默认 true
 */
export function requireDeclaredNumber(
  value: unknown,
  spec: { missing: string; requiredDeclarationLayer: string; min?: number; max?: number; integer?: boolean },
): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) raiseGap(spec);
  if ((spec.integer ?? true) && !Number.isInteger(value)) raiseGap(spec);
  const min = spec.min ?? 1;
  if (value < min) raiseGap(spec);
  if (spec.max !== undefined && value > spec.max) raiseGap(spec);
  return value;
}

/**
 * 消费一个必须由契约声明的数值列表（例如列表页可选的每页条数）。
 *
 * 声明缺失、非数组、空数组或含非法项即停机。每一项都按 `requireDeclaredNumber`
 * 同口径严格校验（真正的数值类型、整数、范围），并且原样返回，不再用 `Math.trunc`
 * 或过滤把非法项悄悄丢弃 —— 静默丢弃会掩盖声明层缺项。
 */
export function requireDeclaredNumberList(
  value: unknown,
  spec: { missing: string; requiredDeclarationLayer: string; min?: number; max?: number; integer?: boolean },
): number[] {
  if (!Array.isArray(value) || value.length === 0) raiseGap(spec);
  return value.map((item) => requireDeclaredNumber(item, spec));
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

/**
 * 消费一个必须由契约声明的布尔参数。声明缺失或非布尔即停机：布尔声明正是
 * 「能力开/关」的事实，前端不得以 `!== false` / `=== true` 之类夹取补默认。
 */
export function requireDeclaredBoolean(
  value: unknown,
  spec: { missing: string; requiredDeclarationLayer: string },
): boolean {
  if (typeof value !== 'boolean') {
    throw contractGapError(
      {
        kind: 'contract_defect',
        missing: spec.missing,
        requiredDeclarationLayer: spec.requiredDeclarationLayer,
      },
      `契约缺少合法声明 ${spec.missing}：前端不停机兜底，等待声明层补齐`,
    );
  }
  return value;
}

/**
 * 消费一个必须由契约声明的非空文本参数（例如策略取值、动作来源）。声明缺失、
 * 非文本或空串即停机；前端不提供默认取值。
 */
export function requireDeclaredText(
  value: unknown,
  spec: { missing: string; requiredDeclarationLayer: string },
): string {
  const declared = typeof value === 'string' ? value.trim() : '';
  if (!declared) {
    throw contractGapError(
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

/** 判定一个错误是否为契约缺陷停机错误（供停机态渲染与诊断使用）。 */
export function isContractGapError(error: unknown): error is ContractGapError {
  return typeof error === 'object' && error !== null
    && (error as { name?: string }).name === 'ContractGapError';
}
