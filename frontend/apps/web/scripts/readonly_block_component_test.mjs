/** Real SFC setup/template and Vue lifecycle; only transport and presentation boundaries are mocked. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import { parse, compileScript, registerTS } from 'vue/compiler-sfc';
const require = createRequire(import.meta.url);
registerTS(() => require('typescript'));
const kind = process.argv[process.argv.indexOf('--kind') + 1];
assert.ok(['chart', 'boq', 'grid', 'attachment', 'form-header', 'native-layout'].includes(kind), '--kind chart|boq|grid|attachment|form-header required');
const root = process.cwd();
const component = { 'native-layout': 'components/template/NativeFormTreeRenderer.vue', 'form-header': 'pages/contractForm/ContractFormProductHeader.vue', attachment: 'components/template/X2ManyRelationRenderer.vue', chart: 'components/page/blocks/BlockChartDataset.vue', boq: 'components/page/blocks/BlockBoqImportPreview.vue', grid: 'views/SceneContractBlockGridView.vue' }[kind];
const entry = `${root}/frontend/apps/web/src/${component}`;
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), `readonly-block-${kind}-`));
const output = path.join(temporary, 'mounted.mjs');

async function runMounted({ useRecordFormLayout, createContractV2Store, Component, kind, createRenderer, h, ref, nextTick, calls, route, assert }) {
  let checks = 0;
  const equal = (actual, expected, label) => { assert.deepEqual(actual, expected, label); checks += 1; };
  const node = type => ({ type, children: [], parent: null, props: {}, text: '' });
  const renderer = createRenderer({
    patchProp(n, key, _old, value) { n.props[key] = value; },
    insert(n, parent, anchor) {
      if (n.parent) { const old = n.parent.children.indexOf(n); if (old >= 0) n.parent.children.splice(old, 1); }
      n.parent = parent;
      const index = anchor ? parent.children.indexOf(anchor) : -1;
      if (index < 0) parent.children.push(n); else parent.children.splice(index, 0, n);
    },
    remove(n) { if (n.parent) { const index = n.parent.children.indexOf(n); if (index >= 0) n.parent.children.splice(index, 1); n.parent = null; } },
    createElement: type => node(type), createText: text => ({ ...node('text'), text }), createComment: text => ({ ...node('comment'), text }),
    setText(n, text) { n.text = text; }, setElementText(n, text) { n.text = text; n.children = []; },
    parentNode: n => n.parent, nextSibling: n => n.parent?.children[n.parent.children.indexOf(n) + 1] || null,
    querySelector: () => null, setScopeId() {}, cloneNode: n => ({ ...n, children: [...n.children], props: { ...n.props }, parent: null }),
    insertStaticContent(_html, parent, anchor) { const n = node('static'); n.parent = parent; parent.children.push(n); return [n, n]; },
  });
  const rootNode = node('root');
  function find(type, from = rootNode) { return from.type === type ? from : from.children.map(child => find(type, child)).find(Boolean); }
  const tick = async () => { for (let i = 0; i < 6; i += 1) { await Promise.resolve(); await nextTick(); } };
  const waitCalls = async total => { for (let i = 0; calls.length < total && i < 20; i += 1) await tick(); equal(calls.length, total, 'actual transport call count'); };
  if (kind === 'native-layout') {
    globalThis.window = { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }) };
    globalThis.document = { getElementById: () => null };
    const all = (predicate, n = rootNode) => [n, ...n.children.flatMap(child => all(() => true, child))].filter(predicate);
    const schema = nodes => nodes.filter(n => n.type === 'field').map(n => ({ name: n.name, label: n.name, key: n.name, type: n.fieldType || 'char', value: Object.hasOwn(n, 'value') ? n.value : 'visible', inputValue: Object.hasOwn(n, 'value') ? n.value : 'visible', widget: n.widget, widgetSemantics: n.widgetSemantics, readonlyEmptyText: n.readonlyEmptyText, readonly: n.readonly !== false, helpText: n.helpText, span: n.span }));
    const direct = { type: 'field', name: 'direct', span: 12 };
    const group = { type: 'group', name: 'g', span: 24, columns: 2, children: [
      { type: 'field', name: 'a', span: 12 }, { type: 'field', name: 'b', span: 8 }] };
    const props = ref({ nodes: [direct, group], fieldSchemasForNodes: schema });
    const errors = [];
    const app = renderer.createApp({ render: () => h(Component, props.value) });
    app.config.errorHandler = error => errors.push(error);
    app.mount(rootNode); await tick();
    equal(errors.length, 0, 'valid direct/group declared layout mounts');
    const spans = () => all(n => n.props['data-field-name']).map(n => [n.props['data-field-name'], n.props['data-field-span']]);
    equal(spans(), [['direct', 24], ['a', 12], ['b', 8]], 'direct child fills occupied cell; group fields keep parent spans');
    equal(all(n => n.props.style?.['--sc-layout-span'] === '12').length > 0, true, 'direct outer placement still consumes declared parent 12');
    const emptyFields = [
      { type: 'field', name: 'declared_empty', span: 12, value: '', readonlyEmptyText: '尚未生成' },
      { type: 'field', name: 'empty_without_copy', span: 12, value: null },
      { type: 'field', name: 'false_value', span: 12, fieldType: 'boolean', value: false },
      { type: 'field', name: 'zero_value', span: 12, fieldType: 'float', value: 0 },
      { type: 'field', name: 'empty_relation', span: 12, fieldType: 'many2one', value: null },
      { type: 'field', name: 'empty_ids', span: 12, fieldType: 'many2many', value: [] },
      { type: 'field', name: 'hidden_empty', span: 12, value: '', visible: false },
    ];
    props.value = { ...props.value, nodes: [{ ...group, children: emptyFields }], isNodeVisible: n => n.visible !== false, preferReadonlyFacts: true };
    await tick();
    equal(errors.length, 0, 'empty readonly declarations mount through real native renderer and FormSection');
    equal(all(n => n.props['data-field-name']).map(n => n.props['data-field-name']), emptyFields.filter(n => n.visible !== false).map(n => n.name), 'declared visible membership and order survive empty/false/zero; hidden occurrence stays absent');
    const textOf = n => n.text + n.children.map(textOf).join('');
    equal(textOf(all(n => n.props['data-field-name'] === 'declared_empty')[0]).includes('尚未生成'), true, 'declared readonly empty text rendered');
    equal(all(n => n.props['data-field-name'] === 'empty_without_copy').length, 1, 'empty field without copy retains its declared position');
    for (const readonly of [true, false]) {
      props.value = { ...props.value, nodes: [] }; await tick();
      props.value = { ...props.value, preferReadonlyFacts: readonly,
        nodes: [{ ...group, children: [{ type: 'field', name: 'declared_help', span: 12,
          value: 'fact value', readonly, helpText: 'Native field explanation' }] }] };
      await tick();
      equal(textOf(rootNode).includes('Native field explanation'), false, 'help is absent from initial body');
      const trigger = all(n => n.props['data-field-help-trigger'] !== undefined)[0];
      equal(Boolean(trigger), true, 'same occurrence has help interaction in edit and readonly');
      equal(trigger.props['aria-controls'], undefined, 'closed popup does not reference missing content');
      equal(trigger.props['aria-expanded'], false, 'closed state is truthful');
      const popover = all(n => n.type === 'test-help-popover')[0];
      popover.props.onClick(); await tick();
      equal(textOf(rootNode).includes('Native field explanation'), true, 'interaction shows original native help');
      equal(trigger.props['aria-expanded'], true, 'vendor visible event reaches the actual adapter trigger');
      equal(all(n => n.props.id === trigger.props['aria-controls']).length, 1, 'open trigger references exactly one mounted help body');
      popover.props.onClick(); await tick();
      equal(trigger.props['aria-controls'], undefined, 'closing removes dangling reference');
      equal(trigger.props['aria-expanded'], false, 'closing updates expanded state');
      equal(textOf(rootNode).includes('Native field explanation'), false, 'closed help content is destroyed');
    }
    const allocation = { type: 'field', name: 'allocation', fieldType: 'json', span: 12,
      widget: 'analytic_distribution', value: { '1': 100 },
      widgetSemantics: { kind: 'weighted_relation', version: 1, relation_model: 'account.analytic.account',
        label_field: 'display_name', key_encoding: 'csv_ids', value_unit: '%', mode: 'readonly', empty_text: '未分配' } };
    for (const readonly of [false, true]) {
      const start = calls.length;
      props.value = { ...props.value, relationAdapter: { readContext: { allowed_company_ids: [1] } },
        nodes: [{ ...group, children: [{ ...allocation, readonly }] }], preferReadonlyFacts: readonly };
      await waitCalls(start + 1);
      equal(calls[start].request, { intent: 'api.data', params: { op: 'read', model: 'account.analytic.account',
        ids: [1], fields: ['id', 'display_name'], context: { allowed_company_ids: [1] } } }, 'root component uses authorized formal context');
      calls[start].resolve({ records: [{ id: 1, display_name: '授权分析账户' }] }); await tick();
      equal(textOf(rootNode).includes('授权分析账户：100%'), true, 'actual root edit/readonly composition displays native label and percentage');
      equal(all(n => n.props['data-semantic-component'] === 'NativeWeightedRelationDisplay').length, 1, 'exactly one native display mounted');
      equal(all(n => n.props['data-semantic-component'] === 'NativeWeightedRelationDisplay')[0].props['data-display-state'], 'ready', 'native display is ready');
      equal(allocation.value, { '1': 100 }, 'root raw value preserved');
      props.value = { ...props.value, nodes: [{ ...group, children: [{ ...allocation, readonly, widgetSemantics: undefined }] }] };
      await tick();
      equal(all(n => n.props['data-semantic-component'] === 'NativeWeightedRelationDisplay')[0].props['data-display-state'], 'error', 'root missing semantics stops rather than JSON fallback');
      equal(calls.length, start + 1, 'missing declaration does not read');
    }
    props.value = { ...props.value, nodes: [{ ...group, columns: undefined }] }; await tick();
    equal(errors.some(e => e.name === 'ContractGapError'), true, 'missing grid columns stops actual renderer');
    errors.length = 0;
    props.value = { ...props.value, nodes: [{ ...group, columns: 5 }] }; await tick();
    equal(errors.some(e => e.name === 'ContractGapError'), true, 'nonintegral equal tracks stop actual renderer');
    app.unmount(); delete globalThis.window; delete globalThis.document;
    return checks;
  }
  if (kind === 'form-header') {
    const listeners = new Set();
    const media = { matches: false, addEventListener: (_event, callback) => listeners.add(callback),
      removeEventListener: (_event, callback) => listeners.delete(callback) };
    globalThis.window = { matchMedia: () => media };
    // Layout measurement is outside this custom-renderer interaction test.
    globalThis.document = { querySelector: () => null };
    globalThis.ResizeObserver = class { observe() {} disconnect() {} };
    const events = [];
    const header = ref({ title: 'Record', subtitle: '', model: 'example.record', recordIdDisplay: '7',
      hideTitle: false, showHud: false, actionId: 1, contractMetaLine: '', intakeMode: false,
      intakeRequiredSummary: '', intakeMissingSummary: '', statusbar: { visible: false, current: '', states: [], readonly: true },
      busy: false, busyKind: '', showReturn: false, mode: 'edit', modeLabel: '', dirty: false, changedFieldCount: 0,
      presentationMode: 'task', showBack: false, backLabel: 'Back', backSemanticIdentity: 'return-list', statusInteractive: false,
      showDraftSave: false, draftSaveDisabled: false, draftSaveLabel: '', showPrimaryFormAction: false,
      primaryFormActionDisabled: false, primaryFormActionHint: '', submitLabel: '', primaryAction: null,
      directActions: [], overflowActions: [], canonicalDirectActions: [], canonicalOverflowActions: [],
      configActions: [], showDiscard: false, showDebug: false, contractPresent: true, discardLabel: '', reloadLabel: '',
      recordActions: [{ key: 'remove', label: 'Remove', enabled: true }], onRecordAction: key => events.push(key) });
    const mounted = renderer.createApp({ render: () => h(Component, header.value) });
    mounted.mount(rootNode); await tick();
    const all = (predicate, from = rootNode) => [...(predicate(from) ? [from] : []), ...from.children.flatMap(child => all(predicate, child))];
    const direct = () => all(n => n.props['data-record-action'] === 'remove');
    const menu = () => all(n => n.type === 'test-dropdown');
    equal(direct().length, 1, 'desktop record action is rendered once');
    equal(menu().length, 0, 'record-only desktop has no mobile overflow');
    direct()[0].props.onClick(); equal(events, ['remove'], 'desktop dispatches once');
    media.matches = true; listeners.forEach(callback => callback()); await tick();
    equal(direct().length, 0, 'narrow viewport removes direct duplicate');
    equal(menu().length, 1, 'record-only mobile authority opens its menu');
    equal(menu()[0].props['data-mobile-action-count'], 1, 'authority counts record action');
    equal(menu()[0].props['data-mobile-action-keys'], 'record:remove', 'authority preserves record identity');
    equal(menu()[0].props.items.map(item => item.value), ['record:remove'], 'one exact menu item');
    menu()[0].props.onSelect(menu()[0].props.items[0]); equal(events, ['remove', 'remove'], 'mobile dispatches once');
    header.value = { ...header.value, recordActions: [{ key: 'remove', label: 'Remove', enabled: false }] }; await tick();
    equal(menu()[0].props.items[0].disabled, true, 'declared denial stays disabled');
    menu()[0].props.onSelect(menu()[0].props.items[0]); equal(events.length, 2, 'disabled event cannot execute');
    header.value = { ...header.value, busy: true, recordActions: [{ key: 'remove', label: 'Remove', enabled: true }] }; await tick();
    menu()[0].props.onSelect(menu()[0].props.items[0]); equal(events.length, 2, 'busy event cannot execute');
    media.matches = false; listeners.forEach(callback => callback()); await tick();
    equal(direct().length, 1, 'desktop returns to one direct action');
    direct()[0].props.onClick(); equal(events.length, 2, 'desktop busy handler is guarded');
    header.value = { ...header.value, busy: false, recordActions: [{ key: 'remove', label: 'Same', enabled: true }, { key: 'archive', label: 'Same', enabled: true }] }; await tick();
    media.matches = true; listeners.forEach(callback => callback()); await tick();
    equal(menu()[0].props.items.map(item => item.value), ['record:remove', 'record:archive'], 'same label never collapses distinct identities');
    header.value = { ...header.value, recordActions: [{ key: 'foo', label: 'Same', enabled: true }, { key: 'foo:bar', label: 'Same', enabled: true }] }; await tick();
    menu()[0].props.onSelect(menu()[0].props.items[1]); equal(events.at(-1), 'foo:bar', 'mobile retains full colon-delimited identity');
    media.matches = false; listeners.forEach(callback => callback()); await tick();
    all(n => n.props['data-record-action'] === 'foo:bar')[0].props.onClick(); equal(events.slice(-2), ['foo:bar', 'foo:bar'], 'desktop retains full identity without prefix dispatch');
    header.value = { ...header.value, recordActions: [{ key: 'foo', label: 'Same', enabled: true }, { key: 'foo:bar', label: 'Same', enabled: false }] }; await tick();
    all(n => n.props['data-record-action'] === 'foo:bar')[0].props.onClick(); equal(events.length, 4, 'disabled colon identity cannot dispatch prefix');
    header.value = { ...header.value, canonicalDirectActions: [{ key: 'blocked', label: '办理', tier: 'secondary', visible: true, enabled: false, reasonCode: 'BLOCKED', reasonMessage: '先补齐依据', actionRef: { actionId: 'blocked', backendIdentity: 'object:blocked', allowed: false } }], onCanonicalAction: key => events.push(key) }; await tick();
    const reasonTrigger = all(n => n.props['aria-label'] === '先补齐依据')[0];
    equal(reasonTrigger.props.tabindex, 0, 'denial explanation is keyboard focusable');
    let explanationClicks = 0;
    const host = { click: () => { explanationClicks += 1; } };
    reasonTrigger.props.onKeydown({ key: 'Enter', currentTarget: host, target: host, preventDefault() {} });
    equal(explanationClicks, 1, 'keyboard activates explanation trigger');
    all(n => n.props['data-action-key'] === 'blocked')[0].props.onClick();
    equal(events.length, 4, 'denial interaction never executes disabled business action');
    media.matches = true; listeners.forEach(callback => callback()); await tick();
    equal(menu()[0].props.items.find(item => item.value === 'canonical:blocked').reasonMessage, '先补齐依据', 'narrow overflow carries paired reason unchanged');
    mounted.unmount(); await tick(); equal(listeners.size, 0, 'viewport observer disposed');
    // Actual layout hook -> actual Header, with two occurrences of one field.
    // Raw field info is writable; only the chosen widget verdict is authoritative.
    const fieldNode = { type:'field', containerId:'state-header', widgetId:'state.header', name:'state',
      nativeLocator:'/form/header/field', occurrenceIndex:1, span:24,
      children:[],widgetList:[{widgetId:'state.header',fieldCode:'state',ownerContainerId:'state-header'}],attributes:{widget:'statusbar'}, fieldInfo:{name:'state',readonly:false,selection:[['draft','Draft'],['done','Done']]} };
    const duplicate = {...fieldNode,containerId:'state-body',widgetId:'state.body',nativeLocator:'/form/sheet/field',occurrenceIndex:2,attributes:{},widgetList:[{widgetId:'state.body',fieldCode:'state',ownerContainerId:'state-body'}]};
    const snapshot = {layoutContract:{containerTree:[fieldNode,duplicate],widgetList:[
      {widgetId:'state.header',fieldCode:'state',ownerContainerId:'state-header'},
      {widgetId:'state.body',fieldCode:'state',ownerContainerId:'state-body'}]},
      actionContract:{actionRuleList:[]},statusContract:{widgetStatus:[
        {widgetId:'state.header',visible:true,readonly:true,required:false,disabled:false,auth:'read'},
        {widgetId:'state.body',visible:false,readonly:false,required:false,disabled:false,auth:'edit'}],buttonStatus:[],containerStatus:[]},
      dataContract:{mainData:{id:7,state:'draft'},dataMeta:{},dataSource:{primary:{}}},workflowContract:{statusbar:{field:'state',readonly:false}}};
    const store = ref(null);
    const data = {state:'draft'};
    let layout;
    const baseContext = {v2ContractStore:store,formData:data,recordId:ref(7),renderProfile:ref('edit'),rights:ref({write:true,create:true}),
      onchangeModifiersPatch:ref({}),contractFieldLabel:name=>name,fieldSemanticMeta:()=>({}),markFieldChanged:name=>events.push(name),
      isContractFieldOrderEditable:ref(false),nativeLayoutVisibilityRevision:ref(0),nativeFormDesignFieldKeys:ref([]),nativeFormDesignFieldLabels:ref({}),
      showHud:ref(false),isQuickIntakeMode:ref(false),advancedExpanded:ref(false),coreFieldNames:ref([]),advancedFieldNames:ref([]),
      contractVisibleFields:ref(['state']),fieldOrderDraft:ref([]),fieldOrderPreviewActive:ref(false),fieldGroupBase:ref({}),fieldGroupDraft:{},
      fieldVisibilityDraft:{},lowCodeFormLayoutBase:ref([]),formLayoutColumnsDraft:ref(2),policyContext:ref({}),layoutNodes:()=>[],effectiveGroupVisible:()=>true};
    const statusApp = renderer.createApp({setup(){layout=useRecordFormLayout(baseContext);return()=>h(Component,{...header.value,recordActions:[],canonicalDirectActions:[],
      statusbar:layout.nativeStatusbar.value,statusInteractive:layout.nativeStatusbar.value.visible&&!layout.nativeStatusbar.value.readonly,
      onSetStatus:layout.setStatusbarValue});}});
    statusApp.mount(rootNode);store.value=createContractV2Store(snapshot);await tick();
    equal(layout.nativeStatusbar.value.readonly,true,'selected read occurrence wins over duplicate raw writable field');
    equal(all(n=>n.props['data-workflow-readonly']==='true').length,1,'actual header advertises readonly');
    equal(all(n=>n.props['aria-label']==='编辑业务状态').length,0,'readonly actual header has no editing selector');
    layout.setStatusbarValue('done');equal(data.state,'draft','readonly hook blocks status mutation');
    snapshot.statusContract.widgetStatus[0]={...snapshot.statusContract.widgetStatus[0],auth:'edit',readonly:false};
    store.value=createContractV2Store(structuredClone(snapshot));await tick();
    equal(layout.nativeStatusbar.value.readonly,false,'explicit writable selected occurrence remains writable');
    equal(all(n=>n.props['aria-label']==='编辑业务状态').length,1,'writable actual header exposes editing selector');
    layout.setStatusbarValue('done');equal(data.state,'done','explicit writable hook dispatches state change');
    snapshot.workflowContract.statusbar.readonly=true;store.value=createContractV2Store(structuredClone(snapshot));await tick();
    equal(layout.nativeStatusbar.value.readonly,true,'same-field workflow readonly cannot be weakened');
    snapshot.workflowContract.statusbar.field='other';store.value=createContractV2Store(structuredClone(snapshot));await tick();
    equal(layout.nativeStatusbar.value.readonly,false,'other-field workflow does not control this occurrence');
    snapshot.statusContract.widgetStatus[0].visible=false;store.value=createContractV2Store(structuredClone(snapshot));await tick();
    equal(layout.nativeStatusbar.value.visible,false,'hidden selected occurrence cannot publish header');
    equal(all(n=>n.props['data-professional-workflow-component']==='statusbar').length,0,'hidden header absent in actual component');
    statusApp.unmount();
    delete globalThis.window; delete globalThis.document; delete globalThis.ResizeObserver;
    return checks;
  }
  const selected = ref([{ id: 15, label: '#15' }]);
  const attachmentProps = { field: { name: 'attachment_ids', type: 'many2many', readonly: true, descriptor: { relation: 'ir.attachment' } }, adapter: {
    selectedRelationOptions: () => selected.value, prepareOne2manyColumns: () => [], visibleOne2manyRows: () => [], one2manyColumns: () => [],
  } };
  const props = ref(kind === 'attachment' ? attachmentProps : kind === 'grid' ? { intent: 'example.entry', sceneKey: 'scene.a' } : { block: { key: 'test', title: 'Test' }, zoneKey: 'main', dataset: {} });
  const app = renderer.createApp({ setup: () => () => h(Component, props.value) });
  app.mount(rootNode); await tick();
  if (kind === 'attachment') {
    const attachmentName = () => {
      const search = n => n.props.class === 'attachment-name' ? n : n.children.map(search).find(Boolean);
      return search(rootNode)?.text;
    };
    await waitCalls(1);
    equal(calls[0].request, { intent: 'api.data', params: { op: 'read', model: 'ir.attachment', ids: [15], fields: ['id', 'name'], context: {} } }, 'name uses authorized metadata only');
    // Historical content may be missing: rendering does not request it.
    calls[0].resolve({ records: [{ id: 15, name: 'Historical document' }] }); await tick();
    equal(attachmentName(), 'Historical document');
    equal(calls.length, 1, 'no automatic download');
    selected.value = [{ id: 15, label: 'Declared current label' }]; await tick();
    equal(attachmentName(), 'Declared current label', 'declared label precedes cached metadata');
    selected.value = [{ id: 16, label: 'Already named' }]; await tick();
    equal([attachmentName(), calls.length], ['Already named', 1], 'known name is request-free');
    selected.value = [{ id: 17, label: '#17' }]; await waitCalls(2);
    calls[1].reject(new Error('metadata access denied')); await tick();
    selected.value = [{ id: 17, label: '#17' }]; await tick();
    equal([attachmentName(), calls.length], ['#17', 2], 'denied metadata neither retries nor downloads');
    find('test-button').props.onClick(); await waitCalls(3);
    equal(calls[2].request, { intent: 'file.download', params: { id: 17 } }, 'explicit download keeps original interface');
    calls[2].reject(new Error('historical file missing')); await tick();
    equal(find('test-state')?.props.label, 'historical file missing', 'explicit download error stays visible');
    selected.value = [{ id: 18, label: '#18' }]; await waitCalls(4);
    calls[3].resolve({ records: [{ id: 19, name: 'Wrong record' }] }); await tick();
    equal(attachmentName(), '#18', 'unrelated metadata never supplies the name');
    selected.value = [{ id: 20, label: '#20' }]; await waitCalls(5);
    app.unmount(); calls[4].resolve({ records: [{ id: 20, name: 'Late' }] }); await tick();
    equal(rootNode.children.length, 0, 'unmounted metadata response publishes nothing');

    // Actual one2many renderer: keep the declared-visible blank row and use
    // the declared two-row page, including the shorter final page.
    const rows = [
      { key: 'r1', values: { title: '' } },
      { key: 'r2', values: { title: 'Second' } },
      { key: 'r3', values: { title: 'Third' } },
      { key: 'r4', values: { title: 'Fourth' } },
      { key: 'r5', values: { title: 'Fifth' } },
    ];
    const columns = [{ name: 'title', label: 'Title', ttype: 'char' }];
    const collectionAdapter = {
      prepareOne2manyColumns: () => [], visibleOne2manyRows: () => rows,
      one2manyColumns: () => columns, one2manyCanOpenRow: () => false,
      one2manyColumnDisplayValue: (_column, value) => value ?? '',
      one2manyRowStateLabel: () => '', one2manyRowHints: () => [],
      isOne2manyHydrating: () => false,
    };
    const collectionProps = pageSize => ({ field: { name: 'line_ids', label: 'Lines', type: 'one2many',
      readonly: true, one2manyPageSize: pageSize }, adapter: collectionAdapter });
    const all = (predicate, from = rootNode) => [
      ...(predicate(from) ? [from] : []), ...from.children.flatMap(child => all(predicate, child)),
    ];
    const textOf = n => n.text + n.children.map(textOf).join('');
    const collection = renderer.createApp({ render: () => h(Component, collectionProps(2)) });
    collection.mount(rootNode); await tick();
    const tableRows = () => all(n => Array.isArray(n.props.data))[0].props.data;
    const cards = () => all(n => n.props.class === 'o2m-readonly-row');
    const pageButtons = () => all(n => n.type === 'test-button' && n.props.class === 'o2m-page-action');
    const count = () => textOf(all(n => Object.hasOwn(n.props, 'data-detail-collection-count'))[0]);
    equal(tableRows().map(row => row.id), ['r1', 'r2'], 'blank declared row is retained in the first page');
    equal(cards().length, 2, 'mobile renders the same two-row window');
    equal(count(), '共 5 条', 'total includes all declared rows, including the blank row');
    equal(pageButtons()[0].props.disabled, true, 'first-page previous is disabled');
    pageButtons()[1].props.onClick(); await tick();
    equal(tableRows().map(row => row.id), ['r3', 'r4'], 'actual next action moves the table window');
    equal(cards().length, 2, 'mobile advances with the table');
    equal(count(), '共 5 条', 'paging does not change authoritative total');
    pageButtons()[1].props.onClick(); await tick();
    equal(tableRows().map(row => row.id), ['r5'], 'last page preserves the remaining row');
    equal(cards().length, 1, 'last mobile page has the same remainder');
    equal(pageButtons()[1].props.disabled, true, 'last-page next is disabled');
    pageButtons()[0].props.onClick(); await tick();
    equal(tableRows().map(row => row.id), ['r3', 'r4'], 'actual previous action restores the prior window');
    collection.unmount(); await tick();
    for (const pageSize of [undefined, 0, -1, 1.5, '2', true]) {
      const errors = [];
      const invalid = renderer.createApp({ render: () => h(Component, collectionProps(pageSize)) });
      invalid.config.errorHandler = error => errors.push(error);
      invalid.config.warnHandler = () => {};
      invalid.mount(rootNode); await tick();
      equal(errors.some(error => error.name === 'ContractGapError'), true, 'invalid page declaration reaches actual Vue stop boundary');
      equal(all(n => Array.isArray(n.props.data)).length, 0, 'invalid declaration never publishes a fallback table');
      invalid.unmount(); await tick();
    }
    return checks;
  }

  const state = () => find(kind === 'grid' ? 'section' : 'article')?.props['data-state'];
  const setProps = async patch => { props.value = { ...props.value, ...patch }; await tick(); };
  if (kind !== 'grid') {
    const intent = kind === 'chart' ? 'project.dashboard.chart.fetch' : 'project.boq.import.preview.fetch';
    const declaration = (id, extra = {}) => ({ data: { fetch_intent: intent, fetch_params: kind === 'chart' ? { chart_key: 'declared.chart', project_id: id } : { batch_id: id }, ...extra } });
    const response = label => kind === 'chart'
      ? { schema: 'sc.visualization.chart.v1', chart_key: 'declared.chart', title: label, chart_type: 'bar', series: [{ name: label, points: [{ dimension_value: label, value: 1 }] }] }
      : { batch: { id: 12, name: label, project_id: 3, state: 'done', preview_payload: { schema: 'sc.boq.import.preview.v1', row_count: 1 } }, preview_schema: 'sc.boq.import.preview.v1' };
    const displayed = () => { const model = find('test-panel')?.props.model; return kind === 'chart' ? model?.title : model?.batch?.name; };
    equal([calls.length, state(), Boolean(find('test-panel'))], [0, 'idle', false], 'missing declaration never dispatches');
    await setProps({ dataset: declaration(1) }); await waitCalls(1);
    equal(calls[0].request, { intent, params: kind === 'chart' ? { chart_key: 'declared.chart', project_id: 1 } : { batch_id: 1 } }, 'actual API adapter sends declared request');
    equal(state(), 'loading');
    await setProps({ dataset: declaration(2) }); await waitCalls(2);
    calls[1].resolve(response('new')); await tick();
    equal([state(), displayed()], ['idle', 'new']);
    calls[0].resolve(response('old')); await tick();
    equal([state(), displayed()], ['idle', 'new'], 'old success cannot overwrite new panel');
    await setProps({ dataset: declaration(2, { loading_message: 'Copy changed', empty_message: 'Empty changed' }) });
    equal(calls.length, 2, 'copy-only change does not dispatch');
    if (kind === 'boq') {
      await setProps({ dataset: { data: { fetch_intent: intent, fetch_params: { batch_id: 2, project_id: 3 } } } }); await waitCalls(3);
      equal(calls[2].request.params, { batch_id: 2, project_id: 3 }, 'both declared selectors retained');
      calls[2].resolve(response('both')); await tick(); equal(displayed(), 'both');
    }
    const offset = calls.length;
    await setProps({ dataset: declaration(3) }); await waitCalls(offset + 1);
    await setProps({ dataset: declaration(4) }); await waitCalls(offset + 2);
    calls[offset].reject(new Error('old failure')); await tick();
    equal([state(), Boolean(find('test-panel'))], ['loading', false], 'old catch/finally cannot end current loading');
    calls[offset + 1].resolve(response('latest')); await tick();
    equal([state(), displayed()], ['idle', 'latest']);
    await setProps({ dataset: declaration(4, { fetch_intent: 'api.data' }) });
    equal([calls.length, state(), Boolean(find('test-panel'))], [offset + 2, 'idle', false], 'invalid declaration clears rendered data');
    await setProps({ dataset: declaration(5) }); await waitCalls(offset + 3);
    await setProps({ dataset: declaration(0) });
    equal([state(), Boolean(find('test-panel')), calls.length], ['idle', false, offset + 3], 'zero context invalidates pending request');
    calls[offset + 2].resolve(response('removed')); await tick();
    equal([state(), Boolean(find('test-panel'))], ['idle', false]);
    await setProps({ dataset: declaration(6) }); await waitCalls(offset + 4);
    await setProps({ dataset: declaration(7) }); await waitCalls(offset + 5);
    app.unmount(); await tick();
    calls[offset + 3].resolve(response('unmounted success')); calls[offset + 4].reject(new Error('unmounted failure')); await tick();
    equal([rootNode.children.length, calls.length], [0, offset + 5], 'unmount suppresses both response paths');
  } else {
    const contract = (label, blocks = ['first', 'second']) => ({ title: label, blocks: blocks.map(key => ({ key, title: key, state: 'deferred' })),
      runtime_fetch_hints: { blocks: Object.fromEntries(blocks.map(key => [key, { intent: `custom.${key}.fetch`, params: { block_key: key, nested: { flags: [label] } }, context: { declared: label } }])) } });
    const displayed = () => find('test-page')?.props.contract?.page?.title;
    await waitCalls(1);
    equal(calls[0].request, { intent: 'example.entry', params: { project_id: 99, record_id: 5 }, context: { scene_key: 'scene.a', project_id: 99, record_id: 5 } }, 'entry keeps existing route input');
    await setProps({ sceneKey: 'scene.b' }); await waitCalls(2);
    calls[1].resolve(contract('new entry', [])); await tick(); equal([state(), displayed()], ['idle', 'new entry']);
    calls[0].resolve(contract('old entry')); await tick(); equal([calls.length, displayed()], [2, 'new entry'], 'stale entry never starts hydration');
    await setProps({ sceneKey: 'scene.c' }); await waitCalls(3);
    const oldHydration = contract('old hydration'); delete oldHydration.runtime_fetch_hints.blocks.first.context;
    calls[2].resolve(oldHydration); await waitCalls(4);
    equal(calls[3].request, { intent: 'custom.first.fetch', params: { block_key: 'first', nested: { flags: ['old hydration'] } }, context: { scene_key: 'scene.c' } }, 'deferred nested params retain captured generic scene without route project synthesis');
    await setProps({ intent: 'other.entry', sceneKey: 'scene.d' }); await waitCalls(5);
    calls[3].reject(new Error('old hydration failure')); await tick();
    equal([state(), calls.length], ['loading', 5], 'stale hydrate catch stops old loop without ending new load');
    const currentContract = contract('current', ['first']);
    currentContract.runtime_fetch_hints.blocks.first.context.scene_key = 'declared.override';
    calls[4].resolve(currentContract); await waitCalls(6);
    equal(calls[5].request.context, { scene_key: 'declared.override', declared: 'current' }, 'explicit context overrides captured scene');
    calls[5].resolve({ block: { block_type: 'metric_card', title: 'Materialized', data: { value: 42 } } }); await tick();
    equal([state(), displayed()], ['idle', 'current']);
    equal(find('test-page').props.datasets, { first: { value: 42 } }, 'current hydrated dataset published');
    const staleSuccessStart = calls.length;
    await setProps({ sceneKey: 'scene.old-success' }); await waitCalls(staleSuccessStart + 1);
    calls[staleSuccessStart].resolve(contract('old hydration success')); await waitCalls(staleSuccessStart + 2);
    await setProps({ sceneKey: 'scene.new-success' }); await waitCalls(staleSuccessStart + 3);
    calls[staleSuccessStart + 2].resolve(contract('new retained', [])); await tick();
    calls[staleSuccessStart + 1].resolve({ block: { data: { stale: true } } }); await tick();
    equal([state(), displayed(), calls.length], ['idle', 'new retained', staleSuccessStart + 3], 'old hydration success cannot publish or dispatch its next block');
    const failSoftStart = calls.length;
    await setProps({ sceneKey: 'scene.fail-soft' }); await waitCalls(failSoftStart + 1);
    calls[failSoftStart].resolve(contract('fail soft')); await waitCalls(failSoftStart + 2);
    calls[failSoftStart + 1].reject(new Error('current block failure')); await waitCalls(failSoftStart + 3);
    calls[failSoftStart + 2].resolve({ block: { block_type: 'metric_card', data: { value: 84 } } }); await tick();
    equal([state(), displayed()], ['idle', 'fail soft'], 'current block failure does not fail entire scene');
    equal(find('test-page').props.contract.zones[0].blocks[0].state, 'error', 'failed stub retains error state');
    equal(find('test-page').props.datasets, { second: { value: 84 } }, 'remaining block succeeds after fail-soft error');
    const closingStart = calls.length;
    await setProps({ sceneKey: 'scene.e' }); await waitCalls(closingStart + 1);
    await setProps({ sceneKey: 'scene.f' }); await waitCalls(closingStart + 2);
    calls[closingStart].reject(new Error('old entry failure')); await tick();
    equal([state(), Boolean(find('test-page'))], ['loading', false], 'old entry catch/finally ignored');
    calls[closingStart + 1].resolve(contract('unmount hydration')); await waitCalls(closingStart + 3);
    app.unmount(); await tick();
    calls[closingStart + 2].resolve({ block: { data: { stale: true } } }); await tick();
    equal([rootNode.children.length, calls.length], [0, closingStart + 3], 'dispose prevents next deferred request');
  }
  return checks;
}

const boundary = `import { reactive } from 'vue';
export const calls = [];
export const route = reactive({query:{project_id:'99',record_id:'5'},fullPath:'/s/test?project_id=99&record_id=5'});
export const intentRequestRaw = (...args) => intentRequest(...args);
export function intentRequest(request) { return new Promise((resolve,reject)=>calls.push({request:JSON.parse(JSON.stringify(request)),resolve,reject})); }
`;
const harness = `import assert from 'node:assert/strict';
import {createRenderer,h,ref,nextTick} from 'vue';
import Component from ${JSON.stringify(entry)};
${kind === 'form-header' ? `import {useRecordFormLayout} from './src/pages/contractForm/useRecordFormLayout.ts'; import {createContractV2Store} from './src/app/contracts/v2/store.ts';` : 'const useRecordFormLayout = null, createContractV2Store = null;'}
import {calls,route} from 'test-boundary';
${runMounted.toString()}
export default () => runMounted({useRecordFormLayout,createContractV2Store,Component,kind:${JSON.stringify(kind)},createRenderer,h,ref,nextTick,calls,route,assert});`;
try {
  await build({ stdin: { contents: harness, resolveDir: `${root}/frontend/apps/web`, loader: 'js' }, bundle: true,
    platform: 'node', format: 'esm', outfile: output, logLevel: 'error',
    define: { __VUE_OPTIONS_API__: 'true', __VUE_PROD_DEVTOOLS__: 'false' },
    alias: { vue: `${root}/frontend/apps/web/node_modules/vue/dist/vue.runtime.esm-bundler.js` },
    plugins: [{ name: 'actual-sfc-with-boundaries', setup(builder) {
      builder.onResolve({ filter: /(^|\/)intents$|^test-boundary$/ }, () => ({ path: 'transport', namespace: 'boundary' }));
      builder.onLoad({ filter: /.*/, namespace: 'boundary' }, () => ({ contents: boundary, loader: 'js', resolveDir: `${root}/frontend/apps/web` }));
      builder.onResolve({ filter: /^vue-router$|\/stores\/session$|\/resolvers\/sceneRegistry$|\/app\/pageContract$/ }, args => ({ path: args.path, namespace: 'context' }));
      builder.onLoad({ filter: /.*/, namespace: 'context' }, args => ({ contents:
        args.path === 'vue-router' ? "import {route} from 'test-boundary'; export const useRoute=()=>route; export const useRouter=()=>({push:async()=>{}});"
          : args.path.endsWith('/session') ? 'export const useSessionStore=()=>({menuTree:[]});'
            : args.path.endsWith('/sceneRegistry') ? 'export const getSceneByKey=()=>null;'
              : "export const usePageContract=()=>({sectionEnabled:()=>true,sectionStyle:()=>({}),sectionTagIs:()=>true});",
        loader: 'js', resolveDir: `${root}/frontend/apps/web` }));
      if (kind === 'native-layout') {
        builder.onResolve({ filter: /tdesignPrimitiveBridge$/ }, () => ({ path: 'popup', namespace: 'popup' }));
        builder.onLoad({ filter: /.*/, namespace: 'popup' }, () => ({ contents: `import {h,defineComponent,ref} from 'vue';export const TDesignAlert=defineComponent({setup:(_, {attrs,slots})=>()=>h('test-alert',attrs,slots.default?.())});export const TDesignPopup=defineComponent({emits:['visible-change'],setup:(_, {attrs,slots,emit})=>{const open=ref(false);return()=>h('test-help-popover',{...attrs,onClick:()=>{open.value=!open.value;emit('visible-change',open.value)}},[slots.default?.(),open.value?slots.content?.():null])}});`, loader: 'js', resolveDir: `${root}/frontend/apps/web` }));
      }
      builder.onLoad({ filter: /\.vue$/ }, args => {
        if (args.path !== entry && !(kind === 'native-layout' && /\/(FormSection|ProfessionalBaseFieldControl|ScPopover|NativeWeightedRelationDisplay)\.vue$/.test(args.path))) {
          if (kind === 'native-layout') {
            assert.ok(/\/(design-system|template|professional-fields)\//.test(args.path) || /\/(SceneFieldControl|SceneButton|SceneUiProvider|RestrictedHtmlEditor)\.vue$/.test(args.path), `unexpected layout presentation ${args.path}`);
            if (args.path.endsWith('/ScDescriptions.vue')) return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({setup:(_, {attrs,slots})=>()=>h('test-descriptions',{},(attrs.items || []).map(item=>slots.item?.({item})))});`, loader: 'js', resolveDir: path.dirname(args.path) };
            return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({setup:(_, {attrs,slots})=>()=>h('test-layout-presentation',{...attrs},slots.default?.())});`, loader: 'js', resolveDir: path.dirname(args.path) };
          }
          if (kind === 'form-header') {
            assert.ok(/\/(PageHeader|ScButton|ScIcon|ScDropdown|ScSelect|ScStatusBadge|ScPopover)\.vue$/.test(args.path), `unexpected header presentation ${args.path}`);
            const tag = args.path.endsWith('/ScDropdown.vue') ? 'test-dropdown' : args.path.endsWith('/ScButton.vue') ? 'test-button' : 'test-header-presentation';
            return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({setup:(_, {attrs,slots})=>()=>h('${tag}',{...attrs},Object.values(slots).map(slot=>slot()))});`, loader: 'js', resolveDir: path.dirname(args.path) };
          }
          if (kind === 'attachment') {
            assert.ok(/\/(ScButton|ScDisclosure|ScEmptyState|ScFileField|ScIcon|ScInput|ScInlineState|ScPopover|ScTable|ProfessionalManyToManySelect|One2ManyCellEditor)\.vue$/.test(args.path), `unexpected attachment stub ${args.path}`);
            const tag = args.path.endsWith('/ScButton.vue') ? 'test-button' : args.path.endsWith('/ScInlineState.vue') ? 'test-state' : 'test-presentation';
            return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({props:['label'],setup:(props,{attrs,slots})=>()=>h('${tag}',{...attrs,...props},slots.default?.())});`, loader: 'js', resolveDir: path.dirname(args.path) };
          }

          if (args.path.endsWith('/ScCard.vue')) return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({setup:(_, {slots})=>()=>h('test-card',{},[slots.actions?.(),slots.default?.()])});`, loader: 'js', resolveDir: path.dirname(args.path) };
          assert.ok(/\/(ChartDatasetPanel|BoqImportPreviewPanel|PageRenderer|StatusPanel)\.vue$/.test(args.path), `unexpected stub ${args.path}`);
          const name = args.path.endsWith('/PageRenderer.vue') ? 'test-page' : args.path.endsWith('/StatusPanel.vue') ? 'test-status' : 'test-panel';
          return { contents: `import {h,defineComponent} from 'vue';export default defineComponent({props:['model','contract','datasets','message','title','variant'],setup:props=>()=>h('${name}',{...props})});`, loader: 'js', resolveDir: path.dirname(args.path) };
        }
        const { descriptor } = parse(fs.readFileSync(args.path, 'utf8'), { filename: args.path });
        const compiled = compileScript(descriptor, { id: args.path, inlineTemplate: true });
        return { contents: compiled.content, loader: 'ts', resolveDir: path.dirname(args.path) };
      });
    } }],
  });
  const run = (await import(pathToFileURL(output).href)).default;
  const checks = await run();
  console.log(`[readonly-block-component] PASS kind=${kind} checks=${checks} actual_sfc=true vue_mount=true transport=mocked presentation=stubbed card_driver=stubbed${kind === 'grid' ? ' grid_child_renderer=stubbed' : ''}`);
} finally { fs.rmSync(temporary, { recursive: true, force: true }); }
