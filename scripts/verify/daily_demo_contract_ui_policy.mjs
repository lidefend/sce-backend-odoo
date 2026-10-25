// Request containment for one explicitly authorized UI journey, not product ACL.
export function permitsContractWrite(body, { enabled, key, recordId }) {
  if (!enabled) return false;
  const request = body?.params?.intent ? body.params : body;
  const p = request?.params || {};
  if (p.model !== 'sc.general.contract') return false;
  // Native onchange works on virtual records; timeline is read-only. Both are
  // limited to this document (or its uniquely named unsaved create values).
  if (['chatter.timeline', 'chatter.followers.list'].includes(request.intent)) return recordId > 0 && Number(p.res_id) === recordId;
  if (request.intent === 'api.onchange') return recordId > 0
    ? Number(p.res_id) === recordId
    : !p.res_id && p.values?.contract_name === key;
  if (request.intent === 'api.data' && p.op === 'create') {
    return !recordId && p.vals?.contract_name === key &&
      (!Object.hasOwn(p.vals, 'state') || p.vals.state === 'draft');
  }
  const ids = request.intent === 'api.data.write' ? [p.id] : p.ids;
  if ((request.intent === 'api.data.write' || (request.intent === 'api.data' && p.op === 'write')) &&
      recordId > 0 && Array.isArray(ids) && ids.length === 1 && Number(ids[0]) === recordId) {
    const values = p.values || p.vals || {};
    return !Object.hasOwn(values, 'state') &&
      (!Object.hasOwn(values, 'contract_name') || values.contract_name === key);
  }
  return request.intent === 'execute_button' && recordId > 0 && Number(p.res_id) === recordId &&
    p.button?.name === 'action_confirm' && p.button?.type === 'object';
}
