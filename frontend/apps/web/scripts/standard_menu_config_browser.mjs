/** Existing fixture data, local unsaved editor changes only. Publication/write requests denied. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { launchChromium } from '../../../../scripts/verify/playwright_runtime.mjs';
import { permitsInventoryRequest } from './bootstrap_inventory_policy.mjs';
const root=process.cwd(), base='http://127.0.0.1:5180';
const build=JSON.parse(await fs.readFile(path.resolve(root,'../sce-offrepo/artifacts/config02-20260929/build-identity.json')));
assert.equal(createHash('sha256').update(Buffer.from(await fetch(`${base}${build.entry}`).then(r=>r.arrayBuffer()))).digest('hex'),build.entry_sha256);
assert.equal(process.env.DB_NAME,'sc_frontend_acceptance');
assert.ok(process.env.SC_ACCEPTANCE_FIXTURE_PASSWORD);
const out=path.join(root,'artifacts/frontend-web-fix-20260928',`menu-config-${Date.now()}`);await fs.mkdir(out,{recursive:true});
const report={build,status:'running',checks:0,errors:[],blocked:[],calls:[]};
const browser=await launchChromium({headless:true});
let page;
try {
 page=await browser.newPage({viewport:{width:1440,height:950}});page.setDefaultTimeout(20000);
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
 await page.goto(`${base}/admin/menu-config?menu_id=545`);
 report.step='menu heading';await page.getByRole('heading',{name:'菜单配置',exact:true}).waitFor();
 const panel=page.getByRole('region',{name:'当前菜单配置'});report.step='selected menu panel';await panel.waitFor();
 const search=page.getByPlaceholder('搜索菜单名称或路径');
 await search.fill('付款');check(await search.inputValue(),'付款');
 await page.getByRole('button',{name:'清空筛选',exact:true}).click();check(await search.inputValue(),'');
 const name=panel.locator('[data-semantic-component="ScInput"] input').first();
 const original=await name.inputValue();await name.fill('菜单验收未保存');check(await name.inputValue(),'菜单验收未保存');
 await page.locator('.menu-side-panel').getByRole('button',{name:'展开批量维护表格',exact:true}).click();
 const row=page.locator('tr.selected');const bulk=row.locator('[data-semantic-component="ScInput"] input').first();
 check(await bulk.inputValue(),'菜单验收未保存');await bulk.fill('');check(await name.inputValue(),'');
 await name.fill(original);check(await bulk.inputValue(),original);
 await page.getByRole('button',{name:'新增一级菜单',exact:true}).click();
 const createName=page.getByPlaceholder('输入业务菜单名称');await createName.fill('新菜单未保存');check(await createName.inputValue(),'新菜单未保存');
 await createName.fill('');check(await page.getByRole('button',{name:'创建菜单',exact:true}).isDisabled(),true);
 await page.getByRole('button',{name:'收起新增入口',exact:true}).click();
 for(const width of [1440,390]){await page.setViewportSize({width,height:950});await panel.scrollIntoViewIfNeeded();check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);await page.screenshot({path:path.join(out,`menu-${width}.png`)});}
 // Unsaved local state is discarded by closing the browser; no config action is executed.
 await page.unrouteAll({behavior:'wait'});check(report.errors,[]);check(report.blocked,[]);report.status='passed';
}catch(e){await page?.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});report.status='failed';report.error=String(e.message).split('\n')[0];process.exitCode=1;}
finally{await browser.close();await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(`[menu-config] ${report.status} checks=${report.checks} report=${out}/report.json`);}
