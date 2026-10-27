import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { build } from 'esbuild';
import { parse, compileScript } from 'vue/compiler-sfc';

const root = process.cwd();
const entry = path.join(root, 'frontend/apps/web/src/components/template/NativeWeightedRelationDisplay.vue');
const api = path.join(root, 'frontend/apps/web/src/api/data.ts');
const output = path.join(root, '.runtime/weighted-relation-component-test.mjs');
const harness = `
import { createRenderer, h, ref, nextTick } from 'vue';
import Component from ${JSON.stringify(entry)};
import { calls } from ${JSON.stringify(api)};
import assert from 'node:assert/strict';
const node = type => ({ type, children: [], parent: null, props: {}, text: '' });
const renderer=createRenderer({
  patchProp(n,key,old,value){n.props[key]=value;},
  insert(n,parent,anchor){if(n.parent){const i=n.parent.children.indexOf(n);if(i>=0)n.parent.children.splice(i,1);}n.parent=parent;const i=anchor?parent.children.indexOf(anchor):-1;if(i<0)parent.children.push(n);else parent.children.splice(i,0,n);},
  remove(n){if(n.parent){const i=n.parent.children.indexOf(n);if(i>=0)n.parent.children.splice(i,1);n.parent=null;}},
  createElement:node,createText:text=>({...node('text'),text}),createComment:text=>({...node('comment'),text}),
  setText(n,text){n.text=text;},setElementText(n,text){n.text=text;n.children=[];},parentNode:n=>n.parent,
  nextSibling:n=>n.parent?.children[n.parent.children.indexOf(n)+1]||null,setScopeId(){},
});
const host=node('root');
const declaration={kind:'weighted_relation',version:1,relation_model:'account.analytic.account',label_field:'display_name',key_encoding:'csv_ids',value_unit:'%',mode:'readonly',empty_text:'未分配'};
const props=ref({declaration,value:{'1':100},context:{allowed_company_ids:[1]}});
const tick=async()=>{for(let i=0;i<6;i++){await Promise.resolve();await nextTick();}};
const all=(n=host)=>[n,...n.children.flatMap(child=>all(child))];
const text=()=>all().map(n=>n.text).join('');
const state=()=>all().find(n=>n.props['data-semantic-component']==='NativeWeightedRelationDisplay')?.props['data-display-state'];
const app=renderer.createApp({setup:()=>()=>h(Component,props.value)});app.mount(host);await tick();
assert.equal(calls.length,1);assert.equal(state(),'loading');
props.value={...props.value,value:{'2':50}};await tick();assert.equal(calls.length,2);
calls[1].resolve({records:[{id:2,display_name:'新账户'}]});await tick();assert.equal(text(),'新账户：50%');
assert(all().some(n=>n.type==='button'&&n.props.type==='button'));assert(!all().some(n=>n.type==='input'));
calls[0].resolve({records:[{id:1,display_name:'过期账户'}]});await tick();assert.equal(text(),'新账户：50%');
props.value={...props.value,context:{allowed_company_ids:[2]}};await tick();assert.equal(calls.length,3);
assert.deepEqual(calls[2].params.context,{allowed_company_ids:[2]});assert.equal(state(),'loading');assert(!text().includes('新账户'));
calls[2].reject(new Error('permission denied'));await tick();assert.equal(state(),'error');assert(!text().includes('新账户'));
props.value={...props.value,value:{}};await tick();assert.equal(state(),'ready');assert.equal(text(),'未分配');assert.equal(calls.length,3);
props.value={...props.value,declaration:undefined};await tick();assert.equal(state(),'error');assert.equal(calls.length,3);
props.value={declaration,value:{'1':100},context:{allowed_company_ids:[1]}};await tick();assert.equal(calls.length,4);
app.unmount();calls[3].resolve({records:[{id:1,display_name:'卸载之后'}]});await tick();assert.equal(host.children.length,0);
assert(calls.every(call=>call.params.model==='account.analytic.account'&&call.params.fields.join(',')==='id,display_name'));
assert.deepEqual(props.value.value,{'1':100});
export const result='PASS actual SFC: stale order/context denial/empty/missing declaration/unmount/raw preservation';
`;
await build({ stdin: { contents: harness, resolveDir: path.dirname(entry), sourcefile: 'weighted-relation-mounted.ts' },
  bundle: true, platform: 'node', format: 'esm', outfile: output, logLevel: 'error', plugins: [{ name: 'mounted-weighted-relation', setup(builder) {
    builder.onLoad({filter:/\/api\/data\.ts$/},()=>({contents:'export const calls=[];export const readRecord=params=>new Promise((resolve,reject)=>calls.push({params,resolve,reject}));',loader:'js'}));
    builder.onLoad({filter:/\.vue$/},args=>{
      if(args.path!==entry){
        assert(/\/(ScInlineState|ScPopover|ScButton)\.vue$/.test(args.path));
        const contents=args.path.endsWith('/ScPopover.vue')
          ? "import {h} from 'vue';export default {inheritAttrs:false,setup:(_, {slots})=>()=>h('span',slots.trigger?.())};"
          : args.path.endsWith('/ScButton.vue')
            ? "import {h} from 'vue';export default {inheritAttrs:false,setup:(_, {attrs,slots})=>()=>h('button',attrs,slots.default?.())};"
            : "import {h} from 'vue';export default {inheritAttrs:false,props:['label'],setup:props=>()=>h('span',props.label)};";
        return {contents,loader:'js',resolveDir:path.dirname(args.path)};
      }
      const {descriptor}=parse(fs.readFileSync(args.path,'utf8'),{filename:args.path});
      return {contents:compileScript(descriptor,{id:args.path,inlineTemplate:true}).content,loader:'ts',resolveDir:path.dirname(args.path)};
    });
  }}] });
console.log('[weighted-relation-mounted]', (await import(output)).result);
