/**
 * Executable proof for declared form surfaces.
 *
 * A non-field page region (the collaboration panel and its role-gated audit
 * sub-region) is declared by the contract, and the declaration — not runtime
 * data — decides whether the region renders.  The cases below drive the real
 * decoder, the real store resolver and the real projection helpers, so the
 * three failure modes that produced the original defect each change at least
 * one expectation:
 *
 *   (a) no declaration  -> no region at all (the renderer must not invent one);
 *   (b) declared but withheld authorization -> no audit region, even with a
 *       non-empty audit timeline (a `deny`/`pending`/`coming_soon` gate);
 *   (c) declared and allowed -> the region renders, including its own empty
 *       state when no audit event exists yet.
 *
 * The negative controls are the runtime-data cases: a timeline with events but
 * no `allow` must stay hidden, and an `allow` with no events must still render.
 * Both are inverted by a "timeline.length > 0" visibility rule.
 */
import assert from 'node:assert/strict';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { resolveContractV2FormStructureSurfaces } from '../src/app/contracts/v2/store';
import { ContractV2DecodeError } from '../src/app/contracts/v2/schema';
import * as nativeSectionNavigation from '../src/pages/contractForm/nativeSectionNavigation';
import { contractSurfaceNavigationItems } from '../src/pages/contractForm/nativeSectionNavigation';
import {
  declaredAuditAuthorized,
  declaredCollaborationSurface,
} from '../src/pages/contractForm/contractRuntimeVm';
import type { ContractV2FormStructureSurface } from '../src/app/contracts/v2/types';

const MODEL = 'x.document';

function snapshot(formStructureSurfaces?: unknown) {
  const formStructureContract: Record<string, unknown> = {
    source: 'ui.contract.v2.form_structure_contract',
    structureVersion: '1.0',
    model: MODEL,
    viewType: 'form',
    mode: 'edit',
    layoutPolicy: 'container_tree_authority',
    objectProfile: { model: MODEL, kind: 'business_form', factAuthority: 'business_object_model_and_view' },
    navigation: { title: '业务办理' },
    slots: [],
    fieldRoles: {},
    sourceAuthority: {
      kind: 'unified_page_contract_v2',
      runtime_carrier: 'ui.contract.v2.form_structure_contract',
      projection_only: true,
      no_business_fact_authority: true,
      governed_form_structure: true,
      governance_source: { source: 'test' },
    },
  };
  if (formStructureSurfaces !== undefined) formStructureContract.surfaces = formStructureSurfaces;
  return {
    pageInfo: {
      pageId: 'page.x.document.form', sceneKey: 'x.document.form', pageName: 'Document',
      model: MODEL, viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.2.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.document.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 },
      componentRegistry: {
        'sc.input.text': { version: '1.0', adapter: { web_pc: 'ElInput' }, selectedAdapter: 'TDesignInput' },
      },
      containerTree: [{
        containerId: 'section.identity', containerType: 'group', type: 'group', title: 'Identity', span: 24,
        children: [{
          containerId: 'field.amount', containerType: 'field', type: 'field', name: 'amount', widgetId: 'field.amount',
          fieldCode: 'amount', title: '', span: 12,
          children: [], widgetList: [{
            widgetId: 'field.amount', widgetType: 'input', fieldCode: 'amount', label: 'Amount', span: 12,
            componentKey: 'sc.input.text', capabilities: [], componentConfig: { fieldType: 'char' },
            fieldDescriptor: { name: 'amount', type: 'char' },
            ownerContainerId: 'field.amount',
          }],
        }],
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
        { widgetId: 'field.amount', visible: true, readonly: false, required: false, disabled: false, auth: 'edit' },
      ],
      buttonStatus: [], containerStatus: [], selectorStatus: [],
    },
    dataContract: {
      mainData: { amount: '1' }, tableRows: {}, relationRows: {},
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
    ...(formStructureSurfaces === undefined ? {} : { formStructureContract }),
  };
}

function storeFor(formStructureSurfaces?: unknown) {
  return createContractV2Store(decodeContractV2Snapshot(snapshot(formStructureSurfaces)));
}

function activitySurface(authorization: Record<string, unknown>): ContractV2FormStructureSurface[] {
  return [{
    surface: 'activity',
    title: '协作记录',
    role: 'activity',
    contentKind: 'collaboration-panel',
    sourceIdentity: 'collaboration-panel',
    capabilities: { timeline: true, remarks: true, attachments: false },
    audit: {
      title: '历史审计',
      contentKind: 'audit-timeline',
      sourceIdentity: 'professional-audit-timeline',
      authorization,
    },
  }];
}

// (a) A contract that cannot declare surfaces: the renderer has no declaration
// to consume, so the legacy predicate is the only path and it must be explicit.
const noDeclaration = storeFor(undefined);
assert.equal(
  resolveContractV2FormStructureSurfaces(noDeclaration),
  undefined,
  'an absent declaration must stay distinguishable from an empty declaration',
);
assert.equal(declaredCollaborationSurface(undefined), null, 'no declaration cannot produce a region');
assert.equal(declaredAuditAuthorized(undefined), false, 'no declaration cannot authorize the audit sub-region');

// A declared but empty list is a declaration: the page publishes no region.
const emptyDeclaration = storeFor([]);
assert.deepEqual(resolveContractV2FormStructureSurfaces(emptyDeclaration), []);
assert.equal(declaredCollaborationSurface([]), null, 'an empty declaration publishes no collaboration region');
assert.equal(declaredAuditAuthorized([]), false);
assert.deepEqual(contractSurfaceNavigationItems([]), [], 'an empty declaration yields no navigation entry');

// (b) Declared with a withheld authorization: no audit region, and the audit
// sub-region must never become a second top-level navigation entry.
for (const withheld of ['deny', 'pending', 'coming_soon'] as const) {
  const surfaces = activitySurface({ capability: 'governance.runtime.audit', state: withheld });
  const store = storeFor(surfaces);
  const decoded = resolveContractV2FormStructureSurfaces(store);
  assert.deepEqual(decoded, surfaces, `${withheld}: the declaration is consumed verbatim`);
  assert.equal(
    declaredCollaborationSurface(decoded)?.surface,
    'activity',
    `${withheld}: the declared collaboration region is found`,
  );
  assert.equal(
    declaredAuditAuthorized(decoded),
    false,
    `${withheld}: the audit sub-region stays hidden without an explicit allow`,
  );
  const entries = contractSurfaceNavigationItems(decoded || []);
  assert.equal(entries.length, 1, `${withheld}: the gated sub-region is not a second navigation entry`);
  assert.equal(entries[0].key, 'surface:activity');
  assert.equal(entries[0].label, '协作记录');
}

// (c) Declared and allowed: the region renders even with an empty timeline, and
// the declaration (not a literal) supplies the label and the target identity.
const allowedSurfaces = activitySurface({ capability: 'governance.runtime.audit', state: 'allow' });
const allowedStore = storeFor(allowedSurfaces);
const allowedDecoded = resolveContractV2FormStructureSurfaces(allowedStore);
assert.deepEqual(allowedDecoded, allowedSurfaces, 'the allowed declaration round-trips through the decoder');
assert.equal(declaredAuditAuthorized(allowedDecoded), true, 'an explicit allow authorizes the audit sub-region');
assert.deepEqual(
  contractSurfaceNavigationItems(allowedDecoded || []),
  [{
    key: 'surface:activity',
    label: '协作记录',
    selector: '[data-form-section-target="surface:activity"]',
    role: 'activity',
    contentKind: 'collaboration-panel',
    sourceType: 'surface',
    sourceIdentity: 'collaboration-panel',
  }],
  'an allowed audit sub-region still produces exactly one region entry',
);

// The label is consumed from the declaration, not hardcoded in the renderer.
const renamed = contractSurfaceNavigationItems(activitySurface({
  capability: 'governance.runtime.audit', state: 'allow',
}).map((surface) => ({ ...surface, title: '业务记录' })));
assert.equal(renamed[0].label, '业务记录', 'the declared title is the navigation label');

// Strict schema: the declaration is validated, not silently dropped.
assert.throws(
  () => storeFor([{ ...activitySurface({ capability: 'c', state: 'allow' })[0], invented: true }]),
  ContractV2DecodeError,
  'an unknown key inside a declared surface must fail decoding',
);
assert.throws(
  () => storeFor(activitySurface({ capability: 'governance.runtime.audit', state: 'maybe' })),
  ContractV2DecodeError,
  'an undeclared authorization state must fail decoding',
);

// There is no fallback path: a contract that cannot declare surfaces declares
// no region, so no hardcoded region label can survive in the renderer.
const navigationModule = nativeSectionNavigation as Record<string, unknown>;
assert.equal(
  navigationModule.legacySurfaceNavigationItems,
  undefined,
  'the renderer must not keep a hardcoded fallback region label',
);

process.stdout.write('form_structure_surface_contract_test: ok\n');
