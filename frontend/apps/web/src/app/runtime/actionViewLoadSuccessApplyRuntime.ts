import { mapActionViewGroupSummaryItems, resolveActionViewGroupWindowMetrics } from './actionViewGroupSummaryRuntime';
import { mapActionViewGroupedRows, resolveActionViewGroupedRowsRaw, resolveActionViewRecords } from './actionViewLoadResultRuntime';
import { resolveLoadSuccessWindowState } from './actionViewLoadSuccessRuntime';

export function resolveLoadSuccessRecordsState(options: {
  resultDataRaw: unknown;
}): Array<Record<string, unknown>> {
  return resolveActionViewRecords(options.resultDataRaw);
}

export function resolveLoadSuccessGroupSummaryState(options: {
  groupSummaryRaw: unknown;
  emptyLabel: string;
  buildGroupKey: (field: unknown, value: unknown, fallback: unknown) => string;
  maxItems?: number;
}) {
  return mapActionViewGroupSummaryItems({
    groupSummaryRaw: options.groupSummaryRaw,
    emptyLabel: options.emptyLabel,
    maxItems: options.maxItems,
    buildGroupKey: options.buildGroupKey,
  });
}

export function resolveLoadSuccessWindowApplyState(options: {
  groupPagingRaw: unknown;
  effectiveGroupOffset: number;
  summaryLength: number;
}) {
  const metrics = resolveActionViewGroupWindowMetrics({
    groupPagingRaw: options.groupPagingRaw,
    effectiveGroupOffset: options.effectiveGroupOffset,
    summaryLength: options.summaryLength,
  });
  return resolveLoadSuccessWindowState({
    groupWindowCount: metrics.groupWindowCount,
    groupWindowStart: metrics.groupWindowStart,
    groupWindowEnd: metrics.groupWindowEnd,
    groupWindowTotal: metrics.groupWindowTotal,
    groupWindowNextOffset: metrics.groupWindowNextOffset,
    groupWindowPrevOffset: metrics.groupWindowPrevOffset,
  });
}

export function resolveLoadSuccessGroupedRowsState(options: {
  resultDataRaw: unknown;
  groupPagingRaw: unknown;
  groupSampleLimit: number;
  groupPageOffsets: Record<string, number>;
  emptyLabel: string;
  maxItems?: number;
  buildGroupKey: (field: unknown, value: unknown, fallback: unknown) => string;
  normalizeGroupPageOffset: (offset: number, limit: number, total: number) => number;
}) {
  return mapActionViewGroupedRows({
    groupedRowsRaw: resolveActionViewGroupedRowsRaw(options.resultDataRaw),
    groupPagingRaw: options.groupPagingRaw,
    groupSampleLimit: options.groupSampleLimit,
    groupPageOffsets: options.groupPageOffsets,
    emptyLabel: options.emptyLabel,
    maxItems: options.maxItems,
    buildGroupKey: options.buildGroupKey,
    normalizeGroupPageOffset: options.normalizeGroupPageOffset,
  });
}
