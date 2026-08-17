import type {
  CanonicalFormAction,
  CanonicalFormNode,
  CanonicalFormRenderModel,
} from './canonicalFormRenderModel';

export type CanonicalFormFloorplan = {
  taskNodes: CanonicalFormNode[];
  contextNodes: CanonicalFormNode[];
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
  const taskNodes = editableNodes.length ? editableNodes : primaryNodes;
  const taskIds = new Set(taskNodes.map((node) => node.nodeId));
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
    taskNodes,
    contextNodes: primaryNodes.filter((node) => !taskIds.has(node.nodeId)),
    subordinateNodes: visibleNodes(renderModel.zones.subordinate, renderModel.identity.mode),
    blockedActions,
    directActions,
    overflowActions: visibleActions.filter((action) => (
      !directActions.includes(action) && !blockedActions.includes(action)
    )),
    effectivePrimaryKey: effectivePrimary?.key || '',
  };
}
