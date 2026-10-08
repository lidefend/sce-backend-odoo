/**
 * Behavioural lock: ActionView 只在契约投影就绪后才渲染依赖契约声明的 surface.
 *
 * 该缺陷在日常开发服务器上实测（PR #622 部署后）：`viewMode` 在契约就绪前就已由
 * 路由/模型元数据推导为 `tree`，模板因此提前进入 ListPage 分支，并在
 * `actionContract === null` 的当口求值 `:page-size-options`（真实消费契约声明
 * `searchContract.defaults.page_size_options`），以 `ContractGapError` 停掉整页
 * —— 89 个业务入口里 80 个 table/hierarchical 入口声明不出任何展示面。
 *
 * 断言的是行为：判据 `resolveActionViewSurfaceDisplayState` 的输出状态，以及
 * 「判为 surface 时那条真实消费链能不能跑通」。不用字符串出现、选择器文本或
 * 常量字面量作为正确性证明。
 */
import assert from 'node:assert/strict';

import { createContractV2Store } from '../src/app/contracts/v2/store';
import type { ContractV2Snapshot } from '../src/app/contracts/v2/types';
import { ContractGapError } from '../src/app/contract/contractGap';
import { resolveActionViewPageSizeOptions } from '../src/app/runtime/actionViewListPageSizeRuntime';
import {
  resolveActionViewSurfaceDisplayState,
  type ActionViewSurfaceDisplayState,
} from '../src/app/runtime/actionViewSurfaceGateRuntime';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

// 生产契约载体的最小形状（与 page-size 行为锁共用同一 store 工厂路径）。
function snapshotWithSearch(searchContract: Record<string, unknown> | undefined): ContractV2Snapshot {
  return {
    layoutContract: { containerTree: [] },
    dataContract: { dataSource: {} },
    actionContract: { actionRuleList: [] },
    statusContract: { widgetStatus: [], buttonStatus: [], containerStatus: [] },
    ...(searchContract === undefined ? {} : { searchContract }),
  } as unknown as ContractV2Snapshot;
}

const resolvedStore = createContractV2Store(snapshotWithSearch({
  defaults: { limit: 20, order: 'id desc', page_size_options: [10, 20, 50], page_size_range: { min: 1, max: 200 } },
}));

const stateFor = (input: { renderError?: string; hasContract: boolean; loadError?: string }): ActionViewSurfaceDisplayState =>
  resolveActionViewSurfaceDisplayState({
    renderError: input.renderError || '',
    hasContract: input.hasContract,
    loadError: input.loadError || '',
  });

// 1. 基线：契约已就绪 → surface 渲染，且同一时刻契约声明确实可消费。
check(stateFor({ hasContract: true }), 'surface', 'a resolved contract renders the surface');
check(
  resolveActionViewPageSizeOptions(resolvedStore),
  [10, 20, 50],
  'the same moment the surface is allowed, the declared page-size surface resolves',
);

// 2. 缺陷形态：契约未就绪 → 停机等契约，绝不进 surface。
//    负例先确认未注入形态的基线正常（第 1 条已证明判据不是常量），此处再注入
//    「契约未就绪」，证明它被检出。
check(stateFor({ hasContract: false }), 'contract-pending', 'an unresolved contract stops at contract-pending');
check(
  stateFor({ hasContract: false }) === 'surface',
  false,
  'an unresolved contract must never be reported as a rendered surface',
);

// 3. 为什么「未就绪却渲染 surface」就是契约缺陷：那条消费链此刻必然停机。
const expectGap = (run: () => unknown, missing: string, label: string) => {
  try {
    run();
  } catch (error) {
    assert.ok(error instanceof ContractGapError, `${label}: expected ContractGapError`);
    assert.equal((error as ContractGapError).defect.missing, missing, `${label}: defect path`);
    cases += 1;
    return;
  }
  throw new Error(`${label}: expected a contract gap, got a value`);
};
expectGap(
  () => resolveActionViewPageSizeOptions(null),
  'search.defaults.page_size_options',
  'rendering the surface with an unresolved contract would stop the page',
);

// 4. 契约未就绪 + 真实加载失败 → 显示真实加载错误（不静默等契约，也不掩盖错误）。
check(
  stateFor({ hasContract: false, loadError: 'code=403 · 无权限访问该业务对象' }),
  'load-error',
  'an unresolved contract with a failed load reports the real load error',
);

// 5. 契约已就绪 + 加载失败 → 仍是 surface，由 surface 自己的错误态呈现（行为不变）。
check(stateFor({ hasContract: true, loadError: 'code=500 · 加载失败' }), 'surface', 'a resolved contract keeps the surface error state');

// 6. 渲染期错误优先：停机等契约不能掩盖渲染失败。
check(
  stateFor({ hasContract: false, renderError: 'ActionView render error: ContractGapError' }),
  'render-error',
  'a render error outranks every other surface state',
);
check(
  stateFor({ hasContract: true, renderError: 'ActionView render error: X' }),
  'render-error',
  'a render error outranks a resolved contract',
);

// 7. 穷尽性：四种状态都能由声明输入到达，判据不得把状态塌陷成常量。
const reachable = new Set([
  stateFor({ hasContract: true }),
  stateFor({ hasContract: false }),
  stateFor({ hasContract: false, loadError: 'code=403 · denied' }),
  stateFor({ hasContract: true, renderError: 'boom' }),
]);
check(reachable.size, 4, 'all four surface display states remain reachable from declared inputs');

console.log(`[action_view_surface_gate_runtime_test] PASS cases=${cases}`);
