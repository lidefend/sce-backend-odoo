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
import { decodeReleaseOperatorSurface } from '../src/app/releaseOperatorActionContract';

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

const promotionSurface = {
  identity: { product_key: 'construction.standard' },
  actor_scope: { user_id: 7, login: 'platform.admin', name: 'Platform Admin' },
  candidate_snapshots: [{ id: 31, version: 'v31', state: 'approved' }],
  available_actions: {
    update_policy: {
      editor_contract: 'product_center_editor.v1',
    },
    promote: [{
      key: 'promote:31',
      label: '发布产品版本 v31',
      intent: 'release.operator.promote',
      enabled: true,
      reason_code: 'OK',
      params: { product_key: 'construction.standard', snapshot_id: 31, replace_active: true },
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
