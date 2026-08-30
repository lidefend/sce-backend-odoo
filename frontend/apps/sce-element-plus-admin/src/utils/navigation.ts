import type { NavNode } from '@/types/contracts'

export interface MenuItem {
  key: string
  label: string
  icon?: string
  route: string
  executable: boolean
  model?: string
  actionId?: number
  menuId?: number
  sceneKey?: string
  children: MenuItem[]
}

const fallbackMenus: MenuItem[] = [
  { key: 'dashboard', label: '工作台', route: '/dashboard', executable: true, icon: 'Odometer', children: [] },
  { key: 'my-work', label: '我的工作', route: '/my-work', executable: true, icon: 'List', children: [] },
  {
    key: 'project', label: '项目管理', route: '', executable: false, icon: 'OfficeBuilding', children: [
      { key: 'project-list', label: '项目列表', route: '/action/project?model=project.project', executable: true, icon: 'Tickets', model: 'project.project', children: [] },
      { key: 'task-list', label: '任务管理', route: '/action/task?model=project.task', executable: true, icon: 'Checked', model: 'project.task', children: [] },
    ],
  },
  {
    key: 'cost', label: '成本管理', route: '', executable: false, icon: 'Coin', children: [
      { key: 'budget', label: '预算台账', route: '/action/budget?model=sc.budget', executable: true, icon: 'DataAnalysis', model: 'sc.budget', children: [] },
      { key: 'purchase', label: '采购计划', route: '/action/purchase?model=purchase.order', executable: true, icon: 'ShoppingCart', model: 'purchase.order', children: [] },
    ],
  },
  { key: 'diagnostics', label: '运行诊断', route: '/diagnostics', executable: true, icon: 'Monitor', children: [] },
]

function positiveInteger(value: unknown): number | undefined {
  const parsed = Number(value || 0)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

function appendQuery(route: string, values: Record<string, string | number | undefined>) {
  const [path, search = ''] = route.split('?', 2)
  const query = new URLSearchParams(search)
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value))
  })
  return query.size ? `${path}?${query}` : path
}

function frontendRoute(route: string, target: Record<string, unknown>) {
  const normalized = route.trim()
  const sceneKey = String(target.sceneKey || '')
  const actionId = positiveInteger(target.actionId)
  const menuId = positiveInteger(target.menuId)
  const model = String(target.model || '')

  if (model === 'mail.notification') {
    return appendQuery('/notifications', { action_id: actionId, menu_id: menuId })
  }

  if (sceneKey) return appendQuery(`/scene/${encodeURIComponent(sceneKey)}`, { menu_id: menuId })
  const actionMatch = normalized.match(/^\/a\/(\d+)(?:\?(.*))?$/)
  if (actionMatch) {
    return appendQuery(`/action/${actionMatch[1]}${actionMatch[2] ? `?${actionMatch[2]}` : ''}`, {
      action_id: Number(actionMatch[1]),
      menu_id: menuId,
      model,
    })
  }
  if (actionId) return appendQuery(`/action/${actionId}`, { action_id: actionId, menu_id: menuId, model })
  const sceneMatch = normalized.match(/^\/s\/(.+)$/)
  if (sceneMatch) return appendQuery(`/scene/${encodeURIComponent(sceneMatch[1])}`, { menu_id: menuId })
  const recordMatch = normalized.match(/^\/(r|f)\/([^/]+)\/([^/?]+)/)
  if (recordMatch) {
    const create = recordMatch[3] === 'new'
    return appendQuery(`/record/${encodeURIComponent(recordMatch[2])}/${recordMatch[3]}`, {
      action_id: actionId,
      menu_id: menuId,
      mode: create ? 'create' : recordMatch[1] === 'f' ? 'edit' : 'view',
    })
  }
  if (normalized === '/workbench' || normalized === '/operations/workbench') return '/diagnostics'
  if (normalized === '/my-work/index') return '/my-work'
  if (normalized === '/dashboard/base') return '/dashboard'
  return normalized
}

export function resolveNavigationTarget(node: NavNode) {
  const meta = node.meta || {}
  const entryTarget = (node.entry_target && typeof node.entry_target === 'object'
    ? node.entry_target
    : meta.entry_target && typeof meta.entry_target === 'object'
      ? meta.entry_target
      : {}) as Record<string, unknown>
  const refs = (entryTarget.compatibility_refs && typeof entryTarget.compatibility_refs === 'object'
    ? entryTarget.compatibility_refs
    : {}) as Record<string, unknown>
  const type = String(entryTarget.type || '').toLowerCase()
  const actionId = positiveInteger(node.action_id || meta.action_id || refs.action_id)
  const menuId = positiveInteger(node.menu_id || meta.menu_id || refs.menu_id)
  const model = String(node.model || meta.model || refs.model || '')
  const sceneKey = String(node.scene_key || entryTarget.scene_key || meta.scene_key || '')
  const backendRoute = String(entryTarget.route || node.route || meta.route || '')
  const explicitGroupTarget = meta.explicit_group_entry_target === true
  const executable = Boolean(
    sceneKey ||
      actionId ||
      (type === 'scene' && (entryTarget.route || entryTarget.scene_key)) ||
      (type === 'compatibility' && (backendRoute || actionId)) ||
      (explicitGroupTarget && backendRoute),
  )

  return {
    executable,
    actionId,
    menuId: executable ? menuId : undefined,
    model,
    sceneKey,
    route: executable ? frontendRoute(backendRoute, { actionId, menuId, model, sceneKey }) : '',
  }
}

export function navigationToMenus(nodes: NavNode[], parent = ''): MenuItem[] {
  return (nodes || []).flatMap((node, index) => {
    const key = String(node.key || node.menu_id || node.id || `${parent}-${index}`)
    const label = String(node.label || node.name || node.title || '未命名菜单')
    const target = resolveNavigationTarget(node)
    const children = navigationToMenus(node.children || [], key)
    if (!target.executable && !children.length) return []
    return [{
      key,
      label,
      route: target.route,
      executable: target.executable,
      icon: String((node.meta || {}).icon || (children.length ? 'FolderOpened' : 'Document')),
      model: target.model,
      actionId: target.actionId,
      menuId: target.menuId,
      sceneKey: target.sceneKey,
      children,
    }]
  })
}

export function groupMenuIndexes(items: MenuItem[]): string[] {
  return items.flatMap((item) => item.children.length ? [`group:${item.key}`, ...groupMenuIndexes(item.children)] : [])
}

export function activeGroupIndexes(items: MenuItem[], fullPath: string): string[] {
  for (const item of items) {
    if (item.executable && item.route === fullPath) return []
    const childPath = activeGroupIndexes(item.children, fullPath)
    if (childPath.length || item.children.some((child) => child.executable && child.route === fullPath)) {
      return [`group:${item.key}`, ...childPath]
    }
  }
  return []
}

export function findMenuByKey(items: MenuItem[], key: string): MenuItem | undefined {
  for (const item of items) {
    if (item.key === key) return item
    const match = findMenuByKey(item.children, key)
    if (match) return match
  }
  return undefined
}

export function firstExecutableRoute(item: MenuItem | undefined): string {
  if (!item) return ''
  if (item.executable && item.route) return item.route
  for (const child of item.children) {
    const route = firstExecutableRoute(child)
    if (route) return route
  }
  return ''
}

export function useNavigation(nodes: NavNode[]) {
  const menus = navigationToMenus(nodes)
  return menus.length ? menus : fallbackMenus
}
