import type { ChatterTimelineEntry } from '../../api/chatter';
import type { CanonicalAuditEvent } from '../../app/presentation/canonicalFormRenderModel';

export function normalizeProfessionalAuditEvent(entry: ChatterTimelineEntry): CanonicalAuditEvent | null {
  if (entry.type !== 'audit' || !entry.audit) return null;
  const actor = String(entry.audit.actor || '').trim();
  const occurredAt = String(entry.audit.occurred_at || '').trim();
  const event = String(entry.audit.event || '').trim();
  const result = String(entry.audit.result || '').trim();
  if (!entry.key || !actor || !occurredAt || !event || !result) return null;
  return Object.freeze({
    key: String(entry.key),
    actor,
    occurredAt,
    event,
    result,
    detail: String(entry.body || '').trim(),
  });
}

export function resolveProfessionalAuditEvents(entries: readonly ChatterTimelineEntry[]): CanonicalAuditEvent[] {
  return entries.flatMap((entry) => {
    const normalized = normalizeProfessionalAuditEvent(entry);
    return normalized ? [normalized] : [];
  });
}

export function formatProfessionalAuditTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(parsed);
}
