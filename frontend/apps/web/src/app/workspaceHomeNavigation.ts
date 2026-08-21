export type WorkspaceNavigationNode = {
  id?: string | number;
  key?: string;
  name?: string;
  label?: string;
  title?: string;
  menu_id?: number;
  children?: WorkspaceNavigationNode[];
  meta?: Record<string, unknown>;
  route?: string;
  scene_key?: string;
  sceneKey?: string;
  action_id?: number;
  actionId?: number;
};

export type WorkspaceNavigationLink = {
  key: string;
  label: string;
  detail: string;
  route: string;
};

export function mergeWorkspaceNavigationLinks(
  authoritative: WorkspaceNavigationLink[],
  supplemental: WorkspaceNavigationLink[],
): WorkspaceNavigationLink[] {
  return [...authoritative, ...supplemental]
    .filter((item, index, rows) => rows.findIndex((row) => row.route === item.route) === index);
}

function text(value: unknown): string {
  return String(value ?? '').trim();
}

export function workspaceNavigationNodeRoute(node: WorkspaceNavigationNode): string {
  const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
  const route = text(node.route || meta.route);
  if (route) return route;
  const sceneKey = text(node.scene_key || node.sceneKey || meta.scene_key || meta.sceneKey);
  if (sceneKey) return `/s/${encodeURIComponent(sceneKey)}`;
  const actionId = Number(node.action_id || node.actionId || meta.action_id || meta.actionId || 0);
  const menuId = Number(node.menu_id || meta.menu_id || meta.menuId || 0);
  if (actionId > 0) return `/a/${actionId}${menuId > 0 ? `?menu_id=${menuId}&action_id=${actionId}` : ''}`;
  if (menuId > 0 && !node.children?.length) return `/m/${menuId}`;
  return '';
}

export function workspaceNavigationNodeLabel(node: WorkspaceNavigationNode): string {
  return text(node.title || node.name || node.label).replace(/\s*\(\d+\)\s*$/g, '');
}

function firstReachable(node: WorkspaceNavigationNode): WorkspaceNavigationNode | null {
  if (workspaceNavigationNodeRoute(node)) return node;
  for (const child of node.children || []) {
    const reachable = firstReachable(child);
    if (reachable) return reachable;
  }
  return null;
}

export function resolveWorkspaceNavigationLink(node: WorkspaceNavigationNode): WorkspaceNavigationLink | null {
  const directRoute = workspaceNavigationNodeRoute(node);
  const target = directRoute ? node : firstReachable(node);
  if (!target) return null;
  const route = workspaceNavigationNodeRoute(target);
  const targetLabel = workspaceNavigationNodeLabel(target);
  if (!route || !targetLabel) return null;
  const groupLabel = workspaceNavigationNodeLabel(node);
  return {
    key: `${text(target.key || target.id)}:${route}`,
    label: targetLabel,
    detail: groupLabel && groupLabel !== targetLabel ? groupLabel : targetLabel,
    route,
  };
}
