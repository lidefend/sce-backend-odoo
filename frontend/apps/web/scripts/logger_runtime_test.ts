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
assert.deepEqual(calls, ['error:visible-error']);

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

console.log('[logger-runtime] PASS quiet, verbose and production policies');
