/** Existing fixture data, local unsaved editor changes only. Publication/write requests denied. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
import { permitsInventoryRequest } from './bootstrap_inventory_policy.mjs';
const root=process.cwd(), base='http://127.0.0.1:5180';
const build=JSON.parse(await fs.readFile(path.resolve(root,'../sce-offrepo/artifacts/config05-20260929/build-identity.json')));
assert.equal(createHash('sha256').update(Buffer.from(await fetch(`${base}${build.entry}`).then(r=>r.arrayBuffer()))).digest('hex'),build.entry_sha256);
assert.equal(process.env.DB_NAME,'sc_frontend_acceptance');
assert.ok(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
const out=path.join(root,'artifacts/frontend-web-fix-20260928',`config-field-${Date.now()}`);await fs.mkdir(out,{recursive:true});
const report={build,status:'running',checks:0,errors:[],blocked:[],calls:[]};
const browser=await launchChromium({headless:true});
try {
 const page=await browser.newPage({viewport:{width:1440,height:950}});page.setDefaultTimeout(20000);
 page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/api/**',async route=>{try{
  const req=route.request(),raw=req.postDataJSON(),body=raw?.params?.intent?raw.params:raw,pathname=new URL(req.url()).pathname;
  if(!permitsInventoryRequest(req.method(),pathname,raw,true)){report.blocked.push(body?.intent||pathname);return route.abort();}
  const response=await route.fetch({timeout:20000});report.calls.push({intent:body?.intent||pathname,status:response.status()});
  if(body?.intent==='ui.business_config.change_set.open'){const payload=await response.json();assert.equal(payload.data.created,false,'resume must not create a draft');}
  await route.fulfill({response});
 }catch(e){report.errors.push(String(e.message).split('\n')[0]);await route.abort().catch(()=>{});}});
 const check=(actual,expected)=>{assert.deepEqual(actual,expected);report.checks++;};
 await page.goto(`${base}/login`);await page.locator('input').nth(0).fill('fixture_role_config_admin');await page.locator('input').nth(1).fill(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
 const db=page.getByPlaceholder('请输入数据库名');if(await db.count() && await db.isEnabled())await db.fill('sc_frontend_acceptance');
 await page.getByRole('button',{name:/^登录$/}).click();await page.waitForURL(u=>u.pathname!='/login');await page.waitForLoadState('networkidle');
 await page.goto(`${base}/admin/business-config?model=payment.request&action_id=775&menu_id=545&open_list_search=1`);
 await page.getByRole('button',{name:'开发者工具',exact:true}).click();
 const form=page.locator('[data-editor-composition="official-field-configuration"]');await form.waitFor();
 const draft=form.getByPlaceholder('输入字段名');
 await draft.fill('id');check(await draft.inputValue(),'id');await draft.press('Enter');
 await page.waitForFunction(()=>document.querySelector('input[placeholder="输入字段名"]')?.value==='');check(await draft.inputValue(),'');
 await draft.fill('id');await form.getByRole('button',{name:'添加',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('input[placeholder="输入字段名"]')?.value==='');check(await draft.inputValue(),'');
 const search=page.getByPlaceholder('搜索可选字段');await search.fill('name');check(await search.inputValue(),'name');await search.fill('');check(await search.inputValue(),'');
 const chips=page.locator('.field-chip-list .field-chip');const original=await chips.allTextContents();assert.ok(original.length>1);
 await chips.nth(0).getByRole('button',{name:/^下移/}).click();await chips.nth(1).getByRole('button',{name:/^上移/}).click();check(await chips.allTextContents(),original);
 for(const width of [1440,390]){await page.setViewportSize({width,height:950});const heading=page.getByRole('heading',{name:'列表与搜索设置',exact:true});await heading.scrollIntoViewIfNeeded();const headingBounds=await heading.boundingBox();check(Boolean(headingBounds && headingBounds.width>100 && headingBounds.height<60),true);await page.screenshot({path:path.join(out,`editor-header-${width}.png`)});await form.scrollIntoViewIfNeeded();const bounds=await form.boundingBox();check(Boolean(bounds && bounds.x>=0 && bounds.x+bounds.width<=width+1),true);check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);await page.screenshot({path:path.join(out,`editor-${width}.png`)});await form.screenshot({path:path.join(out,`form-${width}.png`)});}
 // Unsaved local state is discarded by closing the browser; no config action is executed.
 await page.unrouteAll({behavior:'wait'});check(report.errors,[]);check(report.blocked,[]);report.status='passed';
}catch(e){report.status='failed';report.error=String(e.message).split('\n')[0];process.exitCode=1;}
finally{await browser.close();await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(`[config-field] ${report.status} checks=${report.checks} report=${out}/report.json`);}
