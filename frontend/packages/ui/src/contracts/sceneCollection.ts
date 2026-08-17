import type {
  SceneAction,
  SceneFact,
  SceneRelationTable,
  SceneTone,
  SceneWorkTab,
} from './sceneObjectPage';

export interface SceneWorkspaceIdentity {
  productName: string;
  companyName: string;
  roleName: string;
  breadcrumbs: string[];
  workTabs: SceneWorkTab[];
}

export interface SceneCollectionFilter {
  id: string;
  label: string;
  value: string;
  active?: boolean;
}

export interface SceneCollectionRowPresentation {
  accessibilityLabel: string;
  titleField: string;
  statusField?: string;
  mobileFields: string[];
}

export interface SceneCollectionSourceTrace {
  kind: 'normalized-collection';
  pageId: string;
  sceneKey: string;
  contractVersion: string;
}

export interface SceneCollectionContract {
  identity: SceneWorkspaceIdentity;
  title: string;
  description: string;
  eyebrow: string;
  actions: SceneAction[];
  summaries: SceneFact[];
  filters: SceneCollectionFilter[];
  table: SceneRelationTable;
  rowPresentation: SceneCollectionRowPresentation;
  selectionMode: 'none' | 'multiple';
  readonly: boolean;
  totalCount?: number;
  sourceTrace?: SceneCollectionSourceTrace;
}

export interface SceneHierarchyNode {
  id: string;
  label: string;
  meta?: string;
  value?: string;
  status?: string;
  tone?: SceneTone;
  children?: SceneHierarchyNode[];
}

export interface SceneHierarchyContract {
  identity: SceneWorkspaceIdentity;
  title: string;
  description: string;
  eyebrow: string;
  actions: SceneAction[];
  summaries: SceneFact[];
  nodes: SceneHierarchyNode[];
}
