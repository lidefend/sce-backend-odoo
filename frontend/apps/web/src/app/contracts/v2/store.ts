import type {
  ContractV2ActionRule,
  ContractV2ButtonStatus,
  ContractV2Container,
  ContractV2ContainerStatus,
  ContractV2Dictionary,
  ContractV2FieldDescriptor,
  ContractV2FieldDescriptorMap,
  ContractV2FormFieldDescriptor,
  ContractV2FormStructureRoleName,
  ContractV2FormStructureRole,
  ContractV2FormStructureContract,
  ContractV2NormalizedStore,
  ContractV2Snapshot,
  ContractV2UnsupportedFeature,
  ContractV2Widget,
  ContractV2WidgetStatus,
} from './types';

import type { ContractV2SourceContext } from './types';

export type ContractV2FieldStatusByCode = Record<string, {
  visible?: boolean;
  readonly?: boolean;
  required?: boolean;
  disabled?: boolean;
  reasonCode?: string;
}>;

export type ContractV2ValueSource = {
  kind: 'none' | 'main_data' | 'primary';
  values: ContractV2Dictionary;
};

function walkContainers(containers: ContractV2Container[], visit: (container: ContractV2Container) => void): void {
  containers.forEach((container) => {
    visit(container);
    walkContainers(container.children, visit);
  });
}

function indexBy<T>(rows: T[], readKey: (row: T) => string): Map<string, T> {
  const out = new Map<string, T>();
  rows.forEach((row) => {
    const key = readKey(row);
    if (key) out.set(key, row);
  });
  return out;
}

function collectUnsupported(): ContractV2UnsupportedFeature[] {
  return [];
}

function primaryDataSource(snapshot: ContractV2Snapshot): ContractV2Dictionary | null {
  const source = snapshot.dataContract.dataSource.primary;
  return source && Object.keys(source).length ? source : null;
}

function asDict(value: unknown): ContractV2Dictionary {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as ContractV2Dictionary : {};
}

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asText(value: unknown): string {
  return String(value || '').trim();
}

function collectWidgets(snapshot: ContractV2Snapshot): ContractV2Widget[] {
  const out: ContractV2Widget[] = [];
  const seen = new Set<string>();
  const pushWidget = (widget: ContractV2Widget | null) => {
    if (!widget || !widget.widgetId || seen.has(widget.widgetId)) return;
    seen.add(widget.widgetId);
    out.push(widget);
  };
  walkContainers(snapshot.layoutContract.containerTree, (container) => {
    container.widgetList.forEach(pushWidget);
  });
  return out;
}

export function createContractV2Store(snapshot: ContractV2Snapshot): ContractV2NormalizedStore {
  const widgets = collectWidgets(snapshot);
  const widgetsByFieldCodeAll = new Map<string, ContractV2Widget[]>();
  widgets.forEach((widget) => {
    const rows = widgetsByFieldCodeAll.get(widget.fieldCode) || [];
    rows.push(widget);
    widgetsByFieldCodeAll.set(widget.fieldCode, rows);
  });
  const widgetsByOwnerContainerId = new Map<string, ContractV2Widget[]>();
  widgets.forEach((widget) => {
    const rows = widgetsByOwnerContainerId.get(widget.ownerContainerId) || [];
    rows.push(widget);
    widgetsByOwnerContainerId.set(widget.ownerContainerId, rows);
  });
  return {
    snapshot,
    widgetsById: indexBy<ContractV2Widget>(widgets, (widget) => widget.widgetId),
    widgetsByFieldCode: indexBy<ContractV2Widget>(widgets, (widget) => widget.fieldCode),
    widgetsByFieldCodeAll,
    widgetsByOwnerContainerId,
    actionsById: indexBy<ContractV2ActionRule>(snapshot.actionContract.actionRuleList, (action) => action.actionId),
    widgetStatusById: indexBy<ContractV2WidgetStatus>(snapshot.statusContract.widgetStatus, (status) => status.widgetId),
    buttonStatusById: indexBy<ContractV2ButtonStatus>(snapshot.statusContract.buttonStatus, (status) => status.btnId),
    containerStatusById: indexBy<ContractV2ContainerStatus>(snapshot.statusContract.containerStatus, (status) => status.containerId),
    primaryDataSource: primaryDataSource(snapshot),
    unsupported: collectUnsupported(),
  };
}

export function collectContractV2FieldStatusByCode(store: ContractV2NormalizedStore | null): ContractV2FieldStatusByCode {
  const out: ContractV2FieldStatusByCode = {};
  if (!store) return out;
  store.widgetStatusById.forEach((status, widgetId) => {
    const widget = store.widgetsById.get(widgetId);
    const fieldCode = String(widget?.fieldCode || '').trim();
    if (!fieldCode) return;
    if ((store.widgetsByFieldCodeAll.get(fieldCode) || []).length !== 1) return;
    out[fieldCode] = {
      ...(out[fieldCode] || {}),
      ...(typeof status.visible === 'boolean' ? { visible: status.visible } : {}),
      ...(typeof status.readonly === 'boolean' ? { readonly: status.readonly } : {}),
      ...(typeof status.required === 'boolean' ? { required: status.required } : {}),
      ...(typeof status.disabled === 'boolean' ? { disabled: status.disabled } : {}),
      ...(status.reasonCode ? { reasonCode: status.reasonCode } : {}),
    };
  });
  return out;
}

export function collectContractV2ButtonStatusById(store: ContractV2NormalizedStore | null): Record<string, ContractV2ButtonStatus> {
  const out: Record<string, ContractV2ButtonStatus> = {};
  if (!store) return out;
  store.buttonStatusById.forEach((status, btnId) => {
    out[btnId] = {
      btnId,
      ...(typeof status.visible === 'boolean' ? { visible: status.visible } : {}),
      ...(typeof status.disabled === 'boolean' ? { disabled: status.disabled } : {}),
      ...(status.reasonCode ? { reasonCode: status.reasonCode } : {}),
    };
  });
  return out;
}

export function resolveContractV2ContainerTree(store: ContractV2NormalizedStore | null): ContractV2Container[] {
  if (!store) return [];
  return store.snapshot.layoutContract.containerTree;
}

export function resolveContractV2FormStructureContract(
  store: ContractV2NormalizedStore | null,
): ContractV2FormStructureContract | null {
  return store?.snapshot.formStructureContract || null;
}

export function resolveContractV2SearchContract(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  if (!store) return {};
  return asDict(store.snapshot.searchContract);
}

export function resolveContractV2WorkflowContract(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  if (!store) return {};
  return asDict(store.snapshot.workflowContract);
}

export function resolveContractV2Collaboration(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  if (!store) return {};
  return asDict(store.snapshot.runtimeContract.collaboration);
}

export function resolveContractV2BusinessWorkspace(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  if (!store) return {};
  return asDict(store.snapshot.runtimeContract.businessWorkspace);
}

export function resolveContractV2BusinessActions(store: ContractV2NormalizedStore | null): ContractV2Dictionary[] {
  if (!store) return [];
  return Array.isArray(store.snapshot.runtimeContract.businessActions)
    ? store.snapshot.runtimeContract.businessActions
    : [];
}

export function resolveContractV2ActionRules(store: ContractV2NormalizedStore | null): ContractV2ActionRule[] {
  return store ? store.snapshot.actionContract.actionRuleList : [];
}

export function resolveContractV2FieldWidgets(store: ContractV2NormalizedStore | null): ContractV2Widget[] {
  return store ? Array.from(store.widgetsByFieldCode.values()) : [];
}

export function resolveContractV2SelectorStatus(store: ContractV2NormalizedStore | null, selectors: string[]) {
  if (!store) return null;
  const normalized = selectors.map(asText).filter(Boolean);
  if (!normalized.length) return null;
  return store.snapshot.statusContract.selectorStatus.find((row) => normalized.some((selector) => (
    row.selector === selector || (row.selector.endsWith('.*') && selector.startsWith(row.selector.slice(0, -1)))
  ))) || null;
}

export function resolveContractV2RuntimeContract(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  return resolveContractV2RuntimePolicy(store);
}

/**
 * Materialize the complete runtime policy as one normalized authority.  Each
 * schema field is copied explicitly so decoded policy cannot disappear at the
 * store boundary or remain an unconsumed opaque payload.
 */
export function resolveContractV2RuntimePolicy(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  if (!store) return {};
  const runtime = store.snapshot.runtimeContract;
  return Object.freeze({
    patchStrategy: runtime.patchStrategy,
    cachePolicy: runtime.cachePolicy,
    optimistic: runtime.optimistic,
    lazyContainer: runtime.lazyContainer,
    virtualization: runtime.virtualization,
    retryPolicy: runtime.retryPolicy,
    ...(runtime.renderStrategy !== undefined ? { renderStrategy: runtime.renderStrategy } : {}),
    ...(runtime.hydration !== undefined ? { hydration: runtime.hydration } : {}),
    ...(runtime.patchOperations !== undefined ? { patchOperations: runtime.patchOperations } : {}),
    ...(runtime.tracePolicy !== undefined ? { tracePolicy: runtime.tracePolicy } : {}),
    ...(runtime.complexityBudget !== undefined ? { complexityBudget: runtime.complexityBudget } : {}),
    ...(runtime.aiEnvelope !== undefined ? { aiEnvelope: runtime.aiEnvelope } : {}),
    ...(runtime.interactionMode !== undefined ? { interactionMode: runtime.interactionMode } : {}),
    ...(runtime.actionTarget !== undefined ? { actionTarget: runtime.actionTarget } : {}),
    ...(runtime.collaboration !== undefined ? { collaboration: runtime.collaboration } : {}),
    ...(runtime.businessWorkspace !== undefined ? { businessWorkspace: runtime.businessWorkspace } : {}),
    ...(runtime.businessActions !== undefined ? { businessActions: runtime.businessActions } : {}),
    ...(runtime.deliveryProfile !== undefined ? { deliveryProfile: runtime.deliveryProfile } : {}),
    ...(runtime.intakeAutosave !== undefined ? { intakeAutosave: runtime.intakeAutosave } : {}),
    ...(runtime.fieldSemantics !== undefined ? { fieldSemantics: runtime.fieldSemantics } : {}),
    ...(runtime.validationRules !== undefined ? { validationRules: runtime.validationRules } : {}),
    ...(runtime.governance !== undefined ? { governance: runtime.governance } : {}),
    ...(runtime.recordVersionPolicy !== undefined ? { recordVersionPolicy: runtime.recordVersionPolicy } : {}),
  });
}

export function resolveContractV2ListProfile(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  return store ? asDict(store.snapshot.layoutContract.listProfile) : {};
}

export function resolveContractV2SurfacePolicies(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  return store ? asDict(store.snapshot.actionContract.surfacePolicies) : {};
}

export function resolveContractV2DeletePolicy(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  return store ? asDict(store.snapshot.actionContract.deletePolicy) : {};
}

export function resolveContractV2GlobalStatus(store: ContractV2NormalizedStore | null) {
  if (!store) return null;
  const row = store.snapshot.statusContract.globalStatus || {};
  if (!Object.keys(row).length) return null;
  return {
    ...(typeof row.pageVisible === 'boolean' ? { pageVisible: row.pageVisible } : {}),
    ...(asText(row.pageAuth) ? { pageAuth: asText(row.pageAuth) } : {}),
    ...(asText(row.reasonCode) ? { reasonCode: asText(row.reasonCode) } : {}),
    ...(Object.keys(asDict(row.modelRights)).length ? { modelRights: asDict(row.modelRights) } : {}),
    ...(Object.keys(asDict(row.recordRights)).length ? { recordRights: asDict(row.recordRights) } : {}),
    ...(Object.keys(asDict(row.viewCapabilities)).length ? { viewCapabilities: asDict(row.viewCapabilities) } : {}),
    ...(Object.keys(asDict(row.entryCapabilities)).length ? { entryCapabilities: asDict(row.entryCapabilities) } : {}),
    ...(Object.keys(asDict(row.effectiveRecordCapabilities)).length
      ? { effectiveRecordCapabilities: asDict(row.effectiveRecordCapabilities) }
      : {}),
    ...(asText(row.effectiveRenderProfile) ? { effectiveRenderProfile: asText(row.effectiveRenderProfile) } : {}),
  };
}

export function resolveContractV2MainData(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  if (!store) return {};
  return asDict(store.snapshot.dataContract.mainData);
}

export function resolveContractV2PrimaryDataSource(store: ContractV2NormalizedStore | null): ContractV2Dictionary {
  return store?.primaryDataSource ? { ...store.primaryDataSource } : {};
}

export function resolveContractV2ValueSource(store: ContractV2NormalizedStore | null): ContractV2ValueSource {
  if (!store) return { kind: 'none', values: {} };
  const fieldCodes = Array.from(store.widgetsByFieldCode.keys());
  const coverage = (values: ContractV2Dictionary) => fieldCodes.filter((fieldCode) => (
    Object.prototype.hasOwnProperty.call(values, fieldCode)
  )).length;
  const mainData = resolveContractV2MainData(store);
  if (coverage(mainData) > 0) return { kind: 'main_data', values: mainData };
  const primary = store.primaryDataSource || {};
  if (coverage(primary) > 0) return { kind: 'primary', values: primary };
  if (Object.keys(mainData).length) return { kind: 'main_data', values: mainData };
  if (Object.keys(primary).length) return { kind: 'primary', values: primary };
  return { kind: 'none', values: {} };
}

export function resolveContractV2SourceContext(store: ContractV2NormalizedStore | null): ContractV2SourceContext {
  if (!store) return {};
  const dataMeta = asDict(store.snapshot.dataContract.dataMeta);
  const source = asDict(dataMeta.sourceContext);
  if (!Object.keys(source).length) return {};
  const context = asDict(source.context);
  const domain = asList(source.domain);
  const contextRaw = asText(source.contextRaw);
  const domainRaw = asText(source.domainRaw);
  const renderProfileRaw = asText(source.renderProfile).toLowerCase();
  const renderProfile = renderProfileRaw === 'create' || renderProfileRaw === 'edit' || renderProfileRaw === 'readonly'
    ? renderProfileRaw
    : '';
  return {
    ...(Object.keys(context).length ? { context } : {}),
    ...(domain.length ? { domain } : {}),
    ...(contextRaw ? { contextRaw } : {}),
    ...(domainRaw ? { domainRaw } : {}),
    ...(renderProfile ? { renderProfile } : {}),
  };
}

function selectionPairs(value: unknown): Array<[string, string]> | undefined {
  if (!Array.isArray(value)) return undefined;
  const rows = value.flatMap((item) => (
    Array.isArray(item) && item.length >= 2
      ? [[String(item[0] ?? ''), String(item[1] ?? '')] as [string, string]]
      : []
  ));
  return rows.length ? rows : undefined;
}

export function resolveContractV2FieldDescriptorMap(
  store: ContractV2NormalizedStore | null,
): ContractV2FieldDescriptorMap {
  const out: ContractV2FieldDescriptorMap = {};
  if (!store) return out;
  const widgetsByFieldCode = store.widgetsByFieldCode instanceof Map
    ? store.widgetsByFieldCode
    : new Map(Array.from(store.widgetsByFieldCodeAll?.entries?.() || []).flatMap(([fieldCode, widgets]) => (
      widgets.length === 1 ? [[fieldCode, widgets[0]] as const] : []
    )));
  widgetsByFieldCode.forEach((widget, fieldCode) => {
    const code = asText(fieldCode);
    if (!code) return;
    const config = asDict(widget.componentConfig);
    const descriptor = asDict(widget.fieldDescriptor);
    const fieldType = asText(widget.fieldType || config.fieldType || descriptor.ttype || descriptor.type);
    const relation = asText(widget.relation || config.relation || descriptor.relation);
    const relationField = asText(config.relationField || descriptor.relation_field);
    const relationEntry = asDict(config.relationEntry || descriptor.relation_entry);
    const widgetOptions = asDict(config.widgetOptions || descriptor.widget_options);
    const subview = asDict(config.subview || descriptor.subview);
    const formStructureRoleCandidate = asDict(widget.formStructureRole || config.formStructureRole || descriptor.formStructureRole);
    const roleName = asText(formStructureRoleCandidate.role);
    const canonicalRoles = new Set<ContractV2FormStructureRoleName>(['summary', 'task', 'context', 'risk', 'relation', 'activity', 'audit']);
    const formStructureRole: ContractV2FormStructureRole | undefined = (
      canonicalRoles.has(roleName as ContractV2FormStructureRoleName)
      && asText(formStructureRoleCandidate.slot)
      && asText(formStructureRoleCandidate.group)
    ) ? {
        role: roleName as ContractV2FormStructureRoleName,
        slot: asText(formStructureRoleCandidate.slot),
        group: asText(formStructureRoleCandidate.group),
      } : undefined;
    out[code] = {
      fieldCode: code,
      label: asText(widget.label || descriptor.string) || code,
      fieldType,
      widgetType: asText(widget.widgetType),
      componentKey: asText(widget.componentKey),
      ...(typeof (config.required ?? descriptor.required) === 'boolean' ? { required: Boolean(config.required ?? descriptor.required) } : {}),
      ...(typeof (config.readonly ?? descriptor.readonly) === 'boolean' ? { readonly: Boolean(config.readonly ?? descriptor.readonly) } : {}),
      ...(typeof (config.invisible ?? descriptor.invisible) === 'boolean' ? { invisible: Boolean(config.invisible ?? descriptor.invisible) } : {}),
      ...(relation ? { relation } : {}),
      ...(relationField ? { relationField } : {}),
      ...(selectionPairs(config.selection ?? descriptor.selection)
        ? { selection: selectionPairs(config.selection ?? descriptor.selection) }
        : {}),
      ...(Object.prototype.hasOwnProperty.call(config, 'domain') ? { domain: config.domain } : {}),
      ...(Object.prototype.hasOwnProperty.call(config, 'context') ? { context: config.context } : {}),
      ...(Object.keys(relationEntry).length ? { relationEntry } : {}),
      ...(Object.keys(widgetOptions).length ? { widgetOptions } : {}),
      ...(Object.keys(subview).length ? { subview } : {}),
      ...(asText(config.filename) ? { filename: asText(config.filename) } : {}),
      ...(asText(config.semanticType) ? { semanticType: asText(config.semanticType) } : {}),
      ...(asText(config.surfaceRole) ? { surfaceRole: asText(config.surfaceRole) } : {}),
      ...(typeof config.technical === 'boolean' ? { technical: config.technical } : {}),
      ...(formStructureRole ? { formStructureRole } : {}),
    };
  });
  return out;
}

export function toContractV2FormFieldDescriptor(row: ContractV2FieldDescriptor): ContractV2FormFieldDescriptor {
  return {
    name: row.fieldCode,
    string: row.label,
    type: row.fieldType,
    ttype: row.fieldType,
    widget: row.widgetType,
    ...(typeof row.required === 'boolean' ? { required: row.required } : {}),
    ...(typeof row.readonly === 'boolean' ? { readonly: row.readonly } : {}),
    ...(typeof row.invisible === 'boolean' ? { invisible: row.invisible } : {}),
    ...(row.relation ? { relation: row.relation } : {}),
    ...(row.relationField ? { relation_field: row.relationField } : {}),
    ...(row.selection ? { selection: row.selection } : {}),
    ...(row.relationEntry ? { relation_entry: row.relationEntry } : {}),
    ...(row.widgetOptions ? { widget_options: row.widgetOptions } : {}),
    ...(row.subview ? { subview: row.subview } : {}),
    ...(row.filename ? { filename: row.filename } : {}),
    ...(row.domain !== undefined ? { domain: row.domain } : {}),
    ...(row.context !== undefined ? { context: row.context } : {}),
  };
}

export function resolveContractV2FormFieldMap(
  store: ContractV2NormalizedStore | null,
): Record<string, ContractV2FormFieldDescriptor> {
  return Object.fromEntries(Object.entries(resolveContractV2FieldDescriptorMap(store)).map(
    ([fieldCode, row]) => [fieldCode, toContractV2FormFieldDescriptor(row)],
  ));
}

export function resolveContractV2VisibleFieldCodes(store: ContractV2NormalizedStore | null): string[] {
  return store ? asList(store.snapshot.dataContract.dataMeta.visibleFields?.fields).map(asText).filter(Boolean) : [];
}

export function resolveContractV2FieldGroups(store: ContractV2NormalizedStore | null): ContractV2Dictionary[] {
  return store ? asList(store.snapshot.dataContract.dataMeta.fieldGroups?.groups).map(asDict).filter((row) => Object.keys(row).length) : [];
}

export function collectContractV2FieldContainerStatusByCode(store: ContractV2NormalizedStore | null): ContractV2FieldStatusByCode {
  const out: ContractV2FieldStatusByCode = {};
  if (!store) return out;
  walkContainers(store.snapshot.layoutContract.containerTree, (container) => {
    const type = asText(container.type || container.containerType).toLowerCase();
    const fieldInfo = asDict(container.fieldInfo);
    const fieldCode = asText(container.name || fieldInfo.name);
    if (type !== 'field' || !fieldCode) return;
    const status = store.containerStatusById.get(container.containerId);
    if (!status) return;
    out[fieldCode] = {
      ...(typeof status.visible === 'boolean' ? { visible: status.visible } : {}),
      ...(typeof status.disabled === 'boolean' ? { disabled: status.disabled } : {}),
      ...(status.reasonCode ? { reasonCode: status.reasonCode } : {}),
    };
  });
  return out;
}

export function resolveContractV2RequiredFieldCodes(store: ContractV2NormalizedStore | null): string[] {
  if (!store) return [];
  const required = new Set<string>();
  Object.values(resolveContractV2FieldDescriptorMap(store)).forEach((row) => {
    if (row.required) required.add(row.fieldCode);
  });
  Object.entries(collectContractV2FieldStatusByCode(store)).forEach(([fieldCode, status]) => {
    if (status.required) required.add(fieldCode);
  });
  store.snapshot.actionContract.actionRuleList.forEach((rule) => {
    const submitPolicy = asDict(rule.submitPolicy);
    asList(submitPolicy.requiredFields).map(asText).filter(Boolean).forEach((field) => required.add(field));
  });
  return Array.from(required);
}

export interface ContractV2EffectiveFormCapabilities {
  read: boolean;
  write: boolean;
  create: boolean;
  unlink: boolean;
  duplicate: boolean;
}

export function resolveContractV2EffectiveFormCapabilities(
  store: ContractV2NormalizedStore | null,
): ContractV2EffectiveFormCapabilities | null {
  const status = resolveContractV2GlobalStatus(store);
  const effective = asDict(status?.effectiveRecordCapabilities);
  if (!Object.keys(effective).length) return null;
  return {
    read: effective.read === true,
    write: effective.write === true,
    create: effective.create === true,
    unlink: effective.unlink === true,
    duplicate: effective.duplicate === true,
  };
}
