import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { hasToken } from '@/api/odoo'
import { useSessionStore } from '@/stores/session'
import { findMenuByKey, firstExecutableRoute, useNavigation } from '@/utils/navigation'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'Login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layouts/AppShell.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '工作台' } },
      { path: 'my-work', name: 'MyWork', component: () => import('@/views/MyWorkView.vue'), meta: { title: '我的工作' } },
      { path: 'notifications', name: 'Notifications', component: () => import('@/views/NotificationsView.vue'), meta: { title: '消息中心' } },
      { path: 'profile', name: 'Profile', component: () => import('@/views/ProfileView.vue'), meta: { title: '个人资料' } },
      { path: 'action/:actionId?', name: 'Action', component: () => import('@/views/ActionView.vue'), meta: { title: '业务列表' } },
      { path: 'record/:model/:id', name: 'Record', component: () => import('@/views/RecordView.vue'), meta: { title: '业务详情' } },
      { path: 'scene/:sceneKey', name: 'Scene', component: () => import('@/views/SceneView.vue'), meta: { title: '业务场景' } },
      { path: 'diagnostics', name: 'Diagnostics', component: () => import('@/views/DiagnosticsView.vue'), meta: { title: '运行诊断' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  if (to.meta.public) {
    // Do not redirect an uninitialized/stale session away from the login page.
    // initialize() clears the token when the backend rejects system.init.
    if (to.name === 'Login' && hasToken()) {
      const session = useSessionStore()
      if (session.initialized) return '/dashboard'
    }
    return true
  }
  if (!hasToken()) return { name: 'Login', query: { redirect: to.fullPath } }
  const session = useSessionStore()
  if (!session.initialized) {
    try {
      await session.initialize()
    } catch {
      return { name: 'Login', query: { redirect: to.fullPath } }
    }
  }
  if (to.name === 'Action' && String(to.params.actionId || '').startsWith('group:')) {
    const group = findMenuByKey(useNavigation(session.navigation), String(to.params.actionId))
    return firstExecutableRoute(group) || '/dashboard'
  }
  return true
})

export default router
