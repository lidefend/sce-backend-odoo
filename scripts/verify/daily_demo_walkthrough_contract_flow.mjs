// P4 one-shot UI approval relay for this audit's newly created contract only.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {launchChromium} from './playwright_runtime.mjs';
import {permitsInventoryRequest} from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
import {permitsWalkthroughWrite,validateContractRelayResume} from './daily_demo_walkthrough_policy.mjs';
assert.equal(process.env.SC_DEMO_WALK_CONFIRM,'EXECUTE_RECORDED_DEMO_JOURNEY');
const root='.runtime/demo-user-walkthrough-20261026/writes';
const created=JSON.parse(fs.readFileSync(root+'/contract-ui/created-checkpoint.json'));
const prior=JSON.parse(fs.readFileSync(root+'/contract-ui/report.json'));
const key='DEMO-DELIVERY-20261026-UI01',model='sc.general.contract',id=created.recordId;
assert.equal(created.key,key);assert(Number.isSafeInteger(id)&&id>0);
assert.equal(prior.business_key,key);assert.equal(prior.record_id,id);
assert.equal(prior.status,'UI_CREATE_EDIT_SUBMIT_EXECUTED_PENDING_BACKEND_READBACK');
assert(created.createBody.ok&&created.createBody.data.id===id);
assert(prior.observations.some(s=>s.stage==='ui_formal_submit'&&s.recordId===id&&s.response?.ok&&s.response.data?.result?.res_id===id&&s.response.meta?.source_authority?.model===model&&s.response.meta?.source_authority?.method==='action_confirm'));
const base='http://1.95.85.92:18081/t/demo';
const runtime=await(await fetch(base+'/api/runtime-version')).json();
assert.equal(runtime.source_revision,process.env.DAILY_RUNTIME_EXPECTED_SHA);
assert.equal(runtime.source_revision,prior.runtime.source_revision);assert.equal(runtime.database,'sc_demo');
const seats=[['ct1',14,'validate_tier','审批通过'],['sc_demo_operation',6,'validate_tier','审批通过'],['fin_mgr',13,'validate_tier','审批通过'],['demo_role_executive',49,'validate_tier','审批通过'],['demo_full',40,'action_signed','已签署']];
const resume=process.env.SC_DEMO_FLOW_RESUME;
let skip=0;
if(resume)skip=validateContractRelayResume(JSON.parse(fs.readFileSync(resume)),id,key,runtime.source_revision,seats);
const retry=process.env.SC_DEMO_FLOW_PREWRITE_RETRY;assert(!(resume&&retry));
if(retry){
  const failed=JSON.parse(fs.readFileSync(retry));
  assert.equal(failed.key,key);assert.equal(failed.recordId,id);assert.equal(failed.runtime.source_revision,runtime.source_revision);
  assert.equal(failed.status,'STOPPED_NOT_ACCEPTED');assert(!failed.pendingMutation);
  assert(failed.actors.every(a=>!a.actionSucceeded&&!a.responses.some(r=>r.intent==='execute_button')),'Retry only proven pre-write failure');
}
const out=root+(resume?'/contract-approval-ui-03':retry?'/contract-approval-ui-02':'/contract-approval-ui');
assert(!fs.existsSync(out),'One-shot relay exists: inspect checkpoint, never replay');fs.mkdirSync(out);
const report={runtime,key,model,recordId:id,resumedFrom:resume,completedPriorActors:seats.slice(0,skip).map(s=>s[0]),actors:[],pendingMutation:null};
const save=()=>fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));save();
const credential=JSON.parse(fs.readFileSync('config/acceptance/daily_demo_credential.v1.json'));
const browser=await launchChromium({headless:true});
try{
  for(const [login,uid,method,label] of seats.slice(skip)){
    const context=await browser.newContext({viewport:{width:1440,height:960},locale:'zh-CN'});
    const page=await context.newPage();page.setDefaultTimeout(30000);
    const actor={login,uid,method,responses:[],blocked:[],captures:[]};report.actors.push(actor);save();
    const plan={approvalOnly:true,key,model,actions:[{method}]};let startup,workspace,dispatched=false;
    await page.route('**/api/**',async route=>{
      const req=route.request();let raw;try{raw=req.postDataJSON()}catch{}
      const r=raw?.params?.intent?raw.params:raw;
      const endpoint=new URL(req.url()).pathname.replace('/t/demo','');
      if(!permitsInventoryRequest(req.method(),endpoint,raw,false)&&!(req.method()==='POST'&&endpoint==='/api/v1/intent'&&permitsWalkthroughWrite(raw,plan,id))){actor.blocked.push(r);save();return route.abort();}
      if(r?.intent==='execute_button'){
        assert(!dispatched,'Duplicate action dispatch');dispatched=true;report.pendingMutation={login,method,recordId:id};save();
      }
      let response;try{response=await route.fetch()}catch(error){actor.transportError=String(error.message).split('Call log:')[0];save();return;} let payload;try{payload=await response.json()}catch{}
      if(r?.intent==='my.work.summary')workspace=payload?.data;
      if(r?.intent==='system.init'){startup=payload.data;assert.equal(startup.user.id,uid);assert.equal(startup.user.company_id,1);}
      if(r?.intent!=='login')actor.responses.push({intent:r?.intent,params:r?.params,http:response.status(),payload});
      if(r?.intent==='execute_button'){report.pendingMutation=null;save();}
      await route.fulfill({response});
    });
    async function capture(stage){const screenshot=path.join(out,login+'-'+stage+'.png');await page.screenshot({path:screenshot});actor.captures.push({stage,url:page.url(),screenshot,text:await page.locator('body').innerText()});save();}
    await page.goto(base+'/login');await page.locator('input').nth(0).fill(login);await page.locator('input').nth(1).fill(credential.password);
    await page.getByRole('button',{name:'登录',exact:true}).click();await page.waitForURL(u=>!u.pathname.includes('/login'));
    await page.waitForFunction(()=>document.querySelector('[data-login-home-block]'),{},{timeout:45000});
    if(method==='validate_tier'){
      for(let i=0;i<90&&!workspace;i++)await page.waitForTimeout(500);
      assert(workspace,'Work summary response not observed');
      const matches=(workspace?.product_workspace?.sections||[]).filter(s=>s.key==='todo').flatMap(s=>s.items||[]).filter(i=>i.target?.model===model&&Number(i.target.record_id)===id);
      assert.equal(matches.length,1,'Fresh exact assigned work item missing');actor.workItem=matches[0];save();
      let task=page.locator(`[data-login-home-block="today_actions"] article[data-record-id="${id}"]`);
      await page.waitForTimeout(1500);
      if(!await task.count()){
        await page.getByRole('button',{name:'查看全部',exact:true}).click();
        task=page.locator(`[data-section-key="todo"] [data-work-item-key="${matches[0].key}"]`);
      }
      await task.first().waitFor({timeout:30000});assert.equal(await task.count(),1,'Ambiguous or absent UI work item');await capture('todo');await task.getByRole('button',{name:/^打开/}).click();
    }else{
      await page.goto(`${base}/f/${model}/${id}?menu_id=${created.target.menu_id}&action_id=${created.target.action_id}`);
    }
    const form=page.locator(`[data-semantic-component="ContractFormPage"][data-form-model="${model}"][data-form-record="${id}"]`).filter({visible:true});
    await form.waitFor({timeout:45000});await page.waitForTimeout(2000);
    const keyField=form.locator('[data-field-name="contract_name"]');
    assert((await keyField.innerText()).includes(key)||await keyField.locator('input').inputValue().catch(()=>null)===key,'Owned contract key mismatch');
    await capture('before');let button=page.getByRole('button',{name:label,exact:true});
    if(!await button.count()){await page.getByRole('button',{name:'更多操作',exact:true}).click();button=page.getByText(label,{exact:true}).filter({visible:true});}
    assert.equal(await button.count(),1,'Action must be unique');assert(await button.isEnabled(),'Action disabled');
    const executed=page.waitForResponse(res=>{try{const b=res.request().postDataJSON();return b.intent==='execute_button'&&b.params?.button?.name===method&&Number(b.params?.res_id)===id}catch{return false}},{timeout:45000});
    await button.click();await page.waitForTimeout(500);const dialog=page.getByRole('dialog');if(await dialog.count())await dialog.getByRole('button',{name:/^(确认|确定|提交)$/}).click();
    const response=await executed,payload=await response.json();assert(response.ok()&&payload.ok,'Action rejected; inspect exact response');
    await page.waitForTimeout(2000);await capture('after');actor.actionSucceeded=true;save();await page.unrouteAll({behavior:'wait'});await context.close();
  }
  report.status='UI_APPROVAL_AND_SIGN_EXECUTED_REQUIRES_READBACK';
}catch(error){report.status='STOPPED_NOT_ACCEPTED';report.error=error.message;process.exitCode=1;}
finally{save();for(const c of browser.contexts())for(const p of c.pages())await p.unrouteAll({behavior:'wait'});await browser.close();}
console.log(JSON.stringify({status:report.status,error:report.error,actors:report.actors.map(a=>({login:a.login,success:a.actionSucceeded}))}));
