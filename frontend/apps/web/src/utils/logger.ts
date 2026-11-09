type LogArgs = readonly unknown[];
type ConsoleSink = Pick<Console, 'debug' | 'info' | 'warn' | 'error'>;

export function createLogger(
  env: Record<string, unknown> = import.meta.env || {},
  sink: ConsoleSink = console,
) {
  const debugEnabled = env.DEV === true
    && ['1', 'true', 'yes', 'on'].includes(String(env.VITE_DEBUG_LOGS || '').trim().toLowerCase());
  return Object.freeze({
    debug(message: string, ...args: LogArgs) {
      if (debugEnabled) sink.debug(message, ...args);
    },
    info(message: string, ...args: LogArgs) {
      if (debugEnabled) sink.info(message, ...args);
    },
    warn(message: string, ...args: LogArgs) {
      if (debugEnabled) sink.warn(message, ...args);
    },
    error(message: string, ...args: LogArgs) {
      sink.error(message, ...args);
    },
  });
}

export const logger = createLogger();
