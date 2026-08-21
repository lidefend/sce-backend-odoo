import assert from 'node:assert/strict';

function asRecord(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function positiveInteger(value) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

export function parseActionRoute(route) {
  const url = new URL(String(route || ''), 'http://runtime.invalid');
  const match = url.pathname.match(/^\/a\/(\d+)$/);
  assert(match, `editable form discovery requires an action route: ${route}`);
  const actionId = positiveInteger(match[1]);
  const menuId = positiveInteger(url.searchParams.get('menu_id'));
  assert(actionId, `editable form discovery requires a positive action id: ${route}`);
  return { actionId, menuId };
}

export function extractUnifiedContract(envelope) {
  const body = asRecord(envelope);
  return asRecord(body.data);
}

function contractModel(contract) {
  const pageInfo = asRecord(contract.pageInfo || contract.page_info);
  return String(pageInfo.model || contract.model || '').trim();
}

function primaryDataSourceParams(contract) {
  const dataContract = asRecord(contract.dataContract || contract.data_contract);
  const dataSource = asRecord(dataContract.dataSource || dataContract.data_source);
  const primary = asRecord(dataSource.primary);
  return asRecord(primary.params || primary.parameters);
}

export function isEditableFormContract(envelope) {
  const contract = extractUnifiedContract(envelope);
  const statusContract = asRecord(contract.statusContract || contract.status_contract);
  const globalStatus = asRecord(statusContract.globalStatus || statusContract.global_status);
  return String(globalStatus.pageAuth || globalStatus.page_auth || '').trim().toLowerCase() === 'edit';
}

function intentSucceeded(envelope) {
  const body = asRecord(envelope);
  return body.ok === true && (!body.status || Number(body.status) < 400);
}

function intentFailureDetail(envelope) {
  const body = asRecord(envelope);
  return JSON.stringify(body.error || body.data || body).slice(0, 600);
}

function uniqueOrders(sourceOrder) {
  return ['id asc', String(sourceOrder || '').trim(), 'id desc'].filter((value, index, rows) => value && rows.indexOf(value) === index);
}

export function editableFormRoute({ model, recordId, actionId, menuId }) {
  const query = new URLSearchParams({ action_id: String(actionId) });
  if (menuId > 0) query.set('menu_id', String(menuId));
  return `/f/${encodeURIComponent(model)}/${recordId}?${query.toString()}`;
}

export async function discoverEditableFormRoute({ listRoute, requestIntent, candidateLimit = 40 }) {
  assert.equal(typeof requestIntent, 'function', 'editable form discovery requires an intent requester');
  const { actionId, menuId } = parseActionRoute(listRoute);
  const actionEnvelope = await requestIntent('ui.contract.v2', {
    op: 'action_open',
    action_id: actionId,
    ...(menuId > 0 ? { menu_id: menuId } : {}),
    view_type: 'tree',
    client_type: 'web_pc',
    delivery_profile: 'full',
  });
  assert(intentSucceeded(actionEnvelope), `action contract discovery failed: ${intentFailureDetail(actionEnvelope)}`);
  const actionContract = extractUnifiedContract(actionEnvelope);
  const model = contractModel(actionContract);
  assert(model, `action contract did not expose a model: ${listRoute}`);
  const sourceParams = primaryDataSourceParams(actionContract);
  const baseQuery = {
    op: 'list',
    model,
    fields: ['id'],
    domain: Array.isArray(sourceParams.domain) ? sourceParams.domain : [],
    context: asRecord(sourceParams.context),
    limit: candidateLimit,
  };
  const candidateIds = [];
  const queryEvidence = [];
  for (const order of uniqueOrders(sourceParams.order || sourceParams.order_by)) {
    const response = await requestIntent('api.data', { ...baseQuery, order });
    assert(intentSucceeded(response), `editable candidate query failed (${order}): ${intentFailureDetail(response)}`);
    const records = Array.isArray(asRecord(response).data?.records) ? asRecord(response).data.records : [];
    const ids = records.map((record) => positiveInteger(asRecord(record).id)).filter(Boolean);
    queryEvidence.push({ order, count: ids.length, trace_id: String(asRecord(response).traceId || asRecord(response).trace_id || '') });
    for (const id of ids) if (!candidateIds.includes(id)) candidateIds.push(id);
  }
  const inspected = [];
  for (const recordId of candidateIds) {
    const response = await requestIntent('ui.contract.v2', {
      op: 'model',
      model,
      view_type: 'form',
      record_id: recordId,
      render_profile: 'edit',
      action_id: actionId,
      ...(menuId > 0 ? { menu_id: menuId } : {}),
      client_type: 'web_pc',
      delivery_profile: 'full',
    });
    const editable = intentSucceeded(response) && isEditableFormContract(response);
    inspected.push({ record_id: recordId, editable, trace_id: String(asRecord(response).traceId || asRecord(response).trace_id || '') });
    if (editable) {
      return {
        route: editableFormRoute({ model, recordId, actionId, menuId }),
        model,
        record_id: recordId,
        action_id: actionId,
        menu_id: menuId || null,
        query_evidence: queryEvidence,
        inspected,
      };
    }
  }
  return {
    route: '',
    model,
    record_id: null,
    action_id: actionId,
    menu_id: menuId || null,
    query_evidence: queryEvidence,
    inspected,
  };
}
