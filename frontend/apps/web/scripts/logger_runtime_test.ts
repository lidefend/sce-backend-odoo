import assert from 'node:assert/strict';
import { createLogger } from '../src/utils/logger';

const calls: string[] = [];
const sink = {
  debug: (...args: unknown[]) => calls.push(`debug:${String(args[0])}`),
  info: (...args: unknown[]) => calls.push(`info:${String(args[0])}`),
  warn: (...args: unknown[]) => calls.push(`warn:${String(args[0])}`),
  error: (...args: unknown[]) => calls.push(`error:${String(args[0])}`),
};

const quiet = createLogger({ DEV: true, VITE_DEBUG_LOGS: '' }, sink);
quiet.debug('quiet-debug');
quiet.info('quiet-info');
quiet.warn('quiet-warn');
quiet.error('visible-error');
assert.deepEqual(calls, ['warn:quiet-warn', 'error:visible-error']);

const verbose = createLogger({ DEV: true, VITE_DEBUG_LOGS: 'true' }, sink);
calls.length = 0;
verbose.debug('debug');
verbose.info('info');
verbose.warn('warn');
verbose.error('error');
assert.deepEqual(calls, ['debug:debug', 'info:info', 'warn:warn', 'error:error']);

const production = createLogger({ DEV: false, VITE_DEBUG_LOGS: 'true' }, sink);
calls.length = 0;
production.debug('prod-debug');
production.info('prod-info');
production.warn('prod-warn');
production.error('prod-error');
assert.deepEqual(calls, ['error:prod-error']);

Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: {
    localStorage: { getItem: (key: string) => key === 'DEBUG_INTENT' ? '1' : null },
    location: { search: '' },
  },
});
const runtimeDebug = createLogger({ DEV: true, VITE_DEBUG_LOGS: '' }, sink);
calls.length = 0;
runtimeDebug.debug('runtime-debug');
runtimeDebug.info('runtime-info');
assert.deepEqual(calls, ['debug:runtime-debug', 'info:runtime-info']);

const productionRuntimeDebug = createLogger({ DEV: false, VITE_DEBUG_LOGS: '' }, sink);
calls.length = 0;
productionRuntimeDebug.debug('production-runtime-debug');
productionRuntimeDebug.info('production-runtime-info');
productionRuntimeDebug.warn('production-runtime-warn');
productionRuntimeDebug.error('production-runtime-error');
assert.deepEqual(calls, [
  'debug:production-runtime-debug',
  'info:production-runtime-info',
  'error:production-runtime-error',
]);

Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: {
    localStorage: { getItem: () => null },
    location: { search: '?debug=1' },
  },
});
const productionUrlDebug = createLogger({ DEV: false, VITE_DEBUG_LOGS: '' }, sink);
calls.length = 0;
productionUrlDebug.debug('production-url-debug');
productionUrlDebug.info('production-url-info');
assert.deepEqual(calls, ['debug:production-url-debug', 'info:production-url-info']);
Reflect.deleteProperty(globalThis, 'window');

console.log('[logger-runtime] PASS quiet, verbose, production and runtime opt-in policies');
