import type { RouteLocationNormalizedLoaded, RouteLocationNormalized } from 'vue-router';
import type { NavNode } from '@sc/schema';
import { contractGapError } from './contract/contractGap';
import { findActionMeta, findActionMetaByMenu, findMenuNode } from './menu';
import { getSceneByKey } from './resolvers/sceneRegistry';
import type { PageBreadcrumb, PageIdentityInput } from './pageIdentity';

type RouteLike = RouteLocationNormalized | RouteLocationNormalizedLoaded;
type DeclaredPageContract = {
  texts?: Record<string, unknown>;
  page_orchestration?: { page?: Record<string, unknown> };
};
type PageContracts = Record<string, DeclaredPageContract | undefined>;

const PAGE_CONTRACT_KEY_BY_ROUTE: Record<string, string> = {
  login: 'login',
  'platform-admin-login': 'login',
  'account-activation': 'account_activation',
  'password-recovery': 'password_recovery',
  home: 'home',
  'scene-home': 'home',
  'my-work': 'my_work',
  'scene-my-work': 'my_work',
  workbench: 'workbench',
  'scene-health': 'scene_health',
  'scene-packages': 'scene_packages',
  'usage-analytics': 'usage_analytics',
  'release-operator': 'release_operator',
  'capability-explorer': 'platform_capability_explorer',
  'business-config': 'business_config',
  'menu-config': 'menu_config',
  'form-field-config': 'action',
};

function positiveInteger(value: unknown): number {
  const parsed = Number(Array.isArray(value) ? value[0] : value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : 0;
}

function routeText(value: unknown): string {
  return String(Array.isArray(value) ? value[0] || '' : value || '').trim();
}

export function resolveRouteContractTitle(routeName: unknown, pageContracts?: PageContracts): string {
  const name = String(routeName || '').trim();
  const pageKey = PAGE_CONTRACT_KEY_BY_ROUTE[name];
  if (!pageKey) return '';
  const contract = pageContracts?.[pageKey];
  return routeText(contract?.texts?.title || contract?.page_orchestration?.page?.title);
}

function requireRouteContractTitle(name: string, pageContracts: PageContracts): string {
  const pageKey = PAGE_CONTRACT_KEY_BY_ROUTE[name];
  const title = resolveRouteContractTitle(name, pageContracts);
  if (title) return title;
  const missing = `page_contracts.pages.${pageKey || name}.texts.title`;
  throw contractGapError({
    kind: 'contract_defect',
    failureClass: 'contract_missing',
    missing,
    requiredDeclarationLayer: 'P0:smart_core:page_contracts_builder',
  }, `ContractGapError: ${missing}`);
}

function menuLabel(node: NavNode | null): string {
  return String(node?.label || node?.name || node?.title || '').trim();
}

function findMenuPath(nodes: NavNode[], menuId: number, parents: NavNode[] = []): NavNode[] {
  for (const node of nodes) {
    const path = [...parents, node];
    if (Number(node.menu_id || node.id || 0) === menuId) return path;
    const nested = findMenuPath(node.children || [], menuId, path);
    if (nested.length) return nested;
  }
  return [];
}

function menuBreadcrumbs(nodes: NavNode[], menuId: number): PageBreadcrumb[] {
  return findMenuPath(nodes, menuId).map((node) => {
    const id = Number(node.menu_id || node.id || 0);
    const hasTarget = Boolean(node.meta?.action_id || node.meta?.scene_key);
    return { label: menuLabel(node), ...(id > 0 && hasTarget ? { to: `/m/${id}` } : {}) };
  });
}

export function resolveRoutePageIdentity(
  route: RouteLike,
  menuTree: NavNode[],
  pageContracts: PageContracts = {},
): PageIdentityInput {
  const name = String(route.name || '').trim();
  if (name === 'login' || name === 'platform-admin-login') {
    return { fallbackTitle: resolveRouteContractTitle(name, pageContracts) || '登录' };
  }
  if (name === 'account-activation' || name === 'password-recovery') {
    return { fallbackTitle: requireRouteContractTitle(name, pageContracts) };
  }
  if (name === 'access-denied') {
    const from = routeText(route.query.from);
    let targetAction = 0;
    let targetMenu = 0;
    try {
      const target = new URL(from || '/', 'http://page.identity.local');
      targetAction = positiveInteger(target.pathname.match(/^\/a\/(\d+)/)?.[1] || target.searchParams.get('action_id'));
      targetMenu = positiveInteger(target.pathname.match(/^\/m\/(\d+)/)?.[1] || target.searchParams.get('menu_id'));
    } catch {
      // Invalid source URLs are intentionally ignored on the denial surface.
    }
    const targetNode = targetMenu ? findMenuNode(menuTree, targetMenu) : null;
    const targetMeta = (targetMenu ? findActionMetaByMenu(menuTree, targetMenu, targetAction || undefined) : null)
      || (targetAction ? findActionMeta(menuTree, targetAction) : null);
    return {
      actionName: targetMeta?.name,
      menuName: menuLabel(targetNode),
      breadcrumbs: targetMenu ? menuBreadcrumbs(menuTree, targetMenu) : [],
      fallbackTitle: '无权访问',
      state: 'denied',
    };
  }
  if (name === 'not-found') return { fallbackTitle: '记录不存在', state: 'not-found' };
  if (name === 'home' || name === 'scene-home' || name === 'my-work' || name === 'scene-my-work') {
    const title = requireRouteContractTitle(name, pageContracts);
    return { fallbackTitle: title, breadcrumbs: [{ label: title }] };
  }

  const menuId = positiveInteger(route.params.menuId || route.query.menu_id);
  const actionId = positiveInteger(route.params.actionId || route.query.action_id);
  const menuNode = menuId ? findMenuNode(menuTree, menuId) : null;
  const action = (menuId ? findActionMetaByMenu(menuTree, menuId, actionId || undefined) : null)
    || (actionId ? findActionMeta(menuTree, actionId) : null);
  const actionName = action?.ui_title || action?.scene_title || action?.menu_title || action?.name;
  const crumbs = menuBreadcrumbs(menuTree, menuId);

  if (name === 'action' || name === 'menu') {
    return {
      kind: 'list',
      actionName,
      menuName: menuLabel(menuNode),
      modelName: action?.model,
      modelLabel: action?.model_label,
      breadcrumbs: crumbs,
    };
  }
  if (name === 'record' || name === 'model-form') {
    const isCreate = routeText(route.params.id) === 'new';
    return {
      kind: isCreate ? 'create' : 'detail',
      actionName,
      menuName: menuLabel(menuNode),
      modelName: route.params.model,
      modelLabel: action?.model_label,
      breadcrumbs: crumbs,
      state: isCreate ? '' : 'loading',
    };
  }
  if (name === 'scene' || name.startsWith('scene-')) {
    const sceneKey = routeText(route.params.sceneKey || route.meta?.sceneKey || route.query.scene_key || route.query.scene);
    const scene = sceneKey ? getSceneByKey(sceneKey) : null;
    return { menuName: scene?.label, fallbackTitle: scene?.label || '业务场景', breadcrumbs: crumbs };
  }

  const title = PAGE_CONTRACT_KEY_BY_ROUTE[name]
    ? requireRouteContractTitle(name, pageContracts)
    : '工作台';
  return { fallbackTitle: title, breadcrumbs: [{ label: title }] };
}
