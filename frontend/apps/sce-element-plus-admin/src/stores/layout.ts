import { defineStore } from 'pinia'

export type NavMode = 'side' | 'mix' | 'top'
export type SideTheme = 'light' | 'dark'
export type TabStyle = 'card' | 'chrome'

export interface LayoutSettings {
  navMode: NavMode
  sideTheme: SideTheme
  primaryColor: string
  showTabs: boolean
  persistTabs: boolean
  showTabIcons: boolean
  tabStyle: TabStyle
  fixedHeader: boolean
  showLogo: boolean
  dynamicTitle: boolean
  showFooter: boolean
}

export interface VisitedTab {
  fullPath: string
  path: string
  title: string
  icon?: string
  closable: boolean
}

const STORAGE_KEY = 'sce-element-layout-settings'
const TABS_KEY = 'sce-element-visited-tabs'
const MAX_VISITED_TABS = 6

function isTransientTabPath(fullPath: string): boolean {
  try {
    const url = new URL(fullPath, 'http://localhost')
    const path = url.pathname.toLowerCase()
    return path.startsWith('/action/')
  } catch {
    return false
  }
}

export const defaultLayoutSettings: LayoutSettings = {
  navMode: 'side',
  sideTheme: 'light',
  primaryColor: '#409eff',
  showTabs: true,
  persistTabs: true,
  showTabIcons: true,
  tabStyle: 'chrome',
  fixedHeader: true,
  showLogo: true,
  dynamicTitle: true,
  showFooter: false,
}

function readSettings(): LayoutSettings {
  try {
    return { ...defaultLayoutSettings, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
  } catch {
    return { ...defaultLayoutSettings }
  }
}

function readTabs(): VisitedTab[] {
  try {
    const rows = JSON.parse(localStorage.getItem(TABS_KEY) || '[]')
    if (!Array.isArray(rows)) return []
    const filtered = rows.filter((row): row is VisitedTab => row && typeof row === 'object' && !isTransientTabPath(String(row.fullPath || '')))
    const pinned = filtered.filter((tab) => !tab.closable)
    const closable = filtered.filter((tab) => tab.closable).slice(-MAX_VISITED_TABS)
    return [...pinned, ...closable]
  } catch {
    return []
  }
}

export const useLayoutStore = defineStore('layout', {
  state: () => ({
    settings: readSettings(),
    tabs: readTabs() as VisitedTab[],
  }),
  actions: {
    update<K extends keyof LayoutSettings>(key: K, value: LayoutSettings[K]) {
      this.settings[key] = value
      if (key === 'persistTabs' && value === false) localStorage.removeItem(TABS_KEY)
    },
    addTab(tab: VisitedTab) {
      if (isTransientTabPath(tab.fullPath)) return
      const index = this.tabs.findIndex((item) => item.fullPath === tab.fullPath)
      if (index >= 0) this.tabs[index] = tab
      else this.tabs.push(tab)
      const pinned = this.tabs.filter((item) => !item.closable)
      const closable = this.tabs.filter((item) => item.closable).slice(-MAX_VISITED_TABS)
      this.tabs = [...pinned, ...closable]
      this.persistTabState()
    },
    closeTab(fullPath: string) {
      const index = this.tabs.findIndex((item) => item.fullPath === fullPath)
      if (index < 0 || !this.tabs[index].closable) return ''
      this.tabs.splice(index, 1)
      this.persistTabState()
      return this.tabs[Math.min(index, this.tabs.length - 1)]?.fullPath || '/dashboard'
    },
    closeOtherTabs(fullPath: string) {
      this.tabs = this.tabs.filter((item) => !item.closable || item.fullPath === fullPath)
      this.persistTabState()
    },
    closeLeftTabs(fullPath: string) {
      const index = this.tabs.findIndex((item) => item.fullPath === fullPath)
      if (index < 0) return
      this.tabs = this.tabs.filter((item, itemIndex) => !item.closable || itemIndex >= index)
      this.persistTabState()
    },
    closeRightTabs(fullPath: string) {
      const index = this.tabs.findIndex((item) => item.fullPath === fullPath)
      if (index < 0) return
      this.tabs = this.tabs.filter((item, itemIndex) => !item.closable || itemIndex <= index)
      this.persistTabState()
    },
    closeAllTabs() {
      this.tabs = this.tabs.filter((item) => !item.closable)
      this.persistTabState()
    },
    persistTabState() {
      if (this.settings.persistTabs) localStorage.setItem(TABS_KEY, JSON.stringify(this.tabs))
    },
    saveSettings() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.settings))
      this.persistTabState()
    },
    resetSettings() {
      this.settings = { ...defaultLayoutSettings }
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(TABS_KEY)
      this.tabs = this.tabs.filter((item) => !item.closable)
    },
  },
})
