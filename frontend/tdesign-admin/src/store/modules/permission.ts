import { defineStore } from 'pinia';
import type { RouteRecordRaw } from 'vue-router';

import type { RouteItem } from '@/api/model/permissionModel';
import { navigationToRoutes } from '@/api/odoo';
import router, { fixedRouterList, homepageRouterList } from '@/router';
import { store } from '@/store';
import { transformObjectToRoute } from '@/utils/route';

import { useUserStore } from './user';

function copyRouteTree(routes: Array<RouteRecordRaw>): Array<RouteRecordRaw> {
  return routes.map((route) => {
    // Route metadata and component definitions can contain circular/runtime
    // references. Copy only the route tree; never recursively clone them.
    const copied = { ...route } as RouteRecordRaw;
    if (route.children) copied.children = copyRouteTree(route.children);
    return copied;
  });
}

function authorizedFixedRoutes(isAdmin: boolean) {
  return fixedRouterList.filter((route) => route.meta?.adminOnly !== true || isAdmin);
}

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    whiteListRouters: ['/login'],
    routers: [] as Array<RouteRecordRaw>,
    removeRoutes: [] as Array<RouteRecordRaw>,
    asyncRoutes: [] as Array<RouteRecordRaw>,
  }),
  actions: {
    async initRoutes() {
      const accessedRouters = this.asyncRoutes;
      const userStore = useUserStore(store);

      // 在菜单展示全部路由
      this.routers = copyRouteTree([
        ...homepageRouterList,
        ...accessedRouters,
        ...authorizedFixedRoutes(userStore.isAdmin),
      ]);
      // 在菜单只展示动态路由和首页
      // this.routers = [...homepageRouterList, ...accessedRouters];
      // 在菜单只展示动态路由
      // this.routers = [...accessedRouters];
    },
    async buildAsyncRoutes() {
      try {
        const userStore = useUserStore(store);
        if (!userStore.navigation.length) await userStore.getUserInfo();
        await this.restoreRoutes();
        const asyncRoutes = navigationToRoutes(
          userStore.navigation as Parameters<typeof navigationToRoutes>[0],
        ) as unknown as Array<RouteItem>;
        this.asyncRoutes = transformObjectToRoute(asyncRoutes);
        await this.initRoutes();
        return this.asyncRoutes;
      } catch (error) {
        throw new Error("Can't build routes", error as ErrorOptions);
      }
    },
    async restoreRoutes() {
      // Remove account-scoped routes and immediately reset the visible menu. Waiting
      // for the next navigation guard left the previous account's menu on screen.
      this.asyncRoutes.forEach((item: RouteRecordRaw) => {
        if (item.name) {
          router.removeRoute(item.name);
        }
      });
      this.asyncRoutes = [];
      this.removeRoutes = [];
      this.routers = copyRouteTree([...homepageRouterList, ...authorizedFixedRoutes(false)]);
    },
  },
});

export function getPermissionStore() {
  return usePermissionStore(store);
}
