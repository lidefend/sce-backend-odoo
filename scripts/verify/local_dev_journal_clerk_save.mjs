// P4: exercise the clerk's actual child-onchange path; the caller owns all write gates.
import assert from 'node:assert/strict';
import fs from 'node:fs';

export async function saveClerkJournal({page,base,root,report,leaves,state,api}) {
  assert.equal(report.actor.uid,1988); assert.equal(report.actor.login,'sc_demo_accounting_user');
  const candidateIndex=fs.readFileSync('frontend/apps/web/dist-dev/index.html','utf8');
  const expected=[...candidateIndex.matchAll(/<script[^>]*src="([^"]*assets\/[^"]+)"/g)].map(match=>new URL(match[1],base).pathname);
  const served=await page.locator('script[src]').evaluateAll(nodes=>nodes.map(node=>new URL(node.src).pathname).filter(path=>path.includes('/assets/')));
  assert(expected.length && expected.every(path=>served.includes(path)),'namespace differs from candidate build');
  report.frontendEntries=served;
  const entry=leaves.find(item=>item.meta?.model==='account.move' && new URL(item.meta.route,base).searchParams.get('menu_id')==='175');
  assert(entry);
  const menu=175;
  const wait=predicate=>page.waitForResponse(response=>{
    let body;try {body=response.request().postDataJSON();} catch {return false;}
    const request=body?.params?.intent ? body.params : body;
    return predicate(request);
  });
  const capture=async response=>{
    const payload=await response.json(); assert.equal(response.status(),200); assert.equal(payload.ok,true);
    let body=response.request().postDataJSON();const request=body?.params?.intent ? body.params : body;
    return {params:request.params,data:payload.data,ok:payload.ok,httpStatus:response.status()};
  };
  await page.goto(base+entry.meta.route,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>['ok','empty'].includes(document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state')));
  const [contractResponse,initialResponse]=await Promise.all([
    wait(r=>r?.intent==='ui.contract.v2' && r.params?.op==='model' && r.params?.model==='account.move' && r.params?.view_type==='form'
      && Number(r.params.menu_id)===menu && !r.params.record_id && r.params.render_profile==='create').then(async response => {
        report.createContract = await capture(response);
        return response;
      }),
    wait(r=>r?.intent==='api.onchange' && r.params?.model==='account.move' && !r.params.res_id && !r.params.feedback_evaluation && !r.params.child_initialization),
    page.getByRole('button',{name:/^(新建|新增|创建)$/}).first().click(),
  ]);
  const contract=await capture(contractResponse), initial=await capture(initialResponse);
  report.initialOnchange = initial;
  assert.equal(contract.data.pageInfo.model,'account.move');
  const rules=contract.data.actionContract.actionRuleList; assert(Array.isArray(rules));
  const parentRules=rules.filter(rule=>(rule.sourceWidgetId || rule.source_widget_id)==='field.line_ids'
    && ['change','select','blur'].includes(String(rule.triggerType || rule.trigger_type).toLowerCase())
    && String(rule.dispatchMode || rule.dispatch_mode).toLowerCase().startsWith('server'));
  report.parentLineOnchange={rules:parentRules,declared:parentRules.length>0};
  // This bounded role journey was selected because its contract does not dispatch parent line changes.
  assert.equal(parentRules.length,0,'clerk parent onchange declaration changed; reassess affected journey');
  state.companyId=1;state.currencyId=6;state.journalId=3;state.userId=1988;
  state.date=initial.data.patch.date || initial.params.values.date;
  assert.equal(initial.data.patch.journal_id[0],3);
  const existing=await api('api.data',{op:'list',model:'account.move',domain:[['ref','=',state.ref]],fields:['id','ref'],limit:2});
  assert.equal(existing.payload.ok,true);assert.deepEqual(existing.payload.data.records,[]);
  const ref=page.locator('[data-field-name="ref"] input:visible').first(); await ref.fill(state.ref);await ref.blur();
  const collection=page.locator('[data-field-name="line_ids"]').first();await collection.waitFor({state:'visible'});
  report.childSteps=[];
  for (let index=0;index<2;index++) {
    const [added]=await Promise.all([
      wait(r=>r?.intent==='api.onchange' && r.params?.model==='account.move' && r.params?.child_initialization?.field==='line_ids' && !r.params.res_id
        && r.params.view_id===initial.params.view_id),
      collection.getByRole('button',{name:/新增|添加/}).first().click(),
    ]);
    const defaults=await capture(added);
    assert.equal(defaults.data.patch.currency_id[0],6);assert.equal(defaults.data.patch.company_id[0],1);
    await page.waitForFunction(n=>Number(document.querySelector('[data-field-name="line_ids"] [data-row-count]')?.getAttribute('data-row-count'))===n,index+1);
    const account=collection.locator('input[aria-label="科目"]:visible').nth(index);
    const controlId=await account.getAttribute('id');
    const key=controlId?.match(/^o2m-control-line_ids-(.+)-account_id-desktop$/)?.[1];assert(key);state.rowKeys.push(key);
    const [queryResponse]=await Promise.all([
      wait(r=>r?.intent==='api.data' && r.params?.model==='account.account' && r.params?.op==='list'),account.click(),
    ]);
    const query=await capture(queryResponse);
    assert.deepEqual(query.params.domain,['|',['company_id','=',false],['company_id','parent_of',[1]],['deprecated','=',false],['account_type','!=','off_balance']]);
    const expectedOption=query.data.records[index];assert(expectedOption && typeof expectedOption.display_name==='string' && expectedOption.display_name);
    const option=page.getByText(expectedOption.display_name,{exact:true});await option.waitFor({state:'visible'});
    const label=(await option.innerText()).trim();
    const records=query.data.records.filter(row=>[row.display_name,row.name].includes(label));assert.equal(records.length,1);
    const accountId=records[0].id;assert.equal(accountId,index===0?49:48);state.accounts.push(accountId);
    const [selectionResponse]=await Promise.all([
      wait(r=>r?.intent==='api.onchange' && r.params?.model==='account.move' && r.params?.child_onchange?.field==='line_ids' && !r.params.res_id && !r.params.child_onchange.record_id
        && r.params.view_id===initial.params.view_id && r.params.child_onchange.changed_fields?.includes('account_id')
        && (Array.isArray(r.params.child_onchange.values.account_id)?r.params.child_onchange.values.account_id[0]:r.params.child_onchange.values.account_id)===accountId),option.click(),
    ]);
    const selection=await capture(selectionResponse);
    const amountField=index===0?'debit':'credit';
    const amount=collection.locator(`input[id$="-${amountField}-desktop"]`).nth(index);
    const [amountResponse]=await Promise.all([
      wait(r=>r?.intent==='api.onchange' && r.params?.model==='account.move' && r.params?.child_onchange?.field==='line_ids' && !r.params.res_id && !r.params.child_onchange.record_id
        && r.params.view_id===initial.params.view_id && r.params.child_onchange.changed_fields?.includes(amountField)
        && (Array.isArray(r.params.child_onchange.values.account_id)?r.params.child_onchange.values.account_id[0]:r.params.child_onchange.values.account_id)===accountId
        && r.params.child_onchange.values[amountField]===100),
      (async()=>{await amount.fill('100');await amount.blur();})(),
    ]);
    const changed=await capture(amountResponse);
    report.childSteps.push({index,key,accountId,defaults,selection,changed});
    const effective={...changed.params.child_onchange.values,...changed.data.patch};
    assert.equal(effective[amountField],100);
    assert.equal(effective.balance,index===0?100:-100);
    assert.equal(effective.amount_currency,index===0?100:-100);
    report.childSteps.at(-1).effective=effective;
    await page.waitForFunction(({id})=>document.getElementById(id)?.value==='100',{id:await amount.getAttribute('id')});
  }
  state.ready=true;
  const [savedResponse]=await Promise.all([
    wait(r=>r?.intent==='api.data' && r.params?.op==='create' && r.params?.model==='account.move'),
    page.getByRole('button',{name:'保存',exact:true}).click(),
  ]);
  const saved=await capture(savedResponse);state.createdId=saved.data.id;assert(Number.isSafeInteger(state.createdId)&&state.createdId>0);
  const receipt={head:report.head,ref:state.ref,actor:report.actor.login,uid:report.actor.uid,record_id:state.createdId,line_ids:[]};
  fs.writeFileSync(`${root}/created-receipt.json`,JSON.stringify(receipt));report.saved=saved;
  await page.waitForURL(url=>url.pathname.endsWith('/'+state.createdId));
  const [persistedResponse]=await Promise.all([
    wait(r=>r?.intent==='ui.contract.v2'
      && (r.params?.model==='account.move' || (r.params?.op==='action_open' && Number(r.params.action_id)===292))
      && Number(r.params.record_id)===state.createdId && r.params?.view_type==='form').then(async response=>{
        report.persistedContract=await capture(response);
        return response;
      }),
    page.reload({waitUntil:'domcontentloaded'}),
  ]);
  report.persistedContract=await capture(persistedResponse);
  assert.equal(report.persistedContract.data.pageInfo.model,'account.move');
  for (const field of ['authorized_transaction_ids','duplicated_ref_ids']) {
    const ids=report.persistedContract.data.dataContract.mainData[field];
    assert(Array.isArray(ids),`missing persisted relation dependency: ${field}`);
    assert(ids.every(id=>Number.isSafeInteger(id)&&id>0));
  }
  await page.waitForFunction(value=>document.querySelector('[data-field-name="ref"] input')?.value===value,state.ref);
  const result=await api('api.data',{op:'read',model:'account.move',ids:[state.createdId],fields:['id','ref','state','create_uid','company_id','journal_id','currency_id','line_ids']});
  assert.equal(result.payload.ok,true);assert.equal(result.payload.data.records.length,1);const record=result.payload.data.records[0];
  assert.equal(record.id,state.createdId);assert.equal(record.ref,state.ref);assert.equal(record.state,'draft');assert.equal(record.create_uid[0],1988);
  for(const [key,value] of [['company_id',1],['journal_id',3],['currency_id',6]]) assert.equal(record[key][0],value);
  assert.equal(record.line_ids.length,2);
  const lines=await api('api.data',{op:'read',model:'account.move.line',ids:record.line_ids,fields:['id','move_id','account_id','currency_id','company_id','debit','credit','balance','amount_currency','display_type','sequence','discount_date','discount_amount_currency']});
  assert.equal(lines.payload.ok,true);const rows=lines.payload.data.records;
  assert.equal(rows.length,2);assert.deepEqual(rows.map(row=>row.id).sort((a,b)=>a-b),[...record.line_ids].sort((a,b)=>a-b));
  for(const [account,debit,credit,balance] of [[49,100,0,100],[48,0,100,-100]]) {
    const matching=rows.filter(row=>row.account_id[0]===account);assert.equal(matching.length,1);const row=matching[0];
    assert.equal(row.move_id[0],state.createdId);assert.equal(row.currency_id[0],6);assert.equal(row.company_id[0],1);assert.equal(row.amount_currency,balance);
    assert.equal(row.display_type,'product');assert.equal(row.sequence,100);assert.equal(row.discount_date,false);assert.equal(row.discount_amount_currency,0);
    assert.equal(row.debit,debit);assert.equal(row.credit,credit);assert.equal(row.balance,balance);
  }
  receipt.line_ids=record.line_ids;fs.writeFileSync(`${root}/created-receipt.json`,JSON.stringify(receipt));
  report.readback={record,lines:rows};assert.equal(report.blocked.length,0);
  report.cases.push({model:'account.move',actor:report.actor.login,recordId:state.createdId,reloadedRef:state.ref,passed:true});
  await page.screenshot({path:`${root}/saved-reloaded.png`});
}
