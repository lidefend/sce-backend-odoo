import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const root = process.cwd();
const entry = `${root}/frontend/apps/web/src/views/businessConfigSurface/LowCodeFieldChipEditor.vue`;
const output = '/tmp/field-configuration-component-test.mjs';
const harness = `
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import FieldEditor from ${JSON.stringify(entry)};
export async function render(draftValue, searchValue, advancedPanelOpen=true) {
  const props = { title:'字段配置', names:['id'], fieldOptions:[], fieldOptionTotal:0, searchValue,draftValue,advancedPanelOpen,chipKeyPrefix:'c',optionKeyPrefix:'o',fieldDisplayLabel:n=>n,fieldHelpText:n=>n,fieldOptionHelpText:f=>f.name,fieldOptionLabel:f=>f.label,isDragging:()=>false,isDropTarget:()=>false };
  return renderToString(createSSRApp({render:()=>h(FieldEditor,props)}));
}`;
await build({ stdin:{contents:harness,resolveDir:`${root}/frontend/apps/web`,loader:'js'},bundle:true,platform:'node',format:'esm',outfile:output,
  resolveExtensions:['.tsx','.ts','.jsx','.js','.css','.json','.mjs'],
  banner:{js: "import { createRequire as nodeRequire } from 'node:module'; const require = nodeRequire(import.meta.url);"},
  loader:{'.css':'empty'},alias:{'vue/server-renderer':require.resolve('vue/server-renderer'),vue:`${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,'tdesign-vue-next':`${root}/frontend/packages/ui/node_modules/tdesign-vue-next`},
  plugins:[{name:'actual-vue-sfc',setup(builder){builder.onLoad({filter:/\.vue$/},args=>{const {descriptor}=parse(fs.readFileSync(args.path,'utf8'),{filename:args.path});const compiled=compileScript(descriptor,{id:args.path,inlineTemplate:true});return {contents:compiled.content,loader:'ts',resolveDir:args.path.slice(0,args.path.lastIndexOf('/'))};});}}],logLevel:'error' });
const { render } = await import(output);
let checks=0;
for (const [draft,search] of [['amount','money'],['id','record'],['','']]) {
  const html=await render(draft,search);
  const inputs = html.match(/<input\b[^>]*>/g) || [];
  const valueOf = tag => tag?.match(/ value="([^"]*)"/)?.[1] || '';
  assert.equal(valueOf(inputs[0]), draft); checks++;
  if (search) { assert.equal(valueOf(inputs[1]), search); checks++; }
  assert.equal((html.match(/<form\b/g)||[]).length,1); checks++;
  assert.ok(html.includes('data-editor-composition="official-field-configuration"')); checks++;
}
const closed=await render('amount','search',false);assert.equal((closed.match(/<form\b/g)||[]).length,0);checks++;
const source=fs.readFileSync(entry,'utf8');
const body=source.match(/function onAddValidated\(result: \{ validateResult: unknown \}\) \{([\s\S]*?)\n\}/)[1];
let adds=0;const submit=new Function('result','emit',body);
for(const value of [false,{},undefined,'true']) submit({validateResult:value},()=>adds++);
assert.equal(adds,0);checks++;
submit({validateResult:true},name=>{assert.equal(name,'addName');adds++;});assert.equal(adds,1);checks++;
console.log(`[field-configuration-component] PASS ${checks} cases real SSR component and submit wiring`);
