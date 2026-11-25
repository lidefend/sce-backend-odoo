import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import type { ContractV2Snapshot, ContractV2Container } from '../src/app/contracts/v2/types';
import { projectNodeComponents, navigateToDeclaredNode } from '../src/app/presentation/nodeComponentPresentation';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import {
  createContractV2Store,
  resolveContractV2FieldDescriptorMap,
  resolveContractV2FormFieldMap,
  resolveContractV2RequiredFieldCodes,
} from '../src/app/contracts/v2/store';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import { buildCanonicalNativeFormBridge } from '../src/pages/contractForm/canonicalNativeFormBridge';
function baseSnapshot(): ContractV2Snapshot {
  return {
    pageInfo: {
      pageId: 'page.x.document.form', sceneKey: 'x.document.form', pageName: 'Document',
      model: 'x.document', viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.7.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.document.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 },
      containerTree: [{
        containerId: 'section.identity', containerType: 'group', type: 'group', title: 'Identity', span: 24, columns: 2,
        children: [{
          containerId: 'field.name', containerType: 'field', type: 'field', name: 'name', title: '', span: 12,
          label: 'Name', nolabel: true,
          children: [], widgetList: [{
            widgetId: 'field.name', widgetType: 'input', fieldCode: 'name', label: 'Name', span: 12,
            semanticType: 'text', capabilities: [], componentConfig: { fieldType: 'char' },
            ownerContainerId: 'field.name',
          }],
        }, {
          containerId: 'field.state', containerType: 'field', type: 'field', name: 'state', title: '', span: 12,
          children: [], widgetList: [{
            widgetId: 'field.state', widgetType: 'select', fieldCode: 'state', label: 'State', span: 12,
            semanticType: 'status', capabilities: [], componentConfig: { fieldType: 'selection' },
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
              semanticType: 'detail_collection', capabilities: [], componentConfig: { fieldType: 'one2many' },
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
  const sourceIdentity = {
    schemaVersion: '1.0.0' as const,
    model: 'x.document',
    viewType: 'form',
    viewId: 71,
    viewXmlId: 'x.document_form',
    viewContentHash: 'd'.repeat(64),
    viewStructureKey: `struct.v1.${'e'.repeat(24)}`,
    crossEnvironmentStable: true,
    kind: field ? 'field' as const : 'container' as const,
    name: field ? 'message' : 'content',
    nativeLocator: '/form/content',
    occurrenceIndex: 1,
    sourcePosition: 0,
    occurrenceKey: `occ.v1.${'f'.repeat(24)}`,
    authoritative: true,
    sourceAuthority: { kind: 'ir.ui.view' as const, projectionOnly: true as const, noBusinessFactAuthority: true as const },
  };
  source.nativeIdentity = sourceIdentity;
  s.layoutContract.containerTree=[{containerId:'feedback',title:'',type:'div',containerType:'div',columns:1,span:24,children:[source],widgetList:[],
    semanticType:'feedback_message',componentConfig:{purpose,contentRef:{containerId:'content'}},modifiers:{invisible:purpose==='explanation'?{kind:'static',value:false}:{kind:'not',expr:{kind:'field_truthy',field:'active'}}}}];
  if(field) {
    Object.assign(source,{widgetId:'content',fieldCode:'message',sourcePosition:0});
    source.widgetList=[{widgetId:'content',widgetType:'input',fieldCode:'message',label:'Message',span:24,
      ownerContainerId:'content',semanticType:'long_text',capabilities:[],
      nativeLocator:'/form/content',occurrenceIndex:1,sourcePosition:0,nativeIdentity:sourceIdentity,
      componentConfig:{fieldType:'text',native_locator:'/form/content',occurrence_index:1,source_position:0},
      fieldDescriptor:{
        schemaVersion:'1.0.0',
        fieldCode:'message',
        label:'Message',
        fieldType:'text',
        widgetType:'input',
        semanticType:'long_text',
        readonly:true,
      }}];
    s.statusContract.widgetStatus=[{widgetId:'content',visible:true,readonly:true,required:false,disabled:false,auth:'read'}];
  }
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
for(const mutation of ['semantic','purpose','extra','missing','duplicate','source','condition','owner']) test(mutation,()=>{
  const s=fixture();const n=s.layoutContract.containerTree[0];
  if(mutation==='semantic') n.semanticType='future_node_semantic';
  if(mutation==='purpose') n.componentConfig!.purpose='danger';
  if(mutation==='extra') n.componentConfig!.html='bad';
  if(mutation==='missing') n.children=[];
  if(mutation==='duplicate') n.children.push({...n.children[0]});
  if(mutation==='source') n.children[0].nativeLocator='';
  if(mutation==='condition') n.modifiers={};
  if(mutation==='owner') s.layoutContract.containerTree.push({...n,containerId:'other',children:[]});
  assert.throws(
    () => projectNodeComponents(s),
    {name: mutation === 'semantic' ? 'FrontendCapabilityGapError' : 'ContractGapError'},
  );
});
test('actual decoder presenter bridge',()=>{
  const b=bridge();assert.equal(b.primaryNodes[0].containerId,'feedback');
  assert.equal((b.primaryNodes[0] as { nodeComponent?: { content: string } }).nodeComponent?.content,'Read this');
  assert.equal((b.primaryNodes[0].children![0] as { feedbackContentOwned?: boolean }).feedbackContentOwned,true);
});
export function navigationFixture() {
  const s=fixture();
  const identity = (name:string, locator:string, fill:string) => ({
    schemaVersion:'1.0.0' as const, model:'x.document', viewType:'form', viewId:72,
    viewXmlId:'x.document_navigation_form', viewContentHash:'3'.repeat(64),
    viewStructureKey:`struct.v1.${'3'.repeat(24)}`, crossEnvironmentStable:true,
    kind:'container' as const, name, nativeLocator:locator, occurrenceIndex:1,
    sourcePosition:1, occurrenceKey:`occ.v1.${fill.repeat(24)}`, authoritative:true,
    sourceAuthority:{kind:'ir.ui.view' as const, projectionOnly:true as const, noBusinessFactAuthority:true as const},
  });
  s.layoutContract.containerTree=[{containerId:'link',title:'',nativeLocator:'/form/link',occurrenceIndex:1,nativeIdentity:identity('link','/form/link','1'),sourceAuthority:{kind:'native_view'},type:'div',containerType:'div',span:24,columns:1,text:'Details',children:[],widgetList:[],semanticType:'navigation_anchor',componentConfig:{targetContainerId:'target'}},
    {containerId:'target',nativeLocator:'/form/target',occurrenceIndex:1,nativeIdentity:identity('target','/form/target','2'),sourceAuthority:{kind:'native_view'},type:'group',containerType:'group',span:24,columns:1,title:'Details',text:'Target',children:[],widgetList:[]}];
  return s;
}
function nativeWidgetOccurrence(name: string, locator: string, index: number) {
  return {
    schemaVersion: '1.0.0' as const,
    model: 'x.document',
    viewType: 'form',
    viewId: 71,
    viewXmlId: 'x.document_form',
    viewContentHash: 'a'.repeat(64),
    viewStructureKey: `struct.v1.${'b'.repeat(24)}`,
    crossEnvironmentStable: true,
    kind: 'widget' as const,
    name,
    nativeLocator: locator,
    occurrenceIndex: index,
    sourcePosition: index,
    occurrenceKey: `occ.v1.${String(index).padStart(24, 'c')}`,
    authoritative: true,
    sourceAuthority: { kind: 'ir.ui.view' as const, projectionOnly: true as const, noBusinessFactAuthority: true as const },
  };
}
export function ribbonFixture() {
  const s = baseSnapshot();
  s.pageInfo.contractVersion = '2.7.0';
  s.statusContract.widgetStatus = [];
  s.statusContract.buttonStatus = [];
  s.actionContract.actionRuleList = [];
  s.layoutContract.containerTree = [{
    containerId: 'widget.web_ribbon.1',
    containerType: 'widget',
    type: 'widget',
    name: 'web_ribbon',
    widget: 'web_ribbon',
    title: 'Paid',
    label: 'Paid',
    span: 24,
    children: [],
    widgetList: [],
    nativeLocator: '/form[1]/widget[1]',
    occurrenceIndex: 1,
    sourcePosition: 1,
    nativeIdentity: nativeWidgetOccurrence('web_ribbon', '/form[1]/widget[1]', 1),
    sourceAuthority: { kind: 'native_view', projectionOnly: true, noBusinessFactAuthority: true },
    semanticType: 'display_ribbon',
    componentConfig: {
      nativeWidget: 'web_ribbon',
      widgetStatus: 'ready',
      identityComplete: true,
      optionsResolution: 'parsed',
      optionsRaw: "{'bg_color': 'text-bg-success'}",
      options: { bg_color: 'text-bg-success' },
    },
    attributes: { name: 'web_ribbon', title: 'Paid', bg_color: 'text-bg-success' },
  }];
  s.statusContract.containerStatus = [{ containerId: 'widget.web_ribbon.1', visible: true, disabled: false }];
  return s;
}
export function unsupportedNativeNodeFixture(name = 'sc_stage_requirements') {
  const s = ribbonFixture();
  const node = s.layoutContract.containerTree[0];
  node.containerId = `widget.${name}.1`;
  node.name = name;
  node.widget = name;
  node.title = 'Stages';
  node.label = 'Stages';
  node.nativeIdentity = nativeWidgetOccurrence(name, `/form[1]/widget[1]`, 1);
  node.semanticType = 'unsupported_native_node';
  node.componentConfig = {
    nativeWidget: name,
    widgetStatus: 'unsupported',
    identityComplete: true,
    optionsResolution: 'parsed',
    optionsRaw: "{'limit': 3}",
    options: { limit: 3 },
    reasonCode: 'NATIVE_VIEW_WIDGET_UNSUPPORTED',
  };
  s.statusContract.containerStatus = [{ containerId: node.containerId, visible: true, disabled: true, reasonCode: 'NATIVE_VIEW_WIDGET_UNSUPPORTED' }];
  return s;
}
function payloadNodeFixture(semanticType: 'insight_summary' | 'action_list', nativeWidget: string, payloadSchema: string, payload: Record<string, unknown>) {
  const s = ribbonFixture();
  const node = s.layoutContract.containerTree[0];
  node.containerId = `widget.${nativeWidget}.1`;
  node.name = nativeWidget;
  node.widget = nativeWidget;
  node.title = nativeWidget;
  node.label = nativeWidget;
  node.nativeIdentity = nativeWidgetOccurrence(nativeWidget, '/form[1]/sheet[1]/widget[1]', 1);
  node.nativeLocator = '/form[1]/sheet[1]/widget[1]';
  node.occurrenceIndex = 1;
  node.semanticType = semanticType;
  node.componentConfig = {
    nativeWidget,
    widgetStatus: 'ready',
    identityComplete: true,
    optionsResolution: 'parsed',
    optionsRaw: "{}",
    options: {},
    payloadSchema,
    payload,
    payloadSourceAuthority: {
      kind: 'smart_construction_core_native_view_widget_payload',
      module: 'smart_construction_core',
      projectionOnly: false,
      noBusinessFactAuthority: false,
    },
  };
  s.statusContract.containerStatus = [{ containerId: node.containerId, visible: true, disabled: false }];
  return s;
}
export function insightSummaryFixture() {
  return payloadNodeFixture('insight_summary', 'sc_insight_banner', 'insight_summary.v1', {
    tone: 'warning',
    title: '项目已创建，可以继续推进。',
    message: '建议先补全项目地点。',
    detail: '否则后续办理会受阻。',
  });
}
export function actionListFixture(nativeWidget = 'sc_stage_requirements') {
  return payloadNodeFixture('action_list', nativeWidget, 'action_list.v1', {
    title: nativeWidget === 'sc_next_actions' ? '下一步动作' : '阶段要求',
    emptyText: '当前没有需要处理的事项',
    items: [{
      id: 'item-1',
      title: '项目地点',
      description: '完成即可进入下一阶段',
      state: 'required',
      tone: 'warning',
      actionType: 'act_window_xmlid',
      actionRef: 'smart_construction_core.action_sc_project_manage',
      actionLabel: '去处理',
      actionPayload: { project_id: 7 },
      enabled: true,
    }],
  });
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
test('native ribbon presentation and canonical consumption',()=>{
  const s = ribbonFixture();
  const presentation = projectNodeComponents(s).presentations.get('widget.web_ribbon.1');
  assert.equal(presentation?.kind, 'ribbon');
  assert.equal(presentation?.content, 'Paid');
  assert.equal(presentation?.styleClass, 'text-bg-success');
  const model = presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(s)), 'readonly');
  const node = model.zones.primary[0];
  assert.equal(node.nativeWidgetComponent?.componentKey, 'sc.display.ribbon');
  assert.deepEqual(node.nativeWidgetComponent?.componentConfig.options, { bg_color: 'text-bg-success' });
  assert.equal((node.nativePresentation.nodeComponent as { kind?: string } | undefined)?.kind, 'ribbon');
});
test('insight summary consumes the declared project payload', () => {
  const s = insightSummaryFixture();
  const presentation = projectNodeComponents(s).presentations.get('widget.sc_insight_banner.1');
  assert.equal(presentation?.kind, 'insight_summary');
  assert.deepEqual(presentation?.insight, {
    tone: 'warning',
    title: '项目已创建，可以继续推进。',
    message: '建议先补全项目地点。',
    detail: '否则后续办理会受阻。',
  });
  const model = presentContractV2Form(createContractV2Store(decodeContractV2Snapshot(s)), 'readonly');
  assert.equal((model.zones.primary[0].nativePresentation.nodeComponent as { kind?: string }).kind, 'insight_summary');
});
for (const nativeWidget of ['sc_stage_requirements', 'sc_next_actions']) {
  test(`action list consumes ${nativeWidget}`, () => {
    const s = actionListFixture(nativeWidget);
    const presentation = projectNodeComponents(s).presentations.get(`widget.${nativeWidget}.1`);
    assert.equal(presentation?.kind, 'action_list');
    assert.equal(presentation?.actionList?.items[0].title, '项目地点');
    assert.equal(presentation?.actionList?.items[0].actionType, 'act_window_xmlid');
    assert.equal(presentation?.actionList?.items[0].enabled, true);
  });
}
test('real producer fixture flows through decoder and both consumption paths', () => {
  const producer = JSON.parse(readFileSync(
    'frontend/apps/web/scripts/fixtures/native_embedded_widget_contract_v2.json',
    'utf8',
  )) as ContractV2Snapshot;
  const supported = structuredClone(producer);
  supported.layoutContract.containerTree = supported.layoutContract.containerTree.slice(0, 2);
  supported.statusContract.containerStatus = supported.statusContract.containerStatus.slice(0, 2);

  const decoded = decodeContractV2Snapshot(supported);
  const store = createContractV2Store(decoded);
  decoded.layoutContract.containerTree.slice(0, 2).forEach((node) => {
    assert.equal(node.fieldCode, undefined);
    assert.equal(node.fieldInfo, undefined);
  });
  assert.equal(resolveContractV2FieldDescriptorMap(store).web_ribbon, undefined);
  assert.equal(resolveContractV2FormFieldMap(store).web_ribbon, undefined);
  assert.equal(store.widgetsByFieldCode.has('web_ribbon'), false);
  assert.equal(resolveContractV2RequiredFieldCodes(store).includes('web_ribbon'), false);
  const model = presentContractV2Form(store, 'readonly');
  const nodes = model.zones.primary;
  assert.deepEqual(nodes.map((node) => node.nativeWidgetComponent?.componentKey), [
    'sc.display.ribbon',
    'sc.display.ribbon',
  ]);
  assert.deepEqual(nodes.map((node) => node.title), ['Paid', 'Draft']);
  assert.deepEqual(
    nodes.map((node) => (node.nativePresentation.nodeComponent as { styleClass?: string } | undefined)?.styleClass),
    ['text-bg-success', ''],
  );
  assert.throws(
    () => decodeContractV2Snapshot(producer),
    /NATIVE_VIEW_WIDGET_UNSUPPORTED/,
  );
  const fieldCodeCollision = structuredClone(supported);
  fieldCodeCollision.layoutContract.containerTree[0].fieldCode = 'web_ribbon';
  assert.throws(
    () => decodeContractV2Snapshot(fieldCodeCollision),
    /embedded widget nodes cannot carry a field identity/,
  );
  const fieldInfoCollision = structuredClone(supported);
  fieldInfoCollision.layoutContract.containerTree[0].fieldInfo = { type: 'char' };
  assert.throws(
    () => decodeContractV2Snapshot(fieldInfoCollision),
    /embedded widget nodes cannot carry field metadata/,
  );
  const fieldsCollision = structuredClone(supported);
  fieldsCollision.layoutContract.containerTree[0].fields = ['web_ribbon'];
  assert.throws(
    () => decodeContractV2Snapshot(fieldsCollision),
    /embedded widget nodes cannot own fields/,
  );
  const hidden = structuredClone(supported);
  hidden.statusContract.containerStatus[0].visible = false;
  const hiddenNode = presentContractV2Form(
    createContractV2Store(decodeContractV2Snapshot(hidden)),
    'readonly',
  ).zones.primary[0];
  assert.equal(hiddenNode.visible, false);
});
for (const name of ['unknown_widget']) {
  test(`unsupported native widget ${name}`, () => {
    assert.throws(
      () => projectNodeComponents(unsupportedNativeNodeFixture(name)),
      /NATIVE_VIEW_WIDGET_UNSUPPORTED/,
    );
  });
}
for (const mutation of [
  'widget',
  'identity',
  'options',
  'options-raw-type',
  'parsed-missing-options',
  'missing-reason',
]) test('ribbon '+mutation,()=>{
  const s = ribbonFixture();
  const node = s.layoutContract.containerTree[0];
  if (mutation === 'widget') node.componentConfig!.nativeWidget = 'other';
  if (mutation === 'identity') node.nativeIdentity = nativeWidgetOccurrence('web_ribbon', '/form[1]/widget[2]', 2);
  if (mutation === 'options') node.componentConfig!.optionsResolution = 'broken';
  if (mutation === 'options-raw-type') node.componentConfig!.optionsRaw = { limit: 3 };
  if (mutation === 'parsed-missing-options') delete node.componentConfig!.options;
  if (mutation === 'missing-reason') {
    node.semanticType = 'unsupported_native_node';
    node.componentConfig = {
      nativeWidget: 'unknown_widget',
      widgetStatus: 'unsupported',
      identityComplete: true,
      optionsResolution: 'none',
    };
  }
  assert.throws(() => projectNodeComponents(s), { name: 'ContractGapError' }, mutation);
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
