import type {
  CanonicalFormAction,
  CanonicalFormField,
  CanonicalFormNode,
  CanonicalFormRenderModel,
  CanonicalFormSemanticRole,
  CanonicalFormRenderMode,
  CanonicalRelationValue,
  CanonicalFormZoneRole,
} from './canonicalFormRenderModel';
import type {
  ContractV2ActionRule,
  ContractV2ButtonStatus,
  ContractV2Container,
  ContractV2ContainerStatus,
  ContractV2Dictionary,
  ContractV2NormalizedStore,
  ContractV2Widget,
  ContractV2WidgetStatus,
} from '../contracts/v2/types';

function asDict(value: unknown): ContractV2Dictionary {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as ContractV2Dictionary : {};
}

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function bool(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

const FORM_SEMANTIC_ROLES = new Set<CanonicalFormSemanticRole>([
  'summary', 'task', 'context', 'risk', 'relation', 'activity', 'audit',
]);

function semanticRole(value: unknown): CanonicalFormSemanticRole | '' {
  const structure = asDict(value);
  const role = text(structure.role).toLowerCase() as CanonicalFormSemanticRole;
  return FORM_SEMANTIC_ROLES.has(role) ? role : '';
}

function fieldSemanticRole(
  widget: ContractV2Widget,
  container: ContractV2Container,
): CanonicalFormSemanticRole | '' {
  return semanticRole(widget.formStructureRole) || semanticRole(container.formStructureRole);
}

function zoneRole(container: ContractV2Container): CanonicalFormZoneRole {
  const authority = asDict(container.sourceAuthority
    || container.attributes?.sourceAuthority || container.attributes?.source_authority);
  const projectionOnly = authority.projection_only === true || authority.projectionOnly === true;
  const noBusinessAuthority = authority.no_business_fact_authority === true
    || authority.noBusinessFactAuthority === true;
  return projectionOnly && noBusinessAuthority ? 'subordinate' : 'primary';
}

function relationModel(widget: ContractV2Widget): string {
  return text(widget.relation
    || widget.componentConfig.relation
    || widget.componentConfig.relationModel
    || widget.componentConfig.relation_model);
}

function relationParts(value: unknown): { id: string | number; displayName: string } | null {
  if (Array.isArray(value) && value.length) {
    return { id: value[0] as string | number, displayName: text(value[1]) };
  }
  const row = asDict(value);
  const id = row.id as string | number | undefined;
  if (id !== undefined && id !== null && text(id)) {
    return { id, displayName: text(row.display_name || row.displayName || row.label || row.name) };
  }
  return null;
}

function presentFieldValue(
  widget: ContractV2Widget,
  contractValue: unknown,
  runtimeValue: unknown,
  hasRuntimeValue: boolean,
): unknown | CanonicalRelationValue {
  const fieldType = text(widget.fieldType || widget.componentConfig.fieldType || widget.componentConfig.field_type).toLowerCase();
  const selected = hasRuntimeValue ? runtimeValue : contractValue;
  if (fieldType === 'many2one') {
    const runtimeRelation = relationParts(runtimeValue);
    const contractRelation = relationParts(contractValue);
    const relation = runtimeRelation || contractRelation;
    if (!relation) return null;
    const runtimeId = hasRuntimeValue && runtimeValue !== null && typeof runtimeValue !== 'object'
      ? runtimeValue as string | number
      : relation.id;
    const displayName = runtimeRelation?.displayName
      || (String(runtimeId) === String(contractRelation?.id ?? '') ? contractRelation?.displayName : '')
      || '';
    return Object.freeze({ id: runtimeId, displayName, model: relationModel(widget) });
  }
  if (fieldType !== 'boolean' && (selected === false || selected === null || selected === undefined)) return null;
  if (['date', 'datetime'].includes(fieldType) && text(selected).toLowerCase() === 'false') return null;
  return selected;
}

function fieldFromWidget(
  widget: ContractV2Widget,
  container: ContractV2Container,
  status: ContractV2WidgetStatus | undefined,
  contractValues: ContractV2Dictionary,
  runtimeValues: ContractV2Dictionary | undefined,
  mode: CanonicalFormRenderMode,
  pageCanEdit: boolean,
  ancestorVisible: boolean,
  ancestorDisabled: boolean,
): CanonicalFormField {
  const statusResolved = Boolean(status);
  const hasRuntimeValue = Boolean(runtimeValues)
    && Object.prototype.hasOwnProperty.call(runtimeValues, widget.fieldCode);
  return {
    widgetId: widget.widgetId,
    fieldCode: widget.fieldCode,
    label: widget.label,
    value: presentFieldValue(
      widget,
      contractValues[widget.fieldCode],
      runtimeValues?.[widget.fieldCode],
      hasRuntimeValue,
    ),
    fieldType: text(widget.fieldType || widget.componentConfig.fieldType || widget.componentConfig.field_type),
    componentKey: widget.componentKey,
    span: widget.span,
    visible: ancestorVisible && statusResolved && bool(status?.visible, true),
    readonly: mode === 'readonly' || !pageCanEdit || ancestorDisabled || !statusResolved || bool(status?.readonly, false),
    required: bool(status?.required, false),
    disabled: ancestorDisabled || !statusResolved || bool(status?.disabled, false),
    reasonCode: text(status?.reasonCode) || (!statusResolved ? 'WIDGET_STATUS_UNRESOLVED' : ''),
    semanticRole: fieldSemanticRole(widget, container),
    componentConfig: Object.freeze({ ...widget.componentConfig }),
  };
}

function childCollections(container: ContractV2Container): ContractV2Container[] {
  return [
    ...container.children,
    ...(container.pages || []),
    ...(container.tabs || []),
    ...(container.nodes || []),
    ...(container.items || []),
  ];
}

function descendantWidgetIds(container: ContractV2Container, store: ContractV2NormalizedStore): Set<string> {
  const ids = new Set<string>();
  childCollections(container).forEach((child) => {
    child.widgetList.forEach((widget) => ids.add(widget.widgetId));
    const kind = text(child.type || child.containerType).toLowerCase();
    if (kind === 'field') {
      const fieldInfo = asDict(child.fieldInfo || child.field_info);
      const fieldCode = text(child.name || fieldInfo.name || child.attributes?.name);
      const synthesized = store.widgetsByFieldCode.get(fieldCode);
      if (synthesized) ids.add(synthesized.widgetId);
    }
    descendantWidgetIds(child, store).forEach((widgetId) => ids.add(widgetId));
  });
  return ids;
}

function widgetsOwnedByContainer(
  container: ContractV2Container,
  store: ContractV2NormalizedStore,
): ContractV2Widget[] {
  const descendants = descendantWidgetIds(container, store);
  const direct = container.widgetList.filter((widget) => !descendants.has(widget.widgetId));
  if (direct.length) return direct;
  const kind = text(container.type || container.containerType).toLowerCase();
  if (kind !== 'field') return [];
  const fieldInfo = asDict(container.fieldInfo || container.field_info);
  const fieldCode = text(container.name || fieldInfo.name || container.attributes?.name);
  const widget = store.widgetsByFieldCode.get(fieldCode);
  return widget ? [widget] : [];
}

function presentNode(
  container: ContractV2Container,
  inheritedRole: CanonicalFormZoneRole,
  index: number,
  store: ContractV2NormalizedStore,
  contractValues: ContractV2Dictionary,
  runtimeValues: ContractV2Dictionary | undefined,
  mode: CanonicalFormRenderMode,
  pageCanEdit: boolean,
  ancestorVisible: boolean,
  ancestorDisabled: boolean,
  claimedWidgetIds: Set<string>,
  ancestorTitle = '',
): CanonicalFormNode {
  const ownRole = zoneRole(container);
  const effectiveRole = ownRole === 'subordinate' ? ownRole : inheritedRole;
  const status: ContractV2ContainerStatus | undefined = store.containerStatusById.get(container.containerId);
  const visible = ancestorVisible && bool(status?.visible, true);
  const disabled = ancestorDisabled || bool(status?.disabled, false);
  const widgets = widgetsOwnedByContainer(container, store).flatMap((widget) => {
    if (claimedWidgetIds.has(widget.widgetId)) return [];
    claimedWidgetIds.add(widget.widgetId);
    return [fieldFromWidget(
      widget,
      container,
      store.widgetStatusById.get(widget.widgetId),
      contractValues,
      runtimeValues,
      mode,
      pageCanEdit,
      visible,
      disabled,
    )];
  });
  const rawTitle = text(container.title || container.label || container.string);
  const title = rawTitle && rawTitle === ancestorTitle ? '' : rawTitle;
  return {
    nodeId: container.containerId || `${text(container.type || container.containerType) || 'node'}.${index}`,
    kind: text(container.type || container.containerType) || 'container',
    title,
    zoneRole: effectiveRole,
    columns: Number(container.cols || container.columns || 1) || 1,
    visible,
    disabled,
    reasonCode: text(status?.reasonCode),
    semanticRole: semanticRole(container.formStructureRole),
    fields: widgets,
    children: childCollections(container).map((child, childIndex) => (
      presentNode(
        child, effectiveRole, childIndex, store, contractValues, runtimeValues,
        mode, pageCanEdit, visible, disabled, claimedWidgetIds, rawTitle || ancestorTitle,
      )
    )),
  };
}

function actionTier(action: ContractV2ActionRule): CanonicalFormAction['tier'] {
  const tier = text(action.presentation?.tier).toLowerCase();
  if (tier === 'primary' || tier === 'secondary' || tier === 'overflow' || tier === 'configuration') return tier;
  return 'secondary';
}

function isFormActionBarAction(action: ContractV2ActionRule): boolean {
  const sourceWidgetId = text(action.sourceWidgetId);
  const targetScope = text(action.targetScope).toLowerCase();
  return sourceWidgetId === 'page.header'
    || (sourceWidgetId === 'page.root' && ['header', 'page'].includes(targetScope))
    || targetScope === 'footer';
}

function actionStatus(
  store: ContractV2NormalizedStore,
  action: ContractV2ActionRule,
): ContractV2ButtonStatus | undefined {
  const actionKey = text(action.actionKey);
  const statusKey = actionKey.startsWith('btn.') ? actionKey : `btn.${actionKey}`;
  return store.buttonStatusById.get(action.actionId)
    || (actionKey ? store.buttonStatusById.get(actionKey) : undefined)
    || (actionKey ? store.buttonStatusById.get(statusKey) : undefined);
}

function presentAction(
  action: ContractV2ActionRule,
  status: ContractV2ButtonStatus | undefined,
  mode: CanonicalFormRenderMode,
): CanonicalFormAction {
  const profiles = (action.visibleProfiles || ['create', 'edit', 'readonly'])
    .filter((profile): profile is CanonicalFormRenderMode => ['create', 'edit', 'readonly'].includes(profile));
  const allowed = action.allowed === true;
  const enabled = action.enabled === true && action.disabled !== true && status?.disabled !== true;
  if (!text(action.actionId) || !text(action.backendIdentity)) {
    throw new Error('CANONICAL_FORM_ACTION_REFERENCE_MISSING');
  }
  return {
    key: action.actionKey || action.actionId,
    label: text(action.label || action.actionKey || action.actionId),
    tier: actionTier(action),
    visible: profiles.includes(mode)
      && status?.visible !== false
      && !(mode === 'readonly' && action.actionId === 'form.save'),
    enabled: allowed && enabled,
    reasonCode: text(status?.reasonCode) || (!allowed || !enabled ? 'ACTION_NOT_ALLOWED' : ''),
    visibleProfiles: profiles,
    safety: Object.freeze({ ...(action.actionSafety || {}) }),
    actionRef: action,
  };
}

export function presentContractV2Form(
  store: ContractV2NormalizedStore,
  mode: CanonicalFormRenderMode,
  runtimeValues?: ContractV2Dictionary,
): CanonicalFormRenderModel {
  const snapshot = store.snapshot;
  const contractValues = Object.keys(snapshot.dataContract.mainData).length
    ? snapshot.dataContract.mainData
    : store.primaryDataSource || {};
  const globalStatus = snapshot.statusContract.globalStatus;
  const pageVisible = bool(globalStatus.pageVisible, true);
  const pageAuth = text(globalStatus.pageAuth);
  const pageCanEdit = mode !== 'readonly' && ['edit', 'admin'].includes(pageAuth);
  const claimedWidgetIds = new Set<string>();
  const nodes = snapshot.layoutContract.containerTree.map((container, index) => (
    presentNode(
      container, zoneRole(container), index, store, contractValues, runtimeValues, mode, pageCanEdit,
      pageVisible, pageAuth === 'none', claimedWidgetIds,
    )
  ));
  const actions = snapshot.actionContract.actionRuleList.filter(isFormActionBarAction).map((action) => (
    presentAction(action, actionStatus(store, action), mode)
  ));
  const primaryCount = actions.filter((action) => action.visible && action.enabled && action.tier === 'primary').length;
  if (primaryCount > 1) throw new Error('CANONICAL_FORM_MULTIPLE_PRIMARY_ACTIONS');
  return {
    identity: {
      pageId: snapshot.pageInfo.pageId,
      sceneKey: snapshot.pageInfo.sceneKey,
      model: snapshot.pageInfo.model,
      viewType: snapshot.pageInfo.viewType,
      mode,
      sourceContractSha256: snapshot.meta.lifecycle.integrity.contractSha256,
    },
    shell: {
      title: snapshot.pageInfo.pageName,
      pageVisible,
      pageAuth,
      reasonCode: text(globalStatus.reasonCode),
    },
    actionBar: actions,
    zones: {
      primary: nodes.filter((node) => node.zoneRole === 'primary'),
      subordinate: nodes.filter((node) => node.zoneRole === 'subordinate'),
    },
    responsive: {
      adaptMode: snapshot.layoutContract.adaptMode,
      layoutHints: Object.freeze({ ...snapshot.layoutContract.layoutHints }),
    },
    componentTokens: Object.freeze(Object.fromEntries(
      Object.entries(snapshot.layoutContract.componentRegistry).map(([key, value]) => [key, Object.freeze({ ...asDict(value) })]),
    )),
  };
}
