/**
 * ActionView surface 展示状态的唯一判据（P0 前端渲染机制）。
 *
 * 最高职责界限（AGENTS.md / ARCHITECTURE_GUARD.md / ARCH-DECISION-002）：
 * 前端只做渲染与交互，surface 的展示形态与全部展示数据都来自契约投影
 * （`ContractV2NormalizedStore`）。契约未就绪时前端不得渲染任何依赖契约声明的
 * surface，更不得用路由/模型/id 猜一个形态先行渲染 —— 那等于在
 * `actionContract === null` 时消费契约声明，以 `ContractGapError` 停掉整页。
 *
 * 该缺口已在日常开发服务器实测：契约未就绪先渲染 ListPage 时，
 * `:page-size-options` 求值 `resolveActionViewPageSizeOptions(null)` 立即停机，
 * 89 个业务入口中 80 个 table/hierarchical 入口整页失败、声明不出任何展示面。
 *
 * 因此 surface 的展示状态只由三件事决定，判定顺序固定：
 * 1. `render-error`：渲染期契约缺口等错误 → 显示渲染失败，等声明层修。
 * 2. `surface`：契约已就绪 → 正常渲染 surface（含 surface 自己的错误态）。
 * 3. `load-error`：契约未就绪且加载已失败 → 显示真实加载错误，不静默等契约。
 * 4. `contract-pending`：契约未就绪 → 停机等契约，只渲染加载骨架。
 */
export type ActionViewSurfaceDisplayState =
  | 'render-error'
  | 'load-error'
  | 'contract-pending'
  | 'surface';

export function resolveActionViewSurfaceDisplayState(input: {
  /** 渲染期捕获到的错误信息（onErrorCaptured）。 */
  renderError: string;
  /** 契约投影（ContractV2NormalizedStore）是否已就绪。 */
  hasContract: boolean;
  /** 加载阶段声明的错误信息；契约未就绪时据此显示真实加载错误。 */
  loadError: string;
}): ActionViewSurfaceDisplayState {
  if (input.renderError) return 'render-error';
  if (input.hasContract) return 'surface';
  if (input.loadError) return 'load-error';
  return 'contract-pending';
}
