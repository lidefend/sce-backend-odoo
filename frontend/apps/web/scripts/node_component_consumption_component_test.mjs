import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const componentResolutionWarnings = [];
const baseConsoleWarn = console.warn;
console.warn = (...args) => {
  const message = args.map(String).join(' ');
  if (message.includes('Failed to resolve component')) componentResolutionWarnings.push(message);
  baseConsoleWarn(...args);
};
const root = process.cwd();
const entry = `${root}/frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue`;
const output = '/tmp/fe-gate-03a-node-component-ssr.mjs';
const harness = `
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import Renderer from ${JSON.stringify(entry)};
import CanonicalRenderer from ${JSON.stringify(`${root}/frontend/apps/web/src/pages/contractForm/CanonicalFormNodeRenderer.vue`)};
import { actionListFixture,bridge,fixture,insightSummaryFixture,navigationFixture,ribbonFixture } from '${root}/frontend/apps/web/scripts/node_component_consumption_test.ts';
import { decodeContractV2Snapshot } from '${root}/frontend/apps/web/src/app/contracts/v2/schema.ts';
import { createContractV2Store } from '${root}/frontend/apps/web/src/app/contracts/v2/store.ts';
import { presentContractV2Form } from '${root}/frontend/apps/web/src/app/presentation/contractFormPresenter.ts';
export async function render(purpose, visible=true, field=false) {
 const s=purpose==='anchor'?navigationFixture():fixture(purpose,field || purpose==='error');
 if(!visible) s.statusContract.containerStatus=[{containerId:'feedback',visible:false}];
 const b=bridge(s);
 return renderToString(createSSRApp({render:()=>h(Renderer,{nodes:b.primaryNodes,fieldSchemasForNodes:b.fieldSchemasForNodes,isNodeVisible:b.nodeVisible})}));
}
export async function renderRibbon() {
 const s=ribbonFixture();const b=bridge(s);
 return renderToString(createSSRApp({render:()=>h(Renderer,{nodes:b.primaryNodes,fieldSchemasForNodes:b.fieldSchemasForNodes,isNodeVisible:b.nodeVisible})}));
}
export async function renderCanonicalRibbon() {
 const store=createContractV2Store(decodeContractV2Snapshot(ribbonFixture()));
 const model=presentContractV2Form(store,'readonly');
 return renderToString(createSSRApp({render:()=>h(CanonicalRenderer,{node:model.zones.primary[0],preferReadonlyFacts:true})}));
}
export async function renderCanonicalAction(reasonMessage='', enabled=false) {
 const actionRef={actionId:'backend.inline_action',actionKey:'inline_action',backendIdentity:'object:inline_action',allowed:enabled,button:{name:'inline_action'}};
 const action={key:'inline_action',label:'办理',icon:'',tier:'secondary',visible:true,enabled,
   reasonCode:enabled?'':'STATE_BLOCKED',...(reasonMessage?{reasonMessage}:{}),visibleProfiles:['edit'],safety:{},actionRef};
 const node={nodeId:'inline-action',kind:'container',visible:true,title:'',text:'',fields:[],children:[],action,
   nativePresentation:{nodeComponent:null},attributes:{},columns:24,span:24,zoneRole:null,styleToken:''};
 return renderToString(createSSRApp({render:()=>h(CanonicalRenderer,{node})}));
}
export async function renderProjectNode(fixtureFactory) {
 const s=fixtureFactory();const b=bridge(s);
 return renderToString(createSSRApp({render:()=>h(Renderer,{nodes:b.primaryNodes,fieldSchemasForNodes:b.fieldSchemasForNodes,isNodeVisible:b.nodeVisible})}));
}
export async function renderInsight() {
 return renderProjectNode(insightSummaryFixture);
}
export async function renderActionList(nativeWidget) {
 return renderProjectNode(()=>actionListFixture(nativeWidget));
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
const { render, renderLegacy, renderRibbon, renderCanonicalRibbon, renderCanonicalAction, renderInsight, renderActionList } = await import(output);
let checks=0;
for(const purpose of ['advisory','warning','error','explanation']) {
 const html=await render(purpose);assert.equal((html.match(/Read this/g)||[]).length,1);checks++;
 if (purpose !== 'explanation') assert.ok(html.includes('t-alert'), html);
 if(purpose==='error') assert.ok(html.includes('role="alert"'));
 else if(purpose!=='explanation') assert.ok(html.includes('role="status"'));
 else assert.ok(!html.includes('role="alert"'));checks++;
 const hidden=await render(purpose,false);assert.ok(!hidden.includes('native-explicit-feedback'));checks++;
}
for(const purpose of ['advisory','warning','error','explanation']) { const html=await render(purpose,true,true); assert.equal((html.match(/Read this/g)||[]).length,1);checks++; }
const nav=await render('anchor');assert.ok(nav.includes('data-contract-container-id="target"'));checks++;
assert.ok(nav.includes('<button'));checks++;
for (const html of [await renderRibbon(), await renderCanonicalRibbon()]) {
  assert.equal((html.match(/native-ribbon/g)||[]).length,1);
  assert.equal((html.match(/>Paid</g)||[]).length,1);
  assert.ok(html.includes('text-bg-success'));
  assert.ok(html.includes('data-native-widget="web_ribbon"'));
  checks += 4;
}
const deniedInlineAction = await renderCanonicalAction('先补齐办理依据', false);
assert.ok(deniedInlineAction.includes('data-workflow-reason-trigger="inline_action"'));
assert.ok(deniedInlineAction.includes('aria-label="先补齐办理依据"'));
assert.ok(deniedInlineAction.includes('data-disabled-reason="先补齐办理依据"'));
assert.ok(deniedInlineAction.includes('disabled'));
checks += 4;
const codedInlineAction = await renderCanonicalAction('', false);
assert.ok(codedInlineAction.includes('aria-label="STATE_BLOCKED"'));
checks += 1;
const enabledInlineAction = await renderCanonicalAction('', true);
assert.ok(!enabledInlineAction.includes('data-workflow-reason-trigger'));
assert.ok(!enabledInlineAction.includes('data-disabled-reason'));
checks += 2;
const insightHtml = await renderInsight();
assert.ok(insightHtml.includes('项目已创建，可以继续推进。'));
assert.ok(insightHtml.includes('建议先补全项目地点。'));
assert.ok(insightHtml.includes('t-alert'));
checks += 3;
for (const nativeWidget of ['sc_stage_requirements', 'sc_next_actions']) {
  const html = await renderActionList(nativeWidget);
  assert.ok(html.includes('项目地点'));
  assert.ok(html.includes('去处理'));
  assert.ok(html.includes('data-action-ref="smart_construction_core.action_sc_project_manage"'));
  checks += 3;
}
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
assert.deepEqual(componentResolutionWarnings, []);
console.log(`[node-component-SSR] PASS cases=${checks} actual NativeFormTreeRenderer`);
