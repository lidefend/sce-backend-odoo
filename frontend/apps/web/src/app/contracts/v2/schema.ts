import type {
  ContractV2ActionContract,
  ContractV2ActionRule,
  ContractV2ActivityNode,
  ContractV2ActivityNodeOccurrence,
  ContractV2ActivityProfile,
  ContractV2ActivitySourceAuthority,
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
  ContractV2FormStructureConfiguredSection,
  ContractV2FormStructureContract,
  ContractV2FormStructureGovernanceContract,
  ContractV2FormStructureGovernanceSource,
  ContractV2FormStructureGroup,
  ContractV2FormStructureRole,
  ContractV2FormStructureRoleName,
  ContractV2FormStructureSlot,
  ContractV2FormStructureSourceAuthority,
  ContractV2GlobalStatus,
  ContractV2LayoutType,
  ContractV2LayoutContract,
  ContractV2Meta,
  ContractV2PageRenderMode,
  ContractV2PageInfo,
  ContractV2CachePolicy,
  ContractV2CanonicalFormSemanticRole,
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
import { CONTRACT_V2_FORM_STRUCTURE_ROLES } from './formStructureRoles';
import { normalizeLegacyContractV2Snapshot } from './legacyLayoutNormalizer';

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

function requiredActivityString(
  source: ContractV2Dictionary,
  key: string,
  path: string,
  issues: DecodeIssue[],
): string {
  if (typeof source[key] === 'string') return source[key] as string;
  issues.push({ path: `${path}.${key}`, message: 'must be a string' });
  return '';
}

function requiredActivityNonEmptyString(
  source: ContractV2Dictionary,
  key: string,
  path: string,
  issues: DecodeIssue[],
): string {
  const value = source[key];
  if (typeof value === 'string' && value.trim()) return value;
  issues.push({ path: `${path}.${key}`, message: 'must be a non-empty string' });
  return '';
}

function requiredActivityInteger(
  source: ContractV2Dictionary,
  key: string,
  path: string,
  issues: DecodeIssue[],
  minimum: number,
): number {
  const value = source[key];
  if (typeof value === 'number' && Number.isInteger(value) && value >= minimum) return value;
  issues.push({ path: `${path}.${key}`, message: `must be an integer greater than or equal to ${minimum}` });
  return minimum;
}

function rejectUnknownKeys(
  source: ContractV2Dictionary,
  allowedKeys: readonly string[],
  path: string,
  issues: DecodeIssue[],
): void {
  const allowed = new Set(allowedKeys);
  Object.keys(source).filter((key) => !allowed.has(key)).forEach((key) => {
    issues.push({ path: `${path}.${key}`, message: 'is not allowed' });
  });
}

const FORM_STRUCTURE_ROLE_SET = new Set<ContractV2FormStructureRoleName>(
  CONTRACT_V2_FORM_STRUCTURE_ROLES,
);

function decodeFormStructureRoleName(
  value: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureRoleName {
  const role = asString(value) as ContractV2FormStructureRoleName;
  if (FORM_STRUCTURE_ROLE_SET.has(role)) return role;
  issues.push({ path, message: `unsupported form structure role ${role || '<empty>'}` });
  return 'context';
}

function decodeFormStructureRole(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureRole | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, ['role', 'slot', 'group'], path, issues);
  return {
    role: decodeFormStructureRoleName(raw.role, `${path}.role`, issues),
    slot: requiredString(raw, 'slot', path, issues),
    group: requiredString(raw, 'group', path, issues),
  };
}

function decodeUniqueStringArray(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): string[] {
  if (!Array.isArray(raw)) {
    issues.push({ path, message: 'must be an array' });
    return [];
  }
  const rows: string[] = [];
  raw.forEach((item, index) => {
    if (typeof item !== 'string' || !item.trim()) {
      issues.push({ path: `${path}[${index}]`, message: 'must be a non-empty string' });
      return;
    }
    const value = item.trim();
    if (rows.includes(value)) {
      issues.push({ path: `${path}[${index}]`, message: `duplicates ${value}` });
      return;
    }
    rows.push(value);
  });
  return rows;
}

function decodeStringMap(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): Record<string, string> {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return {};
  }
  const out: Record<string, string> = {};
  Object.entries(raw).forEach(([key, value]) => {
    if (!key.trim() || typeof value !== 'string') {
      issues.push({ path: `${path}.${key}`, message: 'must be a string keyed by a non-empty identity' });
      return;
    }
    out[key] = value;
  });
  return out;
}

function decodeBooleanMap(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): Record<string, boolean> {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return {};
  }
  const out: Record<string, boolean> = {};
  Object.entries(raw).forEach(([key, value]) => {
    if (!key.trim() || typeof value !== 'boolean') {
      issues.push({ path: `${path}.${key}`, message: 'must be a boolean keyed by a non-empty identity' });
      return;
    }
    out[key] = value;
  });
  return out;
}

function decodePositiveIntegerMap(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): Record<string, number> {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return {};
  }
  const out: Record<string, number> = {};
  Object.entries(raw).forEach(([key, value]) => {
    if (!key.trim() || typeof value !== 'number' || !Number.isInteger(value) || value < 1) {
      issues.push({ path: `${path}.${key}`, message: 'must be a positive integer keyed by a non-empty identity' });
      return;
    }
    out[key] = value;
  });
  return out;
}

function requiredIntegerInRange(
  source: ContractV2Dictionary,
  key: string,
  path: string,
  issues: DecodeIssue[],
  fallback: number,
): number {
  const value = source[key];
  if (typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= 24) return value;
  issues.push({ path: `${path}.${key}`, message: 'must be an integer between 1 and 24' });
  return fallback;
}

function decodePageInfo(source: ContractV2Dictionary, issues: DecodeIssue[]): ContractV2PageInfo {
  const contractVersion = requiredString(source, 'contractVersion', 'pageInfo', issues);
  if (!/^2\.(0|1|2)\.\d+$/.test(contractVersion)) {
    issues.push({ path: 'pageInfo.contractVersion', message: 'must be a negotiated 2.0, 2.1, or 2.2 version' });
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
  rejectUnknownKeys(raw, [
    'widgetId', 'widgetType', 'fieldCode', 'label', 'span', 'componentKey', 'capabilities',
    'componentConfig', 'fieldDescriptor', 'fieldType', 'relation', 'formStructureRole',
    'ownerContainerId', 'nativeLocator', 'occurrenceIndex', 'sourcePosition',
  ], path, issues);
  const componentConfig = requiredRecord(raw, 'componentConfig', path, issues);
  const fieldCode = requiredString(raw, 'fieldCode', path, issues);
  const widgetId = requiredString(raw, 'widgetId', path, issues);
  const widgetType = requiredString(raw, 'widgetType', path, issues);
  const componentKey = requiredString(raw, 'componentKey', path, issues);
  const ownerContainerId = requiredString(raw, 'ownerContainerId', path, issues);
  const formStructureRole = raw.formStructureRole === undefined
    ? null
    : decodeFormStructureRole(raw.formStructureRole, `${path}.formStructureRole`, issues);
  const nativeLocator = optionalString(raw, 'nativeLocator');
  const occurrenceIndex = raw.occurrenceIndex;
  const sourcePosition = raw.sourcePosition;
  if (occurrenceIndex !== undefined && (
    typeof occurrenceIndex !== 'number' || !Number.isInteger(occurrenceIndex) || occurrenceIndex < 1
  )) issues.push({ path: `${path}.occurrenceIndex`, message: 'must be a positive integer' });
  if (sourcePosition !== undefined && (
    typeof sourcePosition !== 'number' || !Number.isInteger(sourcePosition) || sourcePosition < 0
  )) issues.push({ path: `${path}.sourcePosition`, message: 'must be a non-negative integer' });
  if (Boolean(nativeLocator) !== (occurrenceIndex !== undefined)) {
    issues.push({ path, message: 'nativeLocator and occurrenceIndex must be supplied together' });
  }
  if (!widgetId || !fieldCode || !ownerContainerId) return null;
  return {
    widgetId,
    widgetType,
    fieldCode,
    label: requiredString(raw, 'label', path, issues),
    span: requiredIntegerInRange(raw, 'span', path, issues, 24),
    componentKey,
    capabilities: decodeUniqueStringArray(raw.capabilities, `${path}.capabilities`, issues),
    componentConfig,
    ownerContainerId,
    ...(nativeLocator ? { nativeLocator } : {}),
    ...(typeof occurrenceIndex === 'number' && Number.isInteger(occurrenceIndex) ? { occurrenceIndex } : {}),
    ...(typeof sourcePosition === 'number' && Number.isInteger(sourcePosition) ? { sourcePosition } : {}),
    ...(isRecord(raw.fieldDescriptor) ? { fieldDescriptor: raw.fieldDescriptor } : {}),
    ...(asString(raw.fieldType || raw.field_type) ? { fieldType: asString(raw.fieldType || raw.field_type) } : {}),
    ...(asString(raw.relation) ? { relation: asString(raw.relation) } : {}),
    ...(formStructureRole ? { formStructureRole } : {}),
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
  rejectUnknownKeys(raw, [
    'containerId', 'containerType', 'type', 'name', 'string', 'label', 'nolabel', 'text', 'title',
    'displayLabel', 'semanticTitle', 'semanticAnchor', 'span', 'styleToken', 'cols', 'columns',
    'widget', 'widgetId', 'fieldCode', 'nativeLocator', 'occurrenceIndex', 'sourcePosition',
    'componentKey', 'componentConfig', 'attributes', 'fieldInfo', 'filename', 'buttonType',
    'action', 'badge', 'modifiers', 'invisible', 'readonly', 'required', 'column_invisible',
    'domain', 'context', 'options', 'visible', 'col', 'class', 'className', 'fieldSize', 'size',
    'formStructure', 'formStructureRole', 'sourceAuthority', 'children', 'widgetList', 'fields',
  ], path, issues);
  const containerId = nestedNativeNode
    ? structuralContainerText(raw, 'containerId')
    : requiredString(raw, 'containerId', path, issues);
  const containerType = nestedNativeNode
    ? structuralContainerText(raw, 'containerType')
    : requiredString(raw, 'containerType', path, issues);
  if (nestedNativeNode && !containerId) issues.push({ path: `${path}.containerId`, message: 'requires a stable native identity' });
  if (nestedNativeNode && !containerType) issues.push({ path: `${path}.containerType`, message: 'requires a native node type' });
  if (!containerId || !containerType) return null;
  const childRows = requiredArray(raw, 'children', path, issues);
  const children = childRows
    .map((item, index) => decodeContainer(item, `${path}.children[${index}]`, issues, true))
    .filter((item): item is ContractV2Container => Boolean(item));
  const widgetRows = requiredArray(raw, 'widgetList', path, issues);
  const widgetList = widgetRows
    .map((item, index) => decodeWidget(item, `${path}.widgetList[${index}]`, issues))
    .filter((item): item is ContractV2Widget => Boolean(item));
  const attributes = asRecord(raw.attributes);
  const fieldInfo = asRecord(raw.fieldInfo);
  const action = asRecord(raw.action);
  const modifiers = asRecord(raw.modifiers);
  const formStructure = asRecord(raw.formStructure);
  const formStructureRole = raw.formStructureRole === undefined
    ? null
    : decodeFormStructureRole(raw.formStructureRole, `${path}.formStructureRole`, issues);
  const sourceAuthority = asRecord(raw.sourceAuthority);
  const componentConfig = asRecord(raw.componentConfig);
  const fieldCode = asString(raw.fieldCode || raw.name);
  const widgetId = asString(raw.widgetId);
  const nativeLocator = asString(raw.nativeLocator);
  const occurrenceIndex = raw.occurrenceIndex;
  const sourcePosition = raw.sourcePosition;
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
    ...(typeof raw.cols === 'number' && Number.isInteger(raw.cols) && raw.cols > 0 ? { cols: raw.cols } : {}),
    ...(typeof raw.columns === 'number' && Number.isInteger(raw.columns) && raw.columns > 0 ? { columns: raw.columns } : {}),
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
    ...(raw.action === null ? { action: null } : Object.keys(action).length ? { action } : {}),
    ...(Object.keys(modifiers).length ? { modifiers } : {}),
    ...(Object.prototype.hasOwnProperty.call(raw, 'invisible') ? { invisible: raw.invisible } : {}),
    ...(Object.prototype.hasOwnProperty.call(raw, 'readonly') ? { readonly: raw.readonly } : {}),
    ...(Object.prototype.hasOwnProperty.call(raw, 'required') ? { required: raw.required } : {}),
    ...(Object.keys(formStructure).length ? { formStructure } : {}),
    ...(formStructureRole ? { formStructureRole } : {}),
    ...(Object.keys(sourceAuthority).length ? { sourceAuthority } : {}),
    children,
    widgetList,
  };
}

function decodeActivityNode(raw: unknown, path: string, issues: DecodeIssue[]): ContractV2ActivityNode | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'activity node must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, [
    'tag', 'native_locator', 'occurrence_index', 'source_position', 'attributes', 'text', 'tail', 'children',
  ], path, issues);
  const tag = requiredActivityNonEmptyString(raw, 'tag', path, issues);
  const nativeLocator = requiredActivityNonEmptyString(raw, 'native_locator', path, issues);
  const occurrenceIndex = requiredActivityInteger(raw, 'occurrence_index', path, issues, 1);
  const sourcePosition = requiredActivityInteger(raw, 'source_position', path, issues, 0);
  const children = requiredArray(raw, 'children', path, issues)
    .map((child, index) => decodeActivityNode(child, `${path}.children[${index}]`, issues))
    .filter((child): child is ContractV2ActivityNode => Boolean(child));
  const nodeText = requiredActivityString(raw, 'text', path, issues);
  const nodeTail = requiredActivityString(raw, 'tail', path, issues);
  if (!tag || !nativeLocator) return null;
  return {
    tag,
    native_locator: nativeLocator,
    occurrence_index: occurrenceIndex,
    source_position: sourcePosition,
    attributes: requiredRecord(raw, 'attributes', path, issues),
    text: nodeText,
    tail: nodeTail,
    children,
  };
}

function decodeActivityNodeOccurrence(raw: unknown, path: string, issues: DecodeIssue[]): ContractV2ActivityNodeOccurrence | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'activity node occurrence must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, [
    'tag', 'native_locator', 'occurrence_index', 'source_position', 'attributes', 'text', 'tail',
  ], path, issues);
  const tag = requiredActivityNonEmptyString(raw, 'tag', path, issues);
  const nativeLocator = requiredActivityNonEmptyString(raw, 'native_locator', path, issues);
  const occurrenceIndex = requiredActivityInteger(raw, 'occurrence_index', path, issues, 1);
  const sourcePosition = requiredActivityInteger(raw, 'source_position', path, issues, 0);
  const nodeText = requiredActivityString(raw, 'text', path, issues);
  const nodeTail = requiredActivityString(raw, 'tail', path, issues);
  if (!tag || !nativeLocator) return null;
  return {
    tag,
    native_locator: nativeLocator,
    occurrence_index: occurrenceIndex,
    source_position: sourcePosition,
    attributes: requiredRecord(raw, 'attributes', path, issues),
    text: nodeText,
    tail: nodeTail,
  };
}

function decodeActivitySourceAuthority(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2ActivitySourceAuthority | undefined {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return undefined;
  }
  rejectUnknownKeys(raw, [
    'kind', 'authorities', 'projection_only', 'no_business_fact_authority', 'runtime_carrier',
  ], path, issues);
  const authorities = raw.authorities;
  const expectedAuthorities = ['ir.ui.view', 'ir.model.fields', 'ir.actions.act_window'] as const;
  const validAuthorities = Array.isArray(authorities)
    && authorities.length === expectedAuthorities.length
    && authorities.every((value, index) => typeof value === 'string' && value === expectedAuthorities[index]);
  if (!validAuthorities) {
    issues.push({ path: `${path}.authorities`, message: 'must exactly match the governed native authorities' });
  }
  if (raw.kind !== 'native_activity_view_projection') {
    issues.push({ path: `${path}.kind`, message: 'must be native_activity_view_projection' });
  }
  if (raw.runtime_carrier !== 'ui.contract.v2.layoutContract.activityProfile') {
    issues.push({ path: `${path}.runtime_carrier`, message: 'must identify the activity profile runtime carrier' });
  }
  if (raw.projection_only !== true || raw.no_business_fact_authority !== true) {
    issues.push({ path, message: 'must remain projection-only without business fact authority' });
  }
  if (!validAuthorities
      || raw.kind !== 'native_activity_view_projection'
      || raw.runtime_carrier !== 'ui.contract.v2.layoutContract.activityProfile'
      || raw.projection_only !== true
      || raw.no_business_fact_authority !== true) {
    return undefined;
  }
  return {
    kind: raw.kind,
    authorities: [authorities[0], authorities[1], authorities[2]],
    projection_only: raw.projection_only,
    no_business_fact_authority: raw.no_business_fact_authority,
    runtime_carrier: raw.runtime_carrier,
  };
}

function decodeActivityProfile(raw: unknown, issues: DecodeIssue[]): ContractV2ActivityProfile | undefined {
  const path = 'layoutContract.activityProfile';
  if (raw === undefined) return undefined;
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return undefined;
  }
  rejectUnknownKeys(raw, [
    'activityTypeSlots', 'deadlineSlots', 'assigneeSlots', 'fieldOccurrences', 'nativeAttrs',
    'nodeOccurrences', 'template', 'templateQwebPresent', 'actions', 'actionCount', 'sourceAuthority',
  ], path, issues);
  const authority = decodeActivitySourceAuthority(raw.sourceAuthority, `${path}.sourceAuthority`, issues);
  const fieldOccurrences = requiredArray(raw, 'fieldOccurrences', path, issues).map((item, index) => {
    const itemPath = `${path}.fieldOccurrences[${index}]`;
    if (!isRecord(item)) {
      issues.push({ path: itemPath, message: 'must be an object' });
      return null;
    }
    rejectUnknownKeys(item, [
      'name', 'label', 'widget', 'native_locator', 'occurrence_index', 'source_position', 'attributes',
      'text', 'tail', 'modifiers', 'decorations', 'field_type', 'currency_field', 'digits',
    ], itemPath, issues);
    const occurrenceIndex = requiredActivityInteger(item, 'occurrence_index', itemPath, issues, 1);
    const sourcePosition = requiredActivityInteger(item, 'source_position', itemPath, issues, 0);
    let digits: [] | [number, number] = [];
    if (!Array.isArray(item.digits) || (item.digits.length !== 0 && item.digits.length !== 2)) {
      issues.push({ path: `${itemPath}.digits`, message: 'must be empty or contain precision and scale' });
    } else if (item.digits.length === 2) {
      const precision = item.digits[0];
      const scale = item.digits[1];
      if (typeof precision !== 'number' || typeof scale !== 'number'
          || !Number.isInteger(precision) || !Number.isInteger(scale)
          || precision < 0 || scale < 0) {
        issues.push({ path: `${itemPath}.digits`, message: 'must contain valid precision and scale integers' });
      } else {
        digits = [precision, scale];
      }
    }
    const decorations = requiredArray(item, 'decorations', itemPath, issues).map((decoration, decorationIndex) => {
      if (isRecord(decoration)) return decoration;
      issues.push({ path: `${itemPath}.decorations[${decorationIndex}]`, message: 'must be an object' });
      return null;
    }).filter((decoration): decoration is ContractV2Dictionary => Boolean(decoration));
    const fieldText = requiredActivityString(item, 'text', itemPath, issues);
    const fieldTail = requiredActivityString(item, 'tail', itemPath, issues);
    return {
      name: requiredActivityNonEmptyString(item, 'name', itemPath, issues),
      label: requiredActivityNonEmptyString(item, 'label', itemPath, issues),
      widget: requiredActivityString(item, 'widget', itemPath, issues),
      native_locator: requiredActivityNonEmptyString(item, 'native_locator', itemPath, issues),
      occurrence_index: occurrenceIndex,
      source_position: sourcePosition,
      attributes: requiredRecord(item, 'attributes', itemPath, issues),
      text: fieldText,
      tail: fieldTail,
      modifiers: requiredActivityString(item, 'modifiers', itemPath, issues),
      decorations,
      field_type: requiredActivityString(item, 'field_type', itemPath, issues),
      currency_field: requiredActivityString(item, 'currency_field', itemPath, issues),
      digits,
    };
  }).filter((item): item is NonNullable<typeof item> => Boolean(item));
  const templateRaw = requiredRecord(raw, 'template', path, issues);
  rejectUnknownKeys(templateRaw, ['native_locator', 'occurrence_index', 'names', 'nodes'], `${path}.template`, issues);
  const templateNodes = requiredArray(templateRaw, 'nodes', `${path}.template`, issues)
    .map((item, index) => decodeActivityNode(item, `${path}.template.nodes[${index}]`, issues))
    .filter((item): item is ContractV2ActivityNode => Boolean(item));
  const templateOccurrenceIndex = requiredActivityInteger(templateRaw, 'occurrence_index', `${path}.template`, issues, 1);
  const templateNames = requiredArray(templateRaw, 'names', `${path}.template`, issues).map((item, index) => {
    if (typeof item === 'string' && item.trim()) return item;
    issues.push({ path: `${path}.template.names[${index}]`, message: 'must be a non-empty string' });
    return '';
  }).filter(Boolean);
  const actions = requiredArray(raw, 'actions', path, issues).map((item, index) => {
    if (isRecord(item)) return item;
    issues.push({ path: `${path}.actions[${index}]`, message: 'must be an object' });
    return null;
  }).filter((item): item is ContractV2Dictionary => Boolean(item));
  const actionCount = requiredActivityInteger(raw, 'actionCount', path, issues, 0);
  if (actionCount !== actions.length) issues.push({ path: `${path}.actionCount`, message: 'must equal actions length' });
  if (!authority) return undefined;
  return {
    activityTypeSlots: requiredRecord(raw, 'activityTypeSlots', path, issues),
    deadlineSlots: requiredRecord(raw, 'deadlineSlots', path, issues),
    assigneeSlots: requiredRecord(raw, 'assigneeSlots', path, issues),
    fieldOccurrences,
    nativeAttrs: requiredRecord(raw, 'nativeAttrs', path, issues),
    nodeOccurrences: requiredArray(raw, 'nodeOccurrences', path, issues)
      .map((item, index) => decodeActivityNodeOccurrence(item, `${path}.nodeOccurrences[${index}]`, issues))
      .filter((item): item is ContractV2ActivityNodeOccurrence => Boolean(item)),
    template: {
      native_locator: requiredActivityNonEmptyString(templateRaw, 'native_locator', `${path}.template`, issues),
      occurrence_index: templateOccurrenceIndex,
      names: templateNames,
      nodes: templateNodes,
    },
    templateQwebPresent: requiredBoolean(raw, 'templateQwebPresent', path, issues, false),
    actions,
    actionCount,
    sourceAuthority: authority,
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
    ...(source.activityProfile !== undefined
      ? { activityProfile: decodeActivityProfile(source.activityProfile, issues) }
      : {}),
  };
}

function decodeFormStructureGovernanceContract(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureGovernanceContract | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, ['id', 'name', 'priority', 'view_type', 'version_no'], path, issues);
  const id = raw.id;
  if (typeof id !== 'number' || !Number.isInteger(id) || id < 1) {
    issues.push({ path: `${path}.id`, message: 'must be a positive integer' });
  }
  const decodeOptionalInteger = (key: 'priority' | 'version_no'): number | undefined => {
    if (raw[key] === undefined) return undefined;
    if (typeof raw[key] === 'number' && Number.isInteger(raw[key])) return raw[key] as number;
    issues.push({ path: `${path}.${key}`, message: 'must be an integer' });
    return undefined;
  };
  return {
    id: typeof id === 'number' && Number.isInteger(id) ? id : 0,
    name: requiredString(raw, 'name', path, issues),
    ...(decodeOptionalInteger('priority') !== undefined ? { priority: decodeOptionalInteger('priority') } : {}),
    ...(optionalString(raw, 'view_type') ? { view_type: optionalString(raw, 'view_type') } : {}),
    ...(decodeOptionalInteger('version_no') !== undefined ? { version_no: decodeOptionalInteger('version_no') } : {}),
  };
}

function decodeFormStructureConfiguredSection(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureConfiguredSection | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, ['identity', 'key', 'title', 'fields'], path, issues);
  return {
    identity: requiredString(raw, 'identity', path, issues),
    key: typeof raw.key === 'string' ? raw.key : '',
    title: requiredString(raw, 'title', path, issues),
    fields: decodeUniqueStringArray(raw.fields, `${path}.fields`, issues),
  };
}

function decodeFormStructureGovernanceSource(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureGovernanceSource | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, [
    'source', 'ownerLayer', 'businessConfigContracts', 'legacyFieldPolicyOverlay',
    'formLayoutOverlay', 'formStructureAuthority', 'fieldNames', 'fieldLabels',
    'fieldSemanticRoles', 'sectionSemanticRoles', 'configuredSections', 'sectionTitles',
    'fieldGroups', 'hiddenFieldNames', 'formColumns', 'groupColumns', 'groupVisibility',
    'categoryId', 'categoryCode', 'targetModel',
  ], path, issues);
  const source = requiredString(raw, 'source', path, issues);
  const businessContracts = raw.businessConfigContracts === undefined
    ? undefined
    : requiredArray(raw, 'businessConfigContracts', path, issues)
      .map((item, index) => decodeFormStructureGovernanceContract(
        item, `${path}.businessConfigContracts[${index}]`, issues,
      ))
      .filter((item): item is ContractV2FormStructureGovernanceContract => Boolean(item));
  const semanticRoleMap = (
    value: unknown,
    rolePath: string,
  ): Record<string, ContractV2CanonicalFormSemanticRole> | undefined => {
    if (value === undefined) return undefined;
    if (!isRecord(value)) {
      issues.push({ path: rolePath, message: 'must be an object' });
      return undefined;
    }
    const out: Record<string, ContractV2CanonicalFormSemanticRole> = {};
    Object.entries(value).forEach(([key, role]) => {
      const decoded = decodeFormStructureRoleName(role, `${rolePath}.${key}`, issues);
      if (!['summary', 'task', 'context', 'risk', 'relation', 'activity', 'audit'].includes(decoded)) {
        issues.push({ path: `${rolePath}.${key}`, message: 'must be a canonical semantic role' });
        return;
      }
      out[key] = decoded as ContractV2CanonicalFormSemanticRole;
    });
    return out;
  };
  const fieldGroups: Record<string, string[]> | undefined = raw.fieldGroups === undefined
    ? undefined
    : (() => {
      if (!isRecord(raw.fieldGroups)) {
        issues.push({ path: `${path}.fieldGroups`, message: 'must be an object' });
        return undefined;
      }
      return Object.fromEntries(Object.entries(raw.fieldGroups).map(([key, value]) => [
        key,
        decodeUniqueStringArray(value, `${path}.fieldGroups.${key}`, issues),
      ]));
    })();
  const configuredSections = raw.configuredSections === undefined
    ? undefined
    : requiredArray(raw, 'configuredSections', path, issues)
      .map((item, index) => decodeFormStructureConfiguredSection(
        item, `${path}.configuredSections[${index}]`, issues,
      ))
      .filter((item): item is ContractV2FormStructureConfiguredSection => Boolean(item));
  const optionalBooleanField = (key: string): boolean | undefined => {
    if (raw[key] === undefined) return undefined;
    if (typeof raw[key] === 'boolean') return raw[key] as boolean;
    issues.push({ path: `${path}.${key}`, message: 'must be a boolean' });
    return undefined;
  };
  const formColumns = raw.formColumns;
  if (formColumns !== undefined && (
    typeof formColumns !== 'number' || !Number.isInteger(formColumns) || formColumns < 1
  )) issues.push({ path: `${path}.formColumns`, message: 'must be a positive integer' });
  const categoryId = raw.categoryId;
  if (categoryId !== undefined && (
    typeof categoryId !== 'number' || !Number.isInteger(categoryId) || categoryId < 1
  )) issues.push({ path: `${path}.categoryId`, message: 'must be a positive integer' });
  const legacyFieldPolicyOverlay = optionalBooleanField('legacyFieldPolicyOverlay');
  const formLayoutOverlay = optionalBooleanField('formLayoutOverlay');
  const fieldSemanticRoles = semanticRoleMap(raw.fieldSemanticRoles, `${path}.fieldSemanticRoles`);
  const sectionSemanticRoles = semanticRoleMap(raw.sectionSemanticRoles, `${path}.sectionSemanticRoles`);
  return {
    source,
    ...(optionalString(raw, 'ownerLayer') ? { ownerLayer: optionalString(raw, 'ownerLayer') } : {}),
    ...(businessContracts ? { businessConfigContracts: businessContracts } : {}),
    ...(legacyFieldPolicyOverlay !== undefined
      ? { legacyFieldPolicyOverlay }
      : {}),
    ...(formLayoutOverlay !== undefined
      ? { formLayoutOverlay }
      : {}),
    ...(optionalString(raw, 'formStructureAuthority')
      ? { formStructureAuthority: optionalString(raw, 'formStructureAuthority') }
      : {}),
    ...(raw.fieldNames !== undefined
      ? { fieldNames: decodeUniqueStringArray(raw.fieldNames, `${path}.fieldNames`, issues) }
      : {}),
    ...(raw.fieldLabels !== undefined
      ? { fieldLabels: decodeStringMap(raw.fieldLabels, `${path}.fieldLabels`, issues) }
      : {}),
    ...(fieldSemanticRoles
      ? { fieldSemanticRoles }
      : {}),
    ...(sectionSemanticRoles
      ? { sectionSemanticRoles }
      : {}),
    ...(configuredSections ? { configuredSections } : {}),
    ...(raw.sectionTitles !== undefined
      ? { sectionTitles: decodeUniqueStringArray(raw.sectionTitles, `${path}.sectionTitles`, issues) }
      : {}),
    ...(fieldGroups ? { fieldGroups } : {}),
    ...(raw.hiddenFieldNames !== undefined
      ? { hiddenFieldNames: decodeUniqueStringArray(raw.hiddenFieldNames, `${path}.hiddenFieldNames`, issues) }
      : {}),
    ...(typeof formColumns === 'number' && Number.isInteger(formColumns) && formColumns > 0
      ? { formColumns }
      : {}),
    ...(raw.groupColumns !== undefined
      ? { groupColumns: decodePositiveIntegerMap(raw.groupColumns, `${path}.groupColumns`, issues) }
      : {}),
    ...(raw.groupVisibility !== undefined
      ? { groupVisibility: decodeBooleanMap(raw.groupVisibility, `${path}.groupVisibility`, issues) }
      : {}),
    ...(typeof categoryId === 'number' && Number.isInteger(categoryId) && categoryId > 0
      ? { categoryId }
      : {}),
    ...(optionalString(raw, 'categoryCode') ? { categoryCode: optionalString(raw, 'categoryCode') } : {}),
    ...(optionalString(raw, 'targetModel') ? { targetModel: optionalString(raw, 'targetModel') } : {}),
  };
}

function decodeFormStructureSourceAuthority(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureSourceAuthority | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, [
    'kind', 'runtime_carrier', 'projection_only', 'no_business_fact_authority',
    'governed_form_structure', 'governance_source',
  ], path, issues);
  const expectConst = (key: string, expected: unknown) => {
    if (raw[key] !== expected) issues.push({ path: `${path}.${key}`, message: `must equal ${String(expected)}` });
  };
  expectConst('kind', 'unified_page_contract_v2');
  expectConst('runtime_carrier', 'ui.contract.v2.form_structure_contract');
  expectConst('projection_only', true);
  expectConst('no_business_fact_authority', true);
  expectConst('governed_form_structure', true);
  const governanceSource = decodeFormStructureGovernanceSource(
    raw.governance_source, `${path}.governance_source`, issues,
  );
  if (!governanceSource) return null;
  return {
    kind: 'unified_page_contract_v2',
    runtime_carrier: 'ui.contract.v2.form_structure_contract',
    projection_only: true,
    no_business_fact_authority: true,
    governed_form_structure: true,
    governance_source: governanceSource,
  };
}

function decodeFormStructureGroup(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureGroup | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, ['name', 'title', 'role', 'fieldRefs', 'fieldLabels', 'columns'], path, issues);
  const columns = raw.columns;
  if (columns !== undefined && (
    typeof columns !== 'number' || !Number.isInteger(columns) || columns < 1
  )) issues.push({ path: `${path}.columns`, message: 'must be a positive integer' });
  return {
    name: requiredString(raw, 'name', path, issues),
    title: requiredDisplayString(raw, 'title', path, issues),
    role: decodeFormStructureRoleName(raw.role, `${path}.role`, issues),
    fieldRefs: decodeUniqueStringArray(raw.fieldRefs, `${path}.fieldRefs`, issues),
    ...(raw.fieldLabels !== undefined
      ? { fieldLabels: decodeStringMap(raw.fieldLabels, `${path}.fieldLabels`, issues) }
      : {}),
    ...(typeof columns === 'number' && Number.isInteger(columns) && columns > 0 ? { columns } : {}),
  };
}

function decodeFormStructureSlot(
  raw: unknown,
  path: string,
  issues: DecodeIssue[],
): ContractV2FormStructureSlot | null {
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return null;
  }
  rejectUnknownKeys(raw, ['slot', 'title', 'role', 'readonly', 'fieldRefs', 'groups'], path, issues);
  const readonly = optionalBoolean(raw.readonly);
  if (raw.readonly !== undefined && readonly === undefined) {
    issues.push({ path: `${path}.readonly`, message: 'must be a boolean' });
  }
  const groups = raw.groups === undefined
    ? undefined
    : requiredArray(raw, 'groups', path, issues)
      .map((item, index) => decodeFormStructureGroup(item, `${path}.groups[${index}]`, issues))
      .filter((item): item is ContractV2FormStructureGroup => Boolean(item));
  return {
    slot: requiredString(raw, 'slot', path, issues),
    title: requiredDisplayString(raw, 'title', path, issues),
    role: decodeFormStructureRoleName(raw.role, `${path}.role`, issues),
    ...(readonly !== undefined ? { readonly } : {}),
    ...(raw.fieldRefs !== undefined
      ? { fieldRefs: decodeUniqueStringArray(raw.fieldRefs, `${path}.fieldRefs`, issues) }
      : {}),
    ...(groups ? { groups } : {}),
  };
}

function collectLayoutFieldCodes(containers: ContractV2Container[]): Set<string> {
  const out = new Set<string>();
  const visit = (container: ContractV2Container) => {
    if ((container.type || container.containerType).toLowerCase() === 'field' && container.fieldCode) {
      out.add(container.fieldCode);
    }
    container.widgetList.forEach((widget) => out.add(widget.fieldCode));
    container.children.forEach(visit);
  };
  containers.forEach(visit);
  return out;
}

function decodeFormStructureContract(
  raw: unknown,
  pageInfo: ContractV2PageInfo,
  layoutContract: ContractV2LayoutContract,
  issues: DecodeIssue[],
): ContractV2FormStructureContract | undefined {
  if (raw === undefined) return undefined;
  const path = '$.formStructureContract';
  if (!isRecord(raw)) {
    issues.push({ path, message: 'must be an object' });
    return undefined;
  }
  rejectUnknownKeys(raw, [
    'source', 'structureVersion', 'model', 'viewType', 'mode', 'presentationMode', 'layoutPolicy', 'columns',
    'objectProfile', 'navigation', 'sourceSectionTitles', 'fieldLabels', 'slots', 'fieldRoles',
    'sourceAuthority',
  ], path, issues);
  if (raw.source !== 'ui.contract.v2.form_structure_contract') {
    issues.push({ path: `${path}.source`, message: 'must equal ui.contract.v2.form_structure_contract' });
  }
  const structureVersion = raw.structureVersion;
  if (structureVersion !== '1.0' && structureVersion !== '1.1') {
    issues.push({ path: `${path}.structureVersion`, message: 'must equal 1.0 or 1.1' });
  }
  const model = requiredString(raw, 'model', path, issues);
  if (model && model !== pageInfo.model) issues.push({ path: `${path}.model`, message: 'must match pageInfo.model' });
  if (raw.viewType !== 'form') issues.push({ path: `${path}.viewType`, message: 'must equal form' });
  const presentationMode = raw.presentationMode;
  if (structureVersion === '1.1' && presentationMode !== 'task' && presentationMode !== 'workspace') {
    issues.push({ path: `${path}.presentationMode`, message: 'must equal task or workspace' });
  }
  if (structureVersion === '1.0' && presentationMode !== undefined) {
    issues.push({ path: `${path}.presentationMode`, message: 'requires structureVersion 1.1' });
  }
  const columns = raw.columns;
  if (columns !== undefined && (
    typeof columns !== 'number' || !Number.isInteger(columns) || columns < 1
  )) issues.push({ path: `${path}.columns`, message: 'must be a positive integer' });
  const objectProfileRaw = requiredRecord(raw, 'objectProfile', path, issues);
  rejectUnknownKeys(objectProfileRaw, ['model', 'kind', 'factAuthority'], `${path}.objectProfile`, issues);
  const objectProfileModel = requiredString(objectProfileRaw, 'model', `${path}.objectProfile`, issues);
  if (objectProfileModel && objectProfileModel !== model) {
    issues.push({ path: `${path}.objectProfile.model`, message: 'must match formStructureContract.model' });
  }
  if (objectProfileRaw.kind !== 'business_form') {
    issues.push({ path: `${path}.objectProfile.kind`, message: 'must equal business_form' });
  }
  const navigationRaw = requiredRecord(raw, 'navigation', path, issues);
  rejectUnknownKeys(navigationRaw, ['title'], `${path}.navigation`, issues);
  const slots = requiredArray(raw, 'slots', path, issues)
    .map((item, index) => decodeFormStructureSlot(item, `${path}.slots[${index}]`, issues))
    .filter((item): item is ContractV2FormStructureSlot => Boolean(item));
  if (!slots.length) issues.push({ path: `${path}.slots`, message: 'must contain at least one slot' });
  const slotNames = new Set<string>();
  const groupNamesBySlot = new Map<string, Set<string>>();
  const referencedFields = new Set<string>();
  slots.forEach((slot, slotIndex) => {
    if (slotNames.has(slot.slot)) issues.push({ path: `${path}.slots[${slotIndex}].slot`, message: 'must be unique' });
    slotNames.add(slot.slot);
    const groups = new Set<string>();
    (slot.fieldRefs || []).forEach((fieldCode) => referencedFields.add(fieldCode));
    (slot.groups || []).forEach((group, groupIndex) => {
      if (groups.has(group.name)) {
        issues.push({ path: `${path}.slots[${slotIndex}].groups[${groupIndex}].name`, message: 'must be unique within slot' });
      }
      groups.add(group.name);
      group.fieldRefs.forEach((fieldCode) => referencedFields.add(fieldCode));
    });
    groupNamesBySlot.set(slot.slot, groups);
  });
  const fieldRolesRaw = requiredRecord(raw, 'fieldRoles', path, issues);
  const fieldRoles: Record<string, ContractV2FormStructureRole> = {};
  Object.entries(fieldRolesRaw).forEach(([fieldCode, roleRaw]) => {
    if (!fieldCode.trim()) {
      issues.push({ path: `${path}.fieldRoles`, message: 'contains a blank field identity' });
      return;
    }
    const role = decodeFormStructureRole(roleRaw, `${path}.fieldRoles.${fieldCode}`, issues);
    if (!role) return;
    fieldRoles[fieldCode] = role;
    if (!slotNames.has(role.slot)) {
      issues.push({ path: `${path}.fieldRoles.${fieldCode}.slot`, message: `references unknown slot ${role.slot}` });
    } else {
      const validGroups = groupNamesBySlot.get(role.slot) || new Set<string>();
      if (role.group !== role.slot && !validGroups.has(role.group)) {
        issues.push({ path: `${path}.fieldRoles.${fieldCode}.group`, message: `references unknown group ${role.group}` });
      }
    }
    if (!referencedFields.has(fieldCode)) {
      issues.push({ path: `${path}.fieldRoles.${fieldCode}`, message: 'is not referenced by a slot or group' });
    }
  });
  referencedFields.forEach((fieldCode) => {
    if (!fieldRoles[fieldCode]) issues.push({ path: `${path}.fieldRoles.${fieldCode}`, message: 'is required' });
  });
  const layoutFields = collectLayoutFieldCodes(layoutContract.containerTree);
  referencedFields.forEach((fieldCode) => {
    if (!layoutFields.has(fieldCode)) {
      issues.push({ path: `${path}.slots`, message: `references field not projected by layout: ${fieldCode}` });
    }
  });
  const sourceAuthority = decodeFormStructureSourceAuthority(
    raw.sourceAuthority, `${path}.sourceAuthority`, issues,
  );
  if (!sourceAuthority) return undefined;
  return {
    source: 'ui.contract.v2.form_structure_contract',
    structureVersion: structureVersion === '1.1' ? '1.1' : '1.0',
    model,
    viewType: 'form',
    mode: requiredString(raw, 'mode', path, issues),
    // Version 1.0 predates formal presentation authority. It is explicitly
    // normalized to the conservative workspace path; new 1.1 structures must
    // declare their authority above.
    presentationMode: structureVersion === '1.1' && presentationMode === 'task' ? 'task' : 'workspace',
    layoutPolicy: requiredString(raw, 'layoutPolicy', path, issues),
    ...(typeof columns === 'number' && Number.isInteger(columns) && columns > 0 ? { columns } : {}),
    objectProfile: {
      model: objectProfileModel,
      kind: 'business_form',
      factAuthority: requiredString(objectProfileRaw, 'factAuthority', `${path}.objectProfile`, issues),
    },
    navigation: { title: requiredDisplayString(navigationRaw, 'title', `${path}.navigation`, issues) },
    ...(raw.sourceSectionTitles !== undefined
      ? { sourceSectionTitles: decodeUniqueStringArray(raw.sourceSectionTitles, `${path}.sourceSectionTitles`, issues) }
      : {}),
    ...(raw.fieldLabels !== undefined
      ? { fieldLabels: decodeStringMap(raw.fieldLabels, `${path}.fieldLabels`, issues) }
      : {}),
    slots,
    fieldRoles,
    sourceAuthority,
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
  const containerIds = new Set<string>();
  const widgets: ContractV2Widget[] = [];
  const formFieldContainers: ContractV2Container[] = [];
  const walk = (rows: ContractV2Container[]) => rows.forEach((row) => {
    if (containerIds.has(row.containerId)) {
      issues.push({ path: 'layoutContract.containerTree', message: `duplicate container identity ${row.containerId}` });
    }
    containerIds.add(row.containerId);
    row.widgetList.forEach((widget) => {
      widgets.push(widget);
      if (widgetsById.has(widget.widgetId)) {
        issues.push({ path: 'layoutContract.containerTree', message: `duplicate widget identity ${widget.widgetId}` });
        return;
      }
      widgetsById.set(widget.widgetId, widget);
    });
    if (String(row.type || row.containerType).toLowerCase() === 'field') formFieldContainers.push(row);
    walk(row.children);
  });
  walk(layoutContract.containerTree);
  widgets.forEach((widget) => {
    if (!containerIds.has(widget.ownerContainerId)) {
      issues.push({
        path: 'layoutContract.containerTree',
        message: `widget ${widget.widgetId} references unknown owner ${widget.ownerContainerId}`,
      });
    }
  });
  formFieldContainers.forEach((row) => {
    if (!row.widgetId) return;
    const widget = widgetsById.get(row.widgetId);
    if (!widget) {
      issues.push({ path: 'layoutContract.containerTree', message: `field owner ${row.containerId} has no widget ${row.widgetId}` });
    } else if (widget.ownerContainerId !== row.containerId) {
      issues.push({ path: 'layoutContract.containerTree', message: `widget ${row.widgetId} is not owned by ${row.containerId}` });
    }
  });

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
  const root = asRecord(normalizeLegacyContractV2Snapshot(value));
  const issues: DecodeIssue[] = [];
  const pageInfo = decodePageInfo(readAliasedObject(root, 'pageInfo', [], '$', issues), issues);
  const layoutContract = decodeLayoutContract(readAliasedObject(root, 'layoutContract', [], '$', issues), issues);
  const statusContract = decodeStatusContract(readAliasedObject(root, 'statusContract', [], '$', issues), issues);
  const actionContract = decodeActionContract(readAliasedObject(root, 'actionContract', [], '$', issues), issues);
  const dataContract = decodeDataContract(readAliasedObject(root, 'dataContract', [], '$', issues), issues);
  const runtimeContract = decodeRuntimeContract(readAliasedObject(root, 'runtimeContract', [], '$', issues), issues);
  const meta = decodeMeta(readAliasedObject(root, 'meta', [], '$', issues), issues);
  const formStructureContract = decodeFormStructureContract(
    root.formStructureContract,
    pageInfo,
    layoutContract,
    issues,
  );
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
