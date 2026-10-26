import assert from 'node:assert/strict';
import type { ContractV2Snapshot, ContractV2Container } from '../src/app/contracts/v2/types';
import { projectNodeComponents, navigateToDeclaredNode } from '../src/app/presentation/nodeComponentPresentation';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import { buildCanonicalNativeFormBridge } from '../src/pages/contractForm/canonicalNativeFormBridge';
function baseSnapshot(): ContractV2Snapshot {
  return {
    pageInfo: {
      pageId: 'page.x.document.form', sceneKey: 'x.document.form', pageName: 'Document',
      model: 'x.document', viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.2.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.document.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 }, componentRegistry: {
        'sc.input.text': { version: '1.0' },
        'sc.display.status': { version: '1.0' },
        'sc.display.text': { version: '1.0' },
        'sc.relation.many2one': { version: '1.0' },
        'sc.relation.table': { version: '1.0' },
      },
      containerTree: [{
        containerId: 'section.identity', containerType: 'group', type: 'group', title: 'Identity', span: 24, columns: 2,
        children: [{
          containerId: 'field.name', containerType: 'field', type: 'field', name: 'name', title: '', span: 12,
          label: 'Name', nolabel: true,
          children: [], widgetList: [{
            widgetId: 'field.name', widgetType: 'input', fieldCode: 'name', label: 'Name', span: 12,
            componentKey: 'sc.input.text', capabilities: [], componentConfig: { fieldType: 'char' },
            ownerContainerId: 'field.name',
          }],
        }, {
          containerId: 'field.state', containerType: 'field', type: 'field', name: 'state', title: '', span: 12,
          children: [], widgetList: [{
            widgetId: 'field.state', widgetType: 'select', fieldCode: 'state', label: 'State', span: 12,
            componentKey: 'sc.display.status', capabilities: [], componentConfig: { fieldType: 'selection' },
            ownerContainerId: 'field.state',
          }],
        }, {
          containerId: 'native.notebook', containerType: 'notebook', type: 'notebook', title: 'Related', span: 24, columns: 1,
          zone: 'detail_zone',
          sourceAuthority: { projection_only: true, no_business_fact_authority: true },
          children: [{
            containerId: 'field.line_ids', containerType: 'field', type: 'field', name: 'line_ids', title: '', span: 24,
            nolabel: true,
            children: [], widgetList: [{
              widgetId: 'field.line_ids', widgetType: 'table', fieldCode: 'line_ids', label: 'Lines', span: 24,
              componentKey: 'sc.relation.table', capabilities: [], componentConfig: { fieldType: 'one2many' },
              ownerContainerId: 'field.line_ids',
            }],
          }], widgetList: [],
        }],
        widgetList: [],
      }, {
        containerId: 'native.attachment', containerType: 'attachment', type: 'attachment', title: 'Attachments', span: 24,
        zone: 'attachment_zone',
        sourceAuthority: { projection_only: true, no_business_fact_authority: true }, children: [], widgetList: [],
      }, {
        containerId: 'native.chatter', containerType: 'chatter', type: 'chatter', title: 'Activity', span: 24,
        zone: 'collaboration_zone',
        sourceAuthority: { projection_only: true, no_business_fact_authority: true }, children: [], widgetList: [],
      }],
    },
    actionContract: {
      actionRuleList: [{
        actionId: 'action.submit', backendIdentity: 'button:object:action_submit', triggerType: 'click',
        sourceWidgetId: 'page.root', targetIds: [], dispatchMode: 'serverBlocking', targetScope: 'page',
        refreshMode: 'full', actionKey: 'action_submit', label: 'Submit', allowed: true, enabled: true,
        disabled: false, entitlementEvaluated: true,
        visibleProfiles: ['edit', 'readonly'], presentation: { tier: 'primary', icon: 'fa-check' },
        actionSafety: { level: 'danger', requiresConfirmation: true },
      }], dependencyGraph: { 'action.submit': ['field.name'] },
    },
    statusContract: {
      globalStatus: {
        pageVisible: true,
        pageAuth: 'edit',
        reasonCode: '',
        modelRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        recordRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        viewCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        entryCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRecordCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRenderProfile: 'edit',
      },
      widgetStatus: [
        { widgetId: 'field.name', visible: true, readonly: false, required: true, disabled: false },
        { widgetId: 'field.state', visible: false, readonly: true, required: false, disabled: true, reasonCode: 'STATE_CONTEXT_ONLY' },
        { widgetId: 'field.line_ids', visible: true, readonly: true, required: false, disabled: false },
      ],
      buttonStatus: [{ btnId: 'action.submit', visible: true, disabled: false }],
      containerStatus: [], selectorStatus: [],
    },
    dataContract: {
      mainData: { name: 'D-001', state: 'draft', line_ids: [7] }, tableRows: {}, relationRows: {},
      dictData: {}, pagination: {}, dataSource: {}, dataMeta: {},
    },
    runtimeContract: {
      patchStrategy: 'full', cachePolicy: 'snapshot', optimistic: false, lazyContainer: [],
      virtualization: {}, retryPolicy: {},
    },
    meta: {
      etag: 'e', snapshotId: 's', traceId: 't', requestId: 'r', sourceType: 'ui.contract',
      lifecycle: {
        lifecycleVersion: '1', stage: 'sealed',
        definition: { schemaId: 'v2', schemaVersion: '2', schemaSha256: 'schema', contractVersion: '2', normativeStatus: 'active' },
        generation: { generator: 'test', generatorVersion: '1', sourceType: 'test', sourceSha256: 'source' },
        runtime: { requestId: 'r', traceId: 't', clientType: 'web_pc', traceSource: 'test' },
        integrity: { algorithm: 'sha256', contractSha256: 'contract-sha' }, authority: {},
      },
    },
  };
}

export function fixture(purpose='advisory', field=false) {
  const s=baseSnapshot();s.statusContract.widgetStatus=[];s.statusContract.buttonStatus=[];s.actionContract.actionRuleList=[];
  const source: ContractV2Container={containerId:'content',type:field?'field':'span',containerType:field?'field':'span',
    name:field?'message':undefined,text:field?'':'Read this',span:24,children:[],widgetList:[],nativeLocator:'/form/content',occurrenceIndex:1,
    sourceAuthority:{kind:'native_view'},fieldInfo:field?{type:'text',readonly:true}:{}};
  s.layoutContract.containerTree=[{containerId:'feedback',title:'',type:'div',containerType:'div',columns:1,span:24,children:[source],widgetList:[],
    componentKey:'sc.feedback.message',componentConfig:{purpose,contentRef:{containerId:'content'}},modifiers:{invisible:purpose==='explanation'?{kind:'static',value:false}:{kind:'not',expr:{kind:'field_truthy',field:'active'}}}}];
  if(field) {
    Object.assign(source,{widgetId:'content',fieldCode:'message',sourcePosition:0});
    source.widgetList=[{widgetId:'content',widgetType:'input',fieldCode:'message',label:'Message',span:24,
      ownerContainerId:'content',componentKey:'sc.input.textarea',capabilities:[],
      componentConfig:{fieldType:'text',native_locator:'/form/content',occurrence_index:1,source_position:0},
      fieldDescriptor:{name:'message',type:'text',readonly:true}}];
    s.layoutContract.componentRegistry['sc.input.textarea']={version:'1.0'};
    s.statusContract.widgetStatus=[{widgetId:'content',visible:true,readonly:true,required:false,disabled:false,auth:'read'}];
  }
  s.layoutContract.componentRegistry['sc.feedback.message']={version:'1.0.0'};
  s.dataContract.mainData.message='Read this';
  return s;
}
export function bridge(s=fixture()) {
  return buildCanonicalNativeFormBridge(presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(s)), 'readonly'));
}
let checks=0;
function test(name:string, run:()=>void) {run();checks++;}
for(const purpose of ['advisory','error','warning','explanation']) for(const field of purpose==='error'?[true]:[false,true]) test(purpose+field,()=>{
  const p=projectNodeComponents(fixture(purpose,field));
  assert.equal(p.presentations.get('feedback')?.content,'Read this');
  assert.equal(p.presentations.get('feedback')?.role,purpose==='error'?'alert':purpose==='explanation'?undefined:'status');
  assert.ok(p.ownedContent.has('content'));
});
for(const purpose of ['advisory','error','warning','explanation']) test('hidden '+purpose,()=>{
  const s=fixture(purpose,purpose==='error');s.statusContract.containerStatus=[{containerId:'feedback',visible:false}];
  s.layoutContract.containerTree[0].children[0].text='';s.dataContract.mainData.message='';
  assert.equal(projectNodeComponents(s).presentations.get('feedback')?.visible,false);
});
for(const purpose of ['advisory','error','warning','explanation']) test('empty '+purpose,()=>{
  const s=fixture(purpose,purpose==='error');s.layoutContract.containerTree[0].children[0].text='';s.dataContract.mainData.message='';
  if(['error','warning'].includes(purpose)) assert.throws(()=>projectNodeComponents(s),{name:'ContractGapError'});
  else assert.equal(projectNodeComponents(s).presentations.get('feedback')?.visible,false);
});
for(const mutation of ['key','purpose','version','extra','missing','duplicate','source','condition','owner']) test(mutation,()=>{
  const s=fixture();const n=s.layoutContract.containerTree[0];
  if(mutation==='key') n.componentKey='sc.unknown';
  if(mutation==='purpose') n.componentConfig!.purpose='danger';
  if(mutation==='version') s.layoutContract.componentRegistry['sc.feedback.message']={version:'9.0.0'};
  if(mutation==='extra') n.componentConfig!.html='bad';
  if(mutation==='missing') n.children=[];
  if(mutation==='duplicate') n.children.push({...n.children[0]});
  if(mutation==='source') n.children[0].nativeLocator='';
  if(mutation==='condition') n.modifiers={};
  if(mutation==='owner') s.layoutContract.containerTree.push({...n,containerId:'other',children:[]});
  assert.throws(()=>projectNodeComponents(s),{name:'ContractGapError'});
});
test('actual decoder presenter bridge',()=>{
  const b=bridge();assert.equal(b.primaryNodes[0].containerId,'feedback');
  assert.equal((b.primaryNodes[0] as { nodeComponent?: { content: string } }).nodeComponent?.content,'Read this');
  assert.equal((b.primaryNodes[0].children![0] as { feedbackContentOwned?: boolean }).feedbackContentOwned,true);
});
export function navigationFixture() {
  const s=fixture();s.layoutContract.componentRegistry['sc.navigation.anchor']={version:'1.0.0'};
  s.layoutContract.containerTree=[{containerId:'link',title:'',nativeLocator:'/form/link',occurrenceIndex:1,sourceAuthority:{kind:'native_view'},type:'div',containerType:'div',span:24,columns:1,text:'Details',children:[],widgetList:[],componentKey:'sc.navigation.anchor',componentConfig:{targetContainerId:'target'}},
    {containerId:'target',nativeLocator:'/form/target',occurrenceIndex:1,sourceAuthority:{kind:'native_view'},type:'group',containerType:'group',span:24,columns:1,title:'Details',text:'Target',children:[],widgetList:[]}];
  return s;
}
for(const mutation of ['valid','missing','duplicate','hidden','url','empty']) test('navigation '+mutation,()=>{
  const s=navigationFixture();const [link,target]=s.layoutContract.containerTree;
  if(mutation==='missing') s.layoutContract.containerTree.pop();
  if(mutation==='duplicate') s.layoutContract.containerTree.push({...target});
  if(mutation==='hidden') target.visible=false;
  if(mutation==='url') link.componentConfig!.href='javascript:bad';
  if(mutation==='empty') link.text='';
  if(mutation==='valid') assert.equal(projectNodeComponents(s).presentations.get('link')?.targetContainerId,'target');
  else assert.throws(()=>projectNodeComponents(s),{name:'ContractGapError'});
});
test('DOM target checked again on activation',()=>{
  let scroll=0,focus=0;const e={dataset:{contractContainerId:'target'},hidden:false,closest:()=>null,getAttribute:()=>null,getClientRects:()=>[{}],scrollIntoView:()=>scroll++,focus:()=>focus++};
  const root={querySelectorAll:()=>[e]} as unknown as HTMLElement;
  navigateToDeclaredNode(root,'target');assert.equal(scroll,1);assert.equal(focus,1);
  assert.throws(()=>navigateToDeclaredNode(root,'missing'),{name:'ContractGapError'});
  e.hidden=true;assert.throws(()=>navigateToDeclaredNode(root,'target'),{name:'ContractGapError'});
});
test('record error refuses ordinary text source',()=>assert.throws(()=>projectNodeComponents(fixture('error',false)),{name:'ContractGapError'}));
test('constant advisory condition rejected',()=>{
 const s=fixture();s.layoutContract.containerTree[0].modifiers={invisible:false};
 assert.throws(()=>projectNodeComponents(s),{name:'ContractGapError'});
});
test('field validation keeps its existing ownership',()=>{
 const model=presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(fixture('error',true))),'readonly');
 const field=model.zones.primary[0].children[0].fields[0];field.errorText='Existing field error';
 assert.throws(()=>buildCanonicalNativeFormBridge(model),{name:'ContractGapError'});
});
test('page visibility is not elevated by feedback',()=>{
 const s=fixture();s.statusContract.globalStatus.pageVisible=false;
 const model=presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(s)),'readonly');
 assert.equal(model.zones.primary[0].visible,false);
});
console.log(`[node-component-consumption] PASS cases=${checks}`);
