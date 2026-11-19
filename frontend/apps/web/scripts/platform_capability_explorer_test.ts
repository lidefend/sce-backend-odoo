import assert from 'node:assert/strict';
import { ApiError } from '../src/api/client';
import {
  buildCapabilityCatalogEntryAddParams,
  decodeCapabilityCatalogEntryWriteResult,
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
  centerSourcePresentation,
  isCatalogAdmissionOperationCurrent,
  isCatalogStaleError,
  releaseStatePresentation,
  sceneUsagePresentation,
  technicalEligibilityPresentation,
} from '../src/app/platformCapabilityExplorerPresentation';
import { createCapabilityExplorerRequestGate } from '../src/app/platformCapabilityExplorerRequestGate';
import { isContractGapError } from '../src/app/contract/contractGap';
import { buildBusinessScenarioMaintenanceTarget } from '../src/app/businessScenarioNavigation';
import { contextReturnHref, pickContractNavQuery } from '../src/app/navigationContext';
import {
  buildConfiguredOperatorParams,
  decodeConfiguredActionResult,
  decodeProductCenterWriteEnvelope,
  decodeReleaseOperatorSurface,
  type OperatorAction,
} from '../src/app/releaseOperatorActionContract';

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
  catalog_scope: {
    mode: 'platform',
    label: '平台原生目录',
    identity_scope: 'current_instance_installed_native_entries',
    product_key: '',
    product_label: '',
    products: [{
      product_key: 'construction.standard',
      label: '施工管理标准版',
      base_product_key: 'construction',
      edition_key: 'standard',
      groups: [{
        group_key: 'construction.center.project',
        label: '项目中心',
        sequence: 20,
        entry_count: 1,
      }],
    }],
    groups: [{
      group_key: 'construction.center.project',
      label: '项目中心',
      sequence: 20,
      entry_count: 1,
    }],
    platform_native_entry_count: 3,
    visible_entry_count: 3,
    management_actions: {
      add_to_product_draft: {
        intent: 'release.operator.add_catalog_entry',
        enabled: true,
        reason_code: 'OK',
        accepted_fields: ['product_key', 'menu_id', 'center_key', 'release_state'],
        default_release_state: 'preview',
        release_state_options: [
          { value: 'preview', label: '预览（推荐）' },
          { value: 'released', label: '正式' },
        ],
        readback_fields: ['action', 'surface', 'readback'],
      },
      open_product_draft: {
        route: '/admin/release-operator',
        product_key: 'construction.standard',
      },
    },
    source_authority: { kind: 'platform_catalog_scope_resolution' },
  },
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
  catalog_admission: {
    enabled: true,
    reason_code: 'CATALOG_ENTRY_ADMISSIBLE',
    blockers: [],
  },
  product_qualification: {
    preview: 'not_verified',
    standard: 'qualified',
    reason_code: 'PRODUCT_QUALIFIED',
    evidence: [{
      product_key: 'construction.standard',
      qualified: true,
      status: 'qualified',
      release_state: 'released',
      snapshot_id: 9,
      version: 'v9',
      fingerprint: 'sha256:v9',
      applied: true,
      reason_code: 'PRODUCT_QUALIFIED',
      source: 'sc.edition.release.snapshot',
      qualification_authority: 'published_product_release',
    }],
  },
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
check(decodedList.meta.catalog_scope.mode, 'platform', 'catalog scope consumed');
check(
  decodedList.meta.catalog_scope.management_actions.add_to_product_draft.intent,
  'release.operator.add_catalog_entry',
  'catalog add action consumed',
);
check(
  decodedList.meta.catalog_scope.management_actions.add_to_product_draft.release_state_options.map(
    (option) => option.value,
  ),
  ['preview', 'released'],
  'release-state options come from the backend declaration',
);
assert.throws(
  () => decodeCapabilityExplorerListResponse({
    ...listResponse,
    meta: {
      ...meta,
      catalog_scope: {
        ...meta.catalog_scope,
        management_actions: {
          ...meta.catalog_scope.management_actions,
          add_to_product_draft: {
            ...meta.catalog_scope.management_actions.add_to_product_draft,
            release_state_options: [],
          },
        },
      },
    },
  }),
  (error) => isContractGapError(error),
  'missing release-state declarations stop the frontend',
);
cases += 1;
assert.throws(
  () => decodeCapabilityExplorerListResponse({
    ...listResponse,
    meta: {
      ...meta,
      catalog_scope: {
        ...meta.catalog_scope,
        management_actions: {
          ...meta.catalog_scope.management_actions,
          add_to_product_draft: {
            ...meta.catalog_scope.management_actions.add_to_product_draft,
            accepted_fields: ['product_key', 'menu_id', 'center_key'],
          },
        },
      },
    },
  }),
  (error) => isContractGapError(error),
  'missing accepted write fields stop the frontend',
);
cases += 1;
const addAction = decodedList.meta.catalog_scope.management_actions.add_to_product_draft;
const addParams = buildCapabilityCatalogEntryAddParams(addAction, {
  product_key: 'construction.standard',
  menu_id: 10,
  center_key: 'construction.center.project',
  release_state: 'preview',
});
check(addParams.release_state, 'preview', 'catalog add params use declared state');
assert.throws(
  () => buildCapabilityCatalogEntryAddParams(addAction, {
    ...addParams,
    release_state: 'hidden',
  }),
  (error) => isContractGapError(error),
  'undeclared release state cannot be sent',
);
cases += 1;
const writeResult = {
  action: {
    product_key: 'construction.standard',
    group_key: 'construction.center.project',
    readback: {
      menu_xmlid: row.entry_ref.menu_xmlid,
      action_xmlid: row.entry_ref.action_xmlid,
      menu_id: 10,
      action_id: 20,
      res_model: 'project.project',
      enabled: true,
      release_state: 'preview',
    },
  },
  surface: {},
  readback: {
    product_key: 'construction.standard',
    group_key: 'construction.center.project',
    menu_xmlid: row.entry_ref.menu_xmlid,
    action_xmlid: row.entry_ref.action_xmlid,
    menu_id: 10,
    action_id: 20,
    res_model: 'project.project',
    enabled: true,
    release_state: 'preview',
    draft_policy_sha256: 'sha256:draft',
    published_snapshot_id: 9,
    published_version: 'v9',
  },
};
const decodedWrite = decodeCapabilityCatalogEntryWriteResult(writeResult, addAction, {
  ...addParams,
  menu_xmlid: row.entry_ref.menu_xmlid,
  action_xmlid: row.entry_ref.action_xmlid,
  action_id: 20,
});
check(decodedWrite.readback.release_state, 'preview', 'catalog add readback consumed');
assert.throws(
  () => decodeCapabilityCatalogEntryWriteResult(
    { ...writeResult, readback: {} },
    addAction,
    {
      ...addParams,
      menu_xmlid: row.entry_ref.menu_xmlid,
      action_xmlid: row.entry_ref.action_xmlid,
      action_id: 20,
    },
  ),
  (error) => isContractGapError(error),
  'missing declared write readback stops success',
);
cases += 1;
assert.throws(
  () => decodeCapabilityCatalogEntryWriteResult(
    {
      ...writeResult,
      readback: { ...writeResult.readback, group_key: 'construction.center.finance' },
    },
    addAction,
    {
      ...addParams,
      menu_xmlid: row.entry_ref.menu_xmlid,
      action_xmlid: row.entry_ref.action_xmlid,
      action_id: 20,
    },
  ),
  (error) => isContractGapError(error),
  'readback identity mismatch stops success',
);
cases += 1;
check(decodedList.rows[0]?.label, '项目台账', 'list row consumed');
check(
  decodedList.rows[0]?.catalog_admission.enabled,
  true,
  'per-entry admission declaration consumed',
);
check(capabilityEntryKey(decodedList.rows[0]!), 'smart_construction_core.menu_project_ledger::smart_construction_core.action_project_ledger', 'stable entry key');
const operationEntryKey = capabilityEntryKey(decodedList.rows[0]!);
check(
  isCatalogAdmissionOperationCurrent(operationEntryKey, {
    drawer_open: true,
    selected_entry_key: operationEntryKey,
    detail_entry_key: operationEntryKey,
  }),
  true,
  'current detail retains the frozen admission identity',
);
check(
  isCatalogAdmissionOperationCurrent(operationEntryKey, {
    drawer_open: true,
    selected_entry_key: 'other.menu::other.action',
    detail_entry_key: 'other.menu::other.action',
  }),
  false,
  'switching detail cannot validate the original admission against another identity',
);
check(
  isCatalogAdmissionOperationCurrent(operationEntryKey, {
    drawer_open: false,
    selected_entry_key: '',
    detail_entry_key: '',
  }),
  false,
  'closing detail suppresses stale success presentation',
);
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
assert.throws(
  () => decodeCapabilityExplorerListResponse({
    ...listResponse,
    rows: [{ ...row, catalog_admission: undefined }],
  }),
  (error) => isContractGapError(error),
  'missing per-entry admission declaration must stop',
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
check(
  centerSourcePresentation({ source: 'published_product_policy' }).label,
  '已发布产品配置',
  'published product center source is explicit',
);
check(
  centerSourcePresentation({ source: 'ir.ui.menu' }).label,
  '原生菜单来源',
  'native center source remains distinct',
);
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
    qualification: row.product_qualification,
    enterprise_enablement: {
      applicable: true,
      enabled: true,
      status: 'enabled',
      reason_code: 'ENTERPRISE_SCENARIO_ENABLED',
      company_id: 7,
      company_name: 'Demo Company',
      source: 'res.company',
      scenes: [{ scene_key: 'project.management', enabled: true, source: 'sc.scene.company.enablement' }],
    },
    current_user_access: {
      entry_groups_allowed: true,
      required_group_ids: [11],
      held_group_ids: [11],
      model_read_acl_present: true,
      model_read_allowed: true,
      record_scope: 'runtime_acl_and_record_rules',
      reason_code: 'CURRENT_USER_ENTRY_AVAILABLE',
      blockers: [],
      product_composition_facts: {
        qualification_status: 'not_verified',
        qualified: false,
        qualification_reason_code: 'PRODUCT_QUALIFICATION_NOT_VERIFIED',
        release_state: 'unknown',
        reviewed_by_product_release: false,
        enterprise_enablement_status: 'enabled',
        enterprise_enabled: true,
      },
    },
    visibility: {
      can_use: true,
      reason_code: 'CURRENT_USER_ENTRY_AVAILABLE',
      blockers: [],
      actor: {
        user_id: 5,
        login: 'platform.admin',
        name: 'Platform Admin',
        company_id: 7,
        company_name: 'Demo Company',
        allowed_company_ids: [7],
        group_ids: [11],
        group_xmlids: ['smart_construction_core.group_sc_cap_project_read'],
        source: 'test principal',
      },
      target_company: { company_id: 7, company_name: 'Demo Company' },
      record_scope: 'runtime_acl_and_record_rules',
    },
    fact_layers: [
      { key: 'native_presence', label: '原生存在', status: 'present', reason_code: 'NATIVE_ENTRY_PRESENT', evidence: {} },
      { key: 'consumer_support', label: '消费者支持', status: 'supported', reason_code: 'CONSUMER_SUPPORTED', evidence: {} },
      { key: 'product_qualification', label: '产品资格', status: 'qualified', reason_code: 'PRODUCT_QUALIFIED', evidence: {} },
      { key: 'product_release', label: '入口发布', status: 'released', reason_code: 'ENTRY_RELEASED', evidence: {} },
      { key: 'enterprise_enablement', label: '企业启用', status: 'enabled', reason_code: 'ENTERPRISE_SCENARIO_ENABLED', evidence: {} },
      { key: 'current_user_access', label: '当前用户权限', status: 'allowed', reason_code: 'CURRENT_USER_ENTRY_AVAILABLE', evidence: {} },
    ],
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
check(decodedDetail.entry.qualification.evidence[0]?.version, 'v9', 'product qualification evidence consumed');
check(decodedDetail.entry.enterprise_enablement.enabled, true, 'enterprise enablement consumed');
check(decodedDetail.entry.visibility.actor.login, 'platform.admin', 'visibility actor consumed');
check(
  decodedDetail.entry.current_user_access.product_composition_facts.qualified,
  false,
  'product composition qualification remains a separate fact',
);
check(
  decodedDetail.entry.visibility.can_use,
  true,
  'native availability is not rejected by product qualification',
);
check(decodedDetail.entry.fact_layers.length, 6, 'fact layers consumed');
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

const managementActor = {
  user_id: 7,
  login: 'platform.admin',
  name: 'Platform Admin',
  operator_kind: 'authorized_release_operator',
  roles: ['admin'],
};
const managementTarget = {
  kind: 'product_release',
  scope_key: 'construction.standard',
  product_key: 'construction.standard',
  company_ids: [],
  target_role_codes: [],
  is_global_product_release: true,
  meaning: 'all authorized enterprises',
};
const configuredManagementAction = (
  key: string,
  intent: string,
  params: Record<string, unknown>,
  acceptedFields: string[],
  readbackFields: string[],
  extra: Record<string, unknown> = {},
) => ({
  key,
  label: key,
  intent,
  enabled: true,
  reason_code: 'OK',
  params,
  accepted_fields: acceptedFields,
  actor: managementActor,
  target_scope: managementTarget,
  operation_object: {
    kind: 'product_release_policy',
    product_key: 'construction.standard',
    snapshot_id: 0,
  },
  prerequisites: {
    satisfied: true,
    reason_code: 'OK',
    confirmation_required: false,
  },
  readback: {
    source: 'release.operator.surface',
    mode: 'authoritative_after_write',
    fields: readbackFields,
  },
  ...extra,
});

const compositionEntry = {
  entry_id: 1,
  menu_key: 'project.menu_ledger',
  menu_id: 21,
  intent: 'view',
  intent_label: '查看',
  sequence: -2,
  center_key: 'project',
  center_name: '项目',
  center_sequence: 0,
  source_db: 'sc_test',
};
const compositionScenario = {
  key: 'project',
  name: '项目台账',
  active: true,
  sequence: -1,
  source_db: 'sc_test',
  entries: [compositionEntry],
};
const compositionState = (
  status: 'draft' | 'candidate' | 'active',
  identity: Record<string, unknown>,
) => ({
  contract_version: 'business_scene_composition_management.v1',
  status,
  status_label: status,
  available: true,
  reason_code: 'BUSINESS_SCENE_COMPOSITION_AVAILABLE',
  identity: { product_key: 'construction.standard', ...identity },
  source_db: 'sc_test',
  runtime_scope: 'published_release',
  scenario_count: 1,
  entry_count: 1,
  empty: false,
  digest: 'a'.repeat(64),
  scenarios: [compositionScenario],
});

const promotionSurface = {
  identity: { product_key: 'construction.standard' },
  actor_scope: { user_id: 7, login: 'platform.admin', name: 'Platform Admin' },
  candidate_snapshots: [{ id: 31, version: 'v31', state: 'approved' }],
  business_scene_composition_states: {
    contract_version: 'business_scene_composition_management.v1',
    product_key: 'construction.standard',
    scope: 'maintained_business_scenario_composition',
    draft: compositionState('draft', { policy_id: 9, version: 'v32' }),
    candidate: compositionState('candidate', { snapshot_id: 31, version: 'v31' }),
    active: compositionState('active', { snapshot_id: 30, version: 'v30' }),
    comparisons: {
      draft_vs_candidate: {
        state: 'identical',
        changed_scenario_keys: [],
        changed_entry_keys: [],
        change_count: 0,
      },
      draft_vs_active: {
        state: 'changed',
        changed_scenario_keys: ['project'],
        changed_entry_keys: [],
        change_count: 1,
      },
      candidate_vs_active: {
        state: 'changed',
        changed_scenario_keys: ['project'],
        changed_entry_keys: [],
        change_count: 1,
      },
    },
  },
  business_scenario_maintenance: {
    contract_version: 'business_scenario_maintenance_entry.v1',
    product_key: 'construction.standard',
    applicable: true,
    provider: 'smart_construction_core',
    enabled: true,
    reason_code: 'SCENARIO_MAINTENANCE_AVAILABLE',
    blockers: [],
    action: {
      xmlid: 'smart_construction_core.action_sc_product_scenario',
      id: 71,
      name: '业务场景定义',
      res_model: 'sc.product.scenario',
      view_mode: 'tree,form',
    },
    menu: {
      xmlid: 'smart_construction_core.menu_sc_product_scenario_business_config',
      id: 72,
      name: '业务场景定义',
    },
    scope: {
      kind: 'shared_maintenance_library',
      label: '当前维护库共享业务场景定义',
      model: 'sc.product.scenario',
      has_product_key: false,
      has_company_id: false,
      applies_to: 'all_product_drafts_frozen_from_this_maintenance_database',
      filter_by_current_product: false,
    },
    future_freeze_product_key: 'construction.standard',
    access: {
      read_allowed: true,
      write_allowed: true,
    },
    return_readback: {
      intent: 'release.operator.surface',
      product_key: 'construction.standard',
      fields: [
        'business_scene_composition_states.draft',
        'business_scene_composition_states.comparisons',
      ],
    },
  },
  available_actions: {
    freeze: configuredManagementAction(
      'freeze:construction.standard',
      'release.operator.freeze',
      { product_key: 'construction.standard', replace_active: false },
      ['product_key', 'version', 'role_code', 'note'],
      ['snapshot', 'surface'],
    ),
    sync_policy: configuredManagementAction(
      'sync_policy:construction.standard',
      'release.operator.sync_policy',
      { product_key: 'construction.standard' },
      ['product_key', 'preserve_state', 'preserve_access_level'],
      ['policy', 'surface'],
    ),
    set_page_enabled: configuredManagementAction(
      'set_page_enabled:construction.standard',
      'release.operator.set_page_enabled',
      { product_key: 'construction.standard' },
      ['product_key', 'page_key', 'enabled'],
      ['policy', 'surface'],
    ),
    update_page_policy: configuredManagementAction(
      'update_page_policy:construction.standard',
      'release.operator.update_page_policy',
      { product_key: 'construction.standard' },
      ['product_key', 'page_key', 'enabled', 'release_state', 'access_level', 'policy_note'],
      ['policy', 'surface'],
      {
        editable_fields: [
          {
            key: 'release_state',
            type: 'select',
            options: [
              { value: 'released', label: '正式' },
              { value: 'preview', label: '预览' },
              { value: 'hidden', label: '隐藏' },
              { value: 'retired', label: '退役' },
            ],
          },
          {
            key: 'access_level',
            type: 'select',
            options: [
              { value: 'public', label: '公开' },
              { value: 'internal', label: '内部' },
              { value: 'role_restricted', label: '按角色限制' },
            ],
          },
        ],
      },
    ),
    update_policy: {
      ...configuredManagementAction(
        'update_policy:construction.standard',
        'release.operator.update_policy',
        { product_key: 'construction.standard' },
        [
          'product_key',
          'state',
          'access_level',
          'active',
          'allowed_role_codes',
          'center_updates',
          'entry_placements',
        ],
        ['policy', 'surface', 'readback'],
        {
          editable_fields: [
            {
              key: 'state',
              type: 'select',
              options: [
                { value: 'draft', label: '草稿' },
                { value: 'preview', label: '预览' },
                { value: 'stable', label: '稳定' },
                { value: 'archived', label: '归档' },
              ],
            },
            {
              key: 'access_level',
              type: 'select',
              options: [
                { value: 'public', label: '公开' },
                { value: 'internal', label: '内部' },
                { value: 'role_restricted', label: '按角色限制' },
              ],
            },
          ],
        },
      ),
      editor_contract: 'product_center_editor.v1',
    },
    runtime_probe: configuredManagementAction(
      'runtime_probe:construction.standard',
      'release.operator.runtime_probe',
      { product_key: 'construction.standard' },
      ['product_key'],
      ['runtime_user_probe'],
    ),
    rollback: configuredManagementAction(
      'rollback:construction.standard',
      'release.operator.rollback',
      {
        product_key: 'construction.standard',
        target_snapshot_id: 29,
        replace_active: true,
      },
      ['product_key', 'target_snapshot_id', 'replace_active', 'note'],
      ['action', 'surface'],
      {
        operation_object: {
          kind: 'release_snapshot',
          product_key: 'construction.standard',
          snapshot_id: 29,
        },
        prerequisites: {
          satisfied: true,
          reason_code: 'OK',
          confirmation_required: true,
        },
      },
    ),
    promote: [{
      key: 'promote:31',
      label: '发布产品版本 v31',
      intent: 'release.operator.promote',
      enabled: true,
      reason_code: 'OK',
      params: { product_key: 'construction.standard', snapshot_id: 31, replace_active: true },
      accepted_fields: ['product_key', 'snapshot_id', 'replace_active'],
      actor: {
        user_id: 7,
        login: 'platform.admin',
        name: 'Platform Admin',
        operator_kind: 'authorized_release_operator',
        roles: ['admin'],
      },
      target_scope: {
        kind: 'product_release',
        scope_key: 'construction.standard',
        product_key: 'construction.standard',
        company_ids: [],
        target_role_codes: [],
        is_global_product_release: true,
        meaning: 'all authorized enterprises',
      },
      operation_object: {
        kind: 'release_snapshot',
        product_key: 'construction.standard',
        snapshot_id: 31,
      },
      prerequisites: {
        satisfied: true,
        reason_code: 'OK',
        confirmation_required: true,
      },
      readback: {
        source: 'release.operator.surface',
        mode: 'authoritative_after_write',
        fields: ['current_release_state.active_snapshot'],
      },
    }],
  },
  operation_readback: {
    product_key: 'construction.standard',
    active_snapshot: { id: 30, version: 'v30', state: 'released' },
    rollback_target_snapshot_id: 29,
  },
  pending_approval: {
    count: 1,
    actions: [{
      id: 31,
      action_type: 'promote_snapshot',
      product_key: 'construction.standard',
      can_approve: true,
      approve_action: configuredManagementAction(
        'approve:31',
        'release.operator.approve',
        { product_key: 'construction.standard', action_id: 31 },
        ['action_id'],
        ['action', 'surface'],
        {
          operation_object: {
            kind: 'release_action',
            product_key: 'construction.standard',
            snapshot_id: 0,
            action_id: 31,
          },
          prerequisites: {
            satisfied: true,
            reason_code: 'OK',
            confirmation_required: true,
          },
        },
      ),
    }],
  },
  product_center_editor: {
    contract_version: 'product_center_editor.v1',
    product_key: 'construction.standard',
    operation_scope: {
      kind: 'product_draft',
      product_key: 'construction.standard',
    },
    editable_fields: [
      { key: 'label', label: '中心名称', type: 'text', required: true, max_length: 80 },
      { key: 'sequence', label: '显示顺序', type: 'integer', required: true, minimum: 0, maximum: 9999 },
      { key: 'center_key', label: '入口所属中心', type: 'select', required: true, options_source: 'centers' },
    ],
    centers: [{
      center_key: 'construction.center.project',
      label: '项目中心',
      sequence: 20,
      entry_count: 1,
      editable_fields: ['label', 'sequence'],
      config_ref: {
        kind: 'release_operator_action',
        intent: 'release.operator.update_policy',
        product_key: 'construction.standard',
      },
      published_label: '项目中心',
      published_sequence: 20,
      changed_from_published: false,
    }],
    entries: [{
      menu_xmlid: 'smart_construction_core.menu_sc_project_project',
      label: '项目台账',
      center_key: 'construction.center.project',
      center_label: '项目中心',
      center_sequence: 20,
      published_center_key: 'construction.center.project',
      published_center_label: '项目中心',
      changed_from_published: false,
    }],
    published: {
      snapshot_id: 30,
      version: 'v30',
      centers: [],
    },
    change_summary: {
      center_count: 1,
      entry_count: 1,
      changed_center_count: 0,
      changed_entry_placement_count: 0,
    },
    save_action: {
      key: 'update_policy:construction.standard',
      intent: 'release.operator.update_policy',
      enabled: true,
      reason_code: 'OK',
      params: { product_key: 'construction.standard' },
      accepted_fields: ['center_updates', 'entry_placements'],
      readback: ['policy', 'surface', 'readback'],
      confirmation_required: true,
    },
    config_ref: {
      kind: 'release_operator_action',
      intent: 'release.operator.update_policy',
      product_key: 'construction.standard',
    },
  },
};
const decodedPromotion = decodeReleaseOperatorSurface(promotionSurface);
check(
  decodedPromotion.available_actions.promote[0].operation_object.snapshot_id,
  31,
  'complete promotion contract consumed',
);
check(
  decodedPromotion.business_scene_composition_states.candidate.identity.snapshot_id,
  31,
  'candidate composition identity consumed',
);
check(
  decodedPromotion.business_scene_composition_states.comparisons.draft_vs_active.state,
  'changed',
  'backend-owned composition difference consumed',
);
check(
  decodedPromotion.business_scenario_maintenance.scope.kind,
  'shared_maintenance_library',
  'shared maintenance scope consumed',
);
check(
  buildBusinessScenarioMaintenanceTarget(
    decodedPromotion.business_scenario_maintenance,
    '/admin/release-operator?product_key=construction.standard',
  ),
  {
    path: '/a/71',
    query: {
      action_id: '71',
      menu_id: '72',
      return_url: '/admin/release-operator?product_key=construction.standard',
      return_label: '返回发布控制台',
      return_product_key: 'construction.standard',
    },
  },
  'native shared maintenance target uses backend identity',
);
const previewMaintenance = {
  ...decodedPromotion.business_scenario_maintenance,
  return_readback: {
    ...decodedPromotion.business_scenario_maintenance.return_readback,
    product_key: 'construction.preview',
  },
};
const previewTarget = buildBusinessScenarioMaintenanceTarget(
  previewMaintenance,
  '/admin/release-operator?product_key=construction.standard',
);
check(
  previewTarget?.query.return_url,
  '/admin/release-operator?product_key=construction.preview',
  'return URL is rebound to the backend-declared product',
);
check(
  pickContractNavQuery(previewTarget?.query || {}),
  {
    menu_id: '72',
    action_id: '71',
    return_url: '/admin/release-operator?product_key=construction.preview',
    return_label: '返回发布控制台',
    return_product_key: 'construction.preview',
  },
  'generic record navigation preserves maintenance return context',
);
check(
  contextReturnHref(previewTarget?.query || {}),
  '/admin/release-operator?product_key=construction.preview',
  'generic action navigation consumes the backend-bound return product',
);
check(
  decodedPromotion.business_scene_composition_states.draft.scenarios[0].entries[0].sequence,
  -2,
  'signed entry sequence is consumed',
);
check(
  decodedPromotion.business_scene_composition_states.draft.scenarios[0].sequence,
  -1,
  'signed scenario sequence is consumed',
);
check(
  decodedPromotion.business_scene_composition_states.draft.scenarios[0].entries[0].center_sequence,
  0,
  'zero center sequence is preserved',
);
check(
  buildBusinessScenarioMaintenanceTarget({
    ...decodedPromotion.business_scenario_maintenance,
    enabled: false,
  }, '/admin/release-operator'),
  null,
  'disabled maintenance entry cannot navigate',
);
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    business_scenario_maintenance: {
      ...promotionSurface.business_scenario_maintenance,
      product_key: 'construction.preview',
    },
  }),
  (error) => isContractGapError(error),
  'wrong-product maintenance context is rejected',
);
cases += 1;
const notApplicable = decodeReleaseOperatorSurface({
  ...promotionSurface,
  business_scenario_maintenance: {
    ...promotionSurface.business_scenario_maintenance,
    applicable: false,
    provider: '',
    enabled: false,
    reason_code: 'SCENARIO_MAINTENANCE_NOT_APPLICABLE',
    blockers: ['SCENARIO_MAINTENANCE_NOT_APPLICABLE'],
    action: { xmlid: '', id: 0, name: '', res_model: '', view_mode: '' },
    menu: { xmlid: '', id: 0, name: '' },
    scope: {
      kind: 'not_applicable',
      label: '当前产品不消费共享施工业务场景定义',
      model: '',
      has_product_key: false,
      has_company_id: false,
      applies_to: '',
      filter_by_current_product: false,
    },
    future_freeze_product_key: '',
  },
});
check(
  notApplicable.business_scenario_maintenance.enabled,
  false,
  'not-applicable product cannot claim a maintenance entry',
);
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    business_scene_composition_states: {
      ...promotionSurface.business_scene_composition_states,
      active: {
        ...promotionSurface.business_scene_composition_states.active,
        identity: { product_key: 'construction.preview', snapshot_id: 30 },
      },
    },
  }),
  (error) => isContractGapError(error),
  'wrong-product composition identity cannot replace the active state',
);
cases += 1;
check(
  (decodedPromotion.available_actions as Record<string, Record<string, unknown>>).freeze.intent,
  'release.operator.freeze',
  'declared freeze action consumed',
);
check(
  ((decodedPromotion.available_actions as Record<string, Record<string, unknown>>).rollback.readback as Record<string, unknown>).fields,
  ['action', 'surface'],
  'declared rollback action readback consumed',
);
check(
  ((((decodedPromotion.pending_approval as Record<string, unknown>).actions as Array<Record<string, unknown>>)[0].approve_action as Record<string, unknown>).params as Record<string, unknown>).action_id,
  31,
  'pending approval uses backend action object',
);
check(
  buildConfiguredOperatorParams(
    (decodedPromotion.available_actions as Record<string, OperatorAction>).update_policy,
    { state: 'stable', access_level: 'public' },
  ),
  {
    product_key: 'construction.standard',
    state: 'stable',
    access_level: 'public',
  },
  'decoded product policy action builds a valid request',
);
check(
  buildConfiguredOperatorParams(
    (decodedPromotion.available_actions as Record<string, OperatorAction>).update_page_policy,
    { page_key: 'project.list', release_state: 'preview', access_level: 'internal' },
  ),
  {
    product_key: 'construction.standard',
    page_key: 'project.list',
    release_state: 'preview',
    access_level: 'internal',
  },
  'decoded page policy action builds a valid request',
);
assert.throws(
  () => decodeConfiguredActionResult(
    {
      snapshot: null,
      surface: promotionSurface,
    },
    (decodedPromotion.available_actions as Record<string, OperatorAction>).freeze,
    'construction.standard',
  ),
  (error) => isContractGapError(error),
  'null freeze snapshot readback is rejected',
);
cases += 1;
assert.throws(
  () => decodeConfiguredActionResult(
    {
      policy: null,
      surface: promotionSurface,
    },
    (decodedPromotion.available_actions as Record<string, OperatorAction>).sync_policy,
    'construction.standard',
  ),
  (error) => isContractGapError(error),
  'null policy readback is rejected',
);
cases += 1;
const syncAction = (
  decodedPromotion.available_actions as Record<string, OperatorAction>
).sync_policy;
check(
  buildConfiguredOperatorParams(syncAction, {}),
  { product_key: 'construction.standard' },
  'sync action builds its declared request without frontend defaults',
);
const maintainedSyncPolicy = {
  product_key: 'construction.standard',
  label: '施工管理标准版',
  allowed_role_codes: ['project_manager'],
  scene_version_bindings: {
    'scene.project': { version: 'v4', channel: 'stable' },
  },
  menu_groups: [{
    center_key: 'construction.center.project',
    group_key: 'construction.center.project',
    group_label: '项目中心（管理员命名）',
    sequence: 0,
    menus: [{
      menu_xmlid: 'smart_construction_core.menu_sc_project_project',
      action_xmlid: 'smart_construction_core.action_project_project',
      label: '项目台账（管理员命名）',
      sequence: 0,
      release_state: 'hidden',
      entry_intent: 'handling',
      res_model: 'project.project',
    }],
  }],
  scenes: [{
    scene_key: 'scene.project',
    label: '项目管理场景',
    capability_key: 'business.project.ledger',
  }],
  capabilities: [{
    capability_key: 'business.project.ledger',
    menu_xmlid: 'smart_construction_core.menu_sc_project_project',
    business_capability: true,
    provider_authority: 'scene_entry_target',
  }],
};
const maintainedSyncSurface = {
  ...promotionSurface,
  operation_readback: {
    ...promotionSurface.operation_readback,
    active_snapshot: {
      id: 30,
      version: 'v30',
      state: 'released',
    },
  },
  product_center_editor: {
    ...promotionSurface.product_center_editor,
    centers: [{
      ...promotionSurface.product_center_editor.centers[0],
      label: '项目中心（管理员命名）',
      sequence: 0,
      changed_from_published: false,
    }],
    entries: [{
      ...promotionSurface.product_center_editor.entries[0],
      label: '项目台账（管理员命名）',
      center_sequence: 0,
      changed_from_published: false,
    }],
  },
};
const decodedSync = decodeConfiguredActionResult(
  {
    policy: maintainedSyncPolicy,
    surface: maintainedSyncSurface,
  },
  syncAction,
  'construction.standard',
);
const syncedPolicy = decodedSync.readback.policy;
const syncedGroups = syncedPolicy.menu_groups as Array<Record<string, unknown>>;
const syncedMenus = syncedGroups[0].menus as Array<Record<string, unknown>>;
check(syncedGroups[0].group_label, '项目中心（管理员命名）', 'sync policy preserves maintained center label');
check(syncedGroups[0].sequence, 0, 'sync policy preserves center sequence zero');
check(syncedMenus[0].label, '项目台账（管理员命名）', 'sync policy preserves maintained entry label');
check(syncedMenus[0].sequence, 0, 'sync policy preserves entry sequence zero');
check(syncedMenus[0].entry_intent, 'handling', 'sync policy preserves business intent');
check(syncedPolicy.allowed_role_codes, ['project_manager'], 'sync policy preserves role restrictions');
check(syncedPolicy.scene_version_bindings, maintainedSyncPolicy.scene_version_bindings, 'sync policy preserves scene bindings');
const decodedSyncSurface = decodeReleaseOperatorSurface(maintainedSyncSurface);
check(
  decodedSyncSurface.product_center_editor.centers[0].label,
  '项目中心（管理员命名）',
  'sync surface updates the current draft expression',
);
check(
  decodedSyncSurface.operation_readback.active_snapshot.version,
  'v30',
  'sync success does not replace the currently published version',
);
assert.throws(
  () => decodeConfiguredActionResult(
    {
      policy: {
        ...maintainedSyncPolicy,
        product_key: 'construction.preview',
      },
      surface: maintainedSyncSurface,
    },
    syncAction,
    'construction.standard',
  ),
  (error) => isContractGapError(error),
  'sync readback for another product is rejected before surface replacement',
);
cases += 1;
assert.throws(
  () => decodeConfiguredActionResult(
    {
      action: {
        id: 99,
        product_key: 'construction.standard',
      },
      surface: promotionSurface,
    },
    (decodedPromotion.pending_approval as Record<string, unknown> & {
      actions: Array<{ approve_action: OperatorAction }>;
    }).actions[0].approve_action,
    'construction.standard',
  ),
  (error) => isContractGapError(error),
  'approval readback action identity mismatch is rejected',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    available_actions: {
      ...promotionSurface.available_actions,
      update_policy: {
        ...promotionSurface.available_actions.update_policy,
        editable_fields: (
          promotionSurface.available_actions.update_policy.editable_fields as Array<Record<string, unknown>>
        ).filter((field) => field.key !== 'state'),
      },
    },
  }),
  (error) => isContractGapError(error),
  'policy save declaration must include its state field',
);
cases += 1;
const centerWriteEnvelope = {
  policy: {
    product_key: 'construction.standard',
    menu_groups: [],
  },
  surface: promotionSurface,
  readback: {
    product_key: 'construction.standard',
    draft_policy_sha256: 'sha256:draft',
    draft_fingerprint: 'draft-v1',
    published_snapshot_id: 30,
    published_version: 'v30',
  },
};
check(
  decodeProductCenterWriteEnvelope(
    centerWriteEnvelope,
    decodedPromotion.product_center_editor,
  ).policy.product_key,
  'construction.standard',
  'center write binds the submitted product',
);
check(
  decodeProductCenterWriteEnvelope(
    {
      ...centerWriteEnvelope,
      readback: {
        ...centerWriteEnvelope.readback,
        published_snapshot_id: 0,
      },
    },
    decodedPromotion.product_center_editor,
  ).readback.published_snapshot_id,
  0,
  'unpublished center write accepts an explicit integer zero',
);
for (const invalidSnapshotId of [null, false, '0', 1.5]) {
  assert.throws(
    () => decodeProductCenterWriteEnvelope(
      {
        ...centerWriteEnvelope,
        readback: {
          ...centerWriteEnvelope.readback,
          published_snapshot_id: invalidSnapshotId,
        },
      },
      decodedPromotion.product_center_editor,
    ),
    (error) => isContractGapError(error),
    `center write rejects invalid published snapshot identity ${String(invalidSnapshotId)}`,
  );
  cases += 1;
}
assert.throws(
  () => decodeProductCenterWriteEnvelope(
    {
      ...centerWriteEnvelope,
      policy: {
        ...centerWriteEnvelope.policy,
        product_key: 'construction.preview',
      },
      readback: {
        ...centerWriteEnvelope.readback,
        product_key: 'construction.preview',
      },
      surface: {
        ...promotionSurface,
        identity: { product_key: 'construction.preview' },
      },
    },
    decodedPromotion.product_center_editor,
  ),
  (error) => isContractGapError(error),
  'internally consistent center write for another product still stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    available_actions: {
      promote: [{
        ...promotionSurface.available_actions.promote[0],
        operation_object: undefined,
      }],
    },
  }),
  (error) => isContractGapError(error),
  'missing promotion operation object stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    pending_approval: {
      count: 1,
      actions: [{
        ...promotionSurface.pending_approval.actions[0],
        approve_action: undefined,
      }],
    },
  }),
  (error) => isContractGapError(error),
  'pending approval without a complete action object stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    pending_approval: {
      count: 1,
      actions: [{
        ...promotionSurface.pending_approval.actions[0],
        approve_action: {
          ...promotionSurface.pending_approval.actions[0].approve_action,
          params: {
            ...promotionSurface.pending_approval.actions[0].approve_action.params,
            action_id: 99,
          },
        },
      }],
    },
  }),
  (error) => isContractGapError(error),
  'approval row, request parameter and operation object identities must agree',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    product_center_editor: undefined,
  }),
  (error) => isContractGapError(error),
  'missing product center editor contract stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    product_center_editor: {
      ...promotionSurface.product_center_editor,
      product_key: 'construction.preview',
    },
  }),
  (error) => isContractGapError(error),
  'product center editor product identity mismatch stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    product_center_editor: {
      ...promotionSurface.product_center_editor,
      editable_fields: promotionSurface.product_center_editor.editable_fields.slice(0, 2),
    },
  }),
  (error) => isContractGapError(error),
  'missing center field declaration stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    product_center_editor: {
      ...promotionSurface.product_center_editor,
      centers: [{
        ...promotionSurface.product_center_editor.centers[0],
        sequence: 'banana',
      }],
    },
  }),
  (error) => isContractGapError(error),
  'invalid center sequence stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    product_center_editor: {
      ...promotionSurface.product_center_editor,
      centers: [{
        ...promotionSurface.product_center_editor.centers[0],
        sequence: false,
      }],
    },
  }),
  (error) => isContractGapError(error),
  'boolean is never decoded as a numeric sequence declaration',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    product_center_editor: {
      ...promotionSurface.product_center_editor,
      save_action: {
        ...promotionSurface.product_center_editor.save_action,
        readback: ['surface'],
      },
    },
  }),
  (error) => isContractGapError(error),
  'incomplete center save readback declaration stops',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    available_actions: {
      promote: [{
        ...promotionSurface.available_actions.promote[0],
        prerequisites: {
          ...promotionSurface.available_actions.promote[0].prerequisites,
          satisfied: false,
          reason_code: 'RELEASE_EXECUTOR_NOT_ALLOWED',
        },
      }],
    },
  }),
  (error) => isContractGapError(error),
  'promotion enabled state must agree with prerequisites',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    candidate_snapshots: [{ id: 31, version: 'v31', state: 'approved' }],
    available_actions: {},
  }),
  (error) => isContractGapError(error),
  'missing promote declaration stops before display',
);
cases += 1;
const emptyPromotion = decodeReleaseOperatorSurface({
  ...promotionSurface,
  candidate_snapshots: [],
  available_actions: {
    ...promotionSurface.available_actions,
    promote: [],
  },
});
check(
  emptyPromotion.available_actions.promote.length,
  0,
  'complete metadata with an empty promote array is valid',
);
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    identity: undefined,
    available_actions: { promote: [] },
  }),
  (error) => isContractGapError(error),
  'empty promote still requires product identity',
);
cases += 1;
assert.throws(
  () => decodeReleaseOperatorSurface({
    ...promotionSurface,
    operation_readback: undefined,
    available_actions: { promote: [] },
  }),
  (error) => isContractGapError(error),
  'empty promote still requires authoritative readback',
);
cases += 1;

console.log(`[platform_capability_explorer_test] PASS cases=${cases}`);
