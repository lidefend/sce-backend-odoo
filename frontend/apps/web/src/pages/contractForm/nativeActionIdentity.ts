import { parseMaybeJsonRecord, toPositiveInt } from '../../app/contractRuntime';

export function nativeActionOccurrenceKey(value: unknown): string {
  const identity = parseMaybeJsonRecord(value);
  const type = String(identity.type || '').trim().toLowerCase();
  const name = String(identity.name || '').trim();
  const locator = String(identity.native_locator || identity.nativeLocator || '').trim();
  const occurrence = toPositiveInt(identity.occurrence_index || identity.occurrenceIndex) || 0;
  return type && name && locator && occurrence > 0 ? `${type}|${name}|${locator}|${occurrence}` : '';
}
