import type { ActionSemantics } from '@sc/schema';
export type ContractV2ClientType = 'web_pc' | 'wx_mini' | 'harmony_h5';
export type ContractV2DeliveryProfile = 'full' | 'mobile_compact' | 'mobile_primary';
export type ContractV2ViewType = 'form' | 'list' | 'table' | 'kanban' | 'tree' | 'pivot' | 'graph' | 'calendar' | 'gantt' | 'activity' | 'dashboard' | 'combine';
export type ContractV2LayoutType = 'form' | 'table' | 'kanban' | 'tree' | 'pivot' | 'graph' | 'calendar' | 'gantt' | 'activity' | 'dashboard' | 'combine';
export type ContractV2AdaptMode = 'pc' | 'mobile';
export type ContractV2TriggerType = 'change' | 'click' | 'select' | 'refresh' | 'add' | 'delete' | 'confirm' | 'submit' | 'blur' | 'focus';
export type ContractV2DispatchMode = 'local' | 'server' | 'serverDebounced' | 'serverBlocking';
export type ContractV2TargetScope = 'widget' | 'container' | 'page' | 'dataSource' | 'runtime';
export type ContractV2RefreshMode = 'none' | 'partial' | 'full';
export type ContractV2Auth = 'none' | 'read' | 'edit' | 'admin';
export type ContractV2PatchStrategy = 'incremental' | 'full';
export type ContractV2CachePolicy = 'none' | 'etag' | 'snapshot';
export type ContractV2RenderStrategy = 'sync' | 'scheduled' | 'virtualized';
export type ContractV2PatchOperation = 'replace' | 'merge' | 'append' | 'remove' | 'reorder' | 'invalidate';
export type ContractV2PageRenderMode = 'governed';
export type ContractV2ContainerZone = 'detail_zone' | 'collaboration_zone' | 'attachment_zone';
export type ContractV2WidgetType = 'input' | 'select' | 'date' | 'datetime' | 'number' | 'table'
  | 'upload' | 'button' | 'textarea' | 'checkbox' | 'radio' | 'tree' | 'gantt' | 'relation'
  | 'display' | 'binary' | 'many2many_tags';
export type ContractV2Dictionary = Record<string, unknown>;

export type ContractV2CanonicalFormSemanticRole =
  | 'summary'
  | 'task'
  | 'context'
  | 'risk'
  | 'relation'
  | 'activity'
  | 'audit';

export type ContractV2FormStructureRoleName = ContractV2CanonicalFormSemanticRole;
export type ContractV2FormPresentationMode = 'task' | 'workspace';

/** Where the delivered body structure comes from (fact, not rendering implementation). */
export type ContractV2FormStructureSource =
  | 'native_view'
  | 'business_orchestration'
  | 'business_category_policy'
  | 'entry_semantic_surface';

/**
 * Which carrier is the final structural authority of the body.
 *
 * `container_tree` is the single carrier: it forbids independent structural
 * slots, columns and field membership.  The other authorities publish their
 * structure in `slots` and leave the container tree as a projection.
 */
export type ContractV2FormStructureAuthority = 'container_tree' | 'native_form_slots' | 'task_sections';

export interface ContractV2FormStructureRole {
  role: ContractV2FormStructureRoleName;
  slot: string;
  group: string;
}

export interface ContractV2FormStructureGroup {
  name: string;
  title: string;
  role: ContractV2FormStructureRoleName;
  fieldRefs: string[];
  fieldLabels?: Record<string, string>;
  columns?: number;
}

export interface ContractV2FormStructureSlot {
  slot: string;
  title: string;
  role: ContractV2FormStructureRoleName;
  readonly?: boolean;
  fieldRefs?: string[];
  groups?: ContractV2FormStructureGroup[];
}

export interface ContractV2FormStructureGovernanceContract {
  id: number;
  name: string;
  source_kind?: 'published' | 'change_set_preview';
  status?: 'draft' | 'published' | 'preview';
  priority?: number;
  view_type?: string;
  version_no?: number;
}

export interface ContractV2FormStructureConfiguredSection {
  identity: string;
  key: string;
  title: string;
  fields: string[];
}

export interface ContractV2FormStructureGovernanceSource {
  resolvedViewId?: number;
  resolvedActionId?: number;
  structureDiagnostics?: ContractV2Dictionary[];
  compatibilityDependencies?: string[];
  source: string;
  ownerLayer?: string;
  businessConfigContracts?: ContractV2FormStructureGovernanceContract[];
  legacyFieldPolicyOverlay?: boolean;
  formLayoutOverlay?: boolean;
  formStructureAuthority?: string;
  formPresentationMode?: ContractV2FormPresentationMode;
  fieldNames?: string[];
  fieldLabels?: Record<string, string>;
  fieldSemanticRoles?: Record<string, ContractV2CanonicalFormSemanticRole>;
  sectionSemanticRoles?: Record<string, ContractV2CanonicalFormSemanticRole>;
  configuredSections?: ContractV2FormStructureConfiguredSection[];
  sectionTitles?: string[];
  fieldGroups?: Record<string, string[]>;
  hiddenFieldNames?: string[];
  formColumns?: number;
  groupColumns?: Record<string, number>;
  groupVisibility?: Record<string, boolean>;
  categoryId?: number;
  categoryCode?: string;
  targetModel?: string;
}

export interface ContractV2FormStructureSourceAuthority {
  kind: 'unified_page_contract_v2';
  runtime_carrier: 'ui.contract.v2.form_structure_contract';
  projection_only: true;
  no_business_fact_authority: true;
  governed_form_structure: true;
  governance_source: ContractV2FormStructureGovernanceSource;
}

export interface ContractV2FormStructureSurfaceAuthorization {
  capability: string;
  state: 'allow' | 'deny' | 'pending' | 'coming_soon';
  reasonCode?: string;
  reason?: string;
  requiredRoles?: string[];
  requiredGroups?: string[];
}

export interface ContractV2FormStructureSurfaceAudit {
  title: string;
  contentKind: 'collaboration-panel' | 'audit-timeline';
  sourceIdentity: string;
  authorization: ContractV2FormStructureSurfaceAuthorization;
}

export interface ContractV2FormStructureSurface {
  surface: string;
  title: string;
  role: string;
  contentKind: 'collaboration-panel' | 'audit-timeline';
  sourceIdentity: string;
  capabilities?: {
    timeline?: boolean;
    remarks?: boolean;
    attachments?: boolean;
  };
  audit?: ContractV2FormStructureSurfaceAudit;
}

export interface ContractV2FormStructureContract {
  source: 'ui.contract.v2.form_structure_contract';
  structureVersion: '1.0' | '1.1';
  model: string;
  viewType: 'form';
  mode: string;
  presentationMode: ContractV2FormPresentationMode;
  structureSource: ContractV2FormStructureSource;
  structureAuthority: ContractV2FormStructureAuthority;
  columns?: number;
  objectProfile: {
    model: string;
    kind: 'business_form';
    factAuthority: string;
  };
  navigation: {
    title: string;
  };
  sourceSectionTitles?: string[];
  fieldLabels?: Record<string, string>;
  slots: ContractV2FormStructureSlot[];
  fieldRoles: Record<string, ContractV2FormStructureRole>;
  fieldOwnership?: ContractV2FieldOwnership;
  /** Declared page regions that are not Odoo view elements. */
  surfaces?: ContractV2FormStructureSurface[];
  sourceAuthority: ContractV2FormStructureSourceAuthority;
}

export interface ContractV2PageInfo {
  pageId: string;
  sceneKey: string;
  pageName: string;
  model: string;
  viewType: ContractV2ViewType;
  layoutType: ContractV2LayoutType;
  renderMode: ContractV2PageRenderMode;
  contractVersion: string;
  clientType: ContractV2ClientType;
  deliveryProfile?: ContractV2DeliveryProfile;
}

export type ContractV2NativeActionViewType =
  | 'tree'
  | 'kanban'
  | 'pivot'
  | 'graph'
  | 'calendar'
  | 'gantt'
  | 'activity'
  | 'dashboard'
  | 'form';

export interface ContractV2NativeActionView {
  viewType: ContractV2NativeActionViewType;
  viewId: number;
  viewXmlId: string;
  actionViewSequence: number;
  surfaceRole: 'collection' | 'record_detail';
  selectable: boolean;
  projectionStatus: 'ready' | 'blocked' | 'unresolved';
  rendererStatus: 'ready' | 'fallback' | 'unsupported' | 'unknown';
  reasonCode: string;
  profile: string;
}

export interface ContractV2NativeActionReadinessAxis {
  status: 'ready' | 'blocked' | 'unresolved' | 'unknown' | 'not_applicable';
  reasonCodes: string[];
}

export interface ContractV2NativeActionContract {
  schemaVersion: '1.0.0';
  identity: {
    actionType: 'ir.actions.act_window';
    actionId: number;
    actionXmlId: string;
    model: string;
  };
  entryRefs: Array<{
    kind: 'menu';
    menuId: number;
    menuXmlId: string;
  }>;
  actionScope: {
    domainRaw: string;
    domain: unknown[];
    contextRaw: string;
    context: ContractV2Dictionary;
    sourceAuthority: {
      kind: 'ir.actions.act_window';
    };
  };
  projectionAvailability: {
    status: 'available' | 'blocked' | 'unresolved';
    reasonCode: string;
    authorityRef: 'existing_action_access_projection';
  };
  search?: {
    viewId: number;
    viewXmlId: string;
    authority: 'action_search_view' | 'model_default_search_view';
    profileRef: 'searchContract';
  };
  viewSet: {
    orderAuthority: 'ir.actions.act_window.views';
    defaultViewType: ContractV2NativeActionViewType;
    activeViewType: ContractV2NativeActionViewType;
    orderedViews: ContractV2NativeActionView[];
  };
  readiness: {
    backendContract: ContractV2NativeActionReadinessAxis;
    clientRenderer: ContractV2NativeActionReadinessAxis;
    businessExecution: ContractV2NativeActionReadinessAxis;
  };
  capabilities: Array<'action_view_set.v1' | 'search_identity.v1'>;
  sourceAuthority: {
    kind: 'native_action_contract_projection';
    projectionOnly: true;
    noBusinessFactAuthority: true;
  };
}

export type ContractV2NativeOccurrenceKind = 'field' | 'container' | 'button' | 'column' | 'widget';

export interface ContractV2NativeOccurrenceSourceAuthority {
  kind: 'ir.ui.view';
  projectionOnly: true;
  noBusinessFactAuthority: true;
}

export interface ContractV2NativeOccurrenceBehavior {
  domainRaw: string;
  contextRaw: string;
  optionsRaw: string;
}

export interface ContractV2NativeOccurrenceIdentity {
  schemaVersion: '1.0.0';
  model: string;
  viewType: string;
  viewId: number;
  viewXmlId: string;
  viewContentHash: string;
  viewStructureKey: string;
  crossEnvironmentStable: boolean;
  kind: ContractV2NativeOccurrenceKind;
  name: string;
  nativeLocator: string;
  occurrenceIndex: number;
  sourcePosition?: number;
  occurrenceKey: string;
  authoritative: boolean;
  sourceAuthority: ContractV2NativeOccurrenceSourceAuthority;
  nativeBehavior?: ContractV2NativeOccurrenceBehavior;
  type?: string;
  id?: string;
  string?: string;
  title?: string;
  help?: string;
  dataHotkey?: string;
  confirmRaw?: string;
  special?: string;
  icon?: string;
  canonicalRegion?: string;
  projectionRegion?: string;
}

export interface ContractV2ListColumnOccurrence {
  occurrenceKey: string;
  fieldCode: string;
  nativeIdentity: ContractV2NativeOccurrenceIdentity;
  label: string;
  widget: string;
  optional: string;
  sum: string;
  modifiers: ContractV2Dictionary;
  domainRaw: string;
  contextRaw: string;
  optionsRaw: string;
}

export interface ContractV2ListProfile extends ContractV2Dictionary {
  columnOccurrences?: ContractV2ListColumnOccurrence[];
}

export interface ContractV2Widget {
  widgetId: string;
  widgetType: ContractV2WidgetType;
  fieldCode: string;
  label: string;
  span: number;
  semanticType: string;
  capabilities: string[];
  componentConfig: ContractV2Dictionary;
  ownerContainerId: string;
  nativeLocator?: string;
  occurrenceIndex?: number;
  sourcePosition?: number;
  nativeIdentity?: ContractV2NativeOccurrenceIdentity;
  fieldDescriptor?: ContractV2Dictionary;
  formStructureRole?: ContractV2FormStructureRole;
}

export type ContractV2NativeWidgetSource =
  | 'native_explicit'
  | 'model_metadata_derived'
  | 'compatibility_default';

export type ContractV2NativeWidgetResolutionStatus =
  | 'not_applicable'
  | 'ready'
  | 'fallback'
  | 'unsupported';

export interface ContractV2NativeWidgetProvenance {
  nativeWidget: string;
  widgetSource: ContractV2NativeWidgetSource;
  declaredWidget: string;
  derivedWidgetType: string;
  resolvedWidgetType: string;
  resolutionStatus: ContractV2NativeWidgetResolutionStatus;
  reasonCode: string;
}

export interface ContractV2FieldDescriptor extends ContractV2Dictionary {
  schemaVersion?: '1.0.0';
  fieldCode: string;
  label: string;
  fieldType: string;
  widgetType: string;
  /** Frontend renderer identity resolved from the current semantic contract. */
  componentKey: string;
  required?: boolean;
  readonly?: boolean;
  invisible?: boolean;
  relation?: string;
  relationField?: string;
  /** Same-record field containing the target model of a many2one_reference. */
  referenceModelField?: string;
  selection?: Array<[string, string]>;
  domain?: unknown;
  domainExpression?: unknown;
  context?: unknown;
  relationEntry?: ContractV2Dictionary;
  widgetOptions?: ContractV2Dictionary;
  subview?: ContractV2Dictionary;
  filename?: string;
  semanticType?: string;
  surfaceRole?: string;
  help?: string;
  uiUsage?: 'fact' | 'interaction';
  changeDefault?: boolean;
  definitionRecord?: string;
  definitionRecordField?: string;
  groupOperator?: string;
  searchable?: boolean;
  sortable?: boolean;
  store?: boolean;
  translate?: boolean;
  trim?: boolean;
  related?: string[];
  size?: number;
  technical?: boolean;
  formStructureRole?: ContractV2FormStructureRole;
  digits?: [number, number];
  currencyField?: string;
  unit?: {
    kind: 'percent' | 'duration' | 'count' | 'quantity';
    code: string;
    label: string;
  };
  temporal?: {
    kind: 'date' | 'datetime';
    timezoneAuthority: 'user' | 'record' | 'not_applicable';
  };
  attachmentRole?: string;
}

export type ContractV2FieldDescriptorMap = Record<string, ContractV2FieldDescriptor>;

export interface ContractV2RegistryWidgetResolution {
  widgetType: string;
  widgetStatus: 'ready' | 'fallback';
  fallbackReasonCode: string | null;
}

export interface ContractV2FieldDescriptorDecodeResult {
  descriptor: ContractV2FieldDescriptor;
  registryResolution: {
    widget: ContractV2RegistryWidgetResolution;
  };
}

export interface ContractV2PageBlockFieldRefWidget {
  kind: 'widget';
  widgetId: string;
  rawValuePath: string;
}

export interface ContractV2PageBlockFieldRefDescriptor {
  kind: 'descriptor';
  descriptorId: string;
  rawValuePath: string;
}

export type ContractV2PageBlockFieldRef =
  | ContractV2PageBlockFieldRefWidget
  | ContractV2PageBlockFieldRefDescriptor;

export interface ContractV2PageBlockDataRow {
  rowKey: string;
  values: ContractV2Dictionary;
}

export interface ContractV2PageBlockDataContract {
  schemaVersion: '1.0.0';
  fieldRefs: Record<string, ContractV2PageBlockFieldRef>;
  rows: ContractV2PageBlockDataRow[];
  context: {
    currencies: Record<string, ContractV2Dictionary>;
    timezone: string;
  };
  sourceAuthority: ContractV2Dictionary;
}

export interface ContractV2PageBlockActionTarget {
  source: 'ContractV2ActionRule.target';
  value: ContractV2Dictionary;
}

export interface ContractV2PageBlockAction {
  actionId: string;
  actionRuleRef: string;
  actionKey: string;
  label: string;
  intent: string;
  target: ContractV2PageBlockActionTarget;
  visibility: {
    visible: boolean;
    source: 'action_contract';
  };
  permission: {
    evaluated: true;
    allowed: boolean;
    authorizationAllowed: boolean;
    businessAvailable: boolean;
  };
  state: {
    enabled: boolean;
    disabled: boolean;
    reasonCode: string;
    reasonMessage: string;
  };
}

export interface ContractV2PageBlockActionSchema {
  schemaVersion: '1.0.0';
  carrier: 'page-block-action.v1';
  sourceAuthority: ContractV2Dictionary;
  actions: Record<string, ContractV2PageBlockAction>;
}

export interface ContractV2ActionFeedback {
  schemaVersion: '1.0.0';
  actionId: string;
  status: 'success' | 'denied' | 'failed';
  reasonCode: string;
  message: string;
  traceId: string;
}

export interface ContractV2FormFieldDescriptor extends ContractV2Dictionary {
  name: string;
  string: string;
  type: string;
  ttype: string;
  widget: string;
  componentKey?: string;
  semanticType?: string;
  required?: boolean;
  readonly?: boolean;
  invisible?: boolean;
  relation?: string;
  relation_field?: string;
  referenceModelField?: string;
  selection?: Array<[string, string]>;
  relationEntry?: ContractV2Dictionary;
  widgetOptions?: ContractV2Dictionary;
  subview?: ContractV2Dictionary;
  filename?: string;
  digits?: [number, number];
  unit?: ContractV2FieldDescriptor['unit'];
  temporal?: ContractV2FieldDescriptor['temporal'];
  currencyField?: string;
  attachmentRole?: string;
  help?: string;
  uiUsage?: 'fact' | 'interaction';
  changeDefault?: boolean;
  definitionRecord?: string;
  definitionRecordField?: string;
  groupOperator?: string;
  searchable?: boolean;
  sortable?: boolean;
  store?: boolean;
  translate?: boolean;
  trim?: boolean;
  related?: string[];
  size?: number;
  technical?: boolean;
  formStructureRole?: ContractV2FormStructureRole;
}

export interface ContractV2Container {
  containerId: string;
  containerType: string;
  type?: string;
  name?: string;
  string?: string;
  label?: string;
  nolabel?: boolean;
  text?: string;
  displayLabel?: string;
  semanticTitle?: string;
  semanticAnchor?: string;
  title: string;
  span: number;
  styleToken?: string;
  zone?: ContractV2ContainerZone;
  cols?: number;
  columns?: number;
  widget?: string;
  widgetId?: string;
  fieldCode?: string;
  nativeLocator?: string;
  occurrenceIndex?: number;
  sourcePosition?: number;
  nativeIdentity?: ContractV2NativeOccurrenceIdentity;
  semanticType?: string;
  componentConfig?: ContractV2Dictionary;
  attributes?: ContractV2Dictionary;
  fieldInfo?: ContractV2Dictionary;
  filename?: string;
  badge?: ContractV2Dictionary;
  buttonType?: string;
  action?: ContractV2Dictionary | null;
  modifiers?: ContractV2Dictionary;
  invisible?: unknown;
  readonly?: unknown;
  required?: unknown;
  columnInvisible?: unknown;
  domain?: unknown;
  context?: unknown;
  options?: unknown;
  visible?: boolean;
  col?: number | string;
  class?: string;
  className?: string;
  fieldSize?: string;
  size?: string;
  formStructure?: ContractV2Dictionary;
  formStructureRole?: ContractV2FormStructureRole;
  sourceAuthority?: ContractV2Dictionary;
  fields?: string[];
  children: ContractV2Container[];
  widgetList: ContractV2Widget[];
}

export interface ContractV2ActivityNode {
  tag: string;
  native_locator: string;
  occurrence_index: number;
  source_position: number;
  attributes: ContractV2Dictionary;
  text: string;
  tail: string;
  children: ContractV2ActivityNode[];
}

export interface ContractV2ActivityNodeOccurrence {
  tag: string;
  native_locator: string;
  occurrence_index: number;
  source_position: number;
  attributes: ContractV2Dictionary;
  text: string;
  tail: string;
}

export interface ContractV2ActivityFieldOccurrence {
  name: string;
  label: string;
  widget: string;
  native_locator: string;
  occurrence_index: number;
  source_position: number;
  attributes: ContractV2Dictionary;
  text: string;
  tail: string;
  modifiers: string;
  decorations: ContractV2Dictionary[];
  field_type: string;
  currency_field: string;
  digits: [] | [number, number];
}

export interface ContractV2ActivitySourceAuthority {
  kind: 'native_activity_view_projection';
  authorities: ['ir.ui.view', 'ir.model.fields', 'ir.actions.act_window'];
  projection_only: true;
  no_business_fact_authority: true;
  runtime_carrier: 'ui.contract.v2.layoutContract.activityProfile';
}

export interface ContractV2ActivityProfile {
  activityTypeSlots: ContractV2Dictionary;
  deadlineSlots: ContractV2Dictionary;
  assigneeSlots: ContractV2Dictionary;
  fieldOccurrences: ContractV2ActivityFieldOccurrence[];
  nativeAttrs: ContractV2Dictionary;
  nodeOccurrences: ContractV2ActivityNodeOccurrence[];
  template: {
    native_locator: string;
    occurrence_index: number;
    names: string[];
    nodes: ContractV2ActivityNode[];
  };
  templateQwebPresent: boolean;
  actions: ContractV2Dictionary[];
  actionCount: number;
  sourceAuthority: ContractV2ActivitySourceAuthority;
}

export interface ContractV2AnalysisSourceAuthority {
  kind: 'native_pivot_view_projection' | 'native_graph_view_projection';
  authorities: ['ir.ui.view', 'ir.model.fields', 'ir.actions.act_window'];
  projection_only: true;
  no_business_fact_authority: true;
  runtime_carrier: 'ui.contract.v2.layoutContract.pivotProfile' | 'ui.contract.v2.layoutContract.graphProfile';
}

export interface ContractV2AnalysisProfile {
  measures: ContractV2Dictionary[];
  dimensions: ContractV2Dictionary[];
  defaults?: ContractV2Dictionary;
  typeDefault?: string;
  sourceAuthority: ContractV2AnalysisSourceAuthority;
}

export interface ContractV2LayoutContract {
  pageId: string;
  layoutType: ContractV2LayoutType;
  adaptMode: ContractV2AdaptMode;
  containerTree: ContractV2Container[];
  layoutHints: ContractV2Dictionary;
  /** Current native List projection, including column occurrence identity. */
  listProfile?: ContractV2ListProfile;
  activityProfile?: ContractV2ActivityProfile;
  pivotProfile?: ContractV2AnalysisProfile;
  graphProfile?: ContractV2AnalysisProfile;
}

export interface ContractV2ActionRule {
  executionScope?: string;
  actionSemantics?: ActionSemantics;
  actionSemanticsInvalid?: boolean;
  actionId: string;
  backendIdentity?: string;
  nativeIdentity?: ContractV2NativeOccurrenceIdentity;
  triggerType: ContractV2TriggerType;
  sourceWidgetId: string;
  targetIds: string[];
  dispatchMode: ContractV2DispatchMode;
  targetScope: ContractV2TargetScope;
  refreshMode: ContractV2RefreshMode;
  actionKey?: string;
  label?: string;
  intent?: string;
  target?: ContractV2Dictionary;
  button?: ContractV2Dictionary;
  visible?: ContractV2Dictionary;
  modifiers?: ContractV2Dictionary;
  invisible?: unknown;
  allowed?: boolean;
  enabled?: boolean;
  disabled?: boolean;
  visibleProfiles?: string[];
  presentation?: ContractV2Dictionary;
  required_params?: string[];
  requires_reason?: boolean;
  actionSafety?: ContractV2Dictionary;
  refreshPolicy?: ContractV2Dictionary;
  submitPolicy?: ContractV2Dictionary;
  tracePolicy?: ContractV2Dictionary;
  sourceTrace?: ContractV2Dictionary[];
  presentationAuthority?: string;
  presentationPriority?: number;
  sourceActionKey?: string;
  sourceChannel?: string;
  permissionConstraints?: ContractV2Dictionary;
  reasonCode?: string;
  reasonMessage?: string;
  entitlementEvaluated?: boolean;
  authorizationAllowed?: boolean;
  businessAvailable?: boolean;
}

export interface ContractV2ActionContract {
  actionRuleList: ContractV2ActionRule[];
  dependencyGraph: Record<string, string[]>;
  primaryResolution?: ContractV2Dictionary;
  deletePolicy?: ContractV2Dictionary;
  surfacePolicies?: ContractV2Dictionary;
  identityPolicy?: ContractV2Dictionary;
}

export interface ContractV2VisibleFields {
  fields: string[];
  sourceAuthority?: ContractV2Dictionary;
}

export interface ContractV2FieldGroups {
  groups: ContractV2Dictionary[];
  sourceAuthority?: ContractV2Dictionary;
}

export interface ContractV2SourceContext {
  formViewId?: number;
  context?: ContractV2Dictionary;
  domain?: unknown[];
  contextRaw?: string;
  domainRaw?: string;
  renderProfile?: 'create' | 'edit' | 'readonly';
  order?: string;
  limit?: number;
}

export interface ContractV2DataMeta extends ContractV2Dictionary {
  businessOperationProfile?: ContractV2Dictionary;
  visibleFields?: ContractV2VisibleFields;
  fieldGroups?: ContractV2FieldGroups;
  sourceContext?: ContractV2SourceContext;
  nativeModifierFieldTypes?: Record<string, string>;
  nativeModifierRelationSnapshots?: Record<string, { sourceValue: unknown; persistedIds: number[] }>;
}

export interface ContractV2DataContract {
  mainData: ContractV2Dictionary;
  tableRows: Record<string, unknown[]>;
  relationRows: Record<string, unknown[]>;
  dictData: Record<string, unknown>;
  pagination: Record<string, unknown>;
  dataSource: Record<string, ContractV2Dictionary>;
  dataMeta: ContractV2DataMeta;
  treeData?: Record<string, unknown[]>;
  ganttData?: Record<string, unknown[]>;
}

export interface ContractV2GlobalStatus {
  pageVisible?: boolean;
  pageAuth?: 'none' | 'read' | 'edit' | 'admin' | string;
  reasonCode?: string;
  modelRights?: ContractV2Dictionary;
  recordRights?: ContractV2Dictionary;
  viewCapabilities?: ContractV2Dictionary;
  entryCapabilities?: ContractV2Dictionary;
  effectiveRecordCapabilities?: ContractV2Dictionary;
  recordDeniedReasons?: ContractV2Dictionary;
  effectiveRenderProfile?: 'create' | 'edit' | 'readonly' | string;
  workflowPhase?: string;
  approvalPhase?: string;
}

export interface ContractV2WidgetStatus {
  widgetId: string;
  visible?: boolean;
  readonly?: boolean;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  auth?: ContractV2Auth;
  reasonCode?: string;
}

export interface ContractV2ButtonStatus {
  btnId: string;
  backendIdentity?: string;
  visible?: boolean;
  disabled?: boolean;
  reasonCode?: string;
  reasonMessage?: string;
  visibilityExplanation?: 'business_state';
}

export interface ContractV2ContainerStatus {
  containerId: string;
  visible?: boolean;
  disabled?: boolean;
  reasonCode?: string;
}

export interface ContractV2SelectorStatus {
  selector: string;
  visible?: boolean;
  readonly?: boolean;
  required?: boolean;
  disabled?: boolean;
  reasonCode?: string;
}

export interface ContractV2StatusContract {
  globalStatus: ContractV2GlobalStatus;
  widgetStatus: ContractV2WidgetStatus[];
  buttonStatus: ContractV2ButtonStatus[];
  containerStatus: ContractV2ContainerStatus[];
  selectorStatus: ContractV2SelectorStatus[];
}

export interface ContractV2RuntimeContract {
  patchStrategy: ContractV2PatchStrategy;
  cachePolicy: ContractV2CachePolicy;
  optimistic: boolean;
  lazyContainer: string[];
  virtualization: ContractV2Dictionary;
  retryPolicy: ContractV2Dictionary;
  renderStrategy?: ContractV2RenderStrategy;
  hydration?: ContractV2Dictionary;
  patchOperations?: ContractV2PatchOperation[];
  tracePolicy?: ContractV2Dictionary;
  complexityBudget?: ContractV2Dictionary;
  aiEnvelope?: ContractV2Dictionary;
  interactionMode?: string;
  actionTarget?: string;
  collaboration?: ContractV2Dictionary;
  businessWorkspace?: ContractV2Dictionary;
  businessActions?: ContractV2Dictionary[];
  deliveryProfile?: ContractV2DeliveryProfile;
  intakeAutosave?: ContractV2Dictionary;
  fieldSemantics?: ContractV2Dictionary;
  validationRules?: ContractV2Dictionary[];
  governance?: ContractV2Dictionary;
  recordVersionPolicy?: ContractV2Dictionary;
}

export interface ContractV2Lifecycle {
  lifecycleVersion: string;
  stage: string;
  definition: {
    schemaId: string;
    schemaVersion: string;
    schemaSha256: string;
    contractVersion: string;
    normativeStatus: string;
    publishedVersionRef?: string;
  };
  generation: {
    generator: string;
    generatorVersion: string;
    sourceType: string;
    sourceSha256: string;
  };
  runtime: {
    requestId: string;
    traceId: string;
    clientType: string;
    traceSource: string;
  };
  integrity: {
    algorithm: string;
    contractSha256: string;
  };
  authority: ContractV2Dictionary;
}

export interface ContractV2Meta {
  etag: string;
  snapshotId: string;
  traceId: string;
  requestId: string;
  sourceType: string;
  lifecycle: ContractV2Lifecycle;
  deliveryTrim?: {
    clientType: ContractV2ClientType;
    deliveryProfile: ContractV2DeliveryProfile;
    compact: boolean;
    limits: Record<'containers' | 'widgets' | 'actions', number | null>;
    original: Record<'containers' | 'widgets' | 'actions', number>;
    delivered: Record<'containers' | 'widgets' | 'actions', number>;
    omitted: Record<'containers' | 'widgets' | 'actions', number>;
  };
}

export interface ContractV2Snapshot {
  pageInfo: ContractV2PageInfo;
  layoutContract: ContractV2LayoutContract;
  statusContract: ContractV2StatusContract;
  actionContract: ContractV2ActionContract;
  dataContract: ContractV2DataContract;
  runtimeContract: ContractV2RuntimeContract;
  meta: ContractV2Meta;
  formStructureContract?: ContractV2FormStructureContract;
  searchContract?: ContractV2Dictionary;
  workflowContract?: ContractV2Dictionary;
  fieldOwnership?: ContractV2FieldOwnership;
  pageComposition?: ContractV2PageComposition;
  noticeContract?: ContractV2NoticeContract;
  nativeActionContract?: ContractV2NativeActionContract;
}

export interface ContractV2FieldOwnership {
  [fieldRef: string]: { ownerSlotRef: string; ownerGroupRef?: string };
}

export interface ContractV2PageComposition {
  class: string;
  diagnostics?: unknown[];
  schemaVersion?: string;
  permissionSemanticsPreserved?: boolean;
}

export interface ContractV2SubmissionReadinessNotice {
  visible: boolean;
  status: string;
  statusLabel?: string;
  state?: string;
  message?: string;
  nextStep?: string;
  nextStepAction?: string;
  reasonCode?: string;
  sourceAuthority?: string;
}

export interface ContractV2NoticeContract {
  submissionReadiness?: ContractV2SubmissionReadinessNotice;
}

export interface ContractV2UnsupportedFeature {
  code: string;
  message: string;
  path: string;
}

export interface ContractV2NormalizedStore {
  snapshot: ContractV2Snapshot;
  widgetsById: ReadonlyMap<string, ContractV2Widget>;
  widgetsByFieldCode: ReadonlyMap<string, ContractV2Widget>;
  widgetsByFieldCodeAll: ReadonlyMap<string, readonly ContractV2Widget[]>;
  widgetsByOwnerContainerId: ReadonlyMap<string, readonly ContractV2Widget[]>;
  actionsById: ReadonlyMap<string, ContractV2ActionRule>;
  widgetStatusById: ReadonlyMap<string, ContractV2WidgetStatus>;
  buttonStatusById: ReadonlyMap<string, ContractV2ButtonStatus>;
  buttonStatusByBackendIdentity: ReadonlyMap<string, ContractV2ButtonStatus>;
  containerStatusById: ReadonlyMap<string, ContractV2ContainerStatus>;
  primaryDataSource: ContractV2Dictionary | null;
  unsupported: ContractV2UnsupportedFeature[];
}
