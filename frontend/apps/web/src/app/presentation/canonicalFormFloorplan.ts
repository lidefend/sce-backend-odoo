import type {
  CanonicalFormAction,
  CanonicalFormNode,
  CanonicalFormRenderModel,
  CanonicalFormSemanticRole,
} from './canonicalFormRenderModel';

export type CanonicalFormFloorplan = {
  summaryNodes: CanonicalFormNode[];
  taskNodes: CanonicalFormNode[];
  contextNodes: CanonicalFormNode[];
  overflowContextNodes: CanonicalFormNode[];
  riskNodes: CanonicalFormNode[];
  auditNodes: CanonicalFormNode[];
  auditDeclared: boolean;
  relationNodes: CanonicalFormNode[];
  subordinateNodes: CanonicalFormNode[];
  blockedActions: CanonicalFormAction[];
  directActions: CanonicalFormAction[];
  overflowActions: CanonicalFormAction[];
  effectivePrimaryKey: string;
  decisionMode: boolean;
};

function hasEditableField(node: CanonicalFormNode): boolean {
  return node.fields.some((field) => field.visible && !field.readonly && !field.disabled)
    || node.children.some(hasEditableField);
}

function hasPresentableValue(field: CanonicalFormNode['fields'][number]): boolean {
  if (field.fieldType.trim().toLowerCase() === 'boolean') return true;
  if (field.value === null || field.value === undefined || field.value === false) return false;
  if (typeof field.value === 'string') return field.value.trim().length > 0;
  if (Array.isArray(field.value)) return field.value.length > 0;
  if (typeof field.value === 'object') {
    const relation = field.value as { displayName?: unknown };
    if (Object.prototype.hasOwnProperty.call(relation, 'displayName')) {
      return String(relation.displayName || '').trim().length > 0;
    }
    return Object.keys(field.value).length > 0;
  }
  return true;
}

function nodeHasContent(node: CanonicalFormNode): boolean {
  if (!node.visible) return false;
  if (node.fields.some((field) => field.visible)) return true;
  if (['chatter', 'activity', 'attachment'].includes(node.kind.trim().toLowerCase())) return true;
  return node.children.some(nodeHasContent);
}

function createReadyNode(node: CanonicalFormNode): CanonicalFormNode {
  return {
    ...node,
    fields: node.fields.filter((field) => (
      !field.visible
      || !field.readonly
      || field.required
      || Boolean(field.reasonCode)
      || hasPresentableValue(field)
    )),
    children: node.children.map(createReadyNode),
  };
}

function nodeHasSemanticRole(node: CanonicalFormNode): boolean {
  return ['summary', 'task', 'context', 'risk', 'audit'].includes(node.semanticRole)
    || node.fields.some((field) => ['summary', 'task', 'context', 'risk', 'audit'].includes(field.semanticRole))
    || node.children.some(nodeHasSemanticRole);
}

function nodeDeclaresRole(node: CanonicalFormNode, role: CanonicalFormSemanticRole): boolean {
  return node.semanticRole === role
    || node.fields.some((field) => field.semanticRole === role)
    || node.children.some((child) => nodeDeclaresRole(child, role));
}

function projectNodeRoles(
  node: CanonicalFormNode,
  roles: ReadonlySet<CanonicalFormSemanticRole>,
  includeUnassigned = false,
  onlyPresentable = false,
  suppressTitles = false,
  inheritedRole = '',
): CanonicalFormNode {
  const effectiveNodeRole = node.semanticRole || inheritedRole;
  const nodeTextBelongsToProjection = roles.has(effectiveNodeRole as CanonicalFormSemanticRole)
    || (includeUnassigned && !effectiveNodeRole);
  return {
    ...node,
    ...(suppressTitles ? { title: '' } : {}),
    text: nodeTextBelongsToProjection ? node.text : '',
    fields: node.fields.filter((field) => {
      const effectiveFieldRole = field.semanticRole || effectiveNodeRole;
      return (
        (roles.has(effectiveFieldRole as CanonicalFormSemanticRole)
          || (includeUnassigned && !effectiveFieldRole))
        && (!onlyPresentable || hasPresentableValue(field))
      );
    }),
    children: node.children.map((child) => projectNodeRoles(
      child, roles, includeUnassigned, onlyPresentable, suppressTitles, effectiveNodeRole,
    )),
  };
}

function roleNodes(
  nodes: CanonicalFormNode[],
  roles: CanonicalFormSemanticRole[],
  includeUnassigned = false,
  onlyPresentable = false,
  suppressTitles = false,
): CanonicalFormNode[] {
  const roleSet = new Set(roles);
  return nodes
    .map((node) => projectNodeRoles(node, roleSet, includeUnassigned, onlyPresentable, suppressTitles))
    .filter(nodeHasContent);
}

function visibleFieldCount(node: CanonicalFormNode): number {
  return node.fields.filter((field) => field.visible).length
    + node.children.reduce((total, child) => total + visibleFieldCount(child), 0);
}

function nodeHasRelationCapability(node: CanonicalFormNode): boolean {
  const kind = node.kind.trim().toLowerCase();
  return ['notebook', 'relation'].includes(kind)
    || node.semanticRole === 'relation'
    || node.fields.some((field) => (
      field.semanticRole === 'relation'
      || ['one2many', 'many2many'].includes(field.fieldType.trim().toLowerCase())
    ))
    || node.children.some(nodeHasRelationCapability);
}

function fieldHasRelationCapability(field: CanonicalFormNode['fields'][number]): boolean {
  return field.semanticRole === 'relation'
    || ['one2many', 'many2many'].includes(field.fieldType.trim().toLowerCase());
}

function projectRelationNode(node: CanonicalFormNode): CanonicalFormNode {
  const directRelation = node.semanticRole === 'relation' || node.kind.trim().toLowerCase() === 'relation';
  if (directRelation) return node;
  return {
    ...node,
    fields: node.fields.filter(fieldHasRelationCapability),
    children: node.children.map(projectRelationNode).filter(nodeHasContent),
  };
}

function relationRoleNodes(nodes: CanonicalFormNode[]): CanonicalFormNode[] {
  return nodes.map(projectRelationNode).filter(nodeHasContent);
}

function projectContextNode(node: CanonicalFormNode): CanonicalFormNode {
  const nodeKind = node.kind.trim().toLowerCase();
  if ((node.semanticRole && !['context', 'activity'].includes(node.semanticRole)) || nodeKind === 'relation') {
    return { ...node, fields: [], children: [] };
  }
  return {
    ...node,
    fields: node.fields.filter((field) => (
      !fieldHasRelationCapability(field)
      && (!field.semanticRole || ['context', 'activity'].includes(field.semanticRole))
    )),
    children: node.children.map(projectContextNode),
  };
}

function contextRoleNodes(nodes: CanonicalFormNode[]): CanonicalFormNode[] {
  return nodes.map(projectContextNode).filter(nodeHasContent);
}

function flattenPresentableFields(nodes: CanonicalFormNode[], region: string): CanonicalFormNode[] {
  const projected: CanonicalFormNode[] = [];
  const seenFields = new Set<string>();
  function visit(node: CanonicalFormNode) {
    node.fields.filter((field) => field.visible && hasPresentableValue(field)).forEach((field) => {
      const fieldIdentity = String(field.fieldCode || field.widgetId).trim();
      if (fieldIdentity && seenFields.has(fieldIdentity)) return;
      if (fieldIdentity) seenFields.add(fieldIdentity);
      projected.push({
        ...node,
        nodeId: `${node.nodeId}.${region}.${field.widgetId}`,
        title: '',
        columns: 1,
        fields: [field],
        children: [],
      });
    });
    node.children.forEach(visit);
  }
  nodes.forEach(visit);
  return projected;
}

function allVisibleFieldsPresentable(node: CanonicalFormNode): boolean {
  return node.fields.every((field) => !field.visible || hasPresentableValue(field))
    && node.children.every(allVisibleFieldsPresentable);
}

function partitionContextBlocks(nodes: CanonicalFormNode[], limit: number) {
  const direct: CanonicalFormNode[] = [];
  const overflow: CanonicalFormNode[] = [];
  let count = 0;
  let overflowStarted = false;
  nodes.forEach((node) => {
    const blockCount = visibleFieldCount(node);
    if (!overflowStarted && blockCount > 0 && allVisibleFieldsPresentable(node) && count + blockCount <= limit) {
      direct.push(node);
      count += blockCount;
    } else {
      overflowStarted = true;
      overflow.push(node);
    }
  });
  return { direct, overflow };
}

function splitOversizedContextBlocks(nodes: CanonicalFormNode[], limit: number): CanonicalFormNode[] {
  return nodes.flatMap((node) => {
    const ownVisibleFields = node.fields.some((field) => field.visible);
    if (visibleFieldCount(node) <= limit || ownVisibleFields || !node.children.length) return [node];
    return splitOversizedContextBlocks(node.children.filter(nodeHasContent), limit);
  });
}

function visibleNodes(nodes: CanonicalFormNode[], mode: CanonicalFormRenderModel['identity']['mode']): CanonicalFormNode[] {
  return nodes
    .map((node) => mode === 'create' ? createReadyNode(node) : node)
    .filter((node) => node.visible && nodeHasContent(node));
}

/**
 * Pure, ephemeral floorplan projection. It groups canonical nodes without
 * changing field/action identity, visibility, authority, order, or values.
 */
export function composeCanonicalFormFloorplan(
  renderModel: CanonicalFormRenderModel,
): CanonicalFormFloorplan {
  const primaryNodes = visibleNodes(renderModel.zones.primary, renderModel.identity.mode);
  const editableNodes = primaryNodes.filter(hasEditableField);
  const semanticReadonly = renderModel.identity.mode === 'readonly' && primaryNodes.some(nodeHasSemanticRole);
  const summaryNodes = semanticReadonly
    ? flattenPresentableFields(roleNodes(primaryNodes, ['summary'], false, true, true), 'summary')
    : [];
  const riskNodes = semanticReadonly ? roleNodes(primaryNodes, ['risk'], false, true, true) : [];
  const auditNodes = semanticReadonly ? roleNodes(primaryNodes, ['audit'], false, false, true) : [];
  const auditDeclared = semanticReadonly && primaryNodes.some((node) => nodeDeclaresRole(node, 'audit'));
  const taskNodes = semanticReadonly
    ? roleNodes(primaryNodes, ['task'], false, true, true)
    : (editableNodes.length ? editableNodes : primaryNodes);
  const taskIds = new Set(taskNodes.map((node) => node.nodeId));
  const subordinateNodes = visibleNodes(renderModel.zones.subordinate, renderModel.identity.mode);
  const primaryRelationNodes = semanticReadonly ? relationRoleNodes(primaryNodes.filter(nodeHasRelationCapability)) : [];
  const subordinateRelationNodes = semanticReadonly ? relationRoleNodes(subordinateNodes.filter(nodeHasRelationCapability)) : [];
  const relationNodes = [...primaryRelationNodes, ...subordinateRelationNodes];
  const allContextNodes = semanticReadonly
    ? contextRoleNodes(primaryNodes)
    : primaryNodes.filter((node) => !taskIds.has(node.nodeId));
  const emptySemanticNodes = semanticReadonly
    ? roleNodes(primaryNodes, ['summary', 'task', 'risk'], false, false, true)
      .map((node) => ({
        ...node,
        fields: node.fields.filter((field) => !hasPresentableValue(field)),
        children: node.children.map(function emptyOnly(child): CanonicalFormNode {
          return {
            ...child,
            fields: child.fields.filter((field) => !hasPresentableValue(field)),
            children: child.children.map(emptyOnly),
          };
        }),
      }))
      .filter(nodeHasContent)
    : [];
  const contextPartition = semanticReadonly
    ? partitionContextBlocks(splitOversizedContextBlocks(allContextNodes, 24), 24)
    : { direct: allContextNodes, overflow: [] };
  const visibleActions = renderModel.actionBar.filter((action) => action.visible);
  const canonicalPrimary = visibleActions.find((action) => action.tier === 'primary');
  const createSave = renderModel.identity.mode === 'create' && !canonicalPrimary
    ? visibleActions.find((action) => action.enabled && action.actionRef.actionId === 'form.save')
    : undefined;
  const effectivePrimary = canonicalPrimary?.enabled ? canonicalPrimary : createSave;
  const secondaryCandidates = visibleActions.filter((action) => (
    action.enabled
    && action !== effectivePrimary
    && !['overflow', 'configuration'].includes(action.tier)
  ));
  const directSecondary = renderModel.identity.mode === 'create' ? [] : secondaryCandidates.slice(0, 1);
  const directActions = [...(effectivePrimary ? [effectivePrimary] : []), ...directSecondary];
  const blockedActions = visibleActions.filter((action) => !action.enabled && action.tier === 'primary');

  return {
    summaryNodes,
    taskNodes,
    contextNodes: contextPartition.direct,
    overflowContextNodes: [...contextPartition.overflow, ...emptySemanticNodes],
    riskNodes,
    auditNodes,
    auditDeclared,
    relationNodes,
    subordinateNodes: semanticReadonly
      ? subordinateNodes.filter((node) => !nodeHasRelationCapability(node))
      : subordinateNodes,
    blockedActions,
    directActions,
    overflowActions: visibleActions.filter((action) => (
      !directActions.includes(action) && !blockedActions.includes(action)
    )),
    effectivePrimaryKey: effectivePrimary?.key || '',
    decisionMode: semanticReadonly,
  };
}
