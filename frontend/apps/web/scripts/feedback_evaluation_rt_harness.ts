/* eslint-disable @typescript-eslint/no-explicit-any */
import { effectScope, reactive, ref } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import { useDraftFeedbackEvaluation } from '../src/pages/contractForm/useDraftFeedbackEvaluation';
import { useSessionStore } from '../src/stores/session';

const DEFAULT_ADVICE = '建议补充办理日期；建议补充办理说明';

function buildSnapshot(binding: any, options: Record<string, any> = {}) {
  const sourceField = String(options.sourceField || 'note');
  const sourceType = String(options.sourceType || 'text');
  const conditionField = String(options.conditionField || sourceField);
  const sourceWidget = sourceType === 'text' ? 'sc.input.textarea' : 'sc.display.text';
  const source = {
    containerId: binding.source_container_id,
    containerType: 'field',
    type: 'field',
    name: sourceField,
    title: '',
    span: 24,
    nativeLocator: binding.native_locator,
    occurrenceIndex: binding.occurrence_index,
    sourceAuthority: { kind: 'native_view', model: binding.model, view_id: binding.view_id },
    fieldInfo: { type: sourceType, ttype: sourceType },
    children: [],
    widgetList: [{
      widgetId: binding.source_container_id,
      widgetType: sourceType === 'text' ? 'textarea' : 'display_text',
      fieldCode: sourceField,
      label: '办理说明',
      span: 24,
      componentKey: sourceWidget,
      capabilities: [],
      componentConfig: { fieldType: sourceType },
      ownerContainerId: binding.source_container_id,
    }],
  };
  const host = {
    containerId: binding.container_id,
    containerType: 'div',
    type: 'div',
    title: '',
    span: 24,
    columns: 1,
    visible: false,
    componentKey: 'sc.feedback.message',
    componentConfig: {
      purpose: 'advisory',
      contentRef: { containerId: binding.source_container_id },
      evaluation: {
        capability: 'form.feedback.draft.v1',
        visibilityOwner: 'feedback_evaluation',
      },
    },
    modifiers: {
      invisible: { kind: 'not', expr: { kind: 'field_truthy', field: conditionField } },
    },
    children: [source],
    widgetList: [],
  };
  return {
    pageInfo: {
      pageId: 'page.r6_3.rt', sceneKey: 'r6_3.rt', pageName: 'R6.3 RT',
      model: binding.model, viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.2.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.r6_3.rt', layoutType: 'form', adaptMode: 'pc', layoutHints: {},
      componentRegistry: {
        'sc.feedback.message': { version: '1.0.0' },
        [sourceWidget]: { version: '1.0' },
      },
      containerTree: [{
        containerId: 'root', containerType: 'group', type: 'group', title: '', span: 24, columns: 1,
        children: [host], widgetList: [],
      }],
    },
    actionContract: {
      actionRuleList: [], dependencyGraph: {}, deletePolicy: {}, surfacePolicies: {},
    },
    statusContract: {
      globalStatus: {
        pageVisible: true, pageAuth: 'edit',
        modelRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        recordRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        viewCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        entryCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRecordCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRenderProfile: 'edit',
      },
      widgetStatus: [{
        widgetId: binding.source_container_id,
        visible: true,
        readonly: false,
        required: false,
        disabled: false,
      }],
      buttonStatus: [],
      containerStatus: [{ containerId: binding.container_id, visible: false }],
      selectorStatus: [],
    },
    dataContract: {
      mainData: {}, tableRows: {}, relationRows: {}, dictData: {}, pagination: {},
      dataSource: {}, dataMeta: {},
    },
    runtimeContract: {
      patchStrategy: 'full', cachePolicy: 'snapshot', optimistic: false, lazyContainer: [],
      virtualization: {}, retryPolicy: {},
    },
    meta: {
      etag: 'rt-etag', snapshotId: 'rt-snapshot', traceId: 'rt-trace', requestId: 'rt-request',
      sourceType: 'ui.contract',
      lifecycle: {
        lifecycleVersion: '1', stage: 'sealed',
        definition: {
          schemaId: 'v2', schemaVersion: '2', schemaSha256: 'schema',
          contractVersion: '2.2.0', normativeStatus: 'active',
        },
        generation: { generator: 'rt', generatorVersion: '1', sourceType: 'test', sourceSha256: 'source' },
        runtime: { requestId: 'rt-request', traceId: 'rt-trace', clientType: 'web_pc', traceSource: 'test' },
        integrity: { algorithm: 'sha256', contractSha256: 'r6-3-rt-contract' },
        authority: {},
      },
    },
  } as any;
}

function feedbackNode(nodes: any[]): any {
  for (const node of nodes) {
    if (node.nativePresentation?.nodeComponent?.kind === 'feedback') return node;
    const found = feedbackNode(node.children || []);
    if (found) return found;
  }
  return null;
}

let scope: ReturnType<typeof effectScope> | null = null;
let runtime: any = null;
let storeRef: any = null;
let formData: Record<string, unknown> = {};
let presence: any = null;
let recordId: any = null;
let hostId = '';
let initialData: Record<string, unknown> = { business_date: false, note: '' };
let presenceKeys = ['business_date', 'note'];
let advice = DEFAULT_ADVICE;

function render() {
  if (!runtime || !storeRef) return null;
  const model = presentContractV2Form(storeRef.value, 'edit', formData, {
    recordPersisted: false,
    feedbackEvaluations: runtime.states.value,
  });
  const node = feedbackNode(model.zones.primary);
  return {
    content: node?.nativePresentation?.nodeComponent?.content || '',
    visible: Boolean(node?.visible),
    role: node?.nativePresentation?.nodeComponent?.role || '',
    state: runtime.states.value.get(hostId) || null,
  };
}

function start(binding: any, options: Record<string, any> = {}) {
  setActivePinia(createPinia());
  const session = useSessionStore();
  session.restore();
  session.initStatus = 'ready';
  session.isReady = true;
  runtime = null;
  storeRef = null;
  hostId = binding.container_id;
  initialData = { business_date: false, note: '', ...(options.initialData || {}) };
  presenceKeys = Array.isArray(options.presence) ? [...options.presence] : ['business_date', 'note'];
  advice = String(options.advice || DEFAULT_ADVICE);
  formData = reactive({ ...initialData });
  presence = ref(new Set<string>(presenceKeys));
  recordId = ref<number | null>(null);
  const snapshot = buildSnapshot(binding, options);
  storeRef = ref(createContractV2Store(snapshot));
  scope = effectScope();
  runtime = scope.run(() => useDraftFeedbackEvaluation({
    store: storeRef,
    model: () => binding.model,
    recordId: () => recordId.value,
    formData,
    presence,
    contextIdentity: () => [
      String(session.user?.id || 0),
      String(session.recordContext?.company_id || session.recordContext?.selected?.company_id || 0),
    ].join('|'),
    context: () => ({
      allowed_company_ids: session.recordContext?.company_id
        ? [session.recordContext.company_id]
        : undefined,
    }),
    active: () => true,
  }));
  return render();
}

function setDraft(values: Record<string, unknown>) {
  const changed: string[] = [];
  for (const [name, value] of Object.entries(values)) {
    if (formData[name] !== value) changed.push(name);
    formData[name] = value;
  }
  presence.value = new Set(presenceKeys);
  changed.forEach((name) => runtime?.onDraftChanged(name));
  return render();
}

function changeRecord(next: number | null) {
  Object.keys(formData).forEach((key) => delete formData[key]);
  Object.assign(formData, initialData);
  presence.value = new Set();
  recordId.value = next;
  return render();
}

function clearPresence() {
  presence.value = new Set();
}

(window as any).__SC_FEEDBACK_RT__ = {
  start,
  setDraft,
  changeRecord,
  clearPresence,
  render,
  beginSave: () => runtime?.invalidate(),
  finishSave: () => runtime?.reset(),
  state: () => render(),
  advice: () => advice,
};
