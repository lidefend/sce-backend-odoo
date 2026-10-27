// P4: bounded mobile observations on existing demo records, with no business writes.
import assert from 'node:assert/strict';
import { journalLineColumns } from './local_dev_journal_save_policy.mjs';

export async function inspectMobileAccounting({page, base, root, actor, accountingReadonly, entries, report, journalApi, setDetailId}) {
  report.viewport = {width:390,height:844,touch:true};
  report.mobileDetails = [];
  const geometry = async () => {
    const result = await page.evaluate(() => ({width:innerWidth, client:document.documentElement.clientWidth,
      scroll:document.documentElement.scrollWidth}));
    assert.equal(result.width,390,'mobile viewport must not be enlarged by overflow');
    assert(result.scroll<=result.client+1,`page overflow: ${JSON.stringify(result)}`);
    return result;
  };
  const read = async (model, ids, fields) => {
    const result=await journalApi('api.data',{op:'read',model,ids,fields});
    assert.equal(result.status,200); assert.equal(result.payload.ok,true);
    assert.deepEqual(result.payload.data.records.map(row=>row.id).sort((a,b)=>a-b),[...ids].sort((a,b)=>a-b));
    return result.payload.data.records;
  };
  for (const entry of entries) {
    const route=new URL(entry.meta.route,base), menu=Number(route.searchParams.get('menu_id'));
    const action=Number(route.pathname.split('/').at(-1));
    const allowed=await journalApi('route.authority.validate',{action_id:action,menu_id:menu});
    assert.equal(allowed.status,200); assert.equal(allowed.payload.data.allowed,true);
    await page.goto(base+entry.meta.route,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>['ok','empty'].includes(document.querySelector('[data-semantic-component="ActionView"]')?.getAttribute('data-collection-state')));
    const list=page.locator('[data-semantic-component="ActionView"]');
    const item={model:entry.meta.model,menu,route:entry.meta.route,geometry:await geometry(),
      collectionState:await list.getAttribute('data-collection-state'),passed:true};
    report.cases.push(item);
    await page.screenshot({path:`${root}/${actor}-${menu}.png`});
    if (entry.meta.model!=='account.move') continue;
    for (const state of ['draft','posted']) {
      const selected=await journalApi('api.data',{op:'list',model:'account.move',
        domain:[['state','=',state],['move_type','=','entry'],['name','!=','/'],['name','!=',false]],
        fields:['id','name','state','line_ids','write_date'],limit:5});
      assert.equal(selected.status,200); assert.equal(selected.payload.ok,true);
      const record=selected.payload.data.records.find(row=>row.name && row.name!=='/');
      assert(record,`demo gap: named ${state} journal required`);
      assert.equal(record.state,state); assert(record.line_ids.length>0);
      setDetailId(record.id);
      const fields=['id','move_id','name','account_id','debit','credit','analytic_distribution','write_date'];
      const before=await read('account.move.line',record.line_ids,fields);
      const pending=page.waitForResponse(response=>{
        let body; try {body=response.request().postDataJSON();} catch {return false;}
        const request=body?.params?.intent ? body.params : body;
        return request?.intent==='ui.contract.v2' && request.params?.op==='action_open'
          && request.params?.view_type==='form' && Number(request.params.action_id)===action
          && Number(request.params.menu_id)===menu && Number(request.params.record_id)===record.id;
      });
      if (state==='draft') await list.getByRole('button',{name:record.name,exact:true}).click();
      else await page.goto(`${base}/f/account.move/${record.id}?menu_id=${menu}&action_id=${action}`,{waitUntil:'domcontentloaded'});
      const response=await pending, payload=await response.json();
      assert.equal(response.status(),200); assert.equal(payload.ok,true);
      await page.waitForFunction(id=>{
        const form=document.querySelector('[data-semantic-component="ContractFormPage"]');
        return form?.getAttribute('data-state')==='ok' && form?.getAttribute('data-form-record')===String(id);
      },record.id);
      const form=page.locator('[data-semantic-component="ContractFormPage"]');
      const cards=form.locator('[data-field-name="line_ids"] [data-detail-collection-content="mobile-cards"]');
      await cards.waitFor({state:'visible'});
      await page.waitForFunction(count=>document.querySelectorAll('[data-field-name="line_ids"] [data-detail-collection-content="mobile-cards"] article').length===count,before.length);
      assert.equal(await form.locator('[data-field-name="line_ids"] [data-detail-collection-content="desktop-table"]').isVisible(),false);
      const declared=journalLineColumns(payload.data);
      assert.equal(declared.includes('analytic_distribution'),!accountingReadonly);
      assert.equal(payload.data.statusContract.globalStatus.effectiveRecordCapabilities.write,!accountingReadonly);
      if (accountingReadonly) {
        assert.equal(await form.getByRole('button',{name:'保存',exact:true}).count(),0);
        assert.equal(await form.getByRole('button',{name:'过账',exact:true}).count(),0);
      } else await form.getByRole('button',{name:'保存',exact:true}).waitFor({state:'visible'});
      const comparisons=[];
      for (const line of before) {
        const readonly=accountingReadonly || state==='posted';
        const card=readonly ? cards.locator('article').filter({hasText:line.account_id[1]})
          : cards.locator('article').filter({has:page.locator(`#o2m-control-line_ids-o2m_id_${line.id}-account_id-mobile`)});
        assert.equal(await card.count(),1);
        const disclosure=card.locator('[data-disclosure-trigger]');
        let expanded=false;
        if (await disclosure.count()) {
          await disclosure.click(); assert.equal(await disclosure.getAttribute('aria-expanded'),'true'); expanded=true;
        }
        const value=async (field,label)=>readonly
          ? (await card.locator('dl > div').filter({has:page.locator('dt').getByText(label,{exact:true})}).locator('dd').innerText()).trim()
          : await card.locator(`#o2m-control-line_ids-o2m_id_${line.id}-${field}-mobile`).inputValue();
        assert.equal(await value('account_id','科目'),line.account_id[1]);
        for (const [field,label] of [['debit','借项'],['credit','贷项']]) {
          const actual=await value(field,label); assert.match(actual,/^-?\d+(?:\.\d+)?$/); assert.equal(Number(actual),line[field]);
        }
        const analytic=card.locator('[data-semantic-component="NativeWeightedRelationDisplay"]');
        assert.equal(await analytic.count(),declared.includes('analytic_distribution') ? 1 : 0);
        let analyticText=null;
        if (declared.includes('analytic_distribution')) {
          await analytic.locator('[data-display-state="error"]').waitFor({state:'hidden'});
          await page.waitForFunction(()=>[...document.querySelectorAll('[data-detail-collection-content="mobile-cards"] [data-semantic-component="NativeWeightedRelationDisplay"]')].every(node=>node.getAttribute('data-display-state')==='ready'));
          analyticText=(await analytic.innerText()).trim();
          if (state==='posted') {
            assert.deepEqual(Object.values(line.analytic_distribution),[100]);
            const id=Number(Object.keys(line.analytic_distribution)[0]);
            const named=await read('account.analytic.account',[id],['id','display_name']);
            assert.equal(analyticText,`${named[0].display_name}：100%`);
          }
        }
        await card.scrollIntoViewIfNeeded();
        await page.screenshot({path:`${root}/${actor}-${state}-${line.id}-card.png`});
        if (expanded) {await disclosure.click(); assert.equal(await disclosure.getAttribute('aria-expanded'),'false');}
        comparisons.push({id:line.id,account:line.account_id[1],debit:line.debit,credit:line.credit,expanded,closed:expanded,analyticText,passed:true});
      }
      const after=await read('account.move.line',record.line_ids,fields);
      assert.deepEqual(after,before);
      const parentAfter=await read('account.move',[record.id],['id','name','state','line_ids','write_date']);
      assert.deepEqual(parentAfter,[record]);
      report.mobileDetails.push({state,record,before,after,parentAfter,comparisons,declared,geometry:await geometry(),unchanged:true,passed:true});
    }
  }
  assert.equal(report.cases.length,6); assert.equal(report.mobileDetails.length,2);
  assert.equal(report.blocked.length,0);
}
