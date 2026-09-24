/**
 * Request identity for concurrent read coalescing.
 *
 * A coalescing key has to cover every request parameter that can change the
 * response. An allowlist of "known" keys silently merged different requests:
 * `search_term`, `offset`, `order`, grouping and domain_raw were omitted, so a
 * new keyword could reuse an in-flight request for a previous keyword and the
 * caller never received its own result. The whole normalized payload is the
 * identity instead, which also keeps future op-specific keys correct by
 * construction.
 *
 * The normalization only removes values that cannot reach the server
 * (`undefined`, which JSON serialization drops) and sorts object keys so that
 * two equivalent payloads built in a different property order still share one
 * identity. Array order is preserved because it is significant for `domain`.
 */
export function canonicalIntentRequestValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonicalIntentRequestValue);
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const normalized: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) {
      const item = record[key];
      if (item === undefined) continue;
      normalized[key] = canonicalIntentRequestValue(item);
    }
    return normalized;
  }
  return value;
}

export function buildIdempotentIntentIdentity(payload: {
  intent?: unknown;
  params?: unknown;
  context?: unknown;
}): string {
  const intent = String(payload?.intent ?? '').trim();
  const params = payload?.params && typeof payload.params === 'object' && !Array.isArray(payload.params)
    ? payload.params as Record<string, unknown>
    : {};
  const context = payload?.context === undefined ? null : canonicalIntentRequestValue(payload.context);
  return JSON.stringify({
    intent,
    context,
    params: canonicalIntentRequestValue(params),
  });
}
