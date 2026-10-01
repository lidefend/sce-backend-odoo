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
  if (scope.versionProbe === true && scope.versionSubmitProbe === true && scope.phase === 'version-submit'
    && Number.isInteger(scope.versionId) && scope.versionId > 0 && Number.isInteger(scope.parentId) && scope.parentId > 0
    && body?.intent === 'execute_button' && p?.model === 'sc.plan.version' && p.res_id === scope.versionId
    && p.button?.name === 'action_submit' && p.button.type === 'object' && scope.versionActionContext
    && Number(body.meta?.menu_id || 0) === Number(scope.versionActionContext.menu_id || 0)
    && Number(body.meta?.action_id || 0) === Number(scope.versionActionContext.action_id || 0)) return 'version-submit';
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

export function planExecutionWriteKind(role, body, scope) {
  if (!scope?.planExecutionProbe || scope.versionProbe || role !== 'fixture_role_pm' || scope.model !== 'sc.plan.report'
    || !/^TPL53-REPORT-SAVE-\d{13}$/.test(scope.marker) || !Number.isInteger(scope.parentId) || scope.parentId <= 0) return null;
  const parent = scope.parentRequest;
  if (parent?.vals?.name !== scope.marker.replace('REPORT-SAVE', 'REPORT-PARENT') || parent.vals.project_id !== 10
    || parent.context?.company_id !== 8) return null;
  const p = body?.params;
  const method = { 'plan-confirm': 'action_confirm', 'plan-start': 'action_start', 'plan-done': 'action_done' }[scope.phase];
  if (method && body?.intent === 'execute_button' && p?.model === 'sc.plan' && p.res_id === scope.parentId
    && p.button?.name === method && p.button.type === 'object'
    && Number(body.meta?.menu_id) === Number(parent.context.menu_id) && Number(body.meta?.action_id) === Number(parent.context.action_id)) return scope.phase;
  if (!['node-save', 'node-progress', 'node-done'].includes(scope.phase) || body?.intent !== 'api.data') return null;
  const request = scope.planRequest;
  if (!isDeepStrictEqual(p, request) || request?.model !== 'sc.plan' || request.op !== 'write'
    || !isDeepStrictEqual(request.ids, [scope.parentId]) || request.context?.company_id !== 8
    || Object.keys(request.vals || {}).join(',') !== 'line_ids' || request.vals.line_ids?.length !== 1) return null;
  const line = request.vals.line_ids[0];
  if (!Array.isArray(line) || line.length !== 3 || !line[2] || typeof line[2] !== 'object') return null;
  if (scope.phase === 'node-save') {
    return line[0] === 0 && line[1] === 0 && line[2].name === scope.marker.replace('REPORT-SAVE', 'PLAN-NODE')
      && Object.keys(line[2]).every(key => ['name', 'sequence', 'node_type'].includes(key))
      && (line[2].sequence === undefined || line[2].sequence === 10) && (line[2].node_type === undefined || line[2].node_type === 'task') ? scope.phase : null;
  }
  return Number.isInteger(scope.nodeId) && scope.nodeId > 0 && line[0] === 1 && line[1] === scope.nodeId
    && Object.keys(line[2]).sort().join(',') === 'progress_rate,state'
    && line[2].progress_rate === (scope.phase === 'node-progress' ? 50 : 100)
    && line[2].state === (scope.phase === 'node-progress' ? 'in_progress' : 'done') ? scope.phase : null;
}

export function versionReviewWriteKind(role, body, scope) {
  if (!scope?.versionReviewProbe || !scope.versionProbe || !scope.versionSubmitProbe || scope.planExecutionProbe
    || scope.model !== 'sc.plan.report' || !/^TPL53-REPORT-SAVE-\d{13}$/.test(scope.marker)
    || !Number.isInteger(scope.approvalBaseline?.reviewer_id) || scope.approvalBaseline.reviewer_id <= 0) return null;
  const p = body?.params;
  if (role === 'fixture_role_config_admin' && scope.phase === 'version-config'
    && body.intent === 'sc.approval_policy.config.set' && isDeepStrictEqual(p, {
      model: 'sc.plan.version', approval_required: true, mode: 'single', manager_scope_key: 'executive',
    })) return 'version-config';
  if (role === 'fixture_role_config_admin' && scope.phase === 'version-steps'
    && body.intent === 'sc.approval_policy.steps.set' && isDeepStrictEqual(p, {
      model: 'sc.plan.version', steps: [{ name: `${scope.marker}-审批`, approval_scope_key: 'executive',
        active: true, amount_min: false, amount_max: false, condition_note: '', note: '' }],
    })) return 'version-steps';
  if (role === 'fixture_role_executive' && scope.phase === 'version-approve'
    && body.intent === 'execute_button' && p?.model === 'sc.plan.version'
    && Number.isInteger(scope.versionId) && scope.versionId > 0 && p.res_id === scope.versionId
    && p.button?.name === 'validate_tier' && p.button.type === 'object'
    && scope.approvalOrigin?.source === 'tier.review' && Number.isInteger(scope.approvalOrigin.id) && scope.approvalOrigin.id > 0
    && isDeepStrictEqual(body.meta?.work_item_origin, scope.approvalOrigin)) return 'version-approve';
  return null;
}

export function paymentReviewWriteKind(role, body, scope) {
  if (scope?.model !== 'sc.payment.execution' || scope.source?.id !== 1710 || scope.source?.company_id !== 8
    || !/^TPL53-PAYMENT-REVIEW-\d{13}$/.test(scope.marker)
    || !Array.isArray(scope.baseline?.execution_ids) || !scope.baseline.execution_ids.includes(186)) return null;
  const p = body?.params;
  if (scope.phase === 'create' && role === 'fixture_role_finance' && body?.intent === 'api.data'
    && p?.op === 'create' && p.model === scope.model && isDeepStrictEqual(p, scope.request)
    && p.context?.company_id === 8 && Number(p.context?.action_id) === 777 && Number(p.context?.menu_id) === 547
    && p.vals?.payment_request_id === 1710 && p.vals?.paid_amount === 1 && p.vals?.note === scope.marker
    && Object.keys(p.vals).every(key => ['payment_request_id', 'paid_amount', 'note', 'payment_account_name',
      'payment_bank_name', 'payment_account_no', 'payment_method'].includes(key))) return 'create';
  if (!Number.isInteger(scope.id) || scope.id <= 0 || scope.baseline.execution_ids?.includes(scope.id)
    || body?.intent !== 'execute_button' || p?.model !== scope.model || p.res_id !== scope.id || p.button?.type !== 'object') return null;
  if (scope.phase === 'submit' && role === 'fixture_role_pfl035_finance_user' && p.button.name === 'action_confirm'
    && Number(body.meta?.action_id) === 777 && Number(body.meta?.menu_id) === 547) return 'submit';
  if (scope.phase === 'approve' && role === 'fixture_role_finance' && p.button.name === 'validate_tier'
    && scope.origin?.source === 'tier.review' && Number.isInteger(scope.origin.id) && scope.origin.id > 0
    && isDeepStrictEqual(body.meta?.work_item_origin, scope.origin)) return 'approve';
  return null;
}
