import { onBeforeUnmount, onMounted } from 'vue';
import { ensureThemeRuntimeWatch, stopThemeRuntime } from './theme';
import { startTdesignGlobalConfigRuntime, stopTdesignGlobalConfigRuntime } from './tdesignGlobalConfig';

export function startThemeApplicationRuntime(): void {
  ensureThemeRuntimeWatch();
  startTdesignGlobalConfigRuntime();
}

export function stopThemeApplicationRuntime(): void {
  stopTdesignGlobalConfigRuntime();
  stopThemeRuntime();
}

/** Own application-lifetime listeners at the root. Route components must not
 * start or stop them; root remounts (including HMR) restore them idempotently. */
export function useThemeApplicationRuntime(): void {
  onMounted(startThemeApplicationRuntime);
  onBeforeUnmount(stopThemeApplicationRuntime);
}
