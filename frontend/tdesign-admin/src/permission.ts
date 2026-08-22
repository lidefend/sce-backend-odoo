import 'nprogress/nprogress.css'; // progress bar style

import NProgress from 'nprogress'; // progress bar
import { MessagePlugin } from 'tdesign-vue-next';
import type { RouteRecordRaw } from 'vue-router';

import { validateRouteAuthority } from '@/api/odoo';
import { syncDocumentTitle } from '@/config/product';
import router from '@/router';
import { getPermissionStore, useUserStore } from '@/store';
import {
  findRouteAuthority,
  positiveInteger,
  requiresRuntimeRouteValidation,
  routeAuthorityValidationParams,
} from '@/utils/route/authority';
import { firstAvailableRoute, isNotFoundRoute, originalRequestedPath } from '@/utils/route/roleLanding';

NProgress.configure({ showSpinner: false });

router.beforeEach(async (to) => {
  NProgress.start();

  const permissionStore = getPermissionStore();
  const { whiteListRouters } = permissionStore;

  const userStore = useUserStore();

  if (userStore.token) {
    if (to.path === '/login') {
      try {
        await userStore.logout();
      } catch {
        userStore.clearSession();
      }
      await permissionStore.restoreRoutes();
      return true;
    }
    try {
      await userStore.getUserInfo();

      if (to.meta.adminOnly === true && !userStore.isAdmin) {
        return { path: '/result/403', query: { from: to.fullPath, reason: 'ADMIN_ONLY' } };
      }

      const { asyncRoutes } = permissionStore;

      if (asyncRoutes && asyncRoutes.length === 0) {
        const routeList = await permissionStore.buildAsyncRoutes();
        routeList.forEach((item: RouteRecordRaw) => {
          router.addRoute(item);
        });

        const requestedPath = originalRequestedPath(to);
        const resolved = router.resolve(requestedPath);
        if (isNotFoundRoute(resolved)) {
          return { path: firstAvailableRoute(permissionStore.asyncRoutes), replace: true };
        }
        return { path: resolved.fullPath, replace: true };
      }
      if (isNotFoundRoute(to)) {
        return { path: firstAvailableRoute(permissionStore.asyncRoutes), replace: true };
      }
      if (router.hasRoute(to.name!)) {
        const actionId = positiveInteger(to.params.actionId || to.query.action_id || to.meta.actionId);
        const menuId = positiveInteger(to.params.menuId || to.query.menu_id || to.meta.menuId);
        if ((actionId || menuId) && userStore.routeAuthority) {
          const selected = userStore.recordContext.selected as Record<string, unknown> | null | undefined;
          const authority = findRouteAuthority(userStore.routeAuthority, {
            actionId,
            menuId,
            query: to.query as Record<string, unknown>,
            companyId: positiveInteger(userStore.recordContext.company_id || selected?.company_id) || null,
            selectedRecordId: positiveInteger(selected?.id) || null,
          });
          if (!authority) {
            return { path: '/result/403', query: { from: to.fullPath, reason: 'NAVIGATION_AUTHORITY_DENIED' } };
          }
          // The runtime validator expects one contextual action match. Ordinary
          // menus may legitimately share an action, so their delivered
          // route-authority entry is authoritative unless it declares context.
          if (actionId && requiresRuntimeRouteValidation(authority)) {
            try {
              const validation = await validateRouteAuthority(
                routeAuthorityValidationParams(authority, to.query as Record<string, unknown>),
              );
              if (validation.allowed !== true) {
                return { path: '/result/403', query: { from: to.fullPath, reason: 'RUNTIME_AUTHORITY_DENIED' } };
              }
            } catch {
              return { path: '/result/403', query: { from: to.fullPath, reason: 'RUNTIME_AUTHORITY_DENIED' } };
            }
          }
        }
        return true;
      } else {
        return '/';
      }
    } catch (error) {
      MessagePlugin.error((error as Error).message);
      NProgress.done();
      return {
        path: '/login',
        query: { redirect: encodeURIComponent(to.fullPath) },
      };
    }
  } else {
    /* white list router */
    if (whiteListRouters.includes(to.path)) {
      if (to.path === '/login') await permissionStore.restoreRoutes();
      NProgress.done();
      return true;
    } else {
      NProgress.done();
      return {
        path: '/login',
        query: { redirect: encodeURIComponent(to.fullPath) },
      };
    }
  }
});

router.afterEach((to) => {
  const routeTitle = to.meta?.title;
  const pageTitle =
    typeof routeTitle === 'string'
      ? routeTitle
      : String((routeTitle as Record<string, unknown> | undefined)?.zh_CN || '');
  syncDocumentTitle(pageTitle);
  NProgress.done();
});
