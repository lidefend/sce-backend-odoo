import type { ContractV2ActionRule } from '../contracts/v2/types';

export type CanonicalFormRenderMode = 'create' | 'edit' | 'readonly';
export type CanonicalFormZoneRole = 'primary' | 'subordinate';

export type CanonicalFormAction = {
  key: string;
  label: string;
  tier: 'primary' | 'secondary' | 'overflow' | 'configuration';
  visible: boolean;
  enabled: boolean;
  reasonCode: string;
  visibleProfiles: CanonicalFormRenderMode[];
  safety: Readonly<Record<string, unknown>>;
  actionRef: ContractV2ActionRule;
};

export type CanonicalFormField = {
  widgetId: string;
  fieldCode: string;
  label: string;
  value: unknown;
  fieldType: string;
  componentKey: string;
  span: number;
  visible: boolean;
  readonly: boolean;
  required: boolean;
  disabled: boolean;
  reasonCode: string;
  componentConfig: Readonly<Record<string, unknown>>;
};

export type CanonicalFormNode = {
  nodeId: string;
  kind: string;
  title: string;
  zoneRole: CanonicalFormZoneRole;
  columns: number;
  visible: boolean;
  disabled: boolean;
  reasonCode: string;
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
