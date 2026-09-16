import type {
  CanonicalFormNode,
  CanonicalFormPresentationMode,
  CanonicalFormSemanticRole,
} from '../../app/presentation/canonicalFormRenderModel';
import { fieldIsBusinessRelationCollection } from '../../app/presentation/canonicalFormFloorplan';
import { canonicalNodeHasContent } from './canonicalFormRenderer';
import {
  collectNativeBusinessSections,
  governedFormStructureSectionIdentity,
  nativeBusinessSectionIdentity,
} from './nativeBusinessSection';

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

export type VisibleSectionPosition = {
  key: string;
  top: number;
};

export type ActivatedSectionFallback = {
  preferredKey: string;
  visibleBottom: number;
};

export function activeSectionKeyAtAnchor(
  positions: VisibleSectionPosition[],
  anchor: number,
  activatedFallback?: ActivatedSectionFallback,
): string {
  if (!positions.length) return '';
  const anchoredKey = positions.reduce(
    (current, position) => (position.top <= anchor ? position.key : current),
    positions[0].key,
  );
  const preferred = activatedFallback
    ? positions.find((position) => position.key === activatedFallback.preferredKey)
    : undefined;
  if (
    preferred
    && preferred.top > anchor
    && preferred.top < activatedFallback!.visibleBottom
  ) return preferred.key;
  return anchoredKey;
}

export function sectionScrollDelta(
  targetTop: number,
  anchor: number,
  tolerance = 1,
): number {
  const delta = targetTop - anchor;
  return Math.abs(delta) <= tolerance ? 0 : delta;
}

export function sectionRevealTargetsContain(value: unknown, targetKey: string): boolean {
  if (typeof value !== 'string' || !targetKey) return false;
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) && parsed.some((candidate) => candidate === targetKey);
  } catch {
    return false;
  }
}

type NativeSectionAuthorityNode = {
  attributes?: Record<string, unknown>;
  sourceAuthority?: Record<string, unknown>;
  source_authority?: Record<string, unknown>;
};

export function nativeSectionNavigationRole(node: NativeSectionAuthorityNode): NativeSectionNavigationRole {
  const explicitRole = String(
    node?.attributes?.['data-sc-navigation-role']
    || node?.attributes?.sectionNavigationRole
    || '',
  ).trim().toLowerCase();
  if (explicitRole === 'subordinate') return 'subordinate';
  if (explicitRole === 'primary') return 'primary';
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

  authoritativeNativeBusinessSections(nodes).forEach(({ node, identity }) => {
    if (identity && nativeSectionNavigationRole(node) === 'primary' && !emittedAnchors.has(identity.anchor)) {
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
  if (authoritativeItems.length) {
    // A configured section owns its descendants, not unrelated notebooks.
    // Retain collection navigation outside those sections without duplicating
    // collections already reached through an authoritative section anchor.
    const unowned = (rows: CanonicalFormNode[], insideNotebook = false): CanonicalFormNode[] => rows.flatMap((node) => {
      if (nativeBusinessSectionIdentity(node)) return [];
      const inNotebook = insideNotebook || node.kind === 'notebook';
      return [{ ...node, fields: inNotebook ? node.fields : [], children: unowned(node.children, inNotebook) }];
    });
    return [...authoritativeItems, ...relationshipCollectionNavigationItems(unowned(nodes))];
  }

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

export function authoritativeNativeBusinessSections(nodes: CanonicalFormNode[]) {
  return collectNativeBusinessSections(nodes, {
    childrenOf: (node) => node.children,
    isVisible: canonicalNodeHasContent,
  });
}

export function governedFormStructureSectionNavigationItems(
  nodes: CanonicalFormNode[],
): WorkspaceSectionNavigationItem[] {
  const items: WorkspaceSectionNavigationItem[] = [];
  const emitted = new Set<string>();

  function visit(node: CanonicalFormNode) {
    if (!node.visible) return;
    const identity = governedFormStructureSectionIdentity(node) || nativeBusinessSectionIdentity(node);
    if (identity && !emitted.has(identity.anchor)) {
      items.push({
        key: identity.anchor,
        label: identity.label,
        selector: selectorFor(identity.anchor),
        role: node.semanticRole || 'context',
        contentKind: 'semantic-section',
        sourceType: 'node',
        sourceIdentity: node.nodeId,
      });
      emitted.add(identity.anchor);
      return;
    }
    node.children.forEach(visit);
  }

  nodes.forEach(visit);
  return items;
}

/**
 * A task contract still owns task actions and workflow presentation, but an
 * explicitly anchored native business section remains the structural
 * authority for its body. This is deliberately opt-in: unanchored layout
 * groups continue through the ordinary task floorplan classification.
 */
export function shouldPreserveAuthoritativeBusinessSections(
  presentationMode: CanonicalFormPresentationMode,
  nodes: CanonicalFormNode[],
): boolean {
  if (presentationMode !== 'task') return false;
  const sections = authoritativeNativeBusinessSections(nodes);
  if (!sections.length) return false;

  // A native anchor declares authority for that section, not automatically
  // for every sibling in the form.  Only switch the whole body to the native
  // section renderer when every visible, non-notebook business field is owned
  // by an anchored section.  Otherwise the anchors are embedded into the task
  // floorplan and the remaining native fields keep their existing projection.
  function hasUnownedBusinessField(node: CanonicalFormNode, insideSection = false, insideNotebook = false): boolean {
    if (!node.visible) return false;
    const kind = String(node.kind || '').trim().toLowerCase();
    const functionalContainer = ['header', 'statusbar', 'button_box', 'chatter', 'activity', 'attachment'].includes(kind);
    if (functionalContainer || insideNotebook || kind === 'notebook') return false;
    const ownsSection = insideSection || Boolean(nativeBusinessSectionIdentity(node));
    if (ownsSection) return false;
    if (node.fields.some((field) => field.visible)) return true;
    return node.children.some((child) => hasUnownedBusinessField(child, false, false));
  }

  return !nodes.some((node) => hasUnownedBusinessField(node));
}

export function relationshipCollectionNavigationItems(
  nodes: CanonicalFormNode[],
  presentable: (field: CanonicalFormNode['fields'][number]) => boolean = () => true,
): WorkspaceSectionNavigationItem[] {
  const items: WorkspaceSectionNavigationItem[] = [];
  const candidates = new Map<string, CanonicalFormNode['fields'][number]>();

  function semanticRegion(slot: unknown, group: unknown): string {
    const normalizedSlot = String(slot || '').trim();
    const normalizedGroup = String(group || '').trim();
    return normalizedSlot && normalizedGroup ? `structure:${normalizedSlot}:${normalizedGroup}` : '';
  }

  function occurrenceScore(field: CanonicalFormNode['fields'][number]) {
    const descriptor = field.fieldDescriptor && typeof field.fieldDescriptor === 'object'
      ? field.fieldDescriptor as Record<string, unknown>
      : {};
    const config = field.componentConfig && typeof field.componentConfig === 'object'
      ? field.componentConfig as Record<string, unknown>
      : {};
    const subview = descriptor.subview || config.subview;
    const hasStructuredSubview = Boolean(subview && typeof subview === 'object' && !Array.isArray(subview));
    const widget = String(config.nativeWidget || config.widget || field.widgetType || '').trim().toLowerCase();
    return (hasStructuredSubview ? 20 : 0)
      + (field.fieldType.trim().toLowerCase() === 'one2many' ? 10 : 0)
      + (widget === 'many2many_tags' ? -1 : 0);
  }

  function visit(
    node: CanonicalFormNode,
    inheritedRegion = '',
    inheritedBusinessRegion = '',
  ) {
    if (!node.visible) return;
    const businessSection = nativeBusinessSectionIdentity(node);
    const businessRegion = businessSection
      ? `business:${businessSection.anchor}`
      : inheritedBusinessRegion;
    const nodeRegion = businessRegion
      || semanticRegion(node.semanticSlot, node.semanticGroup)
      || inheritedRegion;
    node.fields.filter((field) => (
      field.visible && fieldIsBusinessRelationCollection(field) && presentable(field)
    )).forEach((field) => {
      const fieldRegion = businessRegion
        || semanticRegion(field.semanticSlot, field.semanticGroup)
        || nodeRegion
        || 'page';
      const fieldIdentity = String(field.fieldCode || field.widgetId).trim() || field.widgetId;
      const identity = `${fieldRegion}\u0000${fieldIdentity}`;
      const current = candidates.get(identity);
      if (!current || occurrenceScore(field) > occurrenceScore(current)) candidates.set(identity, field);
    });
    node.children.forEach((child) => visit(child, nodeRegion, businessRegion));
  }

  nodes.forEach((node) => visit(node));
  candidates.forEach((field) => {
    const key = `field:${field.widgetId}:relation`;
    items.push({
      key,
      label: String(field.label || '关系明细').trim() || '关系明细',
      selector: selectorFor(key),
      role: 'relation',
      contentKind: 'relation-collection',
      sourceType: 'field',
      sourceIdentity: field.widgetId,
    });
  });
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
