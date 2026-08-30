import type { ContractV2ActionRule, ContractV2FormPresentationMode } from '../contracts/v2/types';

export type CanonicalFormRenderMode = 'create' | 'edit' | 'readonly';
export type CanonicalFormPresentationMode = ContractV2FormPresentationMode;
export type CanonicalFormZoneRole = 'primary' | 'subordinate';
export type CanonicalFormSemanticRole = 'summary' | 'task' | 'context' | 'risk' | 'relation' | 'activity' | 'audit';

export type CanonicalRelationValue = {
  id: string | number;
  displayName: string;
  model: string;
};

export type CanonicalFormAction = {
  key: string;
  label: string;
  icon: string;
  tier: 'primary' | 'secondary' | 'overflow' | 'configuration';
  visible: boolean;
  enabled: boolean;
  reasonCode: string;
  visibleProfiles: CanonicalFormRenderMode[];
  safety: Readonly<Record<string, unknown>>;
  actionRef: ContractV2ActionRule;
};

export type CanonicalAuditEvent = {
  key: string;
  actor: string;
  occurredAt: string;
  event: string;
  result: string;
  detail: string;
};

export type CanonicalFormField = {
  widgetId: string;
  fieldCode: string;
  widgetType: string;
  label: string;
  hideLabel: boolean;
  value: unknown | CanonicalRelationValue;
  fieldType: string;
  componentKey: string;
  componentResolution: import('./professionalComponentRegistry').ProfessionalComponentResolution;
  presentationMode: CanonicalFormPresentationMode;
  renderProfile: CanonicalFormRenderMode;
  span: number;
  nativeLocator: string;
  occurrenceIndex: number | null;
  sourcePosition: number | null;
  visible: boolean;
  readonly: boolean;
  required: boolean;
  disabled: boolean;
  reasonCode: string;
  placeholder: string;
  auth: string;
  semanticRole: CanonicalFormSemanticRole | '';
  semanticSlot: string;
  semanticGroup: string;
  componentConfig: Readonly<Record<string, unknown>>;
  fieldDescriptor: Readonly<Record<string, unknown>>;
};

export type CanonicalFormNode = {
  nodeId: string;
  kind: string;
  title: string;
  text: string;
  attributes: Readonly<Record<string, unknown>>;
  nativePresentation: Readonly<Record<string, unknown>>;
  span: number;
  styleToken: string;
  zoneRole: CanonicalFormZoneRole;
  columns: number;
  visible: boolean;
  disabled: boolean;
  reasonCode: string;
  semanticRole: CanonicalFormSemanticRole | '';
  semanticSlot: string;
  semanticGroup: string;
  action: CanonicalFormAction | null;
  nativeWidget: string;
  fields: CanonicalFormField[];
  children: CanonicalFormNode[];
};

/**
 * Ephemeral in-memory ViewModel. It is never an API payload, persistence
 * format, business contract, or version-negotiated protocol.
 */
export type CanonicalFormRenderModel = {
  identity: {
    pageId: string;
    sceneKey: string;
    model: string;
    viewType: string;
    mode: CanonicalFormRenderMode;
    presentationMode: CanonicalFormPresentationMode;
    sourceContractSha256: string;
  };
  shell: {
    title: string;
    pageVisible: boolean;
    pageAuth: string;
    reasonCode: string;
  };
  actionBar: CanonicalFormAction[];
  zones: {
    primary: CanonicalFormNode[];
    subordinate: CanonicalFormNode[];
  };
  responsive: {
    adaptMode: string;
    layoutHints: Readonly<Record<string, unknown>>;
  };
  componentTokens: Readonly<Record<string, Readonly<Record<string, unknown>>>>;
};
