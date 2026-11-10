type LogArgs = readonly unknown[];
type ConsoleSink = Pick<Console, 'debug' | 'info' | 'warn' | 'error'>;

function runtimeDebugRequested(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    if (window.localStorage.getItem('DEBUG_INTENT') === '1') return true;
  } catch {
    // Storage can be unavailable in locked-down browser contexts.
  }
  return new URLSearchParams(window.location.search).get('debug') === '1';
}

export function createLogger(
  env: Record<string, unknown> = import.meta.env || {},
  sink: ConsoleSink = console,
) {
  const dev = env.DEV === true;
  const debugConfigured = ['1', 'true', 'yes', 'on']
    .includes(String(env.VITE_DEBUG_LOGS || '').trim().toLowerCase());
  return Object.freeze({
    debug(message: string, ...args: LogArgs) {
      if ((dev && debugConfigured) || runtimeDebugRequested()) sink.debug(message, ...args);
    },
    info(message: string, ...args: LogArgs) {
      if ((dev && debugConfigured) || runtimeDebugRequested()) sink.info(message, ...args);
    },
    warn(message: string, ...args: LogArgs) {
      if (dev) sink.warn(message, ...args);
    },
    error(message: string, ...args: LogArgs) {
      sink.error(message, ...args);
    },
  });
}

export const logger = createLogger();
