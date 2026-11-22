import type { RouteLocationRaw } from 'vue-router';

export type RouteFailureKind =
  | 'authentication'
  | 'forbidden'
  | 'not_found'
  | 'conflict'
  | 'service'
  | 'network'
  | 'unknown';

export type RouteFailure = {
  kind: RouteFailureKind;
  status: number;
  reasonCode: string;
  traceId: string;
};

type FailureRecord = {
  status?: unknown;
  code?: unknown;
  reasonCode?: unknown;
  traceId?: unknown;
  kind?: unknown;
};

function integerStatus(value: unknown): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 && parsed <= 599 ? parsed : 0;
}

function text(value: unknown): string {
  return String(value || '').trim();
}

export function classifyRouteFailure(error: unknown): RouteFailure {
  const record = error && typeof error === 'object' ? error as FailureRecord : {};
  const status = integerStatus(record.status) || integerStatus(record.code);
  const reasonCode = text(record.reasonCode) || (status ? `HTTP_${status}` : 'ROUTE_AUTHORITY_UNAVAILABLE');
  const traceId = text(record.traceId);
  if (status === 401) return { kind: 'authentication', status, reasonCode, traceId };
  if (status === 403) return { kind: 'forbidden', status, reasonCode, traceId };
  if (status === 404) return { kind: 'not_found', status, reasonCode, traceId };
  if (status === 409) return { kind: 'conflict', status, reasonCode, traceId };
  if (status >= 500) return { kind: 'service', status, reasonCode, traceId };
  if (!status || text(record.kind) === 'network') return { kind: 'network', status, reasonCode, traceId };
  return { kind: 'unknown', status, reasonCode, traceId };
}

export function routeFailurePresentation(kind: RouteFailureKind): { title: string; message: string } {
  if (kind === 'conflict') {
    return { title: '上下文已变化', message: '当前页面上下文已变化或发生冲突，请刷新后重试。' };
  }
  if (kind === 'service') {
    return { title: '服务暂时不可用', message: '服务端暂时无法完成请求，请稍后重试。' };
  }
  if (kind === 'network') {
    return { title: '通信异常', message: '无法连接服务，请检查网络后重试。' };
  }
  return { title: '请求未完成', message: '当前请求无法完成，请稍后重试。' };
}

function failureQuery(failure: RouteFailure, from: string): Record<string, string> {
  return {
    from,
    kind: failure.kind,
    reason: failure.reasonCode,
    ...(failure.status ? { status: String(failure.status) } : {}),
    ...(failure.traceId ? { trace_id: failure.traceId } : {}),
  };
}

export function routeFailureRedirect(error: unknown, from: string): RouteLocationRaw {
  const failure = classifyRouteFailure(error);
  if (failure.kind === 'authentication') {
    return { name: 'login', query: { redirect: from, reason: failure.reasonCode } };
  }
  if (failure.kind === 'forbidden') {
    return { name: 'access-denied', query: failureQuery(failure, from) };
  }
  if (failure.kind === 'not_found') {
    return { name: 'not-found', query: failureQuery(failure, from) };
  }
  return { name: 'route-error', query: failureQuery(failure, from) };
}
