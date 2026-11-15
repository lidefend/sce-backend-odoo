import { intentRequest } from './intents';
import { contractGapError } from '../app/contract/contractGap';

const DECLARATION_LAYER = 'P0:smart_core:platform_capability_explorer';

export type CapabilityExplorerFilters = {
  center_keys?: string[];
  business_domain_keys?: string[];
  scene_status?: Array<'bound' | 'unbound'>;
  release_states?: string[];
  draft_selectable?: boolean;
  classification_confidence?: Array<'authoritative_scene_binding' | 'center_only' | 'unclassified'>;
};

export type CapabilityExplorerListParams = {
  query?: string;
  filters?: CapabilityExplorerFilters;
  limit?: number;
  offset?: number;
  sort?: string;
  expected_catalog_token?: string;
};

export type CapabilityExplorerBaseMeta = {
  schema: string;
  generated_at: string;
  runtime_database: string;
  source_revision: string;
  catalog_token: string;
  total: number;
  freshness: string;
  persistence: string;
  language: Record<string, unknown>;
  diagnostics: Record<string, unknown>;
};

export type CapabilityExplorerMeta = CapabilityExplorerBaseMeta & {
  filtered_total: number;
  offset: number;
  limit: number;
  next_offset: number | null;
  has_more: boolean;
  sort?: string[];
};

export type CapabilityExplorerCenter = {
  key: string;
  label: string;
  sequence: number;
  source: string;
};

export type CapabilityExplorerRow = {
  entry_ref: {
    menu_xmlid: string;
    action_xmlid: string;
  };
  label: string;
  origin: {
    module: string;
    model: string;
  };
  center: CapabilityExplorerCenter;
  business_domain: {
    key: string | null;
    label: string | null;
    confidence: 'authoritative_scene_binding' | 'center_only' | 'unclassified';
    reason_code: string;
  };
  scene_usage: {
    bound: boolean;
    count: number;
  };
  release_state: string;
  draft_eligibility: {
    selectable: boolean;
    blockers: string[];
  };
  product_qualification: {
    preview: string;
    standard: string;
  };
};

export type CapabilityExplorerFacets = {
  centers: Array<{ key: string; label: string; count: number }>;
  business_domains: Array<{ key: string; label: string; count: number }>;
  scene_status: Record<string, number>;
  release_states: Record<string, number>;
  classification_confidence: Record<string, number>;
};

export type CapabilityExplorerListResponse = {
  meta: CapabilityExplorerMeta;
  facets: CapabilityExplorerFacets;
  rows: CapabilityExplorerRow[];
};

export type CapabilityExplorerNativeFacts = {
  menu: {
    xmlid: string;
    label: string;
    sequence: number;
    path: string[];
    group_xmlids: string[];
  };
  action: {
    xmlid: string;
    type: string;
    view_modes: string[];
    group_xmlids: string[];
  };
  module: {
    name: string;
    state: string;
    version: string;
    dependencies: string[];
  };
  model: {
    name: string;
    description: string;
    exists: boolean;
    field_count: number;
  };
  views: {
    count: number;
    sha256: string;
  };
  acl: {
    row_count: number;
    group_xmlids: string[];
    sha256: string;
  };
  record_rules: {
    count: number;
    group_xmlids: string[];
    sha256: string;
  };
};

export type CapabilityExplorerScenarioUsage = {
  bound: boolean;
  ambiguous: boolean;
  scenarios: Array<{
    scenario_key: string;
    scenario_name: string;
    scenario_active: boolean;
    scenario_sequence: number;
    sequence: number;
    intent: string;
  }>;
};

export type CapabilityExplorerRelease = {
  state: string;
  entry_published: boolean;
  center: Record<string, unknown> | null;
  blockers: string[];
  ambiguous_center: boolean;
  snapshots: Array<Record<string, unknown>>;
};

export type CapabilityExplorerDiagnostics = {
  native_valid: boolean;
  native_blockers: string[];
  release_blockers: string[];
  blockers: string[];
  draft_selectable: boolean;
  scene_assignable: boolean;
  entry_published: boolean;
  preview_qualified: string;
  standard_qualified: string;
  classification_reason: string;
};

export type CapabilityExplorerDetailEntry = CapabilityExplorerRow & {
  native_facts: CapabilityExplorerNativeFacts;
  scenario_usage: CapabilityExplorerScenarioUsage;
  release: CapabilityExplorerRelease;
  scene_assignment: {
    assignable: boolean;
    blockers: string[];
  };
  qualification: {
    preview: string;
    standard: string;
  };
  diagnostics: CapabilityExplorerDiagnostics;
  classification: {
    source: string;
    candidates: Array<Record<string, unknown>>;
    reason_code: string;
    center_source: string;
    native_center: Record<string, unknown> | null;
    release_center: Record<string, unknown> | null;
  };
};

export type CapabilityExplorerDetailResponse = {
  meta: CapabilityExplorerBaseMeta;
  entry: CapabilityExplorerDetailEntry;
};

export type CapabilityExplorerDiagnosisResponse = {
  meta: CapabilityExplorerBaseMeta;
  entry_ref: {
    menu_xmlid: string;
    action_xmlid: string | null;
  };
  native_valid: boolean;
  draft_selectable: boolean;
  scene_assignable: boolean;
  entry_published: boolean;
  preview_qualified: string;
  standard_qualified: string;
  blockers: string[];
  classification_reason: string;
  native_facts?: Record<string, unknown>;
  sections: Record<string, unknown>;
};

function gap(path: string): never {
  throw contractGapError(
    { kind: 'contract_defect', missing: path, requiredDeclarationLayer: DECLARATION_LAYER },
    `平台能力浏览器契约缺少合法声明 ${path}`,
  );
}

function object(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return gap(path);
  return value as Record<string, unknown>;
}

function text(value: unknown, path: string): string {
  if (typeof value !== 'string') return gap(path);
  return value;
}

function optionalText(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function requiredText(value: unknown, path: string): string {
  const declared = text(value, path).trim();
  return declared || gap(path);
}

function number(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return gap(path);
  return value;
}

function boolean(value: unknown, path: string): boolean {
  return typeof value === 'boolean' ? value : gap(path);
}

function strings(value: unknown, path: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) return gap(path);
  return [...value] as string[];
}

function nullableObject(value: unknown, path: string): Record<string, unknown> | null {
  return value === null ? null : object(value, path);
}

function countMap(value: unknown, path: string): Record<string, number> {
  const source = object(value, path);
  return Object.fromEntries(Object.entries(source).map(([key, count]) => [key, number(count, `${path}.${key}`)]));
}

function decodeBaseMeta(value: unknown): CapabilityExplorerBaseMeta {
  const source = object(value, 'meta');
  return {
    schema: requiredText(source.schema, 'meta.schema'),
    generated_at: requiredText(source.generated_at, 'meta.generated_at'),
    runtime_database: requiredText(source.runtime_database, 'meta.runtime_database'),
    source_revision: requiredText(source.source_revision, 'meta.source_revision'),
    catalog_token: requiredText(source.catalog_token, 'meta.catalog_token'),
    total: number(source.total, 'meta.total'),
    freshness: requiredText(source.freshness, 'meta.freshness'),
    persistence: requiredText(source.persistence, 'meta.persistence'),
    language: object(source.language, 'meta.language'),
    diagnostics: object(source.diagnostics, 'meta.diagnostics'),
  };
}

function decodeMeta(value: unknown): CapabilityExplorerMeta {
  const source = object(value, 'meta');
  return {
    ...decodeBaseMeta(source),
    filtered_total: number(source.filtered_total, 'meta.filtered_total'),
    offset: number(source.offset, 'meta.offset'),
    limit: number(source.limit, 'meta.limit'),
    next_offset: source.next_offset === null ? null : number(source.next_offset, 'meta.next_offset'),
    has_more: boolean(source.has_more, 'meta.has_more'),
    ...(Array.isArray(source.sort) ? { sort: strings(source.sort, 'meta.sort') } : {}),
  };
}

export function decodeCapabilityExplorerRow(value: unknown): CapabilityExplorerRow {
  const source = object(value, 'row');
  const entryRef = object(source.entry_ref, 'row.entry_ref');
  const origin = object(source.origin, 'row.origin');
  const center = object(source.center, 'row.center');
  const business = object(source.business_domain, 'row.business_domain');
  const usage = object(source.scene_usage, 'row.scene_usage');
  const draft = object(source.draft_eligibility, 'row.draft_eligibility');
  const qualification = object(source.product_qualification, 'row.product_qualification');
  const confidence = requiredText(business.confidence, 'row.business_domain.confidence');
  if (!['authoritative_scene_binding', 'center_only', 'unclassified'].includes(confidence)) {
    gap('row.business_domain.confidence');
  }
  return {
    entry_ref: {
      menu_xmlid: requiredText(entryRef.menu_xmlid, 'row.entry_ref.menu_xmlid'),
      action_xmlid: requiredText(entryRef.action_xmlid, 'row.entry_ref.action_xmlid'),
    },
    label: requiredText(source.label, 'row.label'),
    origin: {
      module: requiredText(origin.module, 'row.origin.module'),
      model: text(origin.model, 'row.origin.model'),
    },
    center: {
      key: optionalText(center.key),
      label: optionalText(center.label),
      sequence: center.sequence === undefined ? 0 : number(center.sequence, 'row.center.sequence'),
      source: optionalText(center.source),
    },
    business_domain: {
      key: business.key === null ? null : requiredText(business.key, 'row.business_domain.key'),
      label: business.label === null ? null : requiredText(business.label, 'row.business_domain.label'),
      confidence: confidence as CapabilityExplorerRow['business_domain']['confidence'],
      reason_code: text(business.reason_code, 'row.business_domain.reason_code'),
    },
    scene_usage: {
      bound: boolean(usage.bound, 'row.scene_usage.bound'),
      count: number(usage.count, 'row.scene_usage.count'),
    },
    release_state: requiredText(source.release_state, 'row.release_state'),
    draft_eligibility: {
      selectable: boolean(draft.selectable, 'row.draft_eligibility.selectable'),
      blockers: strings(draft.blockers, 'row.draft_eligibility.blockers'),
    },
    product_qualification: {
      preview: requiredText(qualification.preview, 'row.product_qualification.preview'),
      standard: requiredText(qualification.standard, 'row.product_qualification.standard'),
    },
  };
}

function decodeFacets(value: unknown): CapabilityExplorerFacets {
  const source = object(value, 'facets');
  const decodeGroups = (raw: unknown, path: string) => {
    if (!Array.isArray(raw)) return gap(path);
    return raw.map((item, index) => {
      const row = object(item, `${path}[${index}]`);
      return {
        key: requiredText(row.key, `${path}[${index}].key`),
        label: requiredText(row.label, `${path}[${index}].label`),
        count: number(row.count, `${path}[${index}].count`),
      };
    });
  };
  return {
    centers: decodeGroups(source.centers, 'facets.centers'),
    business_domains: decodeGroups(source.business_domains, 'facets.business_domains'),
    scene_status: countMap(source.scene_status, 'facets.scene_status'),
    release_states: countMap(source.release_states, 'facets.release_states'),
    classification_confidence: countMap(source.classification_confidence, 'facets.classification_confidence'),
  };
}

export function decodeCapabilityExplorerListResponse(value: unknown): CapabilityExplorerListResponse {
  const source = object(value, 'response');
  if (!Array.isArray(source.rows)) return gap('rows');
  return {
    meta: decodeMeta(source.meta),
    facets: decodeFacets(source.facets),
    rows: source.rows.map(decodeCapabilityExplorerRow),
  };
}

function decodeNativeFacts(value: unknown): CapabilityExplorerNativeFacts {
  const source = object(value, 'entry.native_facts');
  const menu = object(source.menu, 'entry.native_facts.menu');
  const action = object(source.action, 'entry.native_facts.action');
  const module = object(source.module, 'entry.native_facts.module');
  const model = object(source.model, 'entry.native_facts.model');
  const views = object(source.views, 'entry.native_facts.views');
  const acl = object(source.acl, 'entry.native_facts.acl');
  const rules = object(source.record_rules, 'entry.native_facts.record_rules');
  return {
    menu: {
      xmlid: requiredText(menu.xmlid, 'entry.native_facts.menu.xmlid'),
      label: requiredText(menu.label, 'entry.native_facts.menu.label'),
      sequence: number(menu.sequence, 'entry.native_facts.menu.sequence'),
      path: strings(menu.path, 'entry.native_facts.menu.path'),
      group_xmlids: strings(menu.group_xmlids, 'entry.native_facts.menu.group_xmlids'),
    },
    action: {
      xmlid: requiredText(action.xmlid, 'entry.native_facts.action.xmlid'),
      type: requiredText(action.type, 'entry.native_facts.action.type'),
      view_modes: strings(action.view_modes, 'entry.native_facts.action.view_modes'),
      group_xmlids: strings(action.group_xmlids, 'entry.native_facts.action.group_xmlids'),
    },
    module: {
      name: requiredText(module.name, 'entry.native_facts.module.name'),
      state: requiredText(module.state, 'entry.native_facts.module.state'),
      version: text(module.version, 'entry.native_facts.module.version'),
      dependencies: strings(module.dependencies, 'entry.native_facts.module.dependencies'),
    },
    model: {
      name: text(model.name, 'entry.native_facts.model.name'),
      description: text(model.description, 'entry.native_facts.model.description'),
      exists: boolean(model.exists, 'entry.native_facts.model.exists'),
      field_count: number(model.field_count, 'entry.native_facts.model.field_count'),
    },
    views: {
      count: number(views.count, 'entry.native_facts.views.count'),
      sha256: text(views.sha256, 'entry.native_facts.views.sha256'),
    },
    acl: {
      row_count: number(acl.row_count, 'entry.native_facts.acl.row_count'),
      group_xmlids: strings(acl.group_xmlids, 'entry.native_facts.acl.group_xmlids'),
      sha256: text(acl.sha256, 'entry.native_facts.acl.sha256'),
    },
    record_rules: {
      count: number(rules.count, 'entry.native_facts.record_rules.count'),
      group_xmlids: strings(rules.group_xmlids, 'entry.native_facts.record_rules.group_xmlids'),
      sha256: text(rules.sha256, 'entry.native_facts.record_rules.sha256'),
    },
  };
}

function decodeScenarios(value: unknown): CapabilityExplorerScenarioUsage {
  const source = object(value, 'entry.scenario_usage');
  if (!Array.isArray(source.scenarios)) return gap('entry.scenario_usage.scenarios');
  return {
    bound: boolean(source.bound, 'entry.scenario_usage.bound'),
    ambiguous: boolean(source.ambiguous, 'entry.scenario_usage.ambiguous'),
    scenarios: source.scenarios.map((item, index) => {
      const row = object(item, `entry.scenario_usage.scenarios[${index}]`);
      return {
        scenario_key: requiredText(row.scenario_key, `entry.scenario_usage.scenarios[${index}].scenario_key`),
        scenario_name: requiredText(row.scenario_name, `entry.scenario_usage.scenarios[${index}].scenario_name`),
        scenario_active: boolean(row.scenario_active, `entry.scenario_usage.scenarios[${index}].scenario_active`),
        scenario_sequence: number(row.scenario_sequence, `entry.scenario_usage.scenarios[${index}].scenario_sequence`),
        sequence: number(row.sequence, `entry.scenario_usage.scenarios[${index}].sequence`),
        intent: text(row.intent, `entry.scenario_usage.scenarios[${index}].intent`),
      };
    }),
  };
}

function decodeRelease(value: unknown): CapabilityExplorerRelease {
  const source = object(value, 'entry.release');
  const snapshots = source.snapshots;
  if (!Array.isArray(snapshots)) return gap('entry.release.snapshots');
  return {
    state: requiredText(source.state, 'entry.release.state'),
    entry_published: boolean(source.entry_published, 'entry.release.entry_published'),
    center: nullableObject(source.center, 'entry.release.center'),
    blockers: strings(source.blockers, 'entry.release.blockers'),
    ambiguous_center: boolean(source.ambiguous_center, 'entry.release.ambiguous_center'),
    snapshots: snapshots.map((item, index) => object(item, `entry.release.snapshots[${index}]`)),
  };
}

export function decodeCapabilityExplorerDetailResponse(value: unknown): CapabilityExplorerDetailResponse {
  const source = object(value, 'response');
  const entry = object(source.entry, 'entry');
  const row = decodeCapabilityExplorerRow(entry);
  const assignment = object(entry.scene_assignment, 'entry.scene_assignment');
  const qualification = object(entry.qualification, 'entry.qualification');
  const diagnostics = object(entry.diagnostics, 'entry.diagnostics');
  const classification = object(entry.classification, 'entry.classification');
  if (!Array.isArray(classification.candidates)) return gap('entry.classification.candidates');
  return {
    meta: decodeBaseMeta(source.meta),
    entry: {
      ...row,
      native_facts: decodeNativeFacts(entry.native_facts),
      scenario_usage: decodeScenarios(entry.scenario_usage),
      release: decodeRelease(entry.release),
      scene_assignment: {
        assignable: boolean(assignment.assignable, 'entry.scene_assignment.assignable'),
        blockers: strings(assignment.blockers, 'entry.scene_assignment.blockers'),
      },
      qualification: {
        preview: requiredText(qualification.preview, 'entry.qualification.preview'),
        standard: requiredText(qualification.standard, 'entry.qualification.standard'),
      },
      diagnostics: {
        native_valid: boolean(diagnostics.native_valid, 'entry.diagnostics.native_valid'),
        native_blockers: strings(diagnostics.native_blockers, 'entry.diagnostics.native_blockers'),
        release_blockers: strings(diagnostics.release_blockers, 'entry.diagnostics.release_blockers'),
        blockers: strings(diagnostics.blockers, 'entry.diagnostics.blockers'),
        draft_selectable: boolean(diagnostics.draft_selectable, 'entry.diagnostics.draft_selectable'),
        scene_assignable: boolean(diagnostics.scene_assignable, 'entry.diagnostics.scene_assignable'),
        entry_published: boolean(diagnostics.entry_published, 'entry.diagnostics.entry_published'),
        preview_qualified: requiredText(diagnostics.preview_qualified, 'entry.diagnostics.preview_qualified'),
        standard_qualified: requiredText(diagnostics.standard_qualified, 'entry.diagnostics.standard_qualified'),
        classification_reason: text(diagnostics.classification_reason, 'entry.diagnostics.classification_reason'),
      },
      classification: {
        source: text(classification.source, 'entry.classification.source'),
        candidates: classification.candidates.map((item, index) => object(item, `entry.classification.candidates[${index}]`)),
        reason_code: text(classification.reason_code, 'entry.classification.reason_code'),
        center_source: text(classification.center_source, 'entry.classification.center_source'),
        native_center: nullableObject(classification.native_center, 'entry.classification.native_center'),
        release_center: nullableObject(classification.release_center, 'entry.classification.release_center'),
      },
    },
  };
}

export function decodeCapabilityExplorerDiagnosisResponse(value: unknown): CapabilityExplorerDiagnosisResponse {
  const source = object(value, 'response');
  const entryRef = object(source.entry_ref, 'entry_ref');
  return {
    meta: decodeBaseMeta(source.meta),
    entry_ref: {
      menu_xmlid: requiredText(entryRef.menu_xmlid, 'entry_ref.menu_xmlid'),
      action_xmlid: entryRef.action_xmlid === null ? null : requiredText(entryRef.action_xmlid, 'entry_ref.action_xmlid'),
    },
    native_valid: boolean(source.native_valid, 'native_valid'),
    draft_selectable: boolean(source.draft_selectable, 'draft_selectable'),
    scene_assignable: boolean(source.scene_assignable, 'scene_assignable'),
    entry_published: boolean(source.entry_published, 'entry_published'),
    preview_qualified: requiredText(source.preview_qualified, 'preview_qualified'),
    standard_qualified: requiredText(source.standard_qualified, 'standard_qualified'),
    blockers: strings(source.blockers, 'blockers'),
    classification_reason: text(source.classification_reason, 'classification_reason'),
    ...(source.native_facts === undefined ? {} : { native_facts: object(source.native_facts, 'native_facts') }),
    sections: object(source.sections, 'sections'),
  };
}

export async function fetchCapabilityExplorerList(params: CapabilityExplorerListParams) {
  const result = await intentRequest<unknown>({
    intent: 'platform.capability.explorer.list',
    params,
  });
  return decodeCapabilityExplorerListResponse(result);
}

export async function fetchCapabilityExplorerDetail(params: {
  entry_ref: CapabilityExplorerRow['entry_ref'];
  expected_catalog_token: string;
}) {
  const result = await intentRequest<unknown>({
    intent: 'platform.capability.explorer.detail',
    params,
  });
  return decodeCapabilityExplorerDetailResponse(result);
}

export async function fetchCapabilityExplorerDiagnose(params: {
  entry_ref?: CapabilityExplorerRow['entry_ref'];
  menu_xmlid?: string;
  action_xmlid?: string;
  expected_catalog_token: string;
}) {
  const result = await intentRequest<unknown>({
    intent: 'platform.capability.explorer.diagnose',
    params,
  });
  return decodeCapabilityExplorerDiagnosisResponse(result);
}
