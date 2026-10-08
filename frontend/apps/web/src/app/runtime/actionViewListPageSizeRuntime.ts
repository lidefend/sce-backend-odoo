import { resolveContractV2SearchContract } from '../contracts/v2/store';
import type { ContractV2NormalizedStore } from '../contracts/v2/types';
import { requireDeclaredNumber, requireDeclaredNumberList } from '../contract/contractGap';

type Dict = Record<string, unknown>;

/**
 * 列表页分页声明的唯一来源：契约 `searchContract.defaults`。
 *
 * 运行时载体是 `ContractV2NormalizedStore`（契约规范化投影）。契约快照只挂在
 * `store.snapshot` 之下，因此这里必须走规范访问器 `resolveContractV2SearchContract`，
 * 前端不自己拼 `searchContract` 键路径 —— 载体形状一旦漂移，必须在编译期被类型签名
 * 拦住，而不是运行期静默取到空对象后抛出 `ContractGapError`。
 */
function searchDefaults(store: ContractV2NormalizedStore | null): Dict {
  const search = resolveContractV2SearchContract(store);
  return search.defaults && typeof search.defaults === 'object' ? (search.defaults as Dict) : {};
}

/**
 * 列表页每页条数可选集合的唯一来源：契约 `searchContract.defaults.page_size_options`。
 * 前端只消费声明值，不再自造 `[10, 20, 50]` 之类的可选范围；声明缺失或非法即
 * 停机（`ContractGapError`）回声明层要结果。
 */
export function resolveActionViewPageSizeOptions(store: ContractV2NormalizedStore | null): number[] {
  return requireDeclaredNumberList(searchDefaults(store).page_size_options, {
    missing: 'search.defaults.page_size_options',
    requiredDeclarationLayer: 'P0:smart_core:app_search_config.get_search_contract',
  });
}

/**
 * 每页条数合法范围的唯一来源：契约 `searchContract.defaults.page_size_range`。
 */
export function resolveActionViewPageSizeRange(store: ContractV2NormalizedStore | null): { min: number; max: number } {
  const spec = {
    requiredDeclarationLayer: 'P0:smart_core:app_search_config.get_search_contract',
  };
  const range = searchDefaults(store).page_size_range as Dict | undefined;
  return {
    min: requireDeclaredNumber(range?.min, { ...spec, missing: 'search.defaults.page_size_range.min' }),
    max: requireDeclaredNumber(range?.max, { ...spec, missing: 'search.defaults.page_size_range.max' }),
  };
}
