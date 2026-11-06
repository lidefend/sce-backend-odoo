/**
 * The page-header submission-readiness notice must survive the formal V2
 * decode, and the native body occurrence of ``submission_readiness_display``
 * must be suppressed on the layout node without deleting it from ``children``
 * (so parent widget ownership bindings stay intact).
 *
 * The baseline decoder rejects undeclared top-level keys, so decoding a
 * complete snapshot that carries ``noticeContract`` proves the declaration has
 * actually entered the consumption chain. A missing ``visible`` or an unknown
 * notice key must fail closed.
 */
import assert from 'node:assert/strict';
import { ContractV2DecodeError, decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

const READINESS_FIELD_ID = 'field.submission_readiness_display.occ.1';
const READINESS_GROUP_ID = 'group.sc_project_submission_readiness';
const LOCATOR = '/form[1]/sheet[1]/group[1]/field[1]';

function readinessFieldNode() {
  return {
    containerId: READINESS_FIELD_ID,
    containerType: 'field',
    type: 'field',
    name: 'submission_readiness_display',
    widgetId: READINESS_FIELD_ID,
    fieldCode: 'submission_readiness_display',
    label: '办理前检查',
    title: '办理前检查',
    span: 12,
    nativeLocator: LOCATOR,
    occurrenceIndex: 1,
    sourcePosition: 1,
    // The assembler hands this content to noticeContract; the body occurrence
    // is suppressed on the layout node only, not removed from children.
    visible: false,
    fieldInfo: { name: 'submission_readiness_display', type: 'text', readonly: true, required: false },
    children: [],
    widgetList: [{
      widgetId: READINESS_FIELD_ID,
      widgetType: 'select',
      fieldCode: 'submission_readiness_display',
      label: '办理前检查',
      span: 12,
      componentKey: 'sc.select.remote',
      capabilities: [],
      componentConfig: {
        fieldType: 'text', native_locator: LOCATOR, occurrence_index: 1,
        source_position: 1, readonly: true, required: false,
      },
      fieldDescriptor: { name: 'submission_readiness_display', type: 'text' },
      nativeLocator: LOCATOR,
      occurrenceIndex: 1,
      sourcePosition: 1,
      ownerContainerId: READINESS_FIELD_ID,
    }],
  };
}

function buildSnapshot() {
  return {
    pageInfo: {
      pageId: 'page.project.project.form', sceneKey: 'project.project.form', pageName: 'Project',
      model: 'project.project', viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.2.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.project.project.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 }, componentRegistry: {},
      containerTree: [{
        containerId: READINESS_GROUP_ID,
        containerType: 'group',
        type: 'group',
        name: 'sc_project_submission_readiness',
        title: '办理前检查',
        string: '办理前检查',
        label: '办理前检查',
        span: 24,
        columns: 1,
        // Single-field readiness group: its only content moved to the notice,
        // so the group caption must not survive as a stray heading either.
        visible: false,
        children: [readinessFieldNode()],
        widgetList: [],
      }],
    },
    actionContract: { actionRuleList: [], dependencyGraph: {} },
    statusContract: {
      globalStatus: {
        pageVisible: true, pageAuth: 'edit', reasonCode: '',
        modelRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        recordRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        viewCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        entryCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRecordCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRenderProfile: 'edit',
      },
      widgetStatus: [
        { widgetId: READINESS_FIELD_ID, visible: true, readonly: true, required: false, disabled: false, auth: 'read' },
      ],
      buttonStatus: [],
      containerStatus: [
        { containerId: READINESS_GROUP_ID, visible: true, disabled: false },
      ],
      selectorStatus: [],
    },
    dataContract: {
      mainData: { lifecycle_state: 'draft', sc_approval_state: 'draft' },
      tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {},
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
    noticeContract: {
      submissionReadiness: {
        visible: true,
        status: 'blocked',
        statusLabel: '待处理',
        state: 'info',
        message: '请先补齐项目资料。',
        nextStep: '处理阻塞原因',
        nextStepAction: 'review_record',
        reasonCode: 'SUBMISSION_PREREQUISITES_BLOCKED',
        sourceAuthority: 'smart_construction_core.services.baseline_readiness.build_readiness',
      },
    },
  };
}

const decoded = decodeContractV2Snapshot(buildSnapshot());

assert.equal(decoded.noticeContract?.submissionReadiness?.status, 'blocked');
assert.equal(decoded.noticeContract?.submissionReadiness?.visible, true);
assert.equal(decoded.noticeContract?.submissionReadiness?.statusLabel, '待处理');
assert.equal(decoded.noticeContract?.submissionReadiness?.state, 'info');
assert.equal(decoded.noticeContract?.submissionReadiness?.nextStep, '处理阻塞原因');

const group = decoded.layoutContract.containerTree[0];
assert.equal(group.containerId, READINESS_GROUP_ID);
assert.equal(group.visible, false, 'single-field readiness group must stay suppressed');
const field = group.children[0];
assert.equal(field.name, 'submission_readiness_display');
assert.equal(field.visible, false, 'native body occurrence must stay suppressed after decode');
assert.ok(field.widgetList.length > 0, 'field widget ownership must be preserved, not orphaned');

// Fail-closed: the notice must declare its visibility.
{
  const broken = buildSnapshot() as Record<string, unknown>;
  const notice = broken.noticeContract as Record<string, unknown>;
  const readiness = notice.submissionReadiness as Record<string, unknown>;
  delete readiness.visible;
  assert.throws(
    () => decodeContractV2Snapshot(broken),
    (error: unknown) => error instanceof ContractV2DecodeError
      && error.issues.some((issue) => issue.path === '$.noticeContract.submissionReadiness.visible'),
  );
}

// Fail-closed: unknown notice keys are not silently accepted.
{
  const broken = buildSnapshot() as Record<string, unknown>;
  const notice = broken.noticeContract as Record<string, unknown>;
  const readiness = notice.submissionReadiness as Record<string, unknown>;
  readiness.bogus = 'undeclared';
  assert.throws(
    () => decodeContractV2Snapshot(broken),
    (error: unknown) => error instanceof ContractV2DecodeError
      && error.issues.some((issue) => issue.path === '$.noticeContract.submissionReadiness.bogus'),
  );
}
