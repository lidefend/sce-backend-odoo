import { isDeepStrictEqual } from 'node:util';

export function documentFlowWriteKind(role, body, scope) {
  const r = scope?.request;
  if (!scope || scope.model !== 'sc.project.document' || !/^TPL53-DOCUMENT-FLOW-\d{13}$/.test(scope.marker)
    || ![scope.projectId, scope.docTypeId, scope.menuId, scope.actionId].every(id => Number.isInteger(id) && id > 0)
    || r?.model !== scope.model || r.op !== 'create' || r.vals?.name !== scope.marker
    || Object.keys(r).some(key => !['op', 'model', 'vals', 'context'].includes(key))
    || r.vals.project_id !== scope.projectId || r.vals.doc_type_id !== scope.docTypeId
    || r.context?.company_id !== 8 || Number(r.context.menu_id) !== scope.menuId || Number(r.context.action_id) !== scope.actionId
    || Object.keys(r.context).some(key => key.startsWith('default_') || /sudo|force|skip|token/i.test(key))) return null;
  const safeContext = context => context === undefined || (context && typeof context === 'object' && !Array.isArray(context)
    && Object.entries(context).every(([key, value]) => {
      const expected = { company_id: 8, allowed_company_ids: [8], lang: 'zh_CN', project_id: scope.projectId,
        menu_id: scope.menuId, action_id: scope.actionId, active_model: scope.model,
        active_id: scope.id, active_ids: scope.id ? [scope.id] : [] };
      return Object.hasOwn(expected, key) && (['menu_id', 'action_id'].includes(key)
        ? Number(value) === expected[key] : isDeepStrictEqual(value, expected[key]));
    }));
  if (!safeContext(r.context) || !safeContext(body?.context) || !safeContext(body?.params?.context)) return null;
  const defaults = { document_kind: 'site', company_id: 8, responsible_id: scope.responsibleId, is_mandatory: false, attachment_ids: [[6, 0, []]] };
  const empty = ['wbs_id', 'task_id', 'contract_id', 'doc_subtype_id', 'date_doc', 'version', 'note'];
  if (Object.entries(r.vals).some(([key, value]) => !['name', 'project_id', 'doc_type_id'].includes(key)
    && !(Object.hasOwn(defaults, key) && defaults[key] !== undefined && isDeepStrictEqual(value, defaults[key]))
    && !(empty.includes(key) && [false, null, ''].includes(value)))) return null;
  const p = body?.params;
  if (scope.phase === 'create' && role === 'fixture_role_pm' && body?.intent === 'api.data' && isDeepStrictEqual(p, r)) return 'create';
  if (!Number.isInteger(scope.id) || scope.id <= 0 || body?.intent !== 'execute_button'
    || p?.model !== scope.model || p.res_id !== scope.id || p.button?.type !== 'object'
    || Object.keys(p).some(key => !['model', 'res_id', 'button', 'context'].includes(key))
    || (p.button.context !== undefined && !isDeepStrictEqual(p.button.context, {}))) return null;
  if (scope.phase === 'approve' && role === 'fixture_role_executive' && p.button.name === 'validate_tier'
    && scope.approvalOrigin?.source === 'tier.review' && Number.isInteger(scope.approvalOrigin.id) && scope.approvalOrigin.id > 0
    && isDeepStrictEqual(body.meta?.work_item_origin, scope.approvalOrigin)) return 'approve';
  if (role !== 'fixture_role_pm' || Number(body.meta?.menu_id) !== scope.menuId || Number(body.meta?.action_id) !== scope.actionId) return null;
  return ['submit', 'archive'].includes(scope.phase) && ({ submit: 'action_submit', archive: 'action_archive' })[scope.phase] === p.button.name ? scope.phase : null;
}

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

// The native continuation is captured before permitting any business write.
function paymentReviewCreateMatchesContract(p, scope) {
  const action = scope.continuation;
  const defaults = action?.context;
  const source = scope.baseline?.source?.[0];
  if (action?.id !== 803 || action?.menu_id !== 335 || action?.res_model !== scope.model
    || defaults?.default_payment_request_id !== 1710 || defaults?.company_id !== 8
    || source?.id !== 1710 || source?.company_id?.[0] !== 8 || source?.state !== 'approved'
    || source.unpaid_amount < 1 || defaults.default_planned_amount !== source.amount
    || defaults.default_project_id !== source.project_id?.[0]
    || defaults.default_partner_id !== source.partner_id?.[0]) return false;
  const context = p.context || {};
  const defaultKeys = Object.keys(context).filter(key => key.startsWith('default_'));
  if (!defaultKeys.includes('default_payment_request_id')
    || defaultKeys.some(key => !Object.hasOwn(defaults, key) || !isDeepStrictEqual(context[key], defaults[key]))
    || Object.keys(defaults).filter(key => key.startsWith('default_')).some(key => !isDeepStrictEqual(context[key], defaults[key]))) return false;
  const vals = p.vals || {};
  const expected = {
    business_category_id: defaults.default_business_category_id,
    date_payment: scope.paymentDate,
    paid_amount: 1, planned_amount: source.amount, payment_method: '银行转账',
    document_no: defaults.default_document_no, note: scope.marker,
    payment_account_name: 'FE Company A Operating Account', payment_bank_name: 'FE Construction Bank',
    payment_account_no: 'FE-PAYER-0001', attachment_ids: [[6, 0, []]],
  };
  return defaults.default_business_category_id === 16
    && defaults.default_business_category_code === 'finance.payment.execution.partner'
    && /^\d{4}-\d{2}-\d{2}$/.test(scope.paymentDate || '')
    && typeof defaults.default_document_no === 'string' && Boolean(defaults.default_document_no)
    && isDeepStrictEqual(vals, expected);
}

export function paymentReviewWriteKind(role, body, scope) {
  if (scope?.model !== 'sc.payment.execution' || scope.source?.id !== 1710 || scope.source?.company_id !== 8
    || !/^TPL53-PAYMENT-REVIEW-\d{13}$/.test(scope.marker)
    || !Array.isArray(scope.baseline?.execution_ids) || !scope.baseline.execution_ids.includes(186)) return null;
  const p = body?.params;
  if (scope.approvalFlow === true && role === 'fixture_role_config_admin'
    && scope.configContext?.company_id === 8) {
    const original = scope.baseline.policies?.find(policy => policy.id === 18);
    if (!original || original.company_id?.[0] !== 8 || original.target_model !== scope.model) return null;
    if (scope.phase === 'flow_config' && body?.intent === 'sc.approval_policy.config.set'
      && isDeepStrictEqual(p, { model: scope.model, approval_required: true, mode: 'single',
        manager_scope_key: 'finance_manager', context: scope.configContext })) return 'flow_config';
    if (scope.phase === 'flow_steps' && body?.intent === 'sc.approval_policy.steps.set'
      && Array.isArray(paymentReviewFlowSteps(scope))
      && isDeepStrictEqual(p, { model: scope.model, steps: paymentReviewFlowSteps(scope), context: scope.configContext })) return 'flow_steps';
    if (scope.phase === 'restore_steps' && body?.intent === 'sc.approval_policy.steps.set'
      && paymentReviewOriginalSteps(scope).length === 1 && paymentReviewOriginalSteps(scope)[0].id === 2187
      && isDeepStrictEqual(p, { model: scope.model, steps: paymentReviewOriginalSteps(scope), context: scope.configContext })) return 'restore_steps';
  }
  if (scope.approvalToggle === true && scope.phase === 'config_disable'
    && role === 'fixture_role_config_admin' && body?.intent === 'sc.approval_policy.config.set'
    && scope.baseline.policies?.some(policy => policy.id === 18 && policy.company_id?.[0] === 8
      && policy.target_model === scope.model && policy.approval_required === true && policy.mode === 'single')
    && scope.configContext?.company_id === 8
    && isDeepStrictEqual(p, { model: scope.model, approval_required: false, mode: 'none', manager_scope_key: 'finance_manager',
      context: scope.configContext })) return 'config_disable';
  if (scope.phase === 'open' && role === 'fixture_role_pfl035_finance_user' && body?.intent === 'execute_button'
    && p?.model === 'payment.request' && p.res_id === 1710 && p.button?.type === 'object'
    && p.button.name === 'action_create_payment_execution' && Number(body.meta?.action_id) === 775
    && Number(body.meta?.menu_id) === 545) return 'open';
  if (scope.phase === 'create' && role === 'fixture_role_pfl035_finance_user' && body?.intent === 'api.data'
    && p?.op === 'create' && p.model === scope.model && isDeepStrictEqual(p, scope.request)
    && p.context?.company_id === 8 && Number(p.context?.action_id) === 803 && Number(p.context?.menu_id) === 335
    && paymentReviewCreateMatchesContract(p, scope)) return 'create';
  if (!Number.isInteger(scope.id) || scope.id <= 0 || scope.baseline.execution_ids?.includes(scope.id)
    || body?.intent !== 'execute_button' || p?.model !== scope.model || p.res_id !== scope.id || p.button?.type !== 'object') return null;
  if (scope.phase === 'submit' && role === 'fixture_role_pfl035_finance_user' && p.button.name === 'action_confirm'
    && Number(body.meta?.action_id) === 803 && Number(body.meta?.menu_id) === 335) return 'submit';
  const reviewer = scope.approvalFlow === true && scope.reviewStage === 2 ? 'fixture_role_executive' : 'fixture_role_finance';
  if (scope.phase === 'approve' && role === reviewer && p.button.name === 'validate_tier'
    && scope.origin?.source === 'tier.review' && Number.isInteger(scope.origin.id) && scope.origin.id > 0
    && isDeepStrictEqual(body.meta?.work_item_origin, scope.origin)) return 'approve';
  return null;
}

export function paymentReviewOriginalSteps(scope) {
  return (scope.baseline.steps || []).filter(step => step.policy_id?.[0] === 18 && step.active).map(step => ({
    id: step.id, name: step.name, approval_scope_key: step.approval_scope_key, active: true,
    amount_min: step.amount_min || false, amount_max: step.amount_max || false,
    condition_note: step.condition_note || '', note: step.note || '',
  }));
}

export function paymentReviewFlowSteps(scope) {
  const original = paymentReviewOriginalSteps(scope);
  if (original.length !== 1 || original[0].id !== 2187 || original[0].approval_scope_key !== 'finance_manager') return null;
  return [{ ...original[0], name: `${scope.marker}-财务复核` }, {
    name: `${scope.marker}-管理层终审`, approval_scope_key: 'executive', active: true,
    amount_min: false, amount_max: false, condition_note: '', note: '',
  }];
}

export function paymentSourceReceiptValid(r, source = r?.readback?.record) {
  const spec = { subcontract: [593, 592, 'sc.subcontract.settlement', 'subcontract_settlement_id', 'subcontractor_id'],
    rental: [592, 593, 'sc.material.rental.settlement', 'rental_settlement_id', 'supplier_id'] }[r?.kind];
  return Boolean(spec && r.status === 'passed' && r.committed === true && r.database === 'sc_frontend_acceptance'
    && r.uid === 30 && r.company_id === 8 && r.readback_uid === 30 && r.readback_sudo === false
    && r.source_preparation_only === true && r.ordinary_role_create_proof === false
    && r.preparation_uid === 30 && r.preparation_sudo === (r.kind === 'rental')
    && r.project_id === spec[0] && r.other_project_id === spec[1] && r.source_model === spec[2] && r.source_field === spec[3]
    && [r.source_id, r.partner_id, r.currency_id].every(id => Number.isInteger(id) && id > 0)
    && new RegExp(`^ITER-PAYMENT-SOURCE-${r.kind.toUpperCase()}-\\d{16}$`).test(r.marker)
    && source?.id === r.source_id && source.name === r.marker && source.state === 'confirmed'
    && source.project_id?.[0] === r.project_id && source.company_id?.[0] === 8 && source.create_uid?.[0] === 30
    && source[spec[4]]?.[0] === r.partner_id && source.currency_id?.[0] === r.currency_id && source.amount_total === 100
    && r.readback?.unreserved_amount === 100);
}

export function paymentSourceDraftWriteKind(role, body, scope) {
  const r = scope?.receipt, p = scope?.request;
  if (role !== 'fixture_role_finance' || scope?.phase !== 'create' || scope.id
    || !paymentSourceReceiptValid(r) || !paymentSourceReceiptValid(r, scope.source)
    || !/^TPL53-PAYMENT-SOURCE-(SUBCONTRACT|RENTAL)-\d{13}$/.test(scope.marker)
    || !scope.marker.includes(r.kind.toUpperCase()) || scope.menuId !== 545 || scope.actionId !== 775
    || body?.intent !== 'api.data' || p?.op !== 'create' || p.model !== 'payment.request'
    || Object.keys(body).some(key => !['intent', 'params', 'context', 'meta'].includes(key))
    || Object.keys(p).some(key => !['op', 'model', 'vals', 'context'].includes(key))) return null;
  const safeContext = c => c === undefined || (c && typeof c === 'object' && !Array.isArray(c)
    && Object.entries(c).every(([key, value]) => {
      const fixed = { company_id: 8, allowed_company_ids: [8], lang: 'zh_CN', project_id: r.project_id,
        menu_id: 545, action_id: 775, default_type: 'pay', default_business_category_code: 'finance.payment.apply.pay',
        search_default_type_pay: 1, search_default_group_by_project_id: 1 };
      return Object.hasOwn(fixed, key) && (['menu_id', 'action_id'].includes(key) ? Number(value) === fixed[key] : isDeepStrictEqual(value, fixed[key]));
    }));
  if (p.context?.company_id !== 8 || Number(p.context.menu_id) !== 545 || Number(p.context.action_id) !== 775
    || !safeContext(p.context) || !safeContext(body.context) || !safeContext(body.params?.context)) return null;
  const v = p.vals;
  if (!v || v.note !== scope.marker || v.project_id !== r.project_id || v[r.source_field] !== r.source_id || v.amount !== 100) return null;
  const fixed = { note: scope.marker, project_id: r.project_id, [r.source_field]: r.source_id, amount: 100,
    company_id: 8, partner_id: r.partner_id, currency_id: r.currency_id, type: 'pay', state: 'draft',
    date_request: scope.dateRequest, business_category_id: scope.businessCategoryId, attachment_ids: [[6, 0, []]],
    actual_payee_unit: scope.source[r.kind === 'rental' ? 'supplier_id' : 'subcontractor_id']?.[1] };
  const empty = ['contract_id', 'settlement_id', 'material_settlement_id', 'accepted_amount_uppercase', 'rental_settlement_id', 'subcontract_settlement_id', 'expense_claim_id',
    'payer_unit', 'actual_payee_unit', 'payment_account_name', 'payment_bank_name', 'payment_account_no'];
  if (Object.entries(v).some(([k, value]) => !(Object.hasOwn(fixed, k) && fixed[k] !== undefined && isDeepStrictEqual(value, fixed[k]))
    && !(empty.includes(k) && k !== r.source_field && [false, null, ''].includes(value)))) return null;
  if (v.date_request !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(scope.dateRequest)) return null;
  if (v.business_category_id !== undefined && (!Number.isInteger(scope.businessCategoryId) || scope.businessCategoryId <= 0)) return null;
  return isDeepStrictEqual(body.params, p) ? 'create' : null;
}
