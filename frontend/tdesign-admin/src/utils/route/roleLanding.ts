import type { RouteRecordRaw } from 'vue-router';

const NOT_FOUND_ROUTE_NAME = '404Page';

export interface ResolvedRouteLike {
  fullPath?: string;
  name?: unknown;
  path?: string;
  redirectedFrom?: ResolvedRouteLike;
}

export function originalRequestedPath(route: ResolvedRouteLike) {
  return route.redirectedFrom?.fullPath || route.fullPath || route.path || '/';
}

export function isNotFoundRoute(route: ResolvedRouteLike) {
  return (
    route.name === NOT_FOUND_ROUTE_NAME ||
    route.redirectedFrom?.name === NOT_FOUND_ROUTE_NAME ||
    route.name === 'Result404' ||
    route.path === '/result/404'
  );
}

export function firstAvailableRoute(routes: RouteRecordRaw[]) {
  const route = routes.find((item) => item.name !== NOT_FOUND_ROUTE_NAME && item.meta?.hidden !== true);
  if (!route) return '/dashboard/base';
  if (route.redirect) return String(route.redirect);
  if (route.children?.length) {
    const child = route.children.find((item) => item.meta?.hidden !== true);
    if (child) {
      const parentPath = String(route.path || '').replace(/\/$/, '');
      const childPath = String(child.path || '').replace(/^\//, '');
      return childPath ? `${parentPath}/${childPath}`.replace('//', '/') : parentPath || '/dashboard/base';
    }
  }
  return String(route.path || '/dashboard/base');
}
