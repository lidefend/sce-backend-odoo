import { computed, inject, provide, type ComputedRef } from 'vue';

const RUNTIME_TIME_ZONE = Symbol('runtime-time-zone');

function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

export function provideRuntimeTimeZone(source: () => unknown): ComputedRef<string> {
  const timeZone = computed(() => String(source() || '').trim() || browserTimeZone());
  provide(RUNTIME_TIME_ZONE, timeZone);
  return timeZone;
}

export function useRuntimeTimeZone(): ComputedRef<string> {
  return inject(RUNTIME_TIME_ZONE, computed(browserTimeZone));
}
