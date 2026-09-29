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
const out=path.join(root,'artifacts/frontend-web-fix-20260928',`menu-config-${Date.now()}`);await fs.mkdir(out,{recursive:true});
const report={build,status:'running',checks:0,errors:[],blocked:[],calls:[]};
const browser=await launchChromium({headless:true});
let page;let failPanel=true;let releasePanel;const panelBarrier=new Promise(resolve=>{releasePanel=resolve;});
try {
 page=await browser.newPage({viewport:{width:1440,height:950}});page.setDefaultTimeout(20000);
 page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/api/**',async route=>{try{
  const req=route.request(),raw=req.postDataJSON(),body=raw?.params?.intent?raw.params:raw,pathname=new URL(req.url()).pathname;
  if(!permitsInventoryRequest(req.method(),pathname,raw,true)){report.blocked.push(body?.intent||pathname);return route.abort();}
  if(body?.intent==='ui.menu_config.panel.get' && failPanel){failPanel=false;await panelBarrier;report.calls.push({intent:body.intent,status:200,simulated:true});await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:false,error:{code:'TEST_READ_FAILURE',message:'模拟菜单读取失败',retryable:false}})});return;}
  const response=await route.fetch({timeout:20000});report.calls.push({intent:body?.intent||pathname,status:response.status()});
  if(body?.intent==='ui.business_config.change_set.open'){const payload=await response.json();assert.equal(payload.data.created,false,'resume must not create a draft');}
  await route.fulfill({response});
 }catch(e){report.errors.push(String(e.message).split('\n')[0]);await route.abort().catch(()=>{});}});
 const check=(actual,expected)=>{assert.deepEqual(actual,expected);report.checks++;};
 const captureState=async(locator,label)=>{for(const width of [1440,390]){await page.setViewportSize({width,height:950});await locator.scrollIntoViewIfNeeded();const bounds=await locator.boundingBox();check(Boolean(bounds && bounds.x>=0 && bounds.x+bounds.width<=width+1),true);await locator.screenshot({path:path.join(out,`${label}-${width}.png`)});}await page.setViewportSize({width:1440,height:950});};
 await page.goto(`${base}/login`);await page.locator('input').nth(0).fill('fixture_role_config_admin');await page.locator('input').nth(1).fill(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
 const db=page.getByPlaceholder('请输入数据库名');if(await db.count() && await db.isEnabled())await db.fill('sc_frontend_acceptance');
 await page.getByRole('button',{name:/^登录$/}).click();await page.waitForURL(u=>u.pathname!='/login');await page.waitForLoadState('networkidle');
 await page.evaluate(()=>sessionStorage.setItem('sc_menu_config_save_notice','已保存：模拟反馈验收，未执行保存'));
 await page.goto(`${base}/admin/menu-config?menu_id=545`);
 const loading=page.locator('[data-semantic-component="ScInlineState"][data-state="loading"]');await loading.waitFor();check(await loading.getAttribute('aria-busy'),'true');releasePanel();
 const failure=page.locator('[data-semantic-component="ScInlineState"][data-state="error"]');await failure.waitFor();check(await failure.getAttribute('role'),'alert');check(await page.locator('[data-semantic-component="ScInlineState"][data-state="success"]').count(),0);
 await captureState(failure,'error');await page.getByRole('button',{name:'刷新菜单配置',exact:true}).click();
 report.step='menu heading';await page.getByRole('heading',{name:'菜单配置',exact:true}).waitFor();
 const panel=page.getByRole('region',{name:'当前菜单配置'});report.step='selected menu panel';await panel.waitFor();await failure.waitFor({state:'hidden'});const success=page.locator('[data-semantic-component="ScInlineState"][data-state="success"]');await success.waitFor();check(await success.getAttribute('role'),'status');check((await success.innerText()).includes('已保存：模拟反馈验收，未执行保存'),true);
 await captureState(success,'success');const search=page.getByPlaceholder('搜索菜单名称或路径');
 await search.fill('付款');check(await search.inputValue(),'付款');
 await page.getByRole('button',{name:'清空筛选',exact:true}).click();check(await search.inputValue(),'');
 const name=panel.locator('[data-semantic-component="ScInput"] input').first();
 const original=await name.inputValue();await name.fill('菜单验收未保存');check(await name.inputValue(),'菜单验收未保存');
 await page.locator('.menu-side-panel').getByRole('button',{name:'展开批量维护表格',exact:true}).click();
 const row=page.locator('tr.selected');const bulk=row.locator('[data-semantic-component="ScInput"] input').first();
 check(await bulk.inputValue(),'菜单验收未保存');await bulk.fill('');check(await name.inputValue(),'');
 await name.fill(original);check(await bulk.inputValue(),original);
 report.step='choice controls';
 const number=panel.locator('[data-semantic-component="ScNumberInput"] input');const bulkNumber=row.locator('[data-semantic-component="ScNumberInput"] input');
 const oldNumber=await number.inputValue();await number.fill('31');await number.press('Tab');check(await bulkNumber.inputValue(),'31');
 await number.fill('');await number.press('Tab');check(await bulkNumber.inputValue(),'');
 await number.fill(oldNumber);await number.press('Tab');check(await bulkNumber.inputValue(),oldNumber);
 const visible=panel.getByRole('checkbox',{name:'显示菜单',exact:true});const wasVisible=await visible.isChecked();
 await panel.getByText('显示菜单',{exact:true}).click();check(await visible.isChecked(),!wasVisible);check(await row.getByRole('checkbox',{name:'显示菜单',exact:true}).isChecked(),!wasVisible);
 await panel.getByText('显示菜单',{exact:true}).click();check(await visible.isChecked(),wasVisible);
 const role=panel.locator('.group-check-item').first();const roleInput=role.getByRole('checkbox');const wasRole=await roleInput.isChecked();
 await role.click();check(await roleInput.isChecked(),!wasRole);await role.click();check(await roleInput.isChecked(),wasRole);
 const parent=panel.locator('[data-semantic-component="ScSelect"]').first();await parent.click();
 await page.locator('.t-popup:visible').getByText('不移动',{exact:true}).click();check(((await parent.locator('input').inputValue()) || (await parent.innerText())).includes('不移动'),true);
 await page.getByRole('button',{name:'新增一级菜单',exact:true}).click();
 const createName=page.getByPlaceholder('输入业务菜单名称');await createName.fill('新菜单未保存');check(await createName.inputValue(),'新菜单未保存');
 await createName.fill('');check(await page.getByRole('button',{name:'创建菜单',exact:true}).isDisabled(),true);
 await page.getByRole('button',{name:'收起新增入口',exact:true}).click();
 report.step='version selection';const versionResponse=page.waitForResponse(r=>(r.request().postData()||'').includes('ui.menu_config.versions'));await page.getByRole('button',{name:'查看菜单版本与回滚',exact:true}).click();
 const versionHttp=await versionResponse;assert.equal(versionHttp.ok(),true);const versionPayload=await versionHttp.json();assert.equal(versionPayload.ok,true);assert.ok(Array.isArray(versionPayload.data?.versions));assert.equal(versionPayload.meta?.bootstrapped_from_current_policies,false);const radios=page.getByRole('radio');if(versionPayload.data?.versions?.length) await radios.first().waitFor();const radioCount=await radios.count();report.versionOptions=radioCount;
 check(radioCount,versionPayload.data.versions.length);if(radioCount===1) report.uncovered=['版本互斥切换：现有数据仅一个版本'];if(radioCount){await radios.last().check();check(await page.getByRole('radio',{checked:true}).count(),1);await radios.first().check();check(await page.getByRole('radio',{checked:true}).count(),1);}
 else report.uncovered=['版本单选：现有数据无历史版本，不新增fixture'];
 for(const width of [1440,390]){await page.setViewportSize({width,height:950});await panel.scrollIntoViewIfNeeded();await parent.click();const option=page.locator('.t-popup:visible').getByText('不移动',{exact:true});await option.waitFor({state:'visible'});const bounds=await option.boundingBox();check(Boolean(bounds && bounds.x>=0 && bounds.x+bounds.width<=width+1),true);await option.click();await option.waitFor({state:'hidden'});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);await page.screenshot({path:path.join(out,`menu-${width}.png`)});}
 // Unsaved local state is discarded by closing the browser; no config action is executed.
 await page.unrouteAll({behavior:'wait'});check(report.errors,[]);check(report.blocked,[]);report.status='passed';
}catch(e){await page?.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});report.status='failed';report.error=String(e.message).split('\n')[0];process.exitCode=1;}
finally{releasePanel();await browser.close();await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(`[menu-config] ${report.status} checks=${report.checks} report=${out}/report.json`);}
