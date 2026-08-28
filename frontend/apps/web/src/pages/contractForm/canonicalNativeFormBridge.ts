import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type {
  CanonicalFormAction,
  CanonicalFormField,
  CanonicalFormNode,
  CanonicalFormRenderModel,
} from '../../app/presentation/canonicalFormRenderModel';
import type { FormSectionFieldSchema } from '../../components/template/formSection.types';
import { canonicalFieldToFormSection } from './canonicalFormRenderer';

export type CanonicalNativeLayoutNode = {
  type: string;
  containerType: string;
  name: string;
  string?: string;
  text?: string;
  cols?: number;
  columns?: number;
  span?: number;
  widget?: string;
  visible?: boolean;
  attributes?: Record<string, unknown>;
  displayLabel?: string;
  semanticTitle?: string;
  semanticAnchor?: string;
  filename?: string;
  badge?: Record<string, unknown>;
  column_invisible?: unknown;
  domain?: unknown;
  context?: unknown;
  options?: unknown;
  col?: number | string;
  class?: string;
  className?: string;
  fieldSize?: string;
  size?: string;
  formStructure?: Record<string, unknown>;
  sourceAuthority?: Record<string, unknown>;
  fields?: readonly string[];
  action?: Record<string, unknown> | null;
  buttonType?: string;
  children?: CanonicalNativeLayoutNode[];
};

export type CanonicalNativeFormBridge = {
  primaryNodes: CanonicalNativeLayoutNode[];
  subordinateNodes: CanonicalNativeLayoutNode[];
  fieldSchemasForNodes: (nodes: CanonicalNativeLayoutNode[]) => FormSectionFieldSchema[];
  actionForPayload: (payload: Record<string, unknown>) => ContractV2ActionRule | null;
  actionStateForNode: (payload: Record<string, unknown>) => { disabled: boolean; title: string };
  nodeVisible: (node: CanonicalNativeLayoutNode) => boolean;
};

const NATIVE_CONTAINER_KINDS = new Set([
  'header', 'footer', 'sheet', 'group', 'notebook', 'page', 'container', 'div', 'span', 'h1', 'h2', 'h3',
]);

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function favoriteActive(value: unknown): boolean {
  return value === true || value === 1 || value === '1' || String(value ?? '').trim().toLowerCase() === 'true';
}

export function resolveCanonicalNativeFieldSchemas(
  schemas: readonly FormSectionFieldSchema[],
): FormSectionFieldSchema[] {
  const favorite = schemas.find((field) => field.widget === 'boolean_favorite' || field.name === 'is_favorite');
  const content = schemas.filter((field) => field !== favorite).map((field) => ({ ...field }));
  if (!favorite || !content.length) return content;
  const targetIndex = content.findIndex((field) => field.name === 'name');
  const textIndex = content.findIndex((field) => ['char', 'text'].includes(text(field.type).toLowerCase()));
  const index = targetIndex >= 0 ? targetIndex : textIndex >= 0 ? textIndex : 0;
  const target = content[index];
  content[index] = {
    ...target,
    favoriteToggle: {
      name: favorite.name,
      label: favorite.label || favorite.name,
      active: favoriteActive(favorite.inputValue ?? favorite.value),
      readonly: favorite.readonly,
      descriptor: favorite.descriptor,
    },
  };
  return content;
}

function isCollaborationNode(node: CanonicalFormNode): boolean {
  return ['chatter', 'activity'].includes(text(node.kind).toLowerCase());
}

function canonicalActionRecord(action: CanonicalFormAction): Record<string, unknown> {
  return {
    backendIdentity: action.actionRef.backendIdentity,
    actionId: action.actionRef.actionId,
    actionKey: action.actionRef.actionKey,
    displayLabel: action.label,
    label: action.label,
    icon: action.icon,
    level: 'body',
    payload: { backendIdentity: action.actionRef.backendIdentity },
  };
}

function fieldNode(
  field: CanonicalFormField,
  fieldSchemas: WeakMap<CanonicalNativeLayoutNode, FormSectionFieldSchema>,
  sourceNode?: CanonicalFormNode,
): CanonicalNativeLayoutNode {
  const node: CanonicalNativeLayoutNode = {
    ...(sourceNode?.nativePresentation || {}),
    type: 'field',
    containerType: 'field',
    name: field.fieldCode,
    string: sourceNode?.title || field.label,
    text: sourceNode?.text || '',
    cols: sourceNode?.columns,
    columns: sourceNode?.columns,
    visible: field.visible && (sourceNode?.visible ?? true),
    attributes: {
      ...(sourceNode?.attributes || {}),
      class: text(
        sourceNode?.attributes.class
        || sourceNode?.nativePresentation.class
        || sourceNode?.nativePresentation.className,
      ),
      name: field.fieldCode,
      canonicalWidgetId: field.widgetId,
      canonicalNodeId: sourceNode?.nodeId || field.widgetId,
      canonicalNodeKind: 'field',
      sectionNavigationRole: sourceNode?.zoneRole,
      contractStyleToken: sourceNode?.styleToken,
    },
    children: [],
  };
  fieldSchemas.set(node, canonicalFieldToFormSection(field));
  return node;
}

export function buildCanonicalNativeFormBridge(
  renderModel: CanonicalFormRenderModel,
): CanonicalNativeFormBridge {
  const fieldSchemas = new WeakMap<CanonicalNativeLayoutNode, FormSectionFieldSchema>();
  const actionsByIdentity = new Map<string, CanonicalFormAction>();
  const headerActionIdentities = new Set(
    renderModel.actionBar.map((action) => action.actionRef.backendIdentity).filter(Boolean),
  );
  const renderedBodyActionIdentities = new Set<string>();

  function mapNode(node: CanonicalFormNode): CanonicalNativeLayoutNode {
    if (text(node.kind).toLowerCase() === 'field' && node.fields.length === 1) {
      return fieldNode(node.fields[0], fieldSchemas, node);
    }
    const rawKind = text(node.kind).toLowerCase() || 'container';
    const action = node.action;
    const actionIdentity = text(action?.actionRef.backendIdentity);
    const kind = rawKind === 'button'
      ? 'button'
      : rawKind === 'widget'
        ? 'widget'
        : NATIVE_CONTAINER_KINDS.has(rawKind) ? rawKind : 'container';
    if (actionIdentity) actionsByIdentity.set(actionIdentity, action!);
    const actionVisible = kind !== 'button' || !actionIdentity
      ? true
      : !headerActionIdentities.has(actionIdentity) && !renderedBodyActionIdentities.has(actionIdentity);
    if (kind === 'button' && actionIdentity && node.visible && actionVisible) {
      renderedBodyActionIdentities.add(actionIdentity);
    }
    const mappedChildren = [
      ...node.fields.map((field) => fieldNode(field, fieldSchemas)),
      ...node.children.filter((child) => !isCollaborationNode(child)).map(mapNode),
    ];
    const children = kind === 'notebook' && !mappedChildren.some((child) => child.type === 'page')
      ? [{
        type: 'page', containerType: 'page', name: `${node.nodeId}.page.default`,
        string: node.title, visible: node.visible, attributes: {}, children: mappedChildren,
      } satisfies CanonicalNativeLayoutNode]
      : mappedChildren;
    return {
      ...node.nativePresentation,
      type: kind,
      containerType: kind,
      name: node.nodeId,
      string: node.title,
      text: node.text,
      cols: node.columns,
      columns: node.columns,
      span: node.span,
      widget: node.nativeWidget,
      visible: node.visible && (kind !== 'button' || Boolean(action)) && actionVisible,
      attributes: {
        ...node.attributes,
        class: text(node.attributes.class || node.nativePresentation.class || node.nativePresentation.className),
        canonicalNodeId: node.nodeId,
        canonicalNodeKind: rawKind,
        sectionNavigationRole: node.zoneRole,
        contractStyleToken: node.styleToken,
      },
      action: action ? canonicalActionRecord(action) : null,
      buttonType: text(action?.actionRef.button?.type) || 'object',
      children,
    };
  }

  function actionIdentity(payload: Record<string, unknown>): string {
    const nested = payload.payload && typeof payload.payload === 'object' && !Array.isArray(payload.payload)
      ? payload.payload as Record<string, unknown>
      : {};
    const action = payload.action && typeof payload.action === 'object' && !Array.isArray(payload.action)
      ? payload.action as Record<string, unknown>
      : {};
    return text(payload.backendIdentity || nested.backendIdentity || action.backendIdentity);
  }

  return {
    primaryNodes: renderModel.zones.primary.map(mapNode),
    subordinateNodes: renderModel.zones.subordinate.filter((node) => !isCollaborationNode(node)).map(mapNode),
    fieldSchemasForNodes(nodes) {
      return resolveCanonicalNativeFieldSchemas(nodes.flatMap((node) => {
        const field = fieldSchemas.get(node);
        return field ? [field] : [];
      }));
    },
    actionForPayload(payload) {
      return actionsByIdentity.get(actionIdentity(payload))?.actionRef || null;
    },
    actionStateForNode(payload) {
      const action = actionsByIdentity.get(actionIdentity(payload));
      return {
        disabled: !action?.enabled,
        title: action?.reasonCode || '',
      };
    },
    nodeVisible(node) {
      return node.visible !== false;
    },
  };
}
