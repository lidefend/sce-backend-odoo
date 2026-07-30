export interface WorkspaceHeroRow {
  key: string;
  label: string;
  value: string;
}

export interface WorkspaceAdviceRow {
  id: string;
  level: 'red' | 'amber' | 'green';
  title: string;
  description: string;
  actionLabel: string;
  actionEntryId: string;
  actionPath: string;
  actionQuery: Record<string, string>;
}

export interface WorkspaceMetricRow {
  key: string;
  label: string;
  value: string;
  delta: string;
  hint: string;
  tone: string;
  progress: string;
}

export interface WorkspaceTodayActionRow {
  id: string;
  title: string;
  description: string;
  count: number;
  status: string;
  tone: string;
  source: string;
  actionLabel: string;
  actionKey: string;
  entryId: string;
  sceneKey: string;
  route: string;
}

export interface WorkspaceRiskAlertRow {
  id: string;
  title: string;
  description: string;
  tone: string;
  source: string;
  actionLabel: string;
  actionKey: string;
  sceneKey: string;
  path: string;
  query: Record<string, string>;
  entryKey: string;
  entryId: string;
}

export interface WorkspaceOpsSummary {
  bars: Record<string, unknown>;
  kpi: Record<string, unknown>;
  summary: string;
}

export interface WorkspaceSceneEntryRow {
  id: string;
  key: string;
  title: string;
  actionLabel: string;
  subtitle: string;
  sceneKey: string;
  sceneLabel: string;
  sequence: number;
  status: string;
  state: string;
  capabilityState: string;
  groupKey: string;
  groupLabel: string;
  reason: string;
  reasonCode: string;
  route: string;
  targetActionId: number;
  targetMenuId: number;
  targetModel: string;
  targetRecordId: string;
  contextQuery: Record<string, string>;
  sceneTags: string[];
  tileTags: string[];
}

export interface WorkspaceCapabilityGroupRow {
  key: string;
  label: string;
  sequence: number;
  capabilityCount: number;
  allowCount: number;
  readonlyCount: number;
  denyCount: number;
  readyCount: number;
  score: number;
  examples: Array<{
    key: string;
    label: string;
    state: string;
    capabilityState: string;
  }>;
}
