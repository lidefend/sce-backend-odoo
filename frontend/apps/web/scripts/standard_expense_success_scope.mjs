import { isDeepStrictEqual } from 'node:util';

export function permitsExpensePolicyWrite(role, body, permit) {
  const p = body?.params;
  return Boolean(permit && role === 'fixture_role_config_admin' && body?.intent === 'api.data'
    && p?.op === 'write' && p.model === 'sc.business.category' && isDeepStrictEqual(p.ids, [permit.id])
    && ['required', 'recommended'].includes(permit.value) && isDeepStrictEqual(p.vals, { attachment_policy: permit.value }));
}

export function expenseProbeWriteKind(role, body, scope) {
  if (!scope || role !== 'fixture_role_finance') return null;
  const p = body?.params;
  const file = scope.files ? scope.files[scope.uploadIndex] : { name: scope.filename, data: scope.data };
  if (scope.phase === 'create' && body?.intent === 'api.data' && p?.op === 'create' && p.model === 'sc.expense.claim'
    && /^TPL53-EXPENSE-SUCCESS-\d{13}$/.test(p.vals?.summary) && p.context?.company_id === 8
    && isDeepStrictEqual(p, scope.request)) return 'create';
  if (scope.phase === 'upload' && body?.intent === 'file.upload' && p?.model === 'sc.expense.claim'
    && p.res_id === scope.id && file && p.name === file.name && p.data === file.data && p.mimetype === 'text/plain') return 'upload';
  if (scope.phase === 'submit' && body?.intent === 'execute_button' && p?.model === 'sc.expense.claim'
    && p.res_id === scope.id && p.button?.name === 'action_submit' && p.button.type === 'object'
    && Number(body.meta?.menu_id) === Number(scope.request.context.menu_id)
    && Number(body.meta?.action_id) === Number(scope.request.context.action_id)) return 'submit';
  return null;
}
