// P4 request containment for owner-authorized Demo observations, never product ACL.
export function permitsWalkthroughWrite(body, plan, recordId = 0) {
  const r = body?.params?.intent ? body.params : body;
  const p = r?.params || {};
  if (Object.hasOwn(p, 'vals') && Object.hasOwn(p, 'values')) return false;
  if (['payload', 'params', 'data', 'args'].some(key => Object.hasOwn(p, key))) return false;
  if(plan?.approvalOnly){
    if(plan.key!=='DEMO-DELIVERY-20261026-UI01'||plan.model!=='sc.general.contract'||p.model!==plan.model||recordId<=0||Number(p.res_id)!==recordId)return false;
    if(['chatter.timeline','chatter.followers.list'].includes(r.intent))return true;
    return r.intent==='execute_button'&&p.button?.type==='object'&&['validate_tier','action_signed'].includes(p.button.name)&&plan.actions?.some(a=>a.method===p.button.name);
  }
  if (!plan || p.model !== plan.model || !/^DEMO-WALK-20261026-[A-Z0-9-]+$/.test(plan.key || '')) return false;
  for (const context of [r.context, p.context]) {
    for (const [key, value] of Object.entries(context || {})) {
      if (key === 'default_state') { if (value !== 'draft') return false; continue; }
      if (key.startsWith('default_') &&
          !(value !== null && typeof value !== 'object' && Object.hasOwn(plan.defaultValues || {}, key) && value === plan.defaultValues[key])) return false;
    }
  }
  function boundedValues(values, creating = false) {
    if (!values || Array.isArray(values) || typeof values !== 'object') return false;
    return Object.entries(values).every(([field, value]) => {
      if (value === null || typeof value !== 'object') return true;
      if (!Array.isArray(value)) return false;
      if (!value.length) return true;
      if (creating && (plan.emptyRelationFields || []).includes(field) && value.length === 1 &&
          Array.isArray(value[0]) && value[0].length === 3 && value[0][0] === 6 && value[0][1] === 0 &&
          Array.isArray(value[0][2]) && value[0][2].length === 0) return true;
      // Only new children explicitly named by this journey; never update/delete/link existing children.
      return (plan.newChildFields || []).includes(field) && value.every(command =>
        Array.isArray(command) && command.length === 3 && command[0] === 0 && command[1] === 0 &&
        boundedValues(command[2]) && !Object.hasOwn(command[2], 'id') && !Object.hasOwn(command[2], 'state'));
    });
  }
  if (r.intent === 'api.onchange') return !p.res_id || Number(p.res_id) === recordId && recordId > 0;
  if (['chatter.timeline', 'chatter.followers.list'].includes(r.intent)) return recordId > 0 && Number(p.res_id) === recordId;
  if (r.intent === 'api.data' && p.op === 'create') {
    return !recordId && boundedValues(p.vals, true) && p.vals?.[plan.keyField] === plan.key &&
      (!Object.hasOwn(p.vals, 'state') || p.vals.state === 'draft');
  }
  if (r.intent === 'api.data.write' || r.intent === 'api.data' && p.op === 'write') {
    const ids = r.intent === 'api.data.write' ? [p.id] : p.ids;
    const vals = p.vals || p.values || {};
    return recordId > 0 && Array.isArray(ids) && ids.length === 1 && Number(ids[0]) === recordId &&
      boundedValues(vals) && !Object.hasOwn(vals, 'state') && (!Object.hasOwn(vals, plan.keyField) || vals[plan.keyField] === plan.key);
  }
  return r.intent === 'execute_button' && recordId > 0 && Number(p.res_id) === recordId &&
    p.button?.type === 'object' && plan.actions.some(a => a.method === p.button.name);
}

// Validate the complete recorded lineage; never skip successful/uncertain actions.
export function validateWalkthroughResume(history, plan, revision) {
  const id=history[0]?.recordId;
  if(!Number.isSafeInteger(id)||id<=0||!history.length)throw Error('Invalid resume record');
  for(const prior of history){
    if(prior.runtime?.source_revision!==revision||prior.plan?.key!==plan.key||prior.plan?.model!==plan.model||prior.recordId!==id)
      throw Error('Resume identity mismatch');
    if(prior.pendingMutation)throw Error('Uncertain prior action');
    if(plan.actions.some(action=>prior.responses?.some(r=>r.intent==='execute_button'&&r.params?.button?.name===action.method&&r.payload?.ok)))
      throw Error('Do not replay a completed action');
  }
  const root=history.at(-1);
  if(!root.responses?.some(r=>r.intent==='api.data'&&r.params?.op==='create'&&r.params?.model===plan.model&&r.params?.vals?.[plan.keyField]===plan.key&&r.http===200&&r.payload?.ok&&Number(r.payload.data?.id)===id))
    throw Error('Resume requires actual owned creation response');
  return id;
}

export function validateContractRelayResume(prior, id, key, revision, seats) {
  if(prior.recordId!==id||prior.key!==key||prior.runtime?.source_revision!==revision||prior.pendingMutation||prior.status!=='STOPPED_NOT_ACCEPTED')throw Error('Relay checkpoint mismatch');
  let completed=0,failed=false;
  for(const [index,actor] of prior.actors.entries()){
    if(actor.login!==seats[index]?.[0]||actor.method!==seats[index]?.[2])throw Error('Relay actor order mismatch');
    const writes=actor.responses.filter(r=>r.intent==='execute_button');
    if(actor.actionSucceeded){
      if(failed||writes.length!==1||writes[0].http!==200||!writes[0].payload?.ok||writes[0].params?.model!=='sc.general.contract'||Number(writes[0].params?.res_id)!==id||writes[0].params?.button?.name!==actor.method)throw Error('Completed relay proof missing');
      completed++;
    }else{if(writes.length)throw Error('Uncertain failed relay action');failed=true;}
  }
  if(!failed||completed>=seats.length)throw Error('No safe pending relay seat');
  return completed;
}
