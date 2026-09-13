const KNOWN_AUXILIARY_LIMIT = 3;
const KNOWN_CONSOLE_MESSAGE = 'Failed to load resource: the server responded with a status of 500 (Internal Server Error)';
const INTENT_PATH = '/api/v1/intent';
const ALLOWED_PHASES = new Set([
  'personnel_initial_form',
  'assignment_create_edit',
  'assignment_deactivate_edit',
  'data_permission_inactive_form',
  'personnel_reactivation_form',
  'reactivated_refresh',
  'data_permission_same_fact_form',
  'personnel_final_deactivation_form',
]);

function isExactKnownHttpFailure(item, personId) {
  const params = item?.params || {};
  return Number(item?.status) === 500
    && item?.business_ok === false
    && item?.intent === 'api.onchange'
    && params.model === 'res.users'
    && params.op === ''
    && Array.isArray(params.ids)
    && params.ids.length === 0
    && params.action_id === null
    && params.menu_id === null
    && Number(params.record_id) === Number(personId)
    && item?.error?.code === 'INTERNAL_ERROR'
    && item?.error?.message === '内部错误'
    && ALLOWED_PHASES.has(item?.phase)
    && String(item?.url || '').includes(INTENT_PATH)
    && Number.isFinite(Number(item?.observed_at_ms));
}

function isMatchingConsoleError(item, failure) {
  return item?.type === 'console'
    && item?.message === KNOWN_CONSOLE_MESSAGE
    && item?.phase === failure?.phase
    && String(item?.location_url || '').includes(INTENT_PATH)
    && Number.isFinite(Number(item?.observed_at_ms))
    && Math.abs(Number(item.observed_at_ms) - Number(failure.observed_at_ms)) <= 3000;
}

export function classifyPersonnelAuthorizationJourneyFailures({ httpFailures, browserErrors, personId }) {
  const auxiliaryHttpFailures = [];
  const auxiliaryConsoleErrors = [];
  const blockingHttpFailures = [];
  const availableErrors = Array.isArray(browserErrors) ? [...browserErrors] : [];

  for (const failure of Array.isArray(httpFailures) ? httpFailures : []) {
    const consoleIndex = availableErrors.findIndex((item) => isMatchingConsoleError(item, failure));
    if (auxiliaryHttpFailures.length < KNOWN_AUXILIARY_LIMIT
      && isExactKnownHttpFailure(failure, personId)
      && consoleIndex >= 0) {
      auxiliaryHttpFailures.push(failure);
      auxiliaryConsoleErrors.push(availableErrors.splice(consoleIndex, 1)[0]);
    } else {
      blockingHttpFailures.push(failure);
    }
  }

  return {
    auxiliary_http_failures: auxiliaryHttpFailures,
    auxiliary_console_errors: auxiliaryConsoleErrors,
    blocking_http_failures: blockingHttpFailures,
    blocking_browser_errors: availableErrors,
  };
}

export const PERSONNEL_AUTHORIZATION_KNOWN_AUXILIARY_LIMIT = KNOWN_AUXILIARY_LIMIT;
