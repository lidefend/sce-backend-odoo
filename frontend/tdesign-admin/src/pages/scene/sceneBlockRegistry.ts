export interface SceneBlockRegistryEntry {
  kind: string;
  label: string;
  aliases?: string[];
  renderer: 'native' | 'table' | 'collection' | 'unsupported';
}

// The old SC Web resolves blocks through a registry before rendering. Keep the
// same boundary in the TDesign runtime so a new backend block is never silently
// interpreted as an unrelated card or table.
const entries: SceneBlockRegistryEntry[] = [
  ...[
    ['metric_row', '核心指标'],
    ['overview_strip', '业务概览'],
    ['progress_summary', '进度概览'],
    ['record_summary', '记录摘要'],
  ].map(([kind, label]) => ({ kind, label, renderer: 'native' as const })),
  ...[
    ['todo_list', '待办事项'],
    ['warning_list', '风险事项'],
    ['shortcut_grid', '快捷入口'],
    ['activity_feed', '最新动态'],
    ['entry_grid', '入口列表'],
  ].map(([kind, label]) => ({ kind, label, renderer: 'collection' as const })),
  ...[
    ['record_table', '业务记录'],
    ['list_view', '业务列表'],
    ['relation_block', '关联记录'],
  ].map(([kind, label]) => ({ kind, label, renderer: 'table' as const })),
  ...[
    ['primary_actions', '主要操作'],
    ['smart_actions', '快捷操作'],
    ['action_bar', '操作栏'],
    ['alert_panel', '风险提醒'],
    ['toolbar', '页面工具'],
    ['statusbar', '状态栏'],
    ['content', '业务内容'],
    ['kanban_board', '业务看板'],
  ].map(([kind, label]) => ({ kind, label, renderer: 'native' as const })),
];

const registry = new Map<string, SceneBlockRegistryEntry>();
entries.forEach((entry) => {
  registry.set(entry.kind, entry);
  entry.aliases?.forEach((alias) => registry.set(alias, entry));
});

export function normalizeSceneBlockKind(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[./ ]+/g, '_');
}

export function resolveSceneBlockRegistryEntry(value: unknown): SceneBlockRegistryEntry | null {
  const kind = normalizeSceneBlockKind(value);
  return kind ? registry.get(kind) || null : null;
}

export function registeredSceneBlockKinds(): string[] {
  return [...new Set([...registry.values()].map((entry) => entry.kind))].sort();
}

export function sceneBlockReasonCode(value: unknown): string {
  const kind = normalizeSceneBlockKind(value);
  return kind ? 'SCENE_BLOCK_KIND_NOT_REGISTERED' : 'SCENE_BLOCK_KIND_MISSING';
}
