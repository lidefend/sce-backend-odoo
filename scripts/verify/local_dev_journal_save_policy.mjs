// P4: one marked balanced draft, strict value/transport boundary, never posting.
const id = value => Array.isArray(value) && value.length === 2 ? value[0] : value;
const empty = value => value === false || value === null || value === '' || (Array.isArray(value) && value.length === 0);
const rootEmpty = new Set(['auto_post_until','partner_id','project_id','invoice_date','payment_reference','partner_bank_id','delivery_date',
  'invoice_payment_term_id','invoice_line_ids','narration','invoice_origin','qr_code_method','invoice_incoterm_id','incoterm_location',
  'fiscal_position_id','invoice_source_email','to_check','reversed_entry_id','purchase_id','purchase_vendor_bill_id','tax_cash_basis_origin_move_id']);
const rootAllowed = new Set([...rootEmpty,'ref','journal_id','company_id','currency_id','state','move_type','date','name','auto_post','invoice_date_due','user_id','invoice_user_id','line_ids']);
const rowAllowed = new Set(['account_id','name','project_id','wbs_id','cost_code_id','analytic_distribution','debit','credit','partner_id',
  'amount_currency','company_currency_id','company_id','currency_id','balance','date_maturity']);
export function permitsJournalSaveMutation(request, state, transport) {
  if (transport?.method !== 'POST' || transport?.path !== '/api/v1/intent') return false;
  const p = request?.params;
  if (!state.enabled || !p || p.model !== 'account.move' || p.sudo) return false;
  const parameterKeys=request.intent==='api.data.unlink' ? ['model','ids','context'] : ['op','model','vals','context'];
  if (Object.keys(p).some(key=>!parameterKeys.includes(key))) return false;
  const context = p.context || {};
  if (Object.keys(context).some(key => !['company_id','allowed_company_ids','lang','tz','menu_id','default_move_type','search_default_posted','view_no_maturity'].includes(key))) return false;
  if (context.default_move_type !== undefined && context.default_move_type !== 'entry') return false;
  if (context.search_default_posted !== undefined && context.search_default_posted !== 1) return false;
  if (context.view_no_maturity !== undefined && context.view_no_maturity !== true) return false;
  if (context.company_id !== undefined && context.company_id !== state.companyId) return false;
  if (context.allowed_company_ids !== undefined && JSON.stringify(context.allowed_company_ids) !== JSON.stringify([state.companyId])) return false;
  if (request.context && JSON.stringify(request.context) !== JSON.stringify(context)) return false;
  if (request.intent === 'api.data.unlink') return state.cleanupVerified === true && Number.isSafeInteger(state.createdId)
    && state.createdId > 0 && Array.isArray(p.ids) && p.ids.length === 1 && p.ids[0] === state.createdId;
  if (request.intent !== 'api.data' || p.op !== 'create' || state.createAttempted || !state.ready) return false;
  const vals = p.vals;
  if (!vals || Object.keys(vals).some(key => !rootAllowed.has(key)) || vals.ref !== state.ref
    || (vals.move_type !== undefined && vals.move_type !== 'entry') || (vals.state !== undefined && vals.state !== 'draft')
    || (vals.journal_id !== undefined && id(vals.journal_id) !== state.journalId) || (vals.company_id !== undefined && id(vals.company_id) !== state.companyId)
    || (vals.currency_id !== undefined && id(vals.currency_id) !== state.currencyId)
    || !Array.isArray(vals.line_ids) || vals.line_ids.length !== 2) return false;
  for (const key of rootEmpty) if (vals[key] !== undefined && !empty(vals[key])) return false;
  if (vals.auto_post !== undefined && vals.auto_post !== 'no') return false;
  if (vals.name !== undefined && !empty(vals.name) && vals.name !== '/') return false;
  for (const key of ['date','invoice_date_due']) if (vals[key] !== undefined && vals[key] !== state.date) return false;
  for (const key of ['user_id','invoice_user_id']) if (vals[key] !== undefined && !empty(vals[key]) && id(vals[key]) !== state.userId) return false;
  const lines = [];
  for (const [index,command] of vals.line_ids.entries()) {
    if (!Array.isArray(command) || command.length !== 3 || command[0] !== 0
      || (command[1] !== 0 && command[1] !== state.rowKeys[index])) return false;
    const row = command[2];
    if (!row || Object.keys(row).some(key => !rowAllowed.has(key)) || id(row.account_id) !== state.accounts[index]
      || id(row.currency_id) !== state.currencyId || (row.company_id !== undefined && id(row.company_id) !== state.companyId)
      || (row.company_currency_id !== undefined && id(row.company_currency_id) !== state.currencyId)) return false;
    for (const key of ['name','project_id','wbs_id','cost_code_id','partner_id','analytic_distribution']) {
      if (row[key] !== undefined && !empty(row[key])) return false;
    }
    if (row.date_maturity !== undefined && !empty(row.date_maturity) && row.date_maturity !== state.date) return false;
    for (const key of ['amount_currency','balance']) {
      if (row[key] !== undefined && (typeof row[key] !== 'number' || ![0,index === 0 ? 100 : -100].includes(row[key]))) return false;
    }
    if (typeof row.debit !== 'number' || typeof row.credit !== 'number') return false;
    lines.push(row);
  }
  return lines[0].debit === 100 && lines[0].credit === 0 && lines[1].debit === 0 && lines[1].credit === 100;
}

export function permitsJournalRoleRead(request, pairs, transport) {
  const params = request?.params;
  return transport?.method === 'POST' && transport?.path === '/api/v1/intent'
    && request?.intent === 'route.authority.validate' && params && Object.keys(params).length === 2
    && Number.isSafeInteger(params.action_id) && Number.isSafeInteger(params.menu_id)
    && pairs.has(`${params.action_id}/${params.menu_id}`);
}

export function permitsJournalDetailRead(request, recordId, transport) {
  return Number.isSafeInteger(recordId) && recordId > 0
    && transport?.method === 'POST' && transport?.path === '/api/v1/intent'
    && ['chatter.timeline','chatter.followers.list'].includes(request?.intent)
    && request.params?.model === 'account.move'
    && (request.params.res_id ?? request.params.record_id) === recordId;
}


// P4 reads published widget membership, never infers it from the acting role.
export function journalFormWidgets(contract) {
  const roots = contract?.layoutContract?.containerTree;
  if (!Array.isArray(roots)) throw new Error('form container declaration missing');
  const visit = nodes => nodes.flatMap(node => {
    if (!Array.isArray(node.widgetList) || !Array.isArray(node.children)) throw new Error('invalid form container');
    return [...node.widgetList, ...visit(node.children)];
  });
  return visit(roots);
}
export function journalLineColumns(contract) {
  const widgets = journalFormWidgets(contract).filter(widget => widget.fieldCode === 'line_ids');
  if (widgets.length !== 1) throw new Error('unique journal lines declaration required');
  const widget = widgets[0];
  const tree = (widget.componentConfig?.subview || widget.fieldDescriptor?.subview)?.tree;
  if (!Array.isArray(tree?.columns)) throw new Error('journal columns declaration missing');
  return tree.columns.map(column => typeof column === 'string' ? column : column.name || column.field);
}
