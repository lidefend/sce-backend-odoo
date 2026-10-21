// Render the real SFC with a Vue host renderer; click its actual button handler.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const vue = require('../../frontend/apps/web/node_modules/vue');
const compiler = require('../../frontend/apps/web/node_modules/vue/compiler-sfc');
const ts = require('../../frontend/apps/web/node_modules/typescript');
const contract = JSON.parse(fs.readFileSync(0, 'utf8'));
let declaration = contract;
const navigations = [];
const mocks = {
 'vue': vue,
 'vue-router': { useRoute:()=>({}), useRouter:()=>({push:async path=>navigations.push(path)}) },
 '../stores/session': {useSessionStore:()=>({get errorStateContract(){return declaration;}})},
 '../config/debug': {isHudEnabled:()=>false},
 '../composables/useSuggestedAction': {useSuggestedAction:()=>({canRun:vue.ref(false),label:vue.ref(''),run:()=>false})},
 './design-system/ScButton.vue': {default:vue.defineComponent({setup:(_,ctx)=>()=>vue.h('button',ctx.attrs,ctx.slots.default?.())})},
};
function evaluate(source) {
 const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 vm.runInNewContext('(function(require,module,exports){'+code+'\n})',{})(name=>{
   if(mocks[name])return mocks[name];
   const path=name.endsWith('contractGap')?'frontend/apps/web/src/app/contract/contractGap.ts':'frontend/apps/web/src/app/productErrorState.ts';
   return evaluate(fs.readFileSync(path,'utf8'));
 },module,module.exports);
 return module.exports;
}
const {descriptor}=compiler.parse(fs.readFileSync('frontend/apps/web/src/components/StatusPanel.vue','utf8'));
const component=evaluate(compiler.compileScript(descriptor,{id:'test-status-panel',inlineTemplate:true}).content).default;
const node=(type,text='')=>({type,text,props:{},children:[],parent:null});
const renderer=vue.createRenderer({
 createElement:type=>node(type),createText:text=>node('#text',text),createComment:text=>node('#comment',text),
 setText:(el,text)=>el.text=text,setElementText:(el,text)=>el.text=text,
 patchProp:(el,key,old,value)=>el.props[key]=value,
 insert:(el,parent)=>{el.parent=parent;parent.children.push(el);},
 remove:el=>{if(el.parent)el.parent.children=el.parent.children.filter(x=>x!==el);},
 parentNode:el=>el.parent,nextSibling:()=>null,
});
const flatten=root=>[root,...root.children.flatMap(flatten)];
const text=root=>root.text+root.children.map(text).join('');
function mount(props){const root=node('root');const app=renderer.createApp(component,{title:'',variant:'error',...props});app.mount(root);return {root,app};}
(async()=>{
 declaration=structuredClone(contract);
 const missing=declaration.states.find(row=>row.statuses.includes(404));
 missing.title='Declared title';missing.action.label='Declared action';missing.action.path='/my-work';
 let mounted=mount({errorCode:404});
 assert.ok(text(mounted.root).includes('Declared title'));
 let button=flatten(mounted.root).find(el=>el.type==='button');
 assert.equal(text(button),'Declared action');await button.props.onClick();
 assert.deepEqual(navigations,['/my-work']);mounted.app.unmount();
 let retries=0;mounted=mount({errorCode:409,onRetry:async()=>{retries++;}});
 button=flatten(mounted.root).find(el=>el.type==='button');await button.props.onClick();assert.equal(retries,1);mounted.app.unmount();
 mounted=mount({errorCode:409});assert.ok(text(mounted.root).includes('error_states.action.retry.executor'));
 assert.equal(flatten(mounted.root).filter(el=>el.type==='button').length,0);mounted.app.unmount();
 declaration=null;mounted=mount({errorCode:404});assert.ok(text(mounted.root).includes('ContractGapError'));mounted.app.unmount();
 declaration=contract;mounted=mount({errorCode:422});assert.equal(flatten(mounted.root).filter(el=>el.type==='button').length,0);mounted.app.unmount();
 console.log('real StatusPanel render/click/contract-gap PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
