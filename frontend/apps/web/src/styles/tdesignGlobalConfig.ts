import { computed, ref } from 'vue';
import type { TDesignGlobalConfigProvider } from '../components/design-system/tdesignPrimitiveBridge';
import { onReducedMotionPreferenceChange, reducedMotionPreference } from './theme';

const TD_ANIMATIONS = ['ripple', 'expand', 'fade'] as const;
const reducedMotion = ref(reducedMotionPreference());

onReducedMotionPreferenceChange((reduced) => {
  reducedMotion.value = reduced;
});

export const tdesignGlobalConfig = computed<TDesignGlobalConfigProvider>(() => reducedMotion.value
  ? { animation: { include: [], exclude: [...TD_ANIMATIONS] } }
  : {});
