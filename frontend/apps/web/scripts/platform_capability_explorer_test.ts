import assert from 'node:assert/strict';
import { ApiError } from '../src/api/client';
import {
  decodeCapabilityExplorerDetailResponse,
  decodeCapabilityExplorerDiagnosisResponse,
  decodeCapabilityExplorerListResponse,
  decodeCapabilityExplorerRow,
} from '../src/api/platformCapabilityExplorer';
import {
  blockerLabel,
  buildListFilters,
  businessDomainPresentation,
  capabilityEntryKey,
  isCatalogStaleError,
  releaseStatePresentation,
  sceneUsagePresentation,
  technicalEligibilityPresentation,
} from '../src/app/platformCapabilityExplorerPresentation';
import { createCapabilityExplorerRequestGate } from '../src/app/platformCapabilityExplorerRequestGate';
import { isContractGapError } from '../src/app/contract/contractGap';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const meta = {
  schema: 'platform.capability.explorer.list.v1',
  generated_at: '2026-11-15T00:00:00Z',
  runtime_database: 'sc_dev_demo',
  source_revision: 'a'.repeat(40),
  catalog_token: `sha256:${'b'.repeat(64)}`,
  total: 3,
  filtered_total: 1,
  offset: 0,
  limit: 25,
  next_offset: null,
  has_more: false,
  freshness: 'request_time_projection',
  persistence: 'none',
  language: { code: 'zh_CN' },
  diagnostics: {},
};
const row = {
  entry_ref: {
    menu_xmlid: 'smart_construction_core.menu_project_ledger',
    action_xmlid: 'smart_construction_core.action_project_ledger',
  },
  label: '项目台账',
  origin: { module: 'smart_construction_core', model: 'project.project' },
  center: {
    key: 'smart_construction_core.menu_sc_project_center',
    label: '项目中心',
    sequence: 10,
    source: 'ir.ui.menu',
  },
  business_domain: {
    key: 'project.management',
    label: '项目管理',
    confidence: 'authoritative_scene_binding',
    reason_code: '',
  },
  scene_usage: { bound: true, count: 1 },
  release_state: 'unknown',
  draft_eligibility: { selectable: true, blockers: [] },
  product_qualification: { preview: 'not_verified', standard: 'not_verified' },
};
const listResponse = {
  meta,
  facets: {
    centers: [{ key: 'smart_construction_core.menu_sc_project_center', label: '项目中心', count: 3 }],
    business_domains: [{ key: 'project.management', label: '项目管理', count: 1 }],
    scene_status: { bound: 1, unbound: 2 },
    release_states: { unknown: 3 },
    classification_confidence: {
      authoritative_scene_binding: 1,
      center_only: 1,
      unclassified: 1,
    },
  },
  rows: [row],
};

const decodedList = decodeCapabilityExplorerListResponse(listResponse);
check(decodedList.meta.total, 3, 'list total consumed');
check(decodedList.rows[0]?.label, '项目台账', 'list row consumed');
check(capabilityEntryKey(decodedList.rows[0]!), 'smart_construction_core.menu_project_ledger::smart_construction_core.action_project_ledger', 'stable entry key');
const requestGate = createCapabilityExplorerRequestGate();
const firstRequest = requestGate.begin();
const secondRequest = requestGate.begin();
check(requestGate.isCurrent(firstRequest), false, 'older detail response is stale after a newer request');
check(requestGate.isCurrent(secondRequest), true, 'latest detail response remains current');
requestGate.invalidate();
check(requestGate.isCurrent(secondRequest), false, 'drawer close invalidates an in-flight detail response');
assert.throws(
  () => decodeCapabilityExplorerListResponse({ ...listResponse, meta: { ...meta, catalog_token: '' } }),
  (error) => isContractGapError(error),
  'missing catalog token must stop',
);
cases += 1;
check(
  decodeCapabilityExplorerRow({ ...row, center: {} }).center.key,
  '',
  'explicit empty center remains unclassified',
);

const centerOnly = {
  ...decodedList.rows[0]!,
  business_domain: {
    key: null,
    label: null,
    confidence: 'center_only' as const,
    reason_code: 'NO_SCENE_BINDING',
  },
};
check(businessDomainPresentation(centerOnly).label, '业务领域未确认', 'center-only label');
check(sceneUsagePresentation(centerOnly).label, '已场景化 · 1', 'scene usage preserved');
check(technicalEligibilityPresentation(centerOnly).label, '技术可选', 'technical eligibility preserved');
check(releaseStatePresentation('unknown').label, '发布状态未知', 'unknown release preserved');
check(blockerLabel(['ACTION_NOT_FOUND']), 'ACTION_NOT_FOUND', 'blocker reason preserved');
check(
  buildListFilters({
    centerKey: 'center.a',
    confidence: 'center_only',
    sceneStatus: 'unbound',
    releaseState: 'unknown',
    draftSelectable: 'true',
  }),
  {
    center_keys: ['center.a'],
    classification_confidence: ['center_only'],
    scene_status: ['unbound'],
    release_states: ['unknown'],
    draft_selectable: true,
  },
  'filters sent in backend contract shape',
);
check(
  isCatalogStaleError(new ApiError('stale', 409, 'trace', { reasonCode: 'CATALOG_STALE' })),
  true,
  'catalog stale error recognized',
);

const detailResponse = {
  meta: { ...meta, schema: 'platform.capability.explorer.detail.v1' },
  entry: {
    ...row,
    native_facts: {
      menu: {
        xmlid: row.entry_ref.menu_xmlid,
        label: row.label,
        sequence: 20,
        path: ['智慧施工管理平台', '项目中心', '项目台账'],
        group_xmlids: [],
      },
      action: {
        xmlid: row.entry_ref.action_xmlid,
        type: 'ir.actions.act_window',
        view_modes: ['tree', 'form'],
        group_xmlids: [],
      },
      module: {
        name: 'smart_construction_core',
        state: 'installed',
        version: '17.0.0.182',
        dependencies: ['project', 'smart_core'],
      },
      model: { name: 'project.project', description: '项目', exists: true, field_count: 235 },
      views: { count: 42, sha256: 'view' },
      acl: { row_count: 10, group_xmlids: ['smart_construction_core.group_sc_project_read'], sha256: 'acl' },
      record_rules: { count: 10, group_xmlids: ['smart_construction_core.group_sc_project_read'], sha256: 'rule' },
    },
    scenario_usage: {
      bound: true,
      ambiguous: false,
      scenarios: [{
        scenario_key: 'project.management',
        scenario_name: '项目管理',
        scenario_active: true,
        scenario_sequence: 10,
        sequence: 10,
        intent: 'handle',
      }],
    },
    release: {
      state: 'unknown',
      entry_published: false,
      center: null,
      blockers: [],
      ambiguous_center: false,
      snapshots: [],
    },
    scene_assignment: { assignable: true, blockers: [] },
    qualification: { preview: 'not_verified', standard: 'not_verified' },
    diagnostics: {
      native_valid: true,
      native_blockers: [],
      release_blockers: [],
      blockers: [],
      draft_selectable: true,
      scene_assignable: true,
      entry_published: false,
      preview_qualified: 'not_verified',
      standard_qualified: 'not_verified',
      classification_reason: '',
    },
    classification: {
      source: 'sc.product.scenario.entry',
      candidates: [{ key: 'project.management', label: '项目管理' }],
      reason_code: '',
      center_source: 'ir.ui.menu',
      native_center: { key: 'center', label: '项目中心' },
      release_center: null,
    },
  },
};
const decodedDetail = decodeCapabilityExplorerDetailResponse(detailResponse);
check(decodedDetail.entry.native_facts.views.count, 42, 'detail native facts consumed');
check(decodedDetail.entry.scenario_usage.scenarios[0]?.scenario_key, 'project.management', 'scenario usage consumed');
const baseMeta = Object.fromEntries(Object.entries(meta).filter(([key]) => (
  !['filtered_total', 'offset', 'limit', 'next_offset', 'has_more', 'sort'].includes(key)
)));
check(
  decodeCapabilityExplorerDetailResponse({
    ...detailResponse,
    meta: { ...baseMeta, schema: 'platform.capability.explorer.detail.v1' },
  }).meta.catalog_token,
  meta.catalog_token,
  'detail accepts base meta without list pagination fields',
);

const diagnosis = decodeCapabilityExplorerDiagnosisResponse({
  meta: { ...baseMeta, schema: 'platform.capability.explorer.diagnose.v1' },
  entry_ref: row.entry_ref,
  native_valid: true,
  draft_selectable: true,
  scene_assignable: true,
  entry_published: false,
  preview_qualified: 'not_verified',
  standard_qualified: 'not_verified',
  blockers: [],
  classification_reason: '',
  sections: {},
});
check(diagnosis.draft_selectable, true, 'diagnosis flags consumed');
check(diagnosis.standard_qualified, 'not_verified', 'qualification not inferred from technical selectability');
assert.throws(
  () => decodeCapabilityExplorerListResponse({ ...listResponse, meta: baseMeta }),
  (error) => isContractGapError(error),
  'list still requires pagination metadata',
);
cases += 1;

console.log(`[platform_capability_explorer_test] PASS cases=${cases}`);
