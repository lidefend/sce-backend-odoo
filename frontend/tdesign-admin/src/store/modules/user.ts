import { defineStore } from 'pinia';

import type { OdooUser, SystemInit } from '@/api/odoo';
import { clearToken, login as loginOdoo, logout as logoutOdoo, systemInit } from '@/api/odoo';
import { applyProductBrandFromSystemInit } from '@/config/product';
import { usePermissionStore, useTabsRouterStore } from '@/store';
import type { UserInfo } from '@/types/interface';
import type { RouteAuthorityContract } from '@/utils/route/authority';
import { normalizeRouteAuthorityContract } from '@/utils/route/authority';

const InitUserInfo: UserInfo = { name: '', roles: [] };

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('sc-odoo-token') || '',
    userInfo: { ...InitUserInfo },
    navigation: [] as Array<Record<string, unknown>>,
    roleLabel: '',
    workspaceHome: {} as Record<string, unknown>,
    recordContext: {} as Record<string, unknown>,
    account: null as OdooUser | null,
    capabilities: [] as string[],
    roleSurface: {} as NonNullable<SystemInit['role_surface']>,
    businessContext: {} as Record<string, unknown>,
    routeAuthority: null as RouteAuthorityContract | null,
  }),
  getters: {
    roles: (state) => state.userInfo?.roles,
    isAdmin: (state) => {
      const roles = (state.userInfo?.roles || []).map((role) => String(role).toLowerCase());
      const roleSurface = state.roleSurface || {};
      const capabilityKeys = new Set(state.capabilities.map((value) => String(value).toLowerCase()));
      const backendAdmin =
        state.account?.is_platform_admin === true ||
        state.account?.is_system_admin === true ||
        roleSurface.is_platform_admin === true ||
        roleSurface.is_system_admin === true ||
        roleSurface.admin === true ||
        (state.routeAuthority?.admin_actions?.length || 0) > 0 ||
        [...capabilityKeys].some((key) =>
          [
            'platform_admin',
            'platform-admin',
            'system_admin',
            'system-admin',
            'operations-admin',
            'release-admin',
            'business-config-admin',
            'menu-config-admin',
            'form-config-admin',
          ].includes(key),
        );
      return (
        backendAdmin ||
        roles.some((role) =>
          [
            'base.group_system',
            'smart_core.group_smart_core_admin',
            'smart_construction_core.group_sc_super_admin',
          ].includes(role),
        )
      );
    },
  },
  actions: {
    async login(credentials: Record<string, unknown>) {
      const permissionStore = usePermissionStore();
      const tabsRouterStore = useTabsRouterStore();
      // A login form can be reached with a stale token (for example after a
      // browser back or an interrupted logout). Clear the previous account
      // before accepting the new identity.
      if (this.token || this.navigation.length || permissionStore.asyncRoutes.length) {
        await permissionStore.restoreRoutes();
        tabsRouterStore.resetForSession();
        this.clearSession();
      }
      const result = await loginOdoo(String(credentials.account || ''), String(credentials.password || ''));
      this.token = result.token;
      this.account = result.user || null;
      this.userInfo = normalizeUser(result.user, String(credentials.account || ''));
    },
    async getUserInfo(context: Record<string, unknown> = {}) {
      if (!this.token) throw new Error('登录会话不存在');
      const activeContext = Object.keys(context).length ? context : this.businessContext;
      const result = await systemInit(activeContext);
      this.applySystemInit(result);
      return result;
    },
    applySystemInit(result: SystemInit) {
      this.userInfo = normalizeUser(result.user, this.userInfo.name);
      this.account = result.user || this.account;
      this.roleSurface = result.role_surface || {};
      this.capabilities = normalizeCapabilityKeys(result.capabilities, result.role_surface?.capabilities);
      this.navigation = (result.navigation_v1?.nav || []) as Array<Record<string, unknown>>;
      this.roleLabel = String(result.role_surface?.role_label || result.role_surface?.role_code || '内部用户');
      this.workspaceHome = result.workspace_home || {};
      this.recordContext = result.record_context || {};
      this.routeAuthority = normalizeRouteAuthorityContract(result.navigation_v1?.route_authority_v1);
      applyProductBrandFromSystemInit(result as unknown as Record<string, unknown>);
      const context = contextFromContract(result.record_context);
      this.businessContext = context;
      localStorage.setItem('sc-odoo-business-context', JSON.stringify(context));
    },
    async switchBusinessContext(context: Record<string, unknown>) {
      const permissionStore = usePermissionStore();
      this.businessContext = Object.fromEntries(
        Object.entries(context).filter(([, value]) => value !== undefined && value !== null && value !== ''),
      );
      localStorage.setItem('sc-odoo-business-context', JSON.stringify(this.businessContext));
      await this.getUserInfo(this.businessContext);
      await permissionStore.buildAsyncRoutes();
    },
    async logout() {
      const permissionStore = usePermissionStore();
      const tabsRouterStore = useTabsRouterStore();
      // Do not block navigation on a remote logout request. The browser must
      // leave the authenticated shell even when the backend is slow or returns
      // an error; the token is cleared locally in the same turn.
      if (this.token) void logoutOdoo().catch(() => undefined);
      try {
        await permissionStore.restoreRoutes();
      } finally {
        tabsRouterStore.resetForSession();
        this.clearSession();
      }
    },
    clearSession() {
      clearToken();
      this.token = '';
      this.userInfo = { ...InitUserInfo };
      this.navigation = [];
      this.account = null;
      this.capabilities = [];
      this.roleSurface = {};
      this.roleLabel = '';
      this.businessContext = {};
      this.workspaceHome = {};
      this.recordContext = {};
      this.routeAuthority = null;
      localStorage.removeItem('sc-odoo-business-context');
    },
  },
  persist: {
    afterHydrate: () => {
      usePermissionStore().initRoutes();
    },
    key: 'user',
    pick: ['token', 'businessContext'],
  },
});

function normalizeUser(user: OdooUser | undefined, fallback: string): UserInfo {
  return { name: user?.name || user?.login || fallback, roles: user?.groups_xmlids || [] };
}

function normalizeCapabilityKeys(...sources: unknown[]): string[] {
  const keys = new Set<string>();
  const visit = (value: unknown) => {
    if (typeof value === 'string' && value.trim()) {
      keys.add(value.trim());
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (value && typeof value === 'object') {
      const row = value as Record<string, unknown>;
      const key = String(row.key || row.code || row.capability_key || '').trim();
      if (key && row.allowed !== false && row.enabled !== false && row.visible !== false) keys.add(key);
    }
  };
  sources.forEach(visit);
  return [...keys];
}

function contextFromContract(raw: Record<string, unknown> | undefined) {
  const contract = raw || {};
  return Object.fromEntries(
    [
      ['company_id', contract.company_id],
      ['current_project_id', (contract.selected as Record<string, unknown> | null | undefined)?.id],
      ['operation_strategy', contract.operation_strategy],
    ].filter(([, value]) => value !== undefined && value !== null && value !== ''),
  );
}
