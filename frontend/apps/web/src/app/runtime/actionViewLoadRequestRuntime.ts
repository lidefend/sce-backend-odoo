import { requireDeclaredNumber } from '../contract/contractGap';

type Dict = Record<string, unknown>;

export function resolveActionViewSortSeed(options: {
  currentSortRaw?: unknown;
  sceneReadyDefaultSortRaw?: unknown;
  sceneDefaultSortRaw?: unknown;
  searchDefaultOrderRaw?: unknown;
  viewOrderRaw?: unknown;
  metaOrderRaw?: unknown;
  fallbackSortRaw?: unknown;
}): string {
  const currentSort = String(options.currentSortRaw || '').trim();
  if (currentSort) return currentSort;
  const candidates = [
    options.sceneReadyDefaultSortRaw,
    options.sceneDefaultSortRaw,
    options.searchDefaultOrderRaw,
    options.viewOrderRaw,
    options.metaOrderRaw,
    options.fallbackSortRaw,
    'id desc',
  ];
  for (const item of candidates) {
    const value = String(item || '').trim();
    if (value) return value;
  }
  return 'id desc';
}

/**
 * 列表首屏每页条数的唯一来源：契约 `searchContract.defaults.limit`。
 * 前端不再持有缺省值，也不自行夹取范围；声明缺失即停机回声明层。
 */
export function resolveActionViewContractLimit(limitRaw?: unknown): number {
  return requireDeclaredNumber(limitRaw, {
    missing: 'search.defaults.limit',
    requiredDeclarationLayer: 'P0:smart_core:app_search_config.get_search_contract',
  });
}

export function buildActionViewListRequest(options: {
  model: string;
  requestedFields: string[];
  domain: unknown[];
  domainRaw: unknown;
  activeGroupByField: string;
  listOffset: number;
  groupWindowOffset: number;
  groupSampleLimit: number;
  contractLimit: number;
  groupPageOffsets: Record<string, number>;
  context: Dict;
  contextRaw: unknown;
  searchTerm: string;
  order: string;
  fieldSemantics?: Dict[];
}): Dict {
  const grouped = Boolean(options.activeGroupByField);
  return {
    model: options.model,
    fields: options.requestedFields.length ? options.requestedFields : ['id', 'name'],
    domain: options.domain,
    domain_raw: options.domainRaw,
    need_total: true,
    need_aggregates: true,
    field_semantics: Array.isArray(options.fieldSemantics) ? options.fieldSemantics : [],
    group_by: grouped ? options.activeGroupByField : undefined,
    group_offset: grouped ? Math.max(0, Math.trunc(options.groupWindowOffset || 0)) : 0,
    need_group_total: grouped,
    group_sample_limit: options.groupSampleLimit,
    group_limit: Math.min(50, Math.max(12, Number(options.contractLimit || 0))),
    group_page_size: options.groupSampleLimit,
    group_page_offsets: options.groupPageOffsets,
    context: options.context,
    context_raw: options.contextRaw,
    limit: options.contractLimit,
    offset: Math.max(0, Math.trunc(options.listOffset || 0)),
    search_term: options.searchTerm.trim() || undefined,
    order: options.order,
  };
}
