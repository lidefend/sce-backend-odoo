import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const root = process.cwd();
const entry = `${root}/frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue`;
const output = '/tmp/fe-gate-03a-node-component-ssr.mjs';
const harness = `
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import Renderer from ${JSON.stringify(entry)};
import { bridge,fixture,navigationFixture } from '${root}/frontend/apps/web/scripts/node_component_consumption_test.ts';
export async function render(purpose, visible=true, field=false) {
 const s=purpose==='anchor'?navigationFixture():fixture(purpose,field || purpose==='error');
 if(!visible) s.statusContract.containerStatus=[{containerId:'feedback',visible:false}];
 const b=bridge(s);
 return renderToString(createSSRApp({render:()=>h(Renderer,{nodes:b.primaryNodes,fieldSchemasForNodes:b.fieldSchemasForNodes,isNodeVisible:b.nodeVisible})}));
}
export async function renderLegacy(styleToken,{text='legacy text',child=false,hidden=false,explicit=false,anchor=false,role}={}) {
 const node = anchor
   ? {containerId:'legacy-node',type:'div',styleToken,span:24,text:'Legacy link',children:[],
      nodeComponent:{kind:'anchor',content:'Legacy link',visible:true,targetContainerId:'target'}}
   : explicit
     ? {containerId:'legacy-node',type:'div',styleToken,span:24,text,children:[],
        nodeComponent:{kind:'feedback',purpose:'advisory',content:'Owned feedback',visible:true,role:'status'}}
     : {containerId:'legacy-node',type:'div',styleToken,span:24,text,role,children:child?[{containerId:'field-node',type:'field',name:'note',span:24}]:[]};
 return renderToString(createSSRApp({render:()=>h(Renderer,{nodes:[node],fieldSchemasForNodes:()=>[],isNodeVisible:()=>!hidden})}));
}`;
await build({ define:{'import.meta.env':'{}'}, stdin:{contents:harness,resolveDir:`${root}/frontend/apps/web`,loader:'js'},bundle:true,platform:'node',format:'esm',outfile:output,
  resolveExtensions:['.tsx','.ts','.jsx','.js','.css','.json','.mjs'],
  banner:{js: "import { createRequire as nodeRequire } from 'node:module'; const require = nodeRequire(import.meta.url);"},
  loader:{'.css':'empty'},alias:{'vue/server-renderer':require.resolve('vue/server-renderer'),vue:`${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,'tdesign-vue-next':`${root}/frontend/packages/ui/node_modules/tdesign-vue-next`},
  plugins:[{name:'actual-vue-sfc',setup(builder){builder.onLoad({filter:/\.vue$/},args=>{const {descriptor}=parse(fs.readFileSync(args.path,'utf8'),{filename:args.path});const compiled=compileScript(descriptor,{id:args.path,inlineTemplate:true});return {contents:compiled.content,loader:'ts',resolveDir:args.path.slice(0,args.path.lastIndexOf('/'))};});}}],logLevel:'error' });
const { render, renderLegacy } = await import(output);
let checks=0;
for(const purpose of ['advisory','warning','error','explanation']) {
 const html=await render(purpose);assert.equal((html.match(/Read this/g)||[]).length,1);checks++;
 if(purpose==='error') assert.ok(html.includes('role="alert"'));
 else if(purpose!=='explanation') assert.ok(html.includes('role="status"'));
 else assert.ok(!html.includes('role="alert"'));checks++;
 const hidden=await render(purpose,false);assert.ok(!hidden.includes('native-explicit-feedback'));checks++;
}
for(const purpose of ['advisory','warning','error','explanation']) { const html=await render(purpose,true,true); assert.equal((html.match(/Read this/g)||[]).length,1);checks++; }
const nav=await render('anchor');assert.ok(nav.includes('data-contract-container-id="target"'));checks++;
assert.ok(nav.includes('<button'));checks++;
const expectedWarnings=[];const originalWarn=console.warn;console.warn=(...args)=>expectedWarnings.push(args.map(String).join(' '));
for(const token of ['alert','alert-info','alert-warning','alert-danger','alert-link']) {
  for(const options of [{},{child:true},{text:''},{hidden:true}]) {
    await assert.rejects(()=>renderLegacy(token,options),/Legacy Vue alert declaration/);checks++;
  }
}
await assert.rejects(()=>renderLegacy('',{role:'alert'}),/role:alert/);checks++;
console.warn=originalWarn;
assert.ok(expectedWarnings.every(message=>message.includes('Unhandled error during execution of render function')));
const explicitFeedback=await renderLegacy('alert alert-info',{explicit:true});
assert.equal((explicitFeedback.match(/native-explicit-feedback/g)||[]).length,1);checks++;
const explicitAnchor=await renderLegacy('alert-link',{anchor:true});
assert.ok(explicitAnchor.includes('<button'));checks++;
const statusText=await renderLegacy('',{text:'Status copy',role:'status'});
assert.ok(statusText.includes('role="status"'));checks++;
console.log(`[node-component-SSR] PASS cases=${checks} actual NativeFormTreeRenderer`);
