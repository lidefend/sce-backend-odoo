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
};

function hasEditableField(node: CanonicalFormNode): boolean {
  return node.fields.some((field) => field.visible && !field.readonly && !field.disabled)
    || node.children.some(hasEditableField);
}

function visibleNodes(nodes: CanonicalFormNode[]): CanonicalFormNode[] {
  return nodes.filter((node) => node.visible);
}

/**
 * Pure, ephemeral floorplan projection. It groups canonical nodes without
 * changing field/action identity, visibility, authority, order, or values.
 */
export function composeCanonicalFormFloorplan(
  renderModel: CanonicalFormRenderModel,
): CanonicalFormFloorplan {
  const primaryNodes = visibleNodes(renderModel.zones.primary);
  const editableNodes = primaryNodes.filter(hasEditableField);
  const taskNodes = editableNodes.length ? editableNodes : primaryNodes;
  const taskIds = new Set(taskNodes.map((node) => node.nodeId));

  return {
    taskNodes,
    contextNodes: primaryNodes.filter((node) => !taskIds.has(node.nodeId)),
    subordinateNodes: visibleNodes(renderModel.zones.subordinate),
    blockedActions: renderModel.actionBar.filter((action) => (
      action.visible && !action.enabled && action.tier === 'primary'
    )),
  };
}
