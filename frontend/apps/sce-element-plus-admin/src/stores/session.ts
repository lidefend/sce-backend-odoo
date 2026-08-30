import { defineStore } from 'pinia'

import { clearToken, hasToken, login as loginApi, logout as logoutApi, searchRecordContext, systemInit } from '@/api/odoo'
import { useLayoutStore } from '@/stores/layout'
import type { Dictionary, NavNode, OdooUser, SystemInit } from '@/types/contracts'

export const useSessionStore = defineStore('session', {
  state: () => ({
    token: hasToken(),
    user: null as OdooUser | null,
    navigation: [] as NavNode[],
    routeAuthority: {} as Dictionary,
    workspaceHome: {} as Dictionary,
    roleSurface: {} as Dictionary,
    recordContext: {} as Dictionary,
    businessContext: (() => {
      try {
        return JSON.parse(localStorage.getItem('sce-element-business-context') || '{}') as Dictionary
      } catch {
        return {}
      }
    })(),
    initialized: false,
    initError: '',
  }),
  getters: {
    isAdmin: (state) => Boolean(state.user?.is_platform_admin || state.user?.is_system_admin || state.roleSurface.admin),
    displayName: (state) => state.user?.name || state.user?.login || '访客',
  },
  actions: {
    async login(loginName: string, password: string) {
      const result = await loginApi(loginName, password)
      this.token = true
      this.user = result.user || null
      await this.initialize()
    },
    async initialize() {
      if (!this.token) return
      this.initError = ''
      try {
        const result = await systemInit(this.businessContext) as SystemInit
        this.applyInit(result)
      } catch (error) {
        this.initError = error instanceof Error ? error.message : '会话初始化失败'
        // A token that cannot initialize a session is no longer usable. Clear it
        // so the router can render the login page instead of redirecting forever.
        this.token = false
        this.initialized = false
        clearToken()
        throw error
      }
    },
    applyInit(result: SystemInit) {
      this.user = result.user || this.user
      this.navigation = result.navigation?.nav || result.navigation_v1?.nav || []
      this.routeAuthority = result.navigation?.route_authority || result.navigation_v1?.route_authority_v1 || {}
      this.workspaceHome = result.workspace_home || {}
      this.roleSurface = result.role_surface || {}
      this.recordContext = result.record_context || {}
      this.businessContext = contextFromRecordContract(this.recordContext)
      this.initialized = true
      localStorage.setItem('sce-element-business-context', JSON.stringify(this.businessContext))
    },
    setBusinessContext(context: Dictionary) {
      this.businessContext = { ...this.businessContext, ...context }
      localStorage.setItem('sce-element-business-context', JSON.stringify(this.businessContext))
    },
    async switchBusinessContext(change: Dictionary) {
      const next = { ...this.businessContext, ...change }
      this.businessContext = Object.fromEntries(
        Object.entries(next).filter(([, value]) => value !== undefined && value !== null && value !== ''),
      )
      localStorage.setItem('sce-element-business-context', JSON.stringify(this.businessContext))
      await this.initialize()
    },
    async refreshRecordContext(search = '') {
      this.recordContext = await searchRecordContext({ ...this.businessContext, search, limit: 100 })
    },
    async logout() {
      try {
        await logoutApi()
      } finally {
        useLayoutStore().closeAllTabs()
        localStorage.removeItem('sce-element-business-context')
        this.$reset()
        clearToken()
      }
    },
  },
})

function contextFromRecordContract(contract: Dictionary): Dictionary {
  const supplied = contract.request_context ?? contract.requestContext
  const requestContext = supplied && typeof supplied === 'object' && !Array.isArray(supplied)
    ? supplied as Dictionary
    : {}
  const selected = contract.selected && typeof contract.selected === 'object' ? contract.selected : {}
  return Object.fromEntries(
    [
      ...Object.entries(requestContext),
      ['company_id', contract.company_id ?? requestContext.company_id],
      ['current_project_id', selected.id ?? requestContext.current_project_id],
      ['operation_strategy', contract.operation_strategy ?? requestContext.operation_strategy],
    ].filter(([, value]) => value !== undefined && value !== null && value !== ''),
  )
}
