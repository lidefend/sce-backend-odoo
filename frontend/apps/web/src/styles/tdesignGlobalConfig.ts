import { computed, ref } from 'vue';
import type { TDesignGlobalConfigProvider } from '../components/design-system/tdesignPrimitiveBridge';
import { onReducedMotionPreferenceChange, reducedMotionPreference } from './theme';

const TD_ANIMATIONS = ['ripple', 'expand', 'fade'] as const;
const reducedMotion = ref(reducedMotionPreference());
let stopReducedMotionSubscription: (() => void) | null = null;

export function startTdesignGlobalConfigRuntime(): () => void {
  reducedMotion.value = reducedMotionPreference();
  if (stopReducedMotionSubscription) return stopReducedMotionSubscription;
  stopReducedMotionSubscription = onReducedMotionPreferenceChange((reduced) => {
    reducedMotion.value = reduced;
  });
  return stopReducedMotionSubscription;
}

export function stopTdesignGlobalConfigRuntime(): void {
  stopReducedMotionSubscription?.();
  stopReducedMotionSubscription = null;
}

export const tdesignGlobalConfig = computed<TDesignGlobalConfigProvider>(() => ({
  animation: reducedMotion.value
    ? { include: [], exclude: [...TD_ANIMATIONS] }
    : { include: [...TD_ANIMATIONS], exclude: [] },
}));
