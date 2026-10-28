import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
const out=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(out,'../../../../..');
const {launchChromium}=await import(pathToFileURL(path.join(root,'scripts/verify/playwright_runtime.mjs')));
let raw='';for await(const part of process.stdin)raw+=part;let {token}=JSON.parse(raw);raw='';
const base='http://1.95.85.92:18081',target=base+'/t/demo/r/project.project/15';
const report={task:'FEPC-08',started_at:new Date().toISOString(),host:{platform:os.platform(),release:os.release(),windows_emulation:false},requests:[],blocked:[],console_errors:[],request_failures:[],samples:[],actions:[]};
const save=()=>fs.writeFileSync(path.join(out,'f1-measurements.json'),JSON.stringify(report,null,2)+'\n');
let phase='startup',browser;const pending=new Set();
const safeText=s=>String(s).split(token).join('[REDACTED]').replace(/Bearer\s+\S+/gi,'Bearer [REDACTED]').slice(0,400);
try{
 browser=await launchChromium({headless:true});report.browser_version=browser.version();
 const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,serviceWorkers:'block'});
 await context.addInitScript(t=>sessionStorage.setItem('sc_auth_token:tenant:/t/demo',t),token);
 const page=await context.newPage();
 const allow=new Set(['system.init','chatter.timeline','chatter.followers.list','user.view.preference.get','route.authority.validate']);
 await context.route('**/*',async route=>{const req=route.request();if(['GET','HEAD','OPTIONS'].includes(req.method()))return route.continue();let b;try{b=req.postDataJSON();}catch{}
  const safe=req.url()===base+'/t/demo/api/v1/intent'&&b&&(allow.has(b.intent)||(b.intent==='api.data'&&['read','list','count'].includes(b.params?.op))||(b.intent==='ui.contract.v2'&&['model','action_open'].includes(b.params?.op)));
  if(!safe){report.blocked.push({phase,path:new URL(req.url()).pathname,method:req.method(),intent:b?.intent,op:b?.params?.op});save();return route.abort('blockedbyclient');}return route.continue();});
 page.on('console',m=>{if(m.type()==='error'){report.console_errors.push({phase,kind:'console',message:safeText(m.text())});save();}});
 page.on('pageerror',e=>{report.console_errors.push({phase,kind:'pageerror',message:safeText(e.message)});save();});
 page.on('requestfailed',r=>{report.request_failures.push({phase,path:new URL(r.url()).pathname,error:r.failure()?.errorText});save();});
 page.on('response',r=>{if(!r.url().includes('/api/v1/intent'))return;let q;try{q=r.request().postDataJSON();}catch{return;}const event={phase,time:new Date().toISOString(),method:r.request().method(),intent:q?.intent,op:q?.params?.op,model:q?.params?.model,http_status:r.status()};report.requests.push(event);const promise=(async()=>{try{const b=await r.json();event.application_ok=b.ok;if(q.intent==='system.init')report.identity={user_id:b.data?.user?.id,role_code:b.data?.role_surface?.role_code,company_id:b.data?.user?.company_id,source_revision:b.data?.source_revision};}catch{event.decode_error=true;}save();})();pending.add(promise);promise.finally(()=>pending.delete(promise));});
 const ident=async()=>{const r=await context.request.get(base+'/t/demo/api/runtime-version');return{time:new Date().toISOString(),http_status:r.status(),body:await r.json()};};
 report.runtime_before=await ident();save();await page.goto(target,{waitUntil:'domcontentloaded',timeout:45000});await page.locator('[data-field-help-trigger]').first().waitFor({timeout:60000});await page.waitForLoadState('networkidle',{timeout:15000}).catch(()=>{});
 report.environment=await page.evaluate(()=>({userAgent:navigator.userAgent,platform:navigator.platform,viewport:{width:innerWidth,height:innerHeight},outer:{width:outerWidth,height:outerHeight},dpr:devicePixelRatio,visualViewport:visualViewport?{scale:visualViewport.scale,width:visualViewport.width,height:visualViewport.height}:null,documentScroll:{height:document.scrollingElement.scrollHeight,clientHeight:document.scrollingElement.clientHeight},url:location.pathname,helpLabels:[...document.querySelectorAll('[data-field-help-trigger]')].map(e=>({label:e.getAttribute('aria-label'),expanded:e.getAttribute('aria-expanded')}))}));
 const labels=report.environment.helpLabels.map(x=>x.label);const label=labels.includes('项目状态')?'项目状态':labels.includes('经营方式')?'经营方式':labels[0];report.selected_help={label,exact_user_target_confirmed:label==='项目状态',basis:label==='项目状态'?'label match':'FEPC-01 existing sample; user target remains unconfirmed'};
 const trigger=()=>page.locator('[data-field-help-trigger]').filter({has:page.locator(':scope')});
 const button=()=>page.locator('[data-field-help-trigger]').and(page.getByRole('button',{name:label,exact:true})).first();
 async function measure(name){phase=name;const sample=await page.evaluate(({label,name})=>{
  const rect=e=>{if(!e)return null;const r=e.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height,top:r.top,right:r.right,bottom:r.bottom,left:r.left};};
  const desc=e=>e?{tag:e.tagName,id:e.id,classes:typeof e.className==='string'?e.className:'',role:e.getAttribute('role')}:null;
  const info=e=>{if(!e)return null;const r=rect(e),s=getComputedStyle(e);let clip={left:0,top:0,right:innerWidth,bottom:innerHeight};const ancestors=[];for(let p=e.parentElement;p;p=p.parentElement){const c=getComputedStyle(p);if(/auto|scroll|hidden|clip/.test(c.overflow+c.overflowY+c.overflowX)){const a=rect(p);ancestors.push({...desc(p),overflow:c.overflow,overflowY:c.overflowY,rect:a,scrollTop:p.scrollTop,scrollHeight:p.scrollHeight,clientHeight:p.clientHeight});clip.left=Math.max(clip.left,a.left);clip.top=Math.max(clip.top,a.top);clip.right=Math.min(clip.right,a.right);clip.bottom=Math.min(clip.bottom,a.bottom);}}
   const visibleRect={left:Math.max(r.left,clip.left),top:Math.max(r.top,clip.top),right:Math.min(r.right,clip.right),bottom:Math.min(r.bottom,clip.bottom)};const intersection=visibleRect.right>visibleRect.left&&visibleRect.bottom>visibleRect.top;const cx=(visibleRect.left+visibleRect.right)/2,cy=(visibleRect.top+visibleRect.bottom)/2;const hit=intersection?document.elementFromPoint(cx,cy):null;
   return{element:desc(e),rect:r,css:{position:s.position,display:s.display,visibility:s.visibility,opacity:s.opacity,transform:s.transform,zIndex:s.zIndex,zoom:s.zoom},intersectsViewport:r.right>0&&r.bottom>0&&r.left<innerWidth&&r.top<innerHeight,intersectsClip:intersection,hitTestOwnsVisibleCenter:!!hit&&(e===hit||e.contains(hit)),ancestorClips:ancestors,parent:desc(e.parentElement),offsetParent:desc(e.offsetParent)};};
  const t=[...document.querySelectorAll('[data-field-help-trigger]')].find(e=>e.getAttribute('aria-label')===label);const id=t?.getAttribute('aria-controls');const content=id?document.getElementById(id):null;const popup=content?.closest('.t-popup')||content?.parentElement;return{name,time:Date.now(),route:location.pathname,windowScroll:{x:scrollX,y:scrollY},scrollingElement:{tag:document.scrollingElement.tagName,top:document.scrollingElement.scrollTop,height:document.scrollingElement.scrollHeight,clientHeight:document.scrollingElement.clientHeight},trigger:info(t),expanded:t?.getAttribute('aria-expanded'),contentId:id,popup:info(popup),content:info(content),relative:popup&&t?{dx:rect(popup).x-rect(t).x,dy:rect(popup).y-rect(t).y}:null,allHelp:[...document.querySelectorAll('[data-field-help-trigger]')].map(e=>({label:e.getAttribute('aria-label'),expanded:e.getAttribute('aria-expanded'),controls:e.getAttribute('aria-controls')})),popupNodes:[...document.querySelectorAll('.t-popup')].map(info)};
 },{label,name});report.samples.push(sample);save();return sample;}
 async function reset(){await page.evaluate(()=>{window.scrollTo(0,0);for(const el of document.querySelectorAll('*'))if(el.scrollHeight>el.clientHeight&&/auto|scroll/.test(getComputedStyle(el).overflowY))el.scrollTop=0;});await button().scrollIntoViewIfNeeded();if(await button().getAttribute('aria-expanded')==='true')await button().click();await page.waitForTimeout(250);}
 async function open(name){phase=name;await button().click();await page.waitForTimeout(500);return measure(name);}
 report.tabs=await page.locator('[data-section-tab]').evaluateAll(es=>es.map(e=>e.getAttribute('data-section-tab')));
 await reset();await open('tab_change_before');phase='tab_change';
 await page.locator('[data-section-tab="经营概况"]').click({timeout:5000});await page.waitForTimeout(800);await measure('tab_change_after');
 const available=await page.locator('[data-field-help-trigger]').evaluateAll(es=>es.filter(e=>e.checkVisibility()).map(e=>e.getAttribute('aria-label')));report.other_help_candidates=available;
 for(const otherLabel of available.filter(x=>x!==label).slice(0,2)){phase='other_help';await page.locator('[data-field-help-trigger][aria-label='+JSON.stringify(otherLabel)+']').first().click({timeout:5000});await page.waitForTimeout(500);report.actions.push({case:'other_help',label:otherLabel});await measure('other_help_'+otherLabel);}
 await page.locator('[data-section-tab="描述"]').click({timeout:5000});await page.waitForTimeout(500);await measure('description_tab');
 const descHelp=page.locator('[data-field-help-trigger][aria-label="描述"]');if(await descHelp.isVisible()){await descHelp.click();await page.waitForTimeout(500);await measure('description_help');}
 await page.locator('[data-section-tab="设置"]').click({timeout:5000});await page.waitForTimeout(500);await measure('hidden_help_after_tab');
 // Open the original field help before a route change; retain an explicit full-navigation limitation.
 await reset();await open('route_change_before');phase='route_change';
 await page.goto(base+'/t/demo/a/588?menu_id=382',{waitUntil:'domcontentloaded',timeout:45000});
 report.actions.push({case:'route_change',navigation:'full document navigation only; SPA switch remains unverified'});
 await page.waitForTimeout(1200);await measure('route_change_after');await Promise.allSettled([...pending]);report.runtime_after=await ident();report.completed_at=new Date().toISOString();save();console.log(JSON.stringify({samples:report.samples.length,selected_help:report.selected_help,requests:report.requests.length,blocked:report.blocked.length,errors:report.console_errors.length}));
}catch(e){report.fatal={phase,name:e.name,message:safeText(e.message)};save();console.log(JSON.stringify(report.fatal));process.exitCode=1;}finally{await browser?.close();token='';}
