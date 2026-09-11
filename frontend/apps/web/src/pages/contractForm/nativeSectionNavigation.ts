import type {
  CanonicalFormNode,
  CanonicalFormSemanticRole,
} from '../../app/presentation/canonicalFormRenderModel';
import { fieldIsBusinessRelationCollection } from '../../app/presentation/canonicalFormFloorplan';
import { collectNativeBusinessSections } from './nativeBusinessSection';

export type NativeSectionNavigationRole = 'primary' | 'subordinate';

export type WorkspaceSectionNavigationItem = {
  key: string;
  label: string;
  selector: string;
  role: CanonicalFormSemanticRole;
  contentKind: 'semantic-section' | 'relation-collection' | 'collaboration-panel' | 'audit-timeline';
  sourceType: 'node' | 'field' | 'surface';
  sourceIdentity: string;
};

type NativeSectionAuthorityNode = {
  sourceAuthority?: Record<string, unknown>;
  source_authority?: Record<string, unknown>;
};

export function nativeSectionNavigationRole(node: NativeSectionAuthorityNode): NativeSectionNavigationRole {
  const authority = node?.sourceAuthority || node?.source_authority || {};
  const projectionOnly = authority.projection_only === true || authority.projectionOnly === true;
  const noBusinessAuthority = authority.no_business_fact_authority === true
    || authority.noBusinessFactAuthority === true;
  return projectionOnly && noBusinessAuthority ? 'subordinate' : 'primary';
}

type BusinessActionCandidate = { label?: string; enabled?: boolean };

export function nextBusinessActionLabel(
  primary: BusinessActionCandidate | null | undefined,
  direct: BusinessActionCandidate[],
): string {
  const candidate = primary?.enabled !== false
    ? primary
    : (direct || []).find((action) => action?.enabled !== false);
  return String(candidate?.label || '').trim();
}

const SECTION_LABELS: Partial<Record<CanonicalFormSemanticRole, string>> = {
  summary: '概览',
  task: '办理信息',
  context: '基本资料',
  risk: '风险与提示',
};

function normalizedKind(node: CanonicalFormNode): string {
  return String(node.kind || '').trim().toLowerCase();
}

function selectorFor(key: string): string {
  return `[data-form-section-target="${key.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"]`;
}

export function workspaceSectionNavigationItems(nodes: CanonicalFormNode[]): WorkspaceSectionNavigationItem[] {
  const authoritativeItems: WorkspaceSectionNavigationItem[] = [];
  const emittedAnchors = new Set<string>();

  collectNativeBusinessSections(nodes, {
    childrenOf: (node) => node.children,
    isVisible: (node) => node.visible,
  }).forEach(({ node, identity }) => {
    if (identity && !emittedAnchors.has(identity.anchor)) {
      authoritativeItems.push({
        key: `node:${node.nodeId}:business-section`,
        label: identity.label,
        selector: selectorFor(`node:${node.nodeId}:business-section`),
        role: node.semanticRole || 'context',
        contentKind: 'semantic-section',
        sourceType: 'node',
        sourceIdentity: node.nodeId,
      });
      emittedAnchors.add(identity.anchor);
    }
  });
  if (authoritativeItems.length) return authoritativeItems;

  const items: WorkspaceSectionNavigationItem[] = [];
  const emittedRoles = new Set<CanonicalFormSemanticRole>();

  function visit(node: CanonicalFormNode, inheritedRole: CanonicalFormSemanticRole | '' = '') {
    if (!node.visible) return;
    const role = node.semanticRole;
    const kind = normalizedKind(node);
    const label = SECTION_LABELS[role];
    if (kind !== 'field' && label && role !== inheritedRole && !emittedRoles.has(role)) {
      const key = `node:${node.nodeId}:${role}`;
      items.push({
        key,
        label,
        selector: selectorFor(key),
        role,
        contentKind: 'semantic-section',
        sourceType: 'node',
        sourceIdentity: node.nodeId,
      });
      emittedRoles.add(role);
    }
    node.children.forEach((child) => visit(child, role || inheritedRole));
  }

  nodes.forEach((node) => visit(node));
  return [...items, ...relationshipCollectionNavigationItems(nodes)];
}

export function relationshipCollectionNavigationItems(
  nodes: CanonicalFormNode[],
  presentable: (field: CanonicalFormNode['fields'][number]) => boolean = () => true,
): WorkspaceSectionNavigationItem[] {
  const items: WorkspaceSectionNavigationItem[] = [];
  const emittedFields = new Set<string>();

  function visit(node: CanonicalFormNode) {
    if (!node.visible) return;
    node.fields.filter((field) => (
      field.visible && fieldIsBusinessRelationCollection(field) && presentable(field)
    )).forEach((field) => {
      if (emittedFields.has(field.widgetId)) return;
      const key = `field:${field.widgetId}:relation`;
      items.push({
        key,
        label: String(field.label || node.title || '关系明细').trim() || '关系明细',
        selector: selectorFor(key),
        role: 'relation',
        contentKind: 'relation-collection',
        sourceType: 'field',
        sourceIdentity: field.widgetId,
      });
      emittedFields.add(field.widgetId);
    });
    node.children.forEach(visit);
  }

  nodes.forEach(visit);
  return items;
}

export function workspaceSurfaceNavigationItems(input: {
  collaborationAvailable: boolean;
  auditAvailable: boolean;
}): WorkspaceSectionNavigationItem[] {
  const items: WorkspaceSectionNavigationItem[] = [];
  if (input.collaborationAvailable) items.push({
    key: 'surface:activity',
    label: '协作记录',
    selector: '[data-form-section-target="surface:activity"]',
    role: 'activity',
    contentKind: 'collaboration-panel',
    sourceType: 'surface',
    sourceIdentity: 'collaboration-panel',
  });
  if (input.auditAvailable) items.push({
    key: 'surface:audit',
    label: '历史审计',
    selector: '[data-form-section-target="surface:audit"]',
    role: 'audit',
    contentKind: 'audit-timeline',
    sourceType: 'surface',
    sourceIdentity: 'professional-audit-timeline',
  });
  return items;
}
