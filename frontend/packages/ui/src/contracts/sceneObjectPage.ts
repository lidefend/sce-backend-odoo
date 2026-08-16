export type SceneTone = 'Neutral' | 'Information' | 'Positive' | 'Critical' | 'Negative';

export type SceneFieldKind = 'text' | 'amount' | 'date' | 'select' | 'textarea';

export interface SceneAction {
  id: string;
  label: string;
  tier: 'primary' | 'secondary' | 'transparent';
  disabled?: boolean;
}

export interface SceneFact {
  id: string;
  label: string;
  value: string;
  tone?: SceneTone;
  emphasis?: boolean;
}

export interface SceneFieldOption {
  key: string;
  label: string;
}

export interface SceneField {
  id: string;
  label: string;
  value: string;
  kind: SceneFieldKind;
  required?: boolean;
  readonly?: boolean;
  invalid?: boolean;
  placeholder?: string;
  hint?: string;
  source?: string;
  span?: 'full' | 'half';
  options?: SceneFieldOption[];
}

export interface SceneFieldGroup {
  id: string;
  title: string;
  description?: string;
  fields: SceneField[];
}

export interface SceneContextGroup {
  id: string;
  title: string;
  facts: SceneFact[];
}

export interface SceneNotice {
  id: string;
  title: string;
  detail: string;
  tone: SceneTone;
}

export interface SceneTableColumn {
  key: string;
  label: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface SceneTableRow {
  id: string;
  values: Record<string, string>;
  tone?: SceneTone;
}

export interface SceneRelationTable {
  id: string;
  title: string;
  description?: string;
  columns: SceneTableColumn[];
  rows: SceneTableRow[];
  emptyText?: string;
}

export interface SceneReviewPanel {
  title: string;
  description: string;
  triggerLabel: string;
  groups: SceneContextGroup[];
  checklist: SceneFact[];
}

export interface SceneActivityItem {
  id: string;
  title: string;
  meta: string;
  detail: string;
  tone?: SceneTone;
}

export interface SceneActivityTab {
  id: string;
  label: string;
  count?: number;
  items: SceneActivityItem[];
  emptyText?: string;
}

export interface SceneWorkTab {
  id: string;
  label: string;
  active?: boolean;
}

export interface SceneObjectPageContract {
  identity: {
    productName: string;
    companyName: string;
    roleName: string;
    breadcrumbs: string[];
    workTabs: SceneWorkTab[];
  };
  object: {
    eyebrow: string;
    title: string;
    subtitle: string;
    status: string;
    statusTone: SceneTone;
    lastSavedLabel: string;
  };
  actions: SceneAction[];
  headerFacts: SceneFact[];
  notices?: SceneNotice[];
  task: {
    title: string;
    description: string;
    groups: SceneFieldGroup[];
  };
  context: {
    title: string;
    description: string;
    groups: SceneContextGroup[];
  };
  relations?: {
    title: string;
    description: string;
    tables: SceneRelationTable[];
  };
  reviewPanel?: SceneReviewPanel;
  activities: {
    title: string;
    tabs: SceneActivityTab[];
  };
}
