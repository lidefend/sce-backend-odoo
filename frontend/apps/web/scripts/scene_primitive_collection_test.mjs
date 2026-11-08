import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { compileScript, parse } from 'vue/compiler-sfc';

const root = process.cwd();
const icon = `${root}/frontend/apps/web/src/components/design-system/scene-adapter/ScSceneIcon.vue`;
const table = `${root}/frontend/apps/web/src/components/design-system/scene-adapter/ScSceneTable.vue`;
const out = await build({
  stdin:{contents:`
import {createApp,h} from 'vue';
import Icon from ${JSON.stringify(icon)};
import Table from ${JSON.stringify(table)};
window.rows=[];
createApp({setup(){return()=>h('div',[
 h(Icon,{id:'semantic',name:'check',label:'完成',decorative:false}),
 h(Icon,{id:'decorative',name:'file'}),
 h(Table,{id:'table',rows:[{id:'r1',title:'A'},{id:'r2',title:'B'}],columns:[{key:'title',label:'标题'}],rowKey:'id',accessibleLabel:'列表',interactiveRows:true,emptyText:'暂无数据',
  onRowActivate:(row,event)=>window.rows.push({id:row.id,source:event.source,trusted:event.nativeEvent?.isTrusted??null})})
])}}).mount('#app');
`,resolveDir:`${root}/frontend/apps/web`,loader:'js'},
  bundle:true,write:false,platform:'browser',format:'iife',
  define:{'process.env.NODE_ENV':'"production"','__VUE_OPTIONS_API__':'true','__VUE_PROD_DEVTOOLS__':'false','__VUE_PROD_HYDRATION_MISMATCH_DETAILS__':'false'},
  resolveExtensions:['.tsx','.ts','.jsx','.js','.css','.json','.mjs'],loader:{'.css':'empty'},
  alias:{vue:`${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,'tdesign-vue-next':`${root}/frontend/packages/ui/node_modules/tdesign-vue-next`},
  plugins:[{name:'sfc',setup(b){b.onLoad({filter:/\.vue$/},a=>{const d=parse(fs.readFileSync(a.path,'utf8'),{filename:a.path}).descriptor;return{contents:compileScript(d,{id:a.path,inlineTemplate:true}).content,loader:'ts',resolveDir:path.dirname(a.path)}})}}],logLevel:'error'});
const {launchChromium}=await import('../../../../scripts/verify/playwright_runtime.mjs');
const browser=await launchChromium();
try{
 const page=await browser.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent('<div id="app"></div>');await page.addScriptTag({content:out.outputFiles[0].text});
 await page.locator('#semantic').waitFor({state:'visible'});
 assert.equal(await page.locator('#semantic').getAttribute('aria-label'),'完成');
 assert.equal(await page.locator('#semantic').getAttribute('role'),'img');
 assert.equal(await page.locator('#semantic').getAttribute('aria-hidden'),null);
 assert.equal(await page.locator('#decorative').getAttribute('aria-hidden'),'true');
 assert.equal(await page.locator('#decorative').getAttribute('aria-label'),null);
 assert.ok(await page.locator('#table').count());
 assert.ok(await page.getByText('标题').count());
 await page.getByText('A',{exact:true}).click();
 await page.getByText('B',{exact:true}).locator('xpath=ancestor::tr').focus();
 await page.keyboard.press('Enter');
 const rows=await page.evaluate(()=>window.rows);
 assert.deepEqual(rows,[{id:'r1',source:'pointer',trusted:true},{id:'r2',source:'keyboard',trusted:true}]);
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({browser:browser.version(),checks:9,consoleErrors:0,tableKeyboard:'PASS',emptyText:'PROJECTED'}));
}finally{await browser.close()}
