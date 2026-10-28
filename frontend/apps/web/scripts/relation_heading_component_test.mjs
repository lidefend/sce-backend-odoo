import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const root = process.cwd();
const source = `${root}/frontend/apps/web/src`;
const harness = `
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import Section from '${source}/components/template/FormSection.vue';
import Tree from '${source}/components/template/NativeFormTreeRenderer.vue';
export async function render({label, hidden=false, state='empty', readonly=true, outer=false, name='line_ids'}) {
 const rows=state==='populated'?[{key:'row-1',id:1,values:{name:'完整关系记录'}}]:[];
 const columns=[{name:'name',label:'记录名称',ttype:'char',required:false,readonly:true}];
 const adapter={busy:false,showOne2manyErrors:false,readContext:{},
  visibleOne2manyRows:()=>rows,one2manyColumns:()=>columns,one2manyVisibleColumns:()=>columns,
  prepareOne2manyColumns:()=>undefined,isOne2manyHydrating:()=>state==='loading',
  one2manyCreateLabel:()=> '新增记录',one2manyCanOpenRow:()=>false,one2manyCanCreate:()=>false,one2manyCanInlineEdit:()=>false,one2manyCanUnlink:()=>false,
  one2manyColumnInputType:()=> 'text',one2manyRowHints:()=>[],one2manyRowErrors:()=>[],one2manyEffectiveColumn:(_name,_row,column)=>column,one2manyCellError:()=>'',one2manyRowStateLabel:()=>'',one2manyRowMessages:()=>[],one2manyRowError:()=>'',
  one2manyColumnDisplayValue:(_column,value)=>String(value??''),one2manySummary:()=>'',removedOne2manyRows:()=>[],
  selectedRelationOptions:()=>[],relationIds:()=>[],one2manyRowLabel:()=> '记录',
  one2manyRemovalLabels:()=>({remove:'移除',cancelCreate:'取消新增',restore:'恢复',removedSummary:'已移除',pendingRemoval:'待移除'}),
  one2manyFieldError:()=>'',one2manyRowHasErrors:()=>false,one2manyRowErrorMessages:()=>[],
 };
 const field={key:'test-field',name,label,type:'one2many',value:[],readonly,hideLabel:hidden,required:false,span:24,
  componentKey:'sc.relation.table',componentRenderer:'ProfessionalDetailCollectionControl',one2manyPageSize:20,
  descriptor:{relation:'x.line'},renderProfile:readonly?'readonly':'edit',presentationMode:'task'};
 const props={title:'',columns:1,fields:[field],relationAdapter:adapter};
 const treeProps={nodes:[{type:'group',name:'outer',string:label,label,columns:1,span:24,children:[{type:'field',name,span:24}]}],
  fieldSchemasForNodes:nodes=>nodes.filter(n=>n.type==='field').map(()=>field),isNodeVisible:()=>true,
  relationAdapter:adapter,preferReadonlyFacts:true};
 const app=createSSRApp({render:()=>outer?h(Tree,treeProps):h(Section,props)});
 const warnings=[];app.config.warnHandler=message=>warnings.push(message);
 const html=await renderToString(app);
 return {html,warnings};
}`;
const result = await build({ stdin: { contents: harness, resolveDir: `${root}/frontend/apps/web`, loader: 'js' }, bundle: true, write: false, platform: 'node', format: 'esm', define: {'import.meta.env':'{}'},
 resolveExtensions: ['.tsx','.ts','.jsx','.js','.css','.json','.mjs'], loader: {'.css':'empty'},
 banner: {js:"import { createRequire } from 'node:module'; const require = createRequire(import.meta.url);"},
 alias:{'vue/server-renderer':require.resolve('vue/server-renderer'),vue:`${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js`,'tdesign-vue-next':`${root}/frontend/packages/ui/node_modules/tdesign-vue-next`},
 plugins:[{name:'actual-vue-sfc',setup(builder){builder.onLoad({filter:/\.vue$/},args=>{if(args.path.endsWith('/ScDialog.vue'))return {contents:'export default { render: () => null };',loader:'js'};const {descriptor}=parse(fs.readFileSync(args.path,'utf8'),{filename:args.path});return {contents:compileScript(descriptor,{id:args.path,inlineTemplate:true}).content,loader:'ts',resolveDir:args.path.slice(0,args.path.lastIndexOf('/'))};});}}],logLevel:'error'});
const output=`${root}/.runtime/relation-heading-component-test.mjs`;fs.mkdirSync(`${root}/.runtime`,{recursive:true});fs.writeFileSync(output,result.outputFiles[0].text);
const {render}=await import(output);
let checks=0;const observations=[];
for(const label of ['任务','合作者','其他关系明细']) for(const state of ['empty','loading','populated']) for(const hidden of [false,true]) for(const readonly of [true,false]) {
 const {html,warnings}=await render({label,state,hidden,readonly});
 const titles=[...html.matchAll(/data-detail-collection-title[^>]*>([^<]*)<\/span>/g)].map(m=>m[1]);
 assert.deepEqual(titles,hidden?[]:[label],`${label}/${state}/hidden=${hidden}/readonly=${readonly}`);checks++;
 assert.equal((html.match(/<label\b[^>]*class="label"/g)||[]).length,0,'FormSection must yield title to relation control');checks++;
 if(readonly && state==='empty'){assert.ok(html.includes('暂无可展示记录'));checks++;}
 if(state==='loading'){assert.ok(html.includes('正在加载关系记录'));checks++;}
 if(state==='populated'){assert.ok(html.includes('完整关系记录'));checks++;}
 assert.deepEqual(warnings,[]);checks++;
 observations.push({label,state,hidden,readonly,titles});
}
for(const state of ['empty','loading','populated']) {
 const {html,warnings}=await render({label:'外层关系标题',hidden:true,state,outer:true});
 const text=html.replace(/<[^>]+>/g,'');
 assert.equal(text.split('外层关系标题').length-1,1,'NativeFormTreeRenderer owns the single outer title');checks++;
 assert.equal((html.match(/data-detail-collection-title/g)||[]).length,0);checks++;
 assert.deepEqual(warnings,[]);checks++;
 observations.push({outer:true,hidden:true,state,titleOccurrences:1});
}
fs.writeFileSync(`${root}/.runtime/fepc11-component-observations.json`,JSON.stringify({kind:'actual_component_SSR',checks,observations},null,2)+'\n');
console.log(`[relation-heading-component] PASS scenarios=${observations.length} checks=${checks} actual FormSection/NativeFormTreeRenderer/X2ManyRelationRenderer`);
