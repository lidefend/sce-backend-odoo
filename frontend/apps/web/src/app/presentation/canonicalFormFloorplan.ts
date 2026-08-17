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
  subordinateNodes: CanonicalFormNode[];
  blockedActions: CanonicalFormAction[];
  directActions: CanonicalFormAction[];
  overflowActions: CanonicalFormAction[];
  effectivePrimaryKey: string;
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

function projectNodeRoles(
  node: CanonicalFormNode,
  roles: ReadonlySet<CanonicalFormSemanticRole>,
  includeUnassigned = false,
  onlyPresentable = false,
  suppressTitles = false,
): CanonicalFormNode {
  const nodeRoleMatches = roles.has(node.semanticRole as CanonicalFormSemanticRole);
  const nodeRoleExcludes = Boolean(node.semanticRole) && !nodeRoleMatches;
  if (nodeRoleMatches) {
    return {
      ...node,
      ...(suppressTitles ? { title: '' } : {}),
    };
  }
  if (nodeRoleExcludes) {
    return { ...node, fields: [], children: [] };
  }
  return {
    ...node,
    ...(suppressTitles ? { title: '' } : {}),
    fields: node.fields.filter((field) => (
      (roles.has(field.semanticRole as CanonicalFormSemanticRole)
        || (includeUnassigned && !field.semanticRole))
      && (!onlyPresentable || hasPresentableValue(field))
    )),
    children: node.children.map((child) => projectNodeRoles(
      child, roles, includeUnassigned, onlyPresentable, suppressTitles,
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
  const summaryNodes = semanticReadonly ? roleNodes(primaryNodes, ['summary'], false, true, true) : [];
  const riskNodes = semanticReadonly ? roleNodes(primaryNodes, ['risk'], false, true, true) : [];
  const auditNodes = semanticReadonly ? roleNodes(primaryNodes, ['audit'], false, false, true) : [];
  const taskNodes = semanticReadonly
    ? roleNodes(primaryNodes, ['task'], false, true, true)
    : (editableNodes.length ? editableNodes : primaryNodes);
  const taskIds = new Set(taskNodes.map((node) => node.nodeId));
  const allContextNodes = semanticReadonly
    ? roleNodes(primaryNodes, ['context', 'relation', 'activity'], true)
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
    ? partitionContextBlocks(allContextNodes, 24)
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
    subordinateNodes: visibleNodes(renderModel.zones.subordinate, renderModel.identity.mode),
    blockedActions,
    directActions,
    overflowActions: visibleActions.filter((action) => (
      !directActions.includes(action) && !blockedActions.includes(action)
    )),
    effectivePrimaryKey: effectivePrimary?.key || '',
  };
}
