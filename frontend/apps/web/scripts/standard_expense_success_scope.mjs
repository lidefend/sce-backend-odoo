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

export function diaryProbeWriteKind(role, body, scope) {
  if (!scope || role !== 'fixture_role_pm' || scope.model !== 'sc.construction.diary') return null;
  const p = body?.params;
  const r = scope.request;
  if (!/^TPL53-DIARY-SAVE-\d{13}$/.test(r?.vals?.title) || r?.vals?.project_id !== 10 || r?.context?.company_id !== 8) return null;
  if (scope.phase === 'create' && body?.intent === 'api.data' && p?.op === 'create'
    && p.model === scope.model && isDeepStrictEqual(p, r)) return 'create';
  if (scope.phase === 'submit' && Number.isInteger(scope.id) && scope.id > 0
    && body?.intent === 'execute_button' && p?.model === scope.model && p.res_id === scope.id
    && p.button?.name === 'action_confirm' && p.button.type === 'object'
    && Number(body.meta?.menu_id) === Number(r.context.menu_id)
    && Number(body.meta?.action_id) === Number(r.context.action_id)) return 'submit';
  return null;
}

export function eventProbeWriteKind(role, body, scope) {
  if (!scope || role !== 'fixture_role_contract_operator' || scope.model !== 'sc.contract.event') return null;
  const p = body?.params;
  const r = scope.request;
  if (!/^TPL53-EVENT-SAVE-\d{13}$/.test(r?.vals?.name) || !Number.isInteger(scope.projectId) || scope.projectId <= 0 || r?.vals?.project_id !== scope.projectId || r?.context?.company_id !== 8) return null;
  if (scope.phase === 'create' && body?.intent === 'api.data' && p?.op === 'create'
    && p.model === scope.model && isDeepStrictEqual(p, r)) return 'create';
  if (scope.phase === 'submit' && Number.isInteger(scope.id) && scope.id > 0
    && body?.intent === 'execute_button' && p?.model === scope.model && p.res_id === scope.id
    && p.button?.name === 'action_submit' && p.button.type === 'object'
    && Number(body.meta?.menu_id) === Number(r.context.menu_id)
    && Number(body.meta?.action_id) === Number(r.context.action_id)) return 'submit';
  return null;
}

export function reportProbeWriteKind(role, body, scope) {
  if (!scope || role !== 'fixture_role_pm' || scope.model !== 'sc.plan.report'
    || !/^TPL53-REPORT-SAVE-\d{13}$/.test(scope.marker)) return null;
  const p = body?.params;
  const parent = scope.parentRequest;
  if (parent?.model !== 'sc.plan' || parent?.vals?.project_id !== 10
    || parent.vals.name !== scope.marker.replace('REPORT-SAVE', 'REPORT-PARENT')
    || Object.keys(parent.vals).sort().join(',') !== 'name,project_id' || parent.context?.company_id !== 8) return null;
  if (scope.phase === 'parent' && body?.intent === 'api.data' && p?.op === 'create'
    && isDeepStrictEqual(p, parent)) return 'parent';
  if (scope.versionProbe === true && scope.phase === 'version-save' && body?.intent === 'api.data'
    && Number.isInteger(scope.parentId) && scope.parentId > 0) {
    const request = scope.versionRequest;
    const line = request?.vals?.version_ids?.[0];
    if (request?.op === 'write' && request.model === 'sc.plan' && request.context?.company_id === 8
      && isDeepStrictEqual(request.ids, [scope.parentId]) && Object.keys(request.vals).join(',') === 'version_ids'
      && request.vals.version_ids.length === 1 && line?.length === 3 && line[0] === 0 && line[1] === 0
      && Object.keys(line[2]).sort().join(',') === 'revision_type,version_date,version_no'
      && line[2].version_no === scope.marker.replace('REPORT-SAVE', 'VERSION-SAVE')
      && line[2].revision_type === 'adjustment' && /^\d{4}-\d{2}-\d{2}$/.test(line[2].version_date)
      && line[2].version_date === scope.versionDefaults?.version_date
      && isDeepStrictEqual(p, request)) return 'version-save';
    return null;
  }
  const request = scope.request;
  if (!Number.isInteger(scope.parentId) || scope.parentId <= 0 || request?.model !== scope.model
    || request?.vals?.plan_id !== scope.parentId || request?.vals?.name !== scope.marker || request?.context?.company_id !== 8
    || Object.keys(request.vals).sort().join(',') !== 'name,plan_id,summary') return null;
  if (scope.phase === 'create' && body?.intent === 'api.data' && p?.op === 'create'
    && isDeepStrictEqual(p, request)) return 'create';
  if (scope.phase === 'submit' && Number.isInteger(scope.id) && scope.id > 0
    && body?.intent === 'execute_button' && p?.model === scope.model && p.res_id === scope.id
    && p.button?.name === 'action_submit' && p.button.type === 'object'
    && Number(body.meta?.menu_id) === Number(request.context.menu_id)
    && Number(body.meta?.action_id) === Number(request.context.action_id)) return 'submit';
  return null;
}
