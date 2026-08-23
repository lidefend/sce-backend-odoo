import type { ContractV2Dictionary } from './types';

const LEGACY_ROLE_TO_CANONICAL = Object.freeze({
  summary: 'summary', task: 'task', context: 'context', risk: 'risk', relation: 'relation', activity: 'activity', audit: 'audit',
  overview: 'summary', identity: 'context', term: 'context', fact: 'context', amount: 'context', status_or_date: 'context',
  collaboration: 'activity', detail: 'relation', provenance: 'audit', history_check: 'audit', business_fact: 'context',
  configured_field: 'context', configured_form: 'task', configured_field_group: 'task', facts: 'context', relations: 'relation',
  terms: 'context', other_facts: 'context', progress: 'context', amounts: 'context', status_dates: 'context', details: 'relation',
  business_category_section: 'task', business_category_fields: 'context',
} as const);

function isRecord(value: unknown): value is ContractV2Dictionary {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function canonicalLegacyRole(value: unknown): string {
  return LEGACY_ROLE_TO_CANONICAL[text(value) as keyof typeof LEGACY_ROLE_TO_CANONICAL] || text(value);
}

function normalizeRoleCarrier(value: unknown): void {
  if (!isRecord(value) || value.role === undefined) return;
  value.role = canonicalLegacyRole(value.role);
}

function synthesizeLegacyWidget(node: ContractV2Dictionary, ownerContainerId: string): ContractV2Dictionary | null {
  if (text(node.type || node.containerType).toLowerCase() !== 'field') return null;
  const fieldInfo = isRecord(node.fieldInfo) ? node.fieldInfo : {};
  const fieldCode = text(node.name || node.fieldCode || fieldInfo.name);
  const widgetId = text(node.widgetId) || (fieldCode ? `field.${fieldCode}` : '');
  if (!fieldCode || !widgetId) return null;
  const componentConfig = isRecord(node.componentConfig) ? node.componentConfig : {};
  const fieldType = text(fieldInfo.type || fieldInfo.ttype || componentConfig.fieldType);
  return {
    widgetId,
    widgetType: text(node.widget || fieldInfo.widget || fieldType) || 'display',
    fieldCode,
    label: text(node.label || node.string || fieldInfo.label || fieldInfo.string) || fieldCode,
    span: typeof node.span === 'number' ? node.span : 24,
    componentKey: text(node.componentKey || fieldInfo.componentKey) || 'sc.display.text',
    capabilities: [],
    componentConfig,
    ownerContainerId,
    ...(isRecord(node.fieldInfo) ? { fieldDescriptor: node.fieldInfo } : {}),
    ...(fieldType ? { fieldType } : {}),
    ...(text(node.nativeLocator) ? { nativeLocator: text(node.nativeLocator) } : {}),
    ...(typeof node.occurrenceIndex === 'number' ? { occurrenceIndex: node.occurrenceIndex } : {}),
    ...(typeof node.sourcePosition === 'number' ? { sourcePosition: node.sourcePosition } : {}),
  };
}

function collectLegacyWidgetIds(rows: unknown, out = new Set<string>()): Set<string> {
  if (!Array.isArray(rows)) return out;
  rows.forEach((value) => {
    if (!isRecord(value)) return;
    if (Array.isArray(value.widgetList)) value.widgetList.forEach((widget) => {
      if (isRecord(widget) && text(widget.widgetId)) out.add(text(widget.widgetId));
    });
    for (const key of ['children', 'pages', 'tabs', 'nodes', 'items'] as const) {
      collectLegacyWidgetIds(value[key], out);
    }
  });
  return out;
}

function normalizeLegacyNodes(rows: unknown, knownWidgetIds: Set<string>): void {
  if (!Array.isArray(rows)) return;
  rows.forEach((value) => {
    if (!isRecord(value)) return;
    const node = value;
    const childKeys = ['children', 'pages', 'tabs', 'nodes', 'items'] as const;
    if (childKeys.some((key) => node[key] !== undefined && !Array.isArray(node[key]))) {
      // Compatibility applies only to structurally valid legacy carriers. Leave
      // malformed values intact so the strict production decoder rejects them.
      return;
    }
    const containerId = text(node.containerId || node.widgetId || node.nativeLocator || node.name);
    if (containerId) node.containerId = containerId;
    const childRows: unknown[] = [];
    for (const key of childKeys) {
      if (Array.isArray(node[key])) childRows.push(...node[key] as unknown[]);
    }
    node.children = childRows;
    delete node.pages;
    delete node.tabs;
    delete node.nodes;
    delete node.items;
    if (node.widgetList === undefined) node.widgetList = [];
    normalizeRoleCarrier(node.formStructureRole);
    normalizeLegacyNodes(node.children, knownWidgetIds);
    const children = Array.isArray(node.children) ? node.children.filter(isRecord) : [];
    const fieldOwnerByWidgetId = new Map<string, string>();
    children.forEach((child) => {
      if (text(child.type || child.containerType).toLowerCase() !== 'field') return;
      const childWidgetId = text(child.widgetId);
      const childOwner = text(child.containerId);
      if (childWidgetId && childOwner) fieldOwnerByWidgetId.set(childWidgetId, childOwner);
    });
    if (Array.isArray(node.widgetList)) {
      node.widgetList.forEach((widget) => {
        if (!isRecord(widget)) return;
        const widgetId = text(widget.widgetId);
        if (!text(widget.ownerContainerId)) {
          widget.ownerContainerId = fieldOwnerByWidgetId.get(widgetId) || containerId;
        }
        normalizeRoleCarrier(widget.formStructureRole);
      });
    }
    if (text(node.type || node.containerType).toLowerCase() === 'field'
        && Array.isArray(node.widgetList) && node.widgetList.length === 0) {
      const synthesized = synthesizeLegacyWidget(node, containerId);
      const widgetId = synthesized ? text(synthesized.widgetId) : '';
      if (synthesized && widgetId && !knownWidgetIds.has(widgetId)) {
        node.widgetList.push(synthesized);
        knownWidgetIds.add(widgetId);
      }
    }
  });
}

function normalizeLegacyFormStructure(root: ContractV2Dictionary): void {
  const structure = root.formStructureContract;
  if (!isRecord(structure)) return;
  if (Array.isArray(structure.slots)) {
    structure.slots.forEach((slot) => {
      if (!isRecord(slot)) return;
      normalizeRoleCarrier(slot);
      if (Array.isArray(slot.groups)) slot.groups.forEach(normalizeRoleCarrier);
    });
  }
  if (isRecord(structure.fieldRoles)) Object.values(structure.fieldRoles).forEach(normalizeRoleCarrier);
}

export function normalizeLegacyContractV2Snapshot(value: unknown): unknown {
  if (!isRecord(value)) return value;
  const pageInfo = isRecord(value.pageInfo) ? value.pageInfo : {};
  const version = text(pageInfo.contractVersion);
  if (!/^2\.(0|1)\./.test(version)) return value;
  const normalized = structuredClone(value);
  const layout = isRecord(normalized.layoutContract) ? normalized.layoutContract : {};
  normalizeLegacyNodes(layout.containerTree, collectLegacyWidgetIds(layout.containerTree));
  normalizeLegacyFormStructure(normalized);
  return normalized;
}
