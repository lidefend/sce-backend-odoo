import { requireDeclaredNumber, requireDeclaredNumberList } from '../contract/contractGap';

type Dict = Record<string, unknown>;

function searchDefaults(contract: unknown): Dict {
  const root: Dict = contract && typeof contract === 'object' ? (contract as Dict) : {};
  const search: Dict = root.searchContract && typeof root.searchContract === 'object'
    ? (root.searchContract as Dict)
    : {};
  return search.defaults && typeof search.defaults === 'object' ? (search.defaults as Dict) : {};
}

/**
 * 列表页每页条数可选集合的唯一来源：契约 `searchContract.defaults.page_size_options`。
 * 前端只消费声明值，不再自造 `[10, 20, 50]` 之类的可选范围。
 */
export function resolveActionViewPageSizeOptions(contract: unknown): number[] {
  return requireDeclaredNumberList(searchDefaults(contract).page_size_options, {
    missing: 'search.defaults.page_size_options',
    requiredDeclarationLayer: 'P0:smart_core:app_search_config.get_search_contract',
  });
}

/**
 * 每页条数合法范围的唯一来源：契约 `searchContract.defaults.page_size_range`。
 */
export function resolveActionViewPageSizeRange(contract: unknown): { min: number; max: number } {
  const spec = {
    requiredDeclarationLayer: 'P0:smart_core:app_search_config.get_search_contract',
  };
  const range = searchDefaults(contract).page_size_range as Dict | undefined;
  return {
    min: requireDeclaredNumber(range?.min, { ...spec, missing: 'search.defaults.page_size_range.min' }),
    max: requireDeclaredNumber(range?.max, { ...spec, missing: 'search.defaults.page_size_range.max' }),
  };
}
