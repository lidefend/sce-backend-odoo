/**
 * Identity and application policy for one onchange roundtrip.
 *
 * An onchange response is derived data computed from an earlier draft. It must
 * never overwrite newer local input, and it must never land on another record's
 * form data. Every roundtrip therefore carries the record it was computed for,
 * its issue order, and the draft values it was computed from; the response is
 * then planned against the draft that is on screen when it arrives.
 */
export type OnchangeRoundtripTicket = {
  sequence: number;
  recordKey: string;
  snapshot: Record<string, string>;
};

export type OnchangeApplicationPlan = {
  dropped: boolean;
  patch: Record<string, unknown>;
};

export function onchangeRecordKey(model: string, recordId: number | null | undefined): string {
  return `${String(model || '').trim()}:${recordId ?? 'new'}`;
}

export function createOnchangeRoundtripTicket(params: {
  sequence: number;
  model: string;
  recordId: number | null | undefined;
  snapshot: Record<string, string>;
}): OnchangeRoundtripTicket {
  return {
    sequence: params.sequence,
    recordKey: onchangeRecordKey(params.model, params.recordId),
    snapshot: params.snapshot,
  };
}

/**
 * Snapshot the comparable draft value of every field a response may patch.
 * The caller passes the same comparability function the form already uses, so
 * relations, dates and x2many values compare in their transport representation.
 */
export function buildOnchangeDraftSnapshot(
  fieldNames: string[],
  comparableValue: (name: string) => string,
): Record<string, string> {
  const snapshot: Record<string, string> = {};
  for (const name of fieldNames) snapshot[name] = comparableValue(name);
  return snapshot;
}

/**
 * A response may write only while it is the newest roundtrip issued for the
 * record still on screen. Anything else describes a draft that no longer exists:
 * an older roundtrip was superseded by newer input, or the form moved to another
 * record while the request was in flight.
 */
export function onchangeResponseStillApplies(
  ticket: OnchangeRoundtripTicket,
  latestSequence: number,
  currentRecordKey: string,
): boolean {
  return ticket.sequence === latestSequence && ticket.recordKey === currentRecordKey;
}

/**
 * Per-field rule: a field whose local value moved after the request was sent
 * keeps the local value. The server answered from the value it received, so its
 * answer for that field is already stale, and the field's own roundtrip carries
 * the authoritative result.
 */
export function onchangePatchFieldStillApplies(
  ticket: OnchangeRoundtripTicket,
  fieldName: string,
  currentComparableValue: string,
): boolean {
  if (!Object.prototype.hasOwnProperty.call(ticket.snapshot, fieldName)) return false;
  return ticket.snapshot[fieldName] === currentComparableValue;
}

export function planOnchangeApplication(params: {
  ticket: OnchangeRoundtripTicket;
  latestSequence: number;
  currentRecordKey: string;
  patch: Record<string, unknown>;
  comparableValue: (name: string) => string;
}): OnchangeApplicationPlan {
  if (!onchangeResponseStillApplies(params.ticket, params.latestSequence, params.currentRecordKey)) {
    return { dropped: true, patch: {} };
  }
  const patch: Record<string, unknown> = {};
  for (const [name, value] of Object.entries(params.patch)) {
    if (!onchangePatchFieldStillApplies(params.ticket, name, params.comparableValue(name))) continue;
    patch[name] = value;
  }
  return { dropped: false, patch };
}
