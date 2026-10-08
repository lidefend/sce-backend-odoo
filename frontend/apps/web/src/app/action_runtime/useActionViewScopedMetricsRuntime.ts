import { readTotalFromListResult } from '../runtime/actionViewRequestRuntime';

type Dict = Record<string, unknown>;

type UseActionViewScopedMetricsRuntimeOptions = {
  listRecordsRaw: (payload: Dict) => Promise<{ data: unknown }>;
  resolveCollectionStateCell: (row: Record<string, unknown>) => { text: string; tone: string };
  isCompletedState: (stateText: string, tone: string) => boolean;
  resolveCollectionAmount: (row: Record<string, unknown>) => number;
  resolveCollectionMetricFields: () => string[];
  /** 取数规模一律由契约声明决定（列表页每页条数声明上界），前端不持有产品常量。 */
  resolveDeclaredScopePageLimit: () => number;
};

export function useActionViewScopedMetricsRuntime(options: UseActionViewScopedMetricsRuntimeOptions) {
  async function fetchScopedTotal(params: {
    model: string;
    domain: unknown[];
    domainRaw: string;
    context: Record<string, unknown>;
    contextRaw: string;
    searchTerm: string;
    order: string;
  }) {
    const result = await options.listRecordsRaw({
      model: params.model,
      fields: ['id'],
      domain: params.domain,
      domain_raw: params.domainRaw,
      need_total: true,
      context: params.context,
      context_raw: params.contextRaw,
      limit: options.resolveDeclaredScopePageLimit(),
      offset: 0,
      search_term: params.searchTerm || undefined,
      order: params.order,
    });
    return readTotalFromListResult(result.data);
  }

  async function fetchCollectionScopeMetrics(params: {
    model: string;
    domain: unknown[];
    domainRaw: string;
    context: Record<string, unknown>;
    contextRaw: string;
    searchTerm: string;
    order: string;
  }) {
    const fields = Array.from(new Set(['id', ...options.resolveCollectionMetricFields()]));
    // 扫描分块规模来自契约声明；扫描上界来自后端声明的 total，而不是前端页数上限。
    const pageLimit = options.resolveDeclaredScopePageLimit();
    let offset = 0;
    let declaredTotal = 0;
    let warning = 0;
    let done = 0;
    let amount = 0;
    for (;;) {
      const result = await options.listRecordsRaw({
        model: params.model,
        fields,
        domain: params.domain,
        domain_raw: params.domainRaw,
        need_total: offset === 0,
        context: params.context,
        context_raw: params.contextRaw,
        limit: pageLimit,
        offset,
        search_term: params.searchTerm || undefined,
        order: params.order,
      });
      const payload = result.data && typeof result.data === 'object'
        ? (result.data as Record<string, unknown>)
        : {};
      const pageRows = Array.isArray(payload.records)
        ? (payload.records as Array<Record<string, unknown>>)
        : [];
      if (!pageRows.length) break;
      if (offset === 0) declaredTotal = readTotalFromListResult(result.data);
      pageRows.forEach((row) => {
        const state = options.resolveCollectionStateCell(row);
        if (state.tone === 'danger' || state.tone === 'warning') warning += 1;
        if (options.isCompletedState(String(state.text || ''), state.tone)) done += 1;
        amount += options.resolveCollectionAmount(row);
      });
      const nextOffset = Number(payload.next_offset || 0);
      const next = Number.isFinite(nextOffset) && nextOffset > offset
        ? Math.trunc(nextOffset)
        : offset + pageRows.length;
      if (next <= offset) break;
      offset = next;
      if (pageRows.length < pageLimit) break;
      if (declaredTotal > 0 && offset >= declaredTotal) break;
    }
    return { warning, done, amount };
  }

  return {
    fetchScopedTotal,
    fetchCollectionScopeMetrics,
  };
}
