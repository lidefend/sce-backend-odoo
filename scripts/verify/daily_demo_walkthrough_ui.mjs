// P4 bounded UI journey. Plans carry observed business choices, not product rules.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {launchChromium} from './playwright_runtime.mjs';
import {permitsInventoryRequest} from '../../frontend/apps/web/scripts/bootstrap_inventory_policy.mjs';
import {permitsWalkthroughWrite, validateWalkthroughResume} from './daily_demo_walkthrough_policy.mjs';
assert.equal(process.env.SC_DEMO_WALK_CONFIRM, 'EXECUTE_RECORDED_DEMO_JOURNEY');
const plan=JSON.parse(fs.readFileSync(process.env.SC_DEMO_WALK_PLAN,'utf8'));
assert(/^DEMO-WALK-20261026-[A-Z0-9-]+$/.test(plan.key));
assert(['sc.labor.worker','tender.opportunity','sc.material.supplier.return','sc.hr.salary.payment','payment.request','sc.invoice.registration'].includes(plan.model));
assert(plan.route.startsWith('/a/') && !plan.route.includes('://'));
const base='http://1.95.85.92:18081/t/demo';
const runtime=await(await fetch(base+'/api/runtime-version')).json();
assert.equal(runtime.source_revision,process.env.DAILY_RUNTIME_EXPECTED_SHA);
assert.equal(runtime.database,'sc_demo');
const out=process.env.SC_ACCEPTANCE_OUTPUT_DIR;
assert(out && !fs.existsSync(path.join(out,'report.json')),'Existing attempt: inspect its checkpoint; never replay creation');
fs.mkdirSync(out,{recursive:true});
const cred=JSON.parse(fs.readFileSync('config/acceptance/daily_demo_credential.v1.json'));
const report={runtime,plan,started_at:new Date().toISOString(),recordId:0,steps:[],responses:[],blocked:[],errors:[]};
if(plan.resumeFrom){
  const history=[];const visited=new Set();let source=plan.resumeFrom;
  while(source){
    const resolved=path.resolve(source);assert(!visited.has(resolved)&&history.length<20,'Invalid resume chain');visited.add(resolved);
    const prior=JSON.parse(fs.readFileSync(resolved,'utf8'));history.push(prior);source=prior.resumedCreation;
  }
  report.recordId=validateWalkthroughResume(history,plan,runtime.source_revision);
  report.resumedCreation=plan.resumeFrom;
}
let creationDispatched=false;
const save=()=>fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));
save();
const browser=await launchChromium({headless:true});
try {
  const page=await browser.newPage({viewport:{width:1440,height:960},locale:'zh-CN'});
  page.setDefaultTimeout(15000);
  await page.route('**/api/**',async route=>{
    const req=route.request();let body;try{body=req.postDataJSON()}catch{}
    const endpoint=new URL(req.url()).pathname.replace('/t/demo','');
    if(!permitsInventoryRequest(req.method(),endpoint,body,false) &&
      !(req.method()==='POST' && endpoint==='/api/v1/intent' && permitsWalkthroughWrite(body,plan,report.recordId))){
      report.blocked.push({intent:body?.intent,params:body?.params});save();return route.abort();
    }
    const r=body?.params?.intent?body.params:body;
    if(r?.intent==='api.data'&&r.params?.op==='create'){
      if(creationDispatched){report.blocked.push({reason:'duplicate_create_request'});save();return route.abort();}
      creationDispatched=true;report.creationDispatchedAt=new Date().toISOString();save();
    }
    const res=await route.fetch();let payload;try{payload=await res.json()}catch{}
    if(r?.intent!=='login')report.responses.push({intent:r?.intent,params:r?.params,http:res.status(),payload});
    if(r?.intent==='system.init'){
      assert.equal(payload?.data?.user?.id,40);
      assert.equal(payload?.data?.user?.company_id,1);
    }
    if(r?.intent==='api.data'&&r.params?.op==='create'&&payload?.ok){
      const id=Number(payload.data?.id || payload.data?.record?.id);
      assert(Number.isSafeInteger(id)&&id>0,'Create response missing authoritative ID; stop instead of replay');report.recordId=id;save();
    }
    await route.fulfill({response:res});
  });
  page.on('pageerror',e=>{report.errors.push(e.message);save()});
  async function capture(label){await page.waitForTimeout(1200);const shot=path.join(out,report.steps.length+'.png');await page.screenshot({path:shot});report.steps.push({label,url:page.url(),screenshot:shot,text:await page.locator('body').innerText()});save();}
  async function ready(kind='form',record=''){
    await page.waitForFunction(({kind,record})=>{
      const selector=kind==='list'?'[data-list-status]':'[data-semantic-component="ContractFormPage"]';
      return [...document.querySelectorAll(selector)].some(root=>root.getClientRects().length>0&&
        (kind==='list'?['ok','empty','error'].includes(root.getAttribute('data-list-status')):
          ['ok','ready','error'].includes(root.getAttribute('data-state'))&&(!record||root.getAttribute('data-form-record')===record))&&
        root.innerText.length>20&&!/正在载入|正在加载/.test(root.innerText));
    },{kind,record},{timeout:45000});
  }
  const entry=new URL(base+plan.route);
  const ownedUrl=()=>`${base}/f/${encodeURIComponent(plan.model)}/${report.recordId}?menu_id=${entry.searchParams.get('menu_id')}&action_id=${entry.pathname.split('/').pop()}`;
  await page.goto(base+'/login',{waitUntil:'domcontentloaded'});
  await page.locator('input').nth(0).fill('demo_full');await page.locator('input').nth(1).fill(cred.password);
  await page.getByRole('button',{name:'登录',exact:true}).click();await page.waitForURL(u=>!u.pathname.includes('/login'));
  if(!plan.resumeFrom){
  await page.goto(base+plan.route,{waitUntil:'domcontentloaded'});await ready('list');
  await page.locator('input[placeholder*="搜索关键字"]:visible').fill(plan.key);
  const searched=page.waitForResponse(response=>{
    try{const raw=response.request().postDataJSON();const r=raw?.params?.intent?raw.params:raw;
      return r?.intent==='api.data'&&r.params?.op==='list'&&r.params?.model===plan.model&&JSON.stringify(r.params).includes(plan.key);
    }catch{return false;}
  },{timeout:30000});
  await page.getByRole('button',{name:'搜索',exact:true}).click();
  const searchResponse=await searched;const searchPayload=await searchResponse.json();
  assert(searchResponse.ok()&&searchPayload.ok&&searchPayload.data?.total===0,'Current scoped key query not proven empty');
  await page.locator('[data-list-status="empty"]').waitFor({state:'visible',timeout:30000});
  await capture('unique business key absent in current actor scope');
  await page.getByRole('button',{name:'新建',exact:true}).click();await page.waitForURL(u=>u.pathname.endsWith('/new'));await ready('form','new');
  for(const field of plan.fields){
    const input=page.locator(`[data-field-name="${field.name}"] input:visible, [data-field-name="${field.name}"] textarea:visible`).first();
    await input.fill(field.value==='KEY'?plan.key:field.value);
    if(field.relation){await page.getByRole('option').filter({hasText:field.value}).first().click();}
    await input.press('Tab');
  }
  await capture('filled');
  const created=page.waitForResponse(response=>{
    try{const r=response.request().postDataJSON();return r?.intent==='api.data'&&r.params?.op==='create'&&r.params?.model===plan.model;}catch{return false;}
  },{timeout:45000});
  await page.getByRole('button',{name:'保存草稿',exact:true}).click();
  const createResponse=await created;const createPayload=await createResponse.json();
  assert(createResponse.ok()&&createPayload.ok,'Create failed; inspect response');
  }
  if(!report.recordId){report.status='SAVE_BLOCKED_OR_FAILED';}
  else {
    await page.goto(ownedUrl(),{waitUntil:'domcontentloaded'});await ready('form',String(report.recordId));
    const keyInput=page.locator(`[data-field-name="${plan.keyField}"] input:visible`).first();
    if(await keyInput.count())assert.equal(await keyInput.inputValue(),plan.key);
    else assert((await page.locator('[data-semantic-component="ContractFormPage"]').innerText()).includes(plan.key),'Owned record key not visible');
    await capture('saved record readback');
    for(const action of plan.actions){
      let button=page.getByRole('button',{name:action.label,exact:true});
      if(!await button.count()){
        const more=page.getByRole('button',{name:'更多操作',exact:true});
        if(await more.count()){
          await more.click();
          button=page.getByText(action.label,{exact:true}).filter({visible:true});
          await capture('expanded action menu: '+action.label);
        }
      }
      if(!await button.count()||!await button.isEnabled()){report.steps.push({label:action.label,status:'not_available'});break;}
      const executed=page.waitForResponse(response=>{
        try{const r=response.request().postDataJSON();return r?.intent==='execute_button'&&r.params?.model===plan.model&&Number(r.params?.res_id)===report.recordId&&r.params?.button?.name===action.method;}catch{return false;}
      },{timeout:45000});
      report.pendingMutation={method:action.method,recordId:report.recordId};save();
      await button.click();await page.waitForTimeout(500);
      const dialog=page.getByRole('dialog');if(await dialog.count())await dialog.getByRole('button',{name:/^(确认|确定|提交)$/}).first().click();
      const response=await executed;const payload=await response.json();
      report.pendingMutation=null;save();assert(response.ok()&&payload.ok,'Business action failed; inspect response');
      await page.waitForTimeout(1500);await ready();await capture(action.label);
    }
    await page.goto(ownedUrl(),{waitUntil:'domcontentloaded'});await ready('form',String(report.recordId));await capture('persisted reload');
    report.status='EXECUTED_REQUIRES_RESULT_REVIEW';
  }
} catch(e){report.status='STOPPED';report.error=e.message;process.exitCode=1;}
finally{report.completed_at=new Date().toISOString();save();await browser.close();}
console.log(JSON.stringify({status:report.status,recordId:report.recordId,error:report.error,blocked:report.blocked.length}));
