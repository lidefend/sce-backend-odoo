import type {
  ContractV2ActionContract,
  ContractV2ActionRule,
  ContractV2Auth,
  ContractV2ButtonStatus,
  ContractV2AdaptMode,
  ContractV2ClientType,
  ContractV2Container,
  ContractV2ContainerStatus,
  ContractV2DataContract,
  ContractV2DataMeta,
  ContractV2Dictionary,
  ContractV2DispatchMode,
  ContractV2FieldGroups,
  ContractV2GlobalStatus,
  ContractV2LayoutType,
  ContractV2LayoutContract,
  ContractV2Meta,
  ContractV2PageRenderMode,
  ContractV2PageInfo,
  ContractV2CachePolicy,
  ContractV2PatchOperation,
  ContractV2PatchStrategy,
  ContractV2SelectorStatus,
  ContractV2Snapshot,
  ContractV2SourceContext,
  ContractV2StatusContract,
  ContractV2RefreshMode,
  ContractV2RenderStrategy,
  ContractV2RuntimeContract,
  ContractV2TargetScope,
  ContractV2TriggerType,
  ContractV2VisibleFields,
  ContractV2ViewType,
  ContractV2Widget,
  ContractV2WidgetStatus,
} from './types';

type DecodeIssue = {
  path: string;
  message: string;
};

export class ContractV2DecodeError extends Error {
  issues: DecodeIssue[];

  constructor(issues: DecodeIssue[]) {
    super(`invalid contract v2 snapshot: ${issues.map((issue) => `${issue.path} ${issue.message}`).join('; ')}`);
    this.name = 'ContractV2DecodeError';
    this.issues = issues;
  }
}

function isRecord(value: unknown): value is ContractV2Dictionary {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function asRecord(value: unknown): ContractV2Dictionary {
  return isRecord(value) ? value : {};
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => asString(item)).filter(Boolean) : [];
}

function optionalBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined;
}

function requiredBoolean(source: ContractV2Dictionary, key: string, path: string, issues: DecodeIssue[], fallback: boolean): boolean {
  const value = source[key];
  if (typeof value === 'boolean') return value;
  issues.push({ path: `${path}.${key}`, message: 'must be a boolean' });
  return fallback;
}

function requiredString(source: ContractV2Dictionary, key: string, path: string, issues: DecodeIssue[]): string {
  const value = asString(source[key]);
  if (!value) {
    issues.push({ path: `${path}.${key}`, message: 'is required' });
  }
  return value;
}

function requiredDisplayString(source: ContractV2Dictionary, key: string, path: string, issues: DecodeIssue[]): string {
  if (typeof source[key] !== 'string') {
    issues.push({ path: `${path}.${key}`, message: 'must be a string' });
    return '';
  }
  return asString(source[key]);
}

function optionalString(source: ContractV2Dictionary, key: string): string | undefined {
  return asString(source[key]) || undefined;
}

function optionalRecord(
  source: ContractV2Dictionary,
  key: string,
  path: string,
  issues: DecodeIssue[],
): ContractV2Dictionary | undefined {
  if (!Object.prototype.hasOwnProperty.call(source, key)) return undefined;
  if (isRecord(source[key])) return source[key] as ContractV2Dictionary;
  issues.push({ path: `${path}.${key}`, message: 'must be an object' });
  return undefined;
}

function optionalRecordArray(
  source: ContractV2Dictionary,
  key: string,
  path: string,
  issues: DecodeIssue[],
): ContractV2Dictionary[] | undefined {
  if (!Object.prototype.hasOwnProperty.call(source, key)) return undefined;
  if (!Array.isArray(source[key])) {
    issues.push({ path: `${path}.${key}`, message: 'must be an array' });
    return undefined;
  }
  const decoded: ContractV2Dictionary[] = [];
  (source[key] as unknown[]).forEach((item, index) => {
    if (!isRecord(item)) {
      issues.push({ path: `${path}.${key}[${index}]`, message: 'must be an object' });
      return;
    }
    decoded.push(item);
  });
  return decoded;
}

function readAliasedObject(
  source: ContractV2Dictionary,
  key: string,
  aliases: string[],
  path: string,
  issues: DecodeIssue[],
): ContractV2Dictionary {
  const value = source[key] || aliases.map((alias) => source[alias]).find(isRecord);
  if (!isRecord(value)) {
    const aliasMessage = aliases.length ? `; aliases checked: ${aliases.join(', ')}` : '';
    issues.push({ path: `${path}.${key}`, message: `must be an object${aliasMessage}` });
    return {};
  }
  return value;
}

function decodeClientType(value: string, issues: DecodeIssue[]): ContractV2ClientType {
  if (value === 'web_pc' || value === 'wx_mini' || value === 'harmony_h5') {
    return value;
  }
  issues.push({ path: 'pageInfo.clientType', message: `unsupported client type ${value || '<empty>'}` });
  return 'web_pc';
}

function decodeViewType(value: string, path: string, issues: DecodeIssue[]): ContractV2ViewType {
  if (value === 'form' || value === 'list' || value === 'table' || value === 'kanban' || value === 'tree' || value === 'pivot' || value === 'graph' || value === 'calendar' || value === 'gantt' || value === 'activity' || value === 'dashboard' || value === 'combine') {
    return value;
  }
  issues.push({ path, message: `unsupported view type ${value || '<empty>'}` });
  return 'form';
}

function decodeLayoutType(value: string, path: string, issues: DecodeIssue[]): ContractV2LayoutType {
  if (value === 'form' || value === 'table' || value === 'kanban' || value === 'tree' || value === 'pivot' || value === 'graph' || value === 'calendar' || value === 'gantt' || value === 'activity' || value === 'dashboard' || value === 'combine') {
    return value;
  }
  issues.push({ path, message: `unsupported layout type ${value || '<empty>'}` });
  return 'form';
}

function decodeAdaptMode(value: string, path: string, issues: DecodeIssue[]): ContractV2AdaptMode {
  if (value === 'pc' || value === 'mobile') {
    return value;
  }
  issues.push({ path, message: `unsupported adapt mode ${value || '<empty>'}` });
  return 'pc';
}

function decodeTriggerType(value: string, path: string, issues: DecodeIssue[]): ContractV2TriggerType {
  if (value === 'change' || value === 'click' || value === 'select' || value === 'refresh' || value === 'add' || value === 'delete' || value === 'confirm' || value === 'submit' || value === 'blur' || value === 'focus') {
    return value;
  }
  issues.push({ path, message: `unsupported trigger type ${value || '<empty>'}` });
  return 'click';
}

function decodeDispatchMode(value: string, path: string, issues: DecodeIssue[]): ContractV2DispatchMode {
  if (value === 'local' || value === 'server' || value === 'serverDebounced' || value === 'serverBlocking') {
    return value;
  }
  issues.push({ path, message: `unsupported dispatch mode ${value || '<empty>'}` });
  return 'local';
}

function decodeTargetScope(value: string, path: string, issues: DecodeIssue[]): ContractV2TargetScope {
  if (value === 'widget' || value === 'container' || value === 'page' || value === 'dataSource' || value === 'runtime') {
    return value;
  }
  issues.push({ path, message: `unsupported target scope ${value || '<empty>'}` });
  return 'page';
}

function decodeRefreshMode(value: string, path: string, issues: DecodeIssue[]): ContractV2RefreshMode {
  if (value === 'none' || value === 'partial' || value === 'full') {
    return value;
  }
  issues.push({ path, message: `unsupported refresh mode ${value || '<empty>'}` });
  return 'none';
}

function decodeAuth(value: string, path: string, issues: DecodeIssue[]): ContractV2Auth | undefined {
  if (!value) return undefined;
  if (value === 'none' || value === 'read' || value === 'edit' || value === 'admin') {
    return value;
  }
  issues.push({ path, message: `unsupported auth ${value}` });
  return undefined;
}

function decodePageRenderMode(value: string, path: string, issues: DecodeIssue[]): ContractV2PageRenderMode {
  if (value === 'governed') {
    return value;
  }
  issues.push({ path, message: `unsupported render mode ${value || '<empty>'}` });
  return 'governed';
}

function decodePatchStrategy(value: string, path: string, issues: DecodeIssue[]): ContractV2PatchStrategy {
  if (value === 'incremental' || value === 'full') {
    return value;
  }
  issues.push({ path, message: `unsupported patch strategy ${value || '<empty>'}` });
  return 'incremental';
}

function decodeCachePolicy(value: string, path: string, issues: DecodeIssue[]): ContractV2CachePolicy {
  if (value === 'none' || value === 'etag' || value === 'snapshot') {
    return value;
  }
  issues.push({ path, message: `unsupported cache policy ${value || '<empty>'}` });
  return 'none';
}

function decodeRenderStrategy(value: string, path: string, issues: DecodeIssue[]): ContractV2RenderStrategy | undefined {
  if (!value) return undefined;
  if (value === 'sync' || value === 'scheduled' || value === 'virtualized') {
    return value;
  }
  issues.push({ path, message: `unsupported render strategy ${value}` });
  return undefined;
}

function decodePatchOperation(value: string, path: string, issues: DecodeIssue[]): ContractV2PatchOperation | null {
  if (value === 'replace' || value === 'merge' || value === 'append' || value === 'remove' || value === 'reorder' || value === 'invalidate') {
    return value;
  }
  issues.push({ path, message: `unsupported patch operation ${value || '<empty>'}` });
  return null;
}

function requiredRecord(source: ContractV2Dictionary, key: string, path: string, issues: DecodeIssue[]): ContractV2Dictionary {
  const value = source[key];
  if (isRecord(value)) return value;
  issues.push({ path: `${path}.${key}`, message: 'must be an object' });
  return {};
}

function requiredArray(source: ContractV2Dictionary, key: string, path: string, issues: DecodeIssue[]): unknown[] {
  const value = source[key];
  if (Array.isArray(value)) return value;
  issues.push({ path: `${path}.${key}`, message: 'must be an array' });
  return [];
}

function requiredIntegerInRange(
  source: ContractV2Dictionary,
  key: string,
  path: string,
  issues: DecodeIssue[],
  fallback: number,
): number {
  const value = Number(source[key]);
  if (Number.isInteger(value) && value >= 1 && value <= 24) return value;
  issues.push({ path: `${path}.${key}`, message: 'must be an integer between 1 and 24' });
  return fallback;
}

function decodePageInfo(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2PageInfo {
  const contractVersion = requiredString(source, 'contractVersion', 'pageInfo', issues);
  if (!/^2\.\d+\.\d+$/.test(contractVersion)) {
    issues.push({ path: 'pageInfo.contractVersion', message: 'must be semantic version 2.x.y' });
  }
  return {
    pageId: requiredString(source, 'pageId', 'pageInfo', issues),
    sceneKey: requiredString(source, 'sceneKey', 'pageInfo', issues),
    pageName: requiredString(source, 'pageName', 'pageInfo', issues),
    model: requiredString(source, 'model', 'pageInfo', issues),
    viewType: decodeViewType(requiredString(source, 'viewType', 'pageInfo', issues), 'pageInfo.viewType', issues),
    layoutType: decodeLayoutType(requiredString(source, 'layoutType', 'pageInfo', issues), 'pageInfo.layoutType', issues),
    renderMode: decodePageRenderMode(requiredString(source, 'renderMode', 'pageInfo', issues), 'pageInfo.renderMode', issues),
    contractVersion,
    clientType: decodeClientType(requiredString(source, 'clientType', 'pageInfo', issues), issues),
  };
}

function decodeWidget(raw: unknown, path: string, issues: DecodeIssue[]): ContractV2Widget | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'widget must be an object' });
    return null;
  }
  const componentConfig = requiredRecord(raw, 'componentConfig', path, issues);
  const fieldCode = requiredString(raw, 'fieldCode', path, issues);
  const widgetId = requiredString(raw, 'widgetId', path, issues);
  const widgetType = requiredString(raw, 'widgetType', path, issues);
  const componentKey = requiredString(raw, 'componentKey', path, issues);
  if (!widgetId || !fieldCode) return null;
  return {
    widgetId,
    widgetType,
    fieldCode,
    label: requiredString(raw, 'label', path, issues),
    span: requiredIntegerInRange(raw, 'span', path, issues, 24),
    componentKey,
    capabilities: asStringArray(raw.capabilities),
    componentConfig,
    ...(isRecord(raw.fieldDescriptor) ? { fieldDescriptor: raw.fieldDescriptor } : {}),
    ...(asString(raw.fieldType || raw.field_type) ? { fieldType: asString(raw.fieldType || raw.field_type) } : {}),
    ...(asString(raw.relation) ? { relation: asString(raw.relation) } : {}),
    ...(isRecord(raw.formStructureRole) ? { formStructureRole: raw.formStructureRole } : {}),
  };
}

function structuralContainerText(raw: ContractV2Dictionary, key: 'containerId' | 'containerType' | 'title'): string {
  if (key === 'containerId') {
    return asString(raw.containerId || raw.widgetId || raw.name);
  }
  if (key === 'containerType') return asString(raw.containerType || raw.type);
  // Structural identity is never user-facing copy. Native nodes commonly carry
  // only `name`/`widgetId`; neither is a display title.
  if (asString(raw.type || raw.containerType).toLowerCase() === 'field') {
    return asString(raw.title);
  }
  return asString(raw.title || raw.label || raw.string);
}

function decodeContainer(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
  nestedNativeNode = false,
): ContractV2Container | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'container must be an object' });
    return null;
  }
  const containerId = nestedNativeNode
    ? structuralContainerText(raw, 'containerId')
    : requiredString(raw, 'containerId', path, issues);
  const containerType = nestedNativeNode
    ? structuralContainerText(raw, 'containerType')
    : requiredString(raw, 'containerType', path, issues);
  if (nestedNativeNode && !containerId) issues.push({ path: `${path}.containerId`, message: 'requires a stable native identity' });
  if (nestedNativeNode && !containerType) issues.push({ path: `${path}.containerType`, message: 'requires a native node type' });
  if (!containerId || !containerType) return null;
  const childRows = nestedNativeNode && !Object.prototype.hasOwnProperty.call(raw, 'children')
    ? []
    : requiredArray(raw, 'children', path, issues);
  const children = childRows
    .map((item, index) => decodeContainer(item, `${path}.children[${index}]`, issues, true))
    .filter((item): item is ContractV2Container => Boolean(item));
  const decodeNodeList = (key: 'pages' | 'tabs' | 'nodes' | 'items'): ContractV2Container[] => (
    Array.isArray(raw[key]) ? raw[key] : []
  )
    .map((item, index) => decodeContainer(item, `${path}.${key}[${index}]`, issues, true))
    .filter((item): item is ContractV2Container => Boolean(item));
  const widgetRows = nestedNativeNode && !Object.prototype.hasOwnProperty.call(raw, 'widgetList')
    ? []
    : requiredArray(raw, 'widgetList', path, issues);
  const widgetList = widgetRows
    .map((item, index) => decodeWidget(item, `${path}.widgetList[${index}]`, issues))
    .filter((item): item is ContractV2Widget => Boolean(item));
  const pages = decodeNodeList('pages');
  const tabs = decodeNodeList('tabs');
  const nodes = decodeNodeList('nodes');
  const items = decodeNodeList('items');
  const attributes = asRecord(raw.attributes);
  const fieldInfo = asRecord(raw.fieldInfo);
  const action = asRecord(raw.action);
  const modifiers = asRecord(raw.modifiers);
  const formStructure = asRecord(raw.formStructure);
  const formStructureRole = asRecord(raw.formStructureRole);
  const sourceAuthority = asRecord(raw.sourceAuthority);
  const componentConfig = asRecord(raw.componentConfig);
  const fieldCode = asString(raw.fieldCode || raw.name);
  const widgetId = asString(raw.widgetId);
  const nativeLocator = asString(raw.nativeLocator);
  const occurrenceIndex = Number(raw.occurrenceIndex);
  const sourcePosition = Number(raw.sourcePosition);
  if (nestedNativeNode && containerType.toLowerCase() === 'field' && widgetId.includes('.occ.')) {
    if (!nativeLocator) issues.push({ path: `${path}.nativeLocator`, message: 'form field occurrence requires nativeLocator' });
    if (!Number.isInteger(occurrenceIndex) || occurrenceIndex < 1) issues.push({ path: `${path}.occurrenceIndex`, message: 'must be a positive integer' });
    if (!Number.isInteger(sourcePosition) || sourcePosition < 0) issues.push({ path: `${path}.sourcePosition`, message: 'must be a non-negative integer' });
  }
  return {
    containerId,
    containerType,
    type: asString(raw.type) || containerType,
    ...(asString(raw.name) ? { name: asString(raw.name) } : {}),
    ...(fieldCode ? { fieldCode } : {}),
    ...(asString(raw.string) ? { string: asString(raw.string) } : {}),
    ...(asString(raw.label) ? { label: asString(raw.label) } : {}),
    ...(optionalBoolean(raw.nolabel) !== undefined ? { nolabel: optionalBoolean(raw.nolabel) } : {}),
    ...(asString(raw.text) ? { text: asString(raw.text) } : {}),
    title: nestedNativeNode
      ? structuralContainerText(raw, 'title')
      : requiredDisplayString(raw, 'title', path, issues),
    span: !Object.prototype.hasOwnProperty.call(raw, 'span')
      ? 24
      : requiredIntegerInRange(raw, 'span', path, issues, 24),
    ...(asString(raw.styleToken) ? { styleToken: asString(raw.styleToken) } : {}),
    ...(Number(raw.cols || raw.col) ? { cols: Number(raw.cols || raw.col) } : {}),
    ...(Number(raw.columns) ? { columns: Number(raw.columns) } : {}),
    ...(asString(raw.widget) ? { widget: asString(raw.widget) } : {}),
    ...(widgetId ? { widgetId } : {}),
    ...(nativeLocator ? { nativeLocator } : {}),
    ...(Number.isInteger(occurrenceIndex) ? { occurrenceIndex } : {}),
    ...(Number.isInteger(sourcePosition) ? { sourcePosition } : {}),
    ...(asString(raw.componentKey) ? { componentKey: asString(raw.componentKey) } : {}),
    ...(Object.keys(componentConfig).length ? { componentConfig } : {}),
    ...(Object.keys(attributes).length ? { attributes } : {}),
    ...(Object.keys(fieldInfo).length ? { fieldInfo } : {}),
    ...(asString(raw.buttonType) ? { buttonType: asString(raw.buttonType) } : {}),
    ...(Object.keys(action).length ? { action } : {}),
    ...(Object.keys(modifiers).length ? { modifiers } : {}),
    ...(Object.prototype.hasOwnProperty.call(raw, 'invisible') ? { invisible: raw.invisible } : {}),
    ...(Object.prototype.hasOwnProperty.call(raw, 'readonly') ? { readonly: raw.readonly } : {}),
    ...(Object.prototype.hasOwnProperty.call(raw, 'required') ? { required: raw.required } : {}),
    ...(Object.keys(formStructure).length ? { formStructure } : {}),
    ...(Object.keys(formStructureRole).length ? { formStructureRole } : {}),
    ...(Object.keys(sourceAuthority).length ? { sourceAuthority } : {}),
    children,
    ...(pages.length ? { pages } : {}),
    ...(tabs.length ? { tabs } : {}),
    ...(nodes.length ? { nodes } : {}),
    ...(items.length ? { items } : {}),
    widgetList,
  };
}

function decodeLayoutContract(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2LayoutContract {
  const containerTreeRaw = Array.isArray(source.containerTree) ? source.containerTree : [];
  if (!Array.isArray(source.containerTree)) {
    issues.push({ path: 'layoutContract.containerTree', message: 'must be an array' });
  }
  const containerTree = containerTreeRaw
    .map((item, index) => decodeContainer(item, `layoutContract.containerTree[${index}]`, issues))
    .filter((item): item is ContractV2Container => Boolean(item));
  return {
    pageId: requiredString(source, 'pageId', 'layoutContract', issues),
    layoutType: decodeLayoutType(requiredString(source, 'layoutType', 'layoutContract', issues), 'layoutContract.layoutType', issues),
    adaptMode: decodeAdaptMode(requiredString(source, 'adaptMode', 'layoutContract', issues), 'layoutContract.adaptMode', issues),
    containerTree,
    layoutHints: requiredRecord(source, 'layoutHints', 'layoutContract', issues),
    componentRegistry: requiredRecord(source, 'componentRegistry', 'layoutContract', issues),
    ...(Object.keys(asRecord(source.listProfile)).length
      ? { listProfile: asRecord(source.listProfile) }
      : {}),
  };
}

function decodeActionRule(raw: unknown, path: string, issues: DecodeIssue[]): ContractV2ActionRule | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'action rule must be an object' });
    return null;
  }
  const actionId = requiredString(raw, 'actionId', path, issues);
  if (!actionId) return null;
  const target = asRecord(raw.target);
  const button = asRecord(raw.button);
  const visible = asRecord(raw.visible);
  const modifiers = asRecord(raw.modifiers);
  const presentation = asRecord(raw.presentation);
  const actionSafety = asRecord(raw.actionSafety);
  const submitPolicy = asRecord(raw.submitPolicy);
  const tracePolicy = asRecord(raw.tracePolicy);
  const sourceTrace = Array.isArray(raw.sourceTrace)
    ? raw.sourceTrace.map((item) => asRecord(item)).filter((item) => Object.keys(item).length > 0)
    : [];
  const permissionConstraints = asRecord(raw.permissionConstraints);
  const nativeIdentity = asRecord(raw.nativeIdentity);
  const allowed = optionalBoolean(raw.allowed);
  const enabled = optionalBoolean(raw.enabled);
  const disabled = optionalBoolean(raw.disabled);
  return {
    actionId,
    ...(optionalString(raw, 'backendIdentity') ? { backendIdentity: optionalString(raw, 'backendIdentity') } : {}),
    ...(Object.keys(nativeIdentity).length ? { nativeIdentity } : {}),
    triggerType: decodeTriggerType(requiredString(raw, 'triggerType', path, issues), `${path}.triggerType`, issues),
    sourceWidgetId: requiredString(raw, 'sourceWidgetId', path, issues),
    targetIds: asStringArray(raw.targetIds),
    dispatchMode: decodeDispatchMode(requiredString(raw, 'dispatchMode', path, issues), `${path}.dispatchMode`, issues),
    targetScope: decodeTargetScope(requiredString(raw, 'targetScope', path, issues), `${path}.targetScope`, issues),
    refreshMode: decodeRefreshMode(requiredString(raw, 'refreshMode', path, issues), `${path}.refreshMode`, issues),
    ...(optionalString(raw, 'actionKey') ? { actionKey: optionalString(raw, 'actionKey') } : {}),
    ...(optionalString(raw, 'label') ? { label: optionalString(raw, 'label') } : {}),
    ...(optionalString(raw, 'intent') ? { intent: optionalString(raw, 'intent') } : {}),
    ...(Object.keys(target).length ? { target } : {}),
    ...(Object.keys(button).length ? { button } : {}),
    ...(Object.keys(visible).length ? { visible } : {}),
    ...(Object.keys(modifiers).length ? { modifiers } : {}),
    ...(Object.prototype.hasOwnProperty.call(raw, 'invisible') ? { invisible: raw.invisible } : {}),
    ...(allowed !== undefined ? { allowed } : {}),
    ...(enabled !== undefined ? { enabled } : {}),
    ...(disabled !== undefined ? { disabled } : {}),
    ...(asStringArray(raw.visibleProfiles).length ? { visibleProfiles: asStringArray(raw.visibleProfiles) } : {}),
    ...(Object.keys(presentation).length ? { presentation } : {}),
    ...(Object.keys(actionSafety).length ? { actionSafety } : {}),
    ...(Object.keys(submitPolicy).length ? { submitPolicy } : {}),
    ...(Object.keys(tracePolicy).length ? { tracePolicy } : {}),
    ...(sourceTrace.length ? { sourceTrace } : {}),
    ...(optionalString(raw, 'presentationAuthority') ? { presentationAuthority: optionalString(raw, 'presentationAuthority') } : {}),
    ...(Number.isInteger(raw.presentationPriority) ? { presentationPriority: Number(raw.presentationPriority) } : {}),
    ...(optionalString(raw, 'sourceActionKey') ? { sourceActionKey: optionalString(raw, 'sourceActionKey') } : {}),
    ...(optionalString(raw, 'sourceChannel') ? { sourceChannel: optionalString(raw, 'sourceChannel') } : {}),
    ...(Object.keys(permissionConstraints).length ? { permissionConstraints } : {}),
    ...(optionalString(raw, 'reasonCode') ? { reasonCode: optionalString(raw, 'reasonCode') } : {}),
    ...(optionalBoolean(raw.entitlementEvaluated) !== undefined ? { entitlementEvaluated: optionalBoolean(raw.entitlementEvaluated) } : {}),
  };
}

export function decodeContractV2ActionRule(value: unknown): ContractV2ActionRule {
  const issues: DecodeIssue[] = [];
  const decoded = decodeActionRule(value, 'actionRule', issues);
  if (!decoded || issues.length) throw new ContractV2DecodeError(issues);
  return decoded;
}

function decodeActionContract(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2ActionContract {
  const actionRuleListRaw = Array.isArray(source.actionRuleList) ? source.actionRuleList : [];
  if (!Array.isArray(source.actionRuleList)) {
    issues.push({ path: 'actionContract.actionRuleList', message: 'must be an array' });
  }
  const actionRuleList = actionRuleListRaw
    .map((item, index) => decodeActionRule(item, `actionContract.actionRuleList[${index}]`, issues))
    .filter((item): item is ContractV2ActionRule => Boolean(item));
  const dependencyGraphRaw = requiredRecord(source, 'dependencyGraph', 'actionContract', issues);
  const dependencyGraph = Object.entries(dependencyGraphRaw).reduce<Record<string, string[]>>((acc, [key, value]) => {
    acc[key] = asStringArray(value);
    return acc;
  }, {});
  return {
    actionRuleList,
    dependencyGraph,
    ...(Object.keys(asRecord(source.primaryResolution)).length
      ? { primaryResolution: asRecord(source.primaryResolution) }
      : {}),
    ...(Object.keys(asRecord(source.identityPolicy)).length
      ? { identityPolicy: asRecord(source.identityPolicy) }
      : {}),
    ...(Object.keys(asRecord(source.deletePolicy)).length
      ? { deletePolicy: asRecord(source.deletePolicy) }
      : {}),
    ...(Object.keys(asRecord(source.surfacePolicies)).length
      ? { surfacePolicies: asRecord(source.surfacePolicies) }
      : {}),
  };
}

function decodeRowsMap(value: unknown): Record<string, unknown[]> {
  const rows = asRecord(value);
  return Object.entries(rows).reduce<Record<string, unknown[]>>((acc, [key, item]) => {
    acc[key] = Array.isArray(item) ? item : [];
    return acc;
  }, {});
}

function decodeDataSources(value: unknown): Record<string, ContractV2Dictionary> {
  const rows = asRecord(value);
  return Object.entries(rows).reduce<Record<string, ContractV2Dictionary>>((acc, [key, item]) => {
    acc[key] = asRecord(item);
    return acc;
  }, {});
}

function decodeVisibleFields(value: unknown, path: string, issues: DecodeIssue[]): ContractV2VisibleFields | undefined {
  const row = asRecord(value);
  const fields = asStringArray(row.fields);
  if (!fields.length) {
    if (Object.keys(row).length) {
      issues.push({ path: `${path}.fields`, message: 'must be a non-empty string array' });
    }
    return undefined;
  }
  const sourceAuthority = asRecord(row.sourceAuthority);
  return {
    fields,
    ...(Object.keys(sourceAuthority).length ? { sourceAuthority } : {}),
  };
}

function decodeFieldGroups(value: unknown, path: string, issues: DecodeIssue[]): ContractV2FieldGroups | undefined {
  const row = asRecord(value);
  const rawGroups = Array.isArray(row.groups) ? row.groups : [];
  const groups = rawGroups
    .map((item) => asRecord(item))
    .filter((item) => Object.keys(item).length > 0);
  if (!groups.length) {
    if (Object.keys(row).length) {
      issues.push({ path: `${path}.groups`, message: 'must be a non-empty object array' });
    }
    return undefined;
  }
  const sourceAuthority = asRecord(row.sourceAuthority);
  return {
    groups,
    ...(Object.keys(sourceAuthority).length ? { sourceAuthority } : {}),
  };
}

function decodeSourceContext(value: unknown, issues: DecodeIssue[]): ContractV2SourceContext | undefined {
  if (value === undefined) return undefined;
  if (!isRecord(value)) {
    issues.push({ path: 'dataContract.dataMeta.sourceContext', message: 'must be an object' });
    return undefined;
  }
  const row = value as ContractV2Dictionary;
  const allowed = new Set(['context', 'domain', 'contextRaw', 'domainRaw', 'renderProfile', 'order', 'limit']);
  Object.keys(row).filter((key) => !allowed.has(key)).forEach((key) => {
    issues.push({ path: `dataContract.dataMeta.sourceContext.${key}`, message: 'is not allowed' });
  });
  const context = optionalRecord(row, 'context', 'dataContract.dataMeta.sourceContext', issues);
  const domain = row.domain;
  if (domain !== undefined && !Array.isArray(domain)) {
    issues.push({ path: 'dataContract.dataMeta.sourceContext.domain', message: 'must be an array' });
  }
  for (const key of ['contextRaw', 'domainRaw', 'order'] as const) {
    if (row[key] !== undefined && typeof row[key] !== 'string') {
      issues.push({ path: `dataContract.dataMeta.sourceContext.${key}`, message: 'must be a string' });
    }
  }
  const renderProfile = asString(row.renderProfile);
  if (row.renderProfile !== undefined && !['create', 'edit', 'readonly'].includes(renderProfile)) {
    issues.push({ path: 'dataContract.dataMeta.sourceContext.renderProfile', message: 'must be create, edit, or readonly' });
  }
  const limit = Number(row.limit);
  if (row.limit !== undefined && (!Number.isInteger(limit) || limit < 1)) {
    issues.push({ path: 'dataContract.dataMeta.sourceContext.limit', message: 'must be a positive integer' });
  }
  return {
    ...(context ? { context } : {}),
    ...(Array.isArray(domain) ? { domain } : {}),
    ...(typeof row.contextRaw === 'string' ? { contextRaw: row.contextRaw } : {}),
    ...(typeof row.domainRaw === 'string' ? { domainRaw: row.domainRaw } : {}),
    ...(['create', 'edit', 'readonly'].includes(renderProfile) ? { renderProfile: renderProfile as 'create' | 'edit' | 'readonly' } : {}),
    ...(typeof row.order === 'string' ? { order: row.order } : {}),
    ...(Number.isInteger(limit) && limit >= 1 ? { limit } : {}),
  };
}

function decodeDataMeta(value: unknown, issues: DecodeIssue[]): ContractV2DataMeta {
  const row = asRecord(value);
  const businessOperationProfile = asRecord(row.businessOperationProfile);
  const sourceContext = decodeSourceContext(row.sourceContext, issues);
  const forbiddenKeys = [
    'business_operation_profile',
    'visible_fields',
    'field_groups',
    'legacy' + 'ContractProjection',
    'legacy_contract' + '_projection',
  ];
  forbiddenKeys.forEach((key) => {
    if (Object.prototype.hasOwnProperty.call(row, key)) {
      issues.push({ path: `dataContract.dataMeta.${key}`, message: 'is not allowed in strict V2 dataMeta' });
    }
  });
  const visibleFields = decodeVisibleFields(row.visibleFields, 'dataContract.dataMeta.visibleFields', issues);
  const fieldGroups = decodeFieldGroups(row.fieldGroups, 'dataContract.dataMeta.fieldGroups', issues);
  return {
    ...row,
    ...(Object.keys(businessOperationProfile).length ? { businessOperationProfile } : {}),
    ...(visibleFields ? { visibleFields } : {}),
    ...(fieldGroups ? { fieldGroups } : {}),
    ...(sourceContext ? { sourceContext } : {}),
  };
}

function decodeDataContract(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2DataContract {
  const treeData = decodeRowsMap(source.treeData);
  const ganttData = decodeRowsMap(source.ganttData);
  return {
    mainData: requiredRecord(source, 'mainData', 'dataContract', issues),
    tableRows: decodeRowsMap(requiredRecord(source, 'tableRows', 'dataContract', issues)),
    relationRows: decodeRowsMap(requiredRecord(source, 'relationRows', 'dataContract', issues)),
    dictData: requiredRecord(source, 'dictData', 'dataContract', issues),
    pagination: requiredRecord(source, 'pagination', 'dataContract', issues),
    dataSource: decodeDataSources(requiredRecord(source, 'dataSource', 'dataContract', issues)),
    dataMeta: decodeDataMeta(requiredRecord(source, 'dataMeta', 'dataContract', issues), issues),
    ...(Object.keys(treeData).length ? { treeData } : {}),
    ...(Object.keys(ganttData).length ? { ganttData } : {}),
  };
}

function decodeGlobalStatus(source: ContractV2Dictionary): ContractV2GlobalStatus {
  const modelRights = asRecord(source.modelRights);
  const recordRights = asRecord(source.recordRights);
  const viewCapabilities = asRecord(source.viewCapabilities);
  const entryCapabilities = asRecord(source.entryCapabilities);
  const effectiveRecordCapabilities = asRecord(source.effectiveRecordCapabilities);
  return {
    pageVisible: optionalBoolean(source.pageVisible),
    ...(optionalString(source, 'pageAuth') ? { pageAuth: optionalString(source, 'pageAuth') } : {}),
    ...(optionalString(source, 'reasonCode')
      ? { reasonCode: optionalString(source, 'reasonCode') }
      : {}),
    ...(Object.keys(modelRights).length ? { modelRights } : {}),
    ...(Object.keys(recordRights).length ? { recordRights } : {}),
    ...(Object.keys(viewCapabilities).length ? { viewCapabilities } : {}),
    ...(Object.keys(entryCapabilities).length ? { entryCapabilities } : {}),
    ...(Object.keys(effectiveRecordCapabilities).length ? { effectiveRecordCapabilities } : {}),
    ...(optionalString(source, 'effectiveRenderProfile')
      ? { effectiveRenderProfile: optionalString(source, 'effectiveRenderProfile') }
      : {}),
    ...(optionalString(source, 'workflowPhase') ? { workflowPhase: optionalString(source, 'workflowPhase') } : {}),
    ...(optionalString(source, 'approvalPhase') ? { approvalPhase: optionalString(source, 'approvalPhase') } : {}),
  };
}

function decodeWidgetStatus(raw: unknown, path: string, issues: DecodeIssue[]): ContractV2WidgetStatus | null {
  if (!isRecord(raw)) return null;
  const widgetId = asString(raw.widgetId);
  if (!widgetId) return null;
  const auth = decodeAuth(asString(raw.auth), `${path}.auth`, issues);
  return {
    widgetId,
    visible: optionalBoolean(raw.visible),
    readonly: optionalBoolean(raw.readonly),
    required: optionalBoolean(raw.required),
    disabled: optionalBoolean(raw.disabled),
    ...(optionalString(raw, 'placeholder') ? { placeholder: optionalString(raw, 'placeholder') } : {}),
    ...(auth ? { auth } : {}),
    ...(optionalString(raw, 'reasonCode')
      ? { reasonCode: optionalString(raw, 'reasonCode') }
      : {}),
  };
}

function decodeButtonStatus(raw: unknown): ContractV2ButtonStatus | null {
  if (!isRecord(raw)) return null;
  const btnId = asString(raw.btnId);
  if (!btnId) return null;
  return {
    btnId,
    ...(asString(raw.backendIdentity) ? { backendIdentity: asString(raw.backendIdentity) } : {}),
    visible: optionalBoolean(raw.visible),
    disabled: optionalBoolean(raw.disabled),
    ...(optionalString(raw, 'reasonCode')
      ? { reasonCode: optionalString(raw, 'reasonCode') }
      : {}),
  };
}

function decodeContainerStatus(raw: unknown): ContractV2ContainerStatus | null {
  if (!isRecord(raw)) return null;
  const containerId = asString(raw.containerId);
  if (!containerId) return null;
  return {
    containerId,
    visible: optionalBoolean(raw.visible),
    disabled: optionalBoolean(raw.disabled),
    ...(optionalString(raw, 'reasonCode')
      ? { reasonCode: optionalString(raw, 'reasonCode') }
      : {}),
  };
}

function decodeSelectorStatus(raw: unknown): ContractV2SelectorStatus | null {
  if (!isRecord(raw)) return null;
  const selector = asString(raw.selector);
  if (!selector) return null;
  return {
    selector,
    visible: optionalBoolean(raw.visible),
    readonly: optionalBoolean(raw.readonly),
    required: optionalBoolean(raw.required),
    disabled: optionalBoolean(raw.disabled),
    ...(optionalString(raw, 'reasonCode')
      ? { reasonCode: optionalString(raw, 'reasonCode') }
      : {}),
  };
}

function decodeStatusContract(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2StatusContract {
  return {
    globalStatus: decodeGlobalStatus(requiredRecord(source, 'globalStatus', 'statusContract', issues)),
    widgetStatus: requiredArray(source, 'widgetStatus', 'statusContract', issues)
      .map((item, index) => decodeWidgetStatus(item, `statusContract.widgetStatus[${index}]`, issues))
      .filter((item): item is ContractV2WidgetStatus => Boolean(item)),
    buttonStatus: requiredArray(source, 'buttonStatus', 'statusContract', issues)
      .map(decodeButtonStatus)
      .filter((item): item is ContractV2ButtonStatus => Boolean(item)),
    containerStatus: requiredArray(source, 'containerStatus', 'statusContract', issues)
      .map(decodeContainerStatus)
      .filter((item): item is ContractV2ContainerStatus => Boolean(item)),
    selectorStatus: requiredArray(source, 'selectorStatus', 'statusContract', issues)
      .map(decodeSelectorStatus)
      .filter((item): item is ContractV2SelectorStatus => Boolean(item)),
  };
}

function validateFormOccurrenceAuthority(
  layoutContract: ContractV2LayoutContract,
  statusContract: ContractV2StatusContract,
  issues: DecodeIssue[],
): void {
  const occurrenceContainers = new Map<string, ContractV2Container>();
  const widgetsById = new Map<string, ContractV2Widget>();
  const formFieldContainers: ContractV2Container[] = [];
  const walk = (rows: ContractV2Container[]) => rows.forEach((row) => {
    row.widgetList.forEach((widget) => widgetsById.set(widget.widgetId, widget));
    if (row.containerType.toLowerCase() === 'field') formFieldContainers.push(row);
    walk(row.children);
    walk(row.pages || []);
    walk(row.tabs || []);
    walk(row.nodes || []);
    walk(row.items || []);
  });
  walk(layoutContract.containerTree);

  const fieldCodeCounts = new Map<string, number>();
  formFieldContainers.forEach((row) => {
    const fieldCode = String(row.fieldCode || '').trim();
    if (fieldCode) fieldCodeCounts.set(fieldCode, (fieldCodeCounts.get(fieldCode) || 0) + 1);
  });
  formFieldContainers.forEach((row) => {
    const fieldCode = String(row.fieldCode || '').trim();
    const isOccurrence = Boolean(row.nativeLocator)
      || Number.isInteger(row.occurrenceIndex)
      || (fieldCodeCounts.get(fieldCode) || 0) > 1;
    if (!isOccurrence) return;
    if (!row.widgetId || !row.nativeLocator || !Number.isInteger(row.occurrenceIndex)
      || Number(row.occurrenceIndex) < 1 || !Number.isInteger(row.sourcePosition)
      || Number(row.sourcePosition) < 0) {
      issues.push({ path: 'layoutContract.containerTree', message: `incomplete form occurrence identity ${fieldCode}` });
      return;
    }
    if (occurrenceContainers.has(row.widgetId)) {
      issues.push({ path: 'layoutContract.containerTree', message: `duplicate form occurrence widgetId ${row.widgetId}` });
    } else {
      occurrenceContainers.set(row.widgetId, row);
    }
    const widget = widgetsById.get(row.widgetId);
    if (!widget || !isRecord(widget.fieldDescriptor) || !Object.keys(widget.fieldDescriptor).length) {
      issues.push({ path: 'layoutContract.containerTree', message: `form occurrence ${row.widgetId} requires a strict field descriptor` });
    } else {
      const descriptorName = asString(widget.fieldDescriptor.name);
      const descriptorType = asString(widget.fieldDescriptor.ttype || widget.fieldDescriptor.type);
      if (descriptorName !== row.fieldCode) {
        issues.push({ path: 'layoutContract.containerTree', message: `form occurrence ${row.widgetId} descriptor identity mismatch` });
      }
      if (!descriptorType) {
        issues.push({ path: 'layoutContract.containerTree', message: `form occurrence ${row.widgetId} descriptor type is required` });
      }
      const config = isRecord(widget.componentConfig) ? widget.componentConfig : {};
      const configLocator = asString(config.native_locator || config.nativeLocator);
      const configOccurrence = Number(config.occurrence_index || config.occurrenceIndex);
      const configPosition = Number(config.source_position ?? config.sourcePosition);
      if (configLocator !== row.nativeLocator || configOccurrence !== row.occurrenceIndex
        || configPosition !== row.sourcePosition) {
        issues.push({ path: 'layoutContract.containerTree', message: `form occurrence ${row.widgetId} carrier identity mismatch` });
      }
    }
  });

  const statusCounts = new Map<string, number>();
  statusContract.widgetStatus.forEach((status) => {
    if (!occurrenceContainers.has(status.widgetId)) return;
    statusCounts.set(status.widgetId, (statusCounts.get(status.widgetId) || 0) + 1);
  });
  occurrenceContainers.forEach((_container, widgetId) => {
    const count = statusCounts.get(widgetId) || 0;
    if (count !== 1) {
      issues.push({ path: 'statusContract.widgetStatus', message: `form occurrence ${widgetId} requires exactly one status; found ${count}` });
    }
    statusContract.widgetStatus.filter((status) => status.widgetId === widgetId).forEach((status) => {
      for (const key of ['visible', 'readonly', 'required', 'disabled'] as const) {
        if (typeof status[key] !== 'boolean') {
          issues.push({ path: `statusContract.widgetStatus.${widgetId}.${key}`, message: 'form occurrence status boolean is required' });
        }
      }
      if (typeof status.auth !== 'string') {
        issues.push({ path: `statusContract.widgetStatus.${widgetId}.auth`, message: 'form occurrence auth is required' });
      } else if ((status.readonly === true || status.disabled === true) && status.auth === 'edit') {
        issues.push({ path: `statusContract.widgetStatus.${widgetId}.auth`, message: 'editable auth conflicts with readonly occurrence status' });
      }
    });
  });
  statusContract.widgetStatus.forEach((status) => {
    if (!status.widgetId || widgetsById.has(status.widgetId)) return;
    issues.push({ path: 'statusContract.widgetStatus', message: `orphan form widget status ${status.widgetId}` });
  });
  statusCounts.forEach((count, widgetId) => {
    if (count > 1) issues.push({ path: 'statusContract.widgetStatus', message: `duplicate form occurrence status ${widgetId}` });
  });
}

function decodeRuntimeContract(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2RuntimeContract {
  const renderStrategy = decodeRenderStrategy(asString(source.renderStrategy), 'runtimeContract.renderStrategy', issues);
  const patchOperations = Array.isArray(source.patchOperations)
    ? source.patchOperations
      .map((item, index) => decodePatchOperation(asString(item), `runtimeContract.patchOperations[${index}]`, issues))
      .filter((item): item is ContractV2PatchOperation => Boolean(item))
    : [];
  const collaboration = optionalRecord(source, 'collaboration', 'runtimeContract', issues);
  const businessWorkspace = optionalRecord(source, 'businessWorkspace', 'runtimeContract', issues);
  const businessActions = optionalRecordArray(source, 'businessActions', 'runtimeContract', issues);
  return {
    patchStrategy: decodePatchStrategy(requiredString(source, 'patchStrategy', 'runtimeContract', issues), 'runtimeContract.patchStrategy', issues),
    cachePolicy: decodeCachePolicy(requiredString(source, 'cachePolicy', 'runtimeContract', issues), 'runtimeContract.cachePolicy', issues),
    optimistic: requiredBoolean(source, 'optimistic', 'runtimeContract', issues, false),
    lazyContainer: asStringArray(source.lazyContainer),
    virtualization: requiredRecord(source, 'virtualization', 'runtimeContract', issues),
    retryPolicy: requiredRecord(source, 'retryPolicy', 'runtimeContract', issues),
    ...(renderStrategy ? { renderStrategy } : {}),
    ...(isRecord(source.hydration) ? { hydration: source.hydration } : {}),
    ...(patchOperations.length ? { patchOperations } : {}),
    ...(isRecord(source.tracePolicy) ? { tracePolicy: source.tracePolicy } : {}),
    ...(isRecord(source.complexityBudget) ? { complexityBudget: source.complexityBudget } : {}),
    ...(isRecord(source.aiEnvelope) ? { aiEnvelope: source.aiEnvelope } : {}),
    ...(asString(source.interactionMode) ? { interactionMode: asString(source.interactionMode) } : {}),
    ...(asString(source.actionTarget) ? { actionTarget: asString(source.actionTarget) } : {}),
    ...(collaboration ? { collaboration } : {}),
    ...(businessWorkspace ? { businessWorkspace } : {}),
    ...(businessActions ? { businessActions } : {}),
  };
}

function decodeMeta(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2Meta {
  const lifecycle = requiredRecord(source, 'lifecycle', 'meta', issues);
  const definition = requiredRecord(lifecycle, 'definition', 'meta.lifecycle', issues);
  const generation = requiredRecord(lifecycle, 'generation', 'meta.lifecycle', issues);
  const runtime = requiredRecord(lifecycle, 'runtime', 'meta.lifecycle', issues);
  const integrity = requiredRecord(lifecycle, 'integrity', 'meta.lifecycle', issues);
  return {
    etag: requiredString(source, 'etag', 'meta', issues),
    snapshotId: requiredString(source, 'snapshotId', 'meta', issues),
    traceId: requiredString(source, 'traceId', 'meta', issues),
    requestId: requiredString(source, 'requestId', 'meta', issues),
    sourceType: requiredString(source, 'sourceType', 'meta', issues),
    lifecycle: {
      lifecycleVersion: requiredString(lifecycle, 'lifecycleVersion', 'meta.lifecycle', issues),
      stage: requiredString(lifecycle, 'stage', 'meta.lifecycle', issues),
      definition: {
        schemaId: requiredString(definition, 'schemaId', 'meta.lifecycle.definition', issues),
        schemaVersion: requiredString(definition, 'schemaVersion', 'meta.lifecycle.definition', issues),
        schemaSha256: requiredString(definition, 'schemaSha256', 'meta.lifecycle.definition', issues),
        contractVersion: requiredString(definition, 'contractVersion', 'meta.lifecycle.definition', issues),
        normativeStatus: requiredString(definition, 'normativeStatus', 'meta.lifecycle.definition', issues),
      },
      generation: {
        generator: requiredString(generation, 'generator', 'meta.lifecycle.generation', issues),
        generatorVersion: requiredString(generation, 'generatorVersion', 'meta.lifecycle.generation', issues),
        sourceType: requiredString(generation, 'sourceType', 'meta.lifecycle.generation', issues),
        sourceSha256: requiredString(generation, 'sourceSha256', 'meta.lifecycle.generation', issues),
      },
      runtime: {
        requestId: requiredString(runtime, 'requestId', 'meta.lifecycle.runtime', issues),
        traceId: requiredString(runtime, 'traceId', 'meta.lifecycle.runtime', issues),
        clientType: requiredString(runtime, 'clientType', 'meta.lifecycle.runtime', issues),
        traceSource: requiredString(runtime, 'traceSource', 'meta.lifecycle.runtime', issues),
      },
      integrity: {
        algorithm: requiredString(integrity, 'algorithm', 'meta.lifecycle.integrity', issues),
        contractSha256: requiredString(integrity, 'contractSha256', 'meta.lifecycle.integrity', issues),
      },
      authority: requiredRecord(lifecycle, 'authority', 'meta.lifecycle', issues),
    },
  };
}

function decodeSearchContract(value: unknown, issues: DecodeIssue[]): ContractV2Dictionary | undefined {
  if (value === undefined) return undefined;
  if (!isRecord(value)) {
    issues.push({ path: '$.searchContract', message: 'must be an object' });
    return undefined;
  }
  const row = value as ContractV2Dictionary;
  const allowed = new Set([
    'default_sort', 'default_order', 'mode', 'filters', 'saved_filters', 'group_by', 'fields',
    'search_panel', 'favorites', 'custom', 'ui_labels', 'defaults',
  ]);
  Object.keys(row).filter((key) => !allowed.has(key)).forEach((key) => {
    issues.push({ path: `$.searchContract.${key}`, message: 'is not allowed' });
  });
  const out: ContractV2Dictionary = {};
  for (const key of ['default_sort', 'default_order', 'mode'] as const) {
    if (row[key] === undefined) continue;
    if (typeof row[key] !== 'string') {
      issues.push({ path: `$.searchContract.${key}`, message: 'must be a string' });
    } else {
      out[key] = row[key];
    }
  }
  for (const key of ['filters', 'saved_filters', 'group_by', 'fields'] as const) {
    const decoded = optionalRecordArray(row, key, '$.searchContract', issues);
    if (decoded) out[key] = decoded;
  }
  for (const key of ['search_panel', 'favorites', 'custom', 'ui_labels', 'defaults'] as const) {
    const decoded = optionalRecord(row, key, '$.searchContract', issues);
    if (decoded) out[key] = decoded;
  }
  return out;
}

export function decodeContractV2Snapshot(value: unknown): ContractV2Snapshot {
  const root = asRecord(value);
  const issues: DecodeIssue[] = [];
  const pageInfo = decodePageInfo(readAliasedObject(root, 'pageInfo', [], '$', issues), issues);
  const layoutContract = decodeLayoutContract(readAliasedObject(root, 'layoutContract', [], '$', issues), issues);
  const statusContract = decodeStatusContract(readAliasedObject(root, 'statusContract', [], '$', issues), issues);
  const actionContract = decodeActionContract(readAliasedObject(root, 'actionContract', [], '$', issues), issues);
  const dataContract = decodeDataContract(readAliasedObject(root, 'dataContract', [], '$', issues), issues);
  const runtimeContract = decodeRuntimeContract(readAliasedObject(root, 'runtimeContract', [], '$', issues), issues);
  const meta = decodeMeta(readAliasedObject(root, 'meta', [], '$', issues), issues);
  const formStructureContract = optionalRecord(root, 'formStructureContract', '$', issues);
  const searchContract = decodeSearchContract(root.searchContract, issues);
  const workflowContract = optionalRecord(root, 'workflowContract', '$', issues);
  validateFormOccurrenceAuthority(layoutContract, statusContract, issues);
  if (issues.length) {
    throw new ContractV2DecodeError(issues);
  }
  return {
    pageInfo,
    layoutContract,
    statusContract,
    actionContract,
    dataContract,
    runtimeContract,
    meta,
    ...(formStructureContract ? { formStructureContract } : {}),
    ...(searchContract ? { searchContract } : {}),
    ...(workflowContract ? { workflowContract } : {}),
  };
}
