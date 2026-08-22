import { LogoutIcon } from 'tdesign-icons-vue-next';
import { shallowRef } from 'vue';
import type { RouteRecordRaw } from 'vue-router';

import { LAYOUT } from '@/utils/route/constant';

export default [
  {
    path: '/user',
    name: 'user',
    component: LAYOUT,
    redirect: '/user/index',
    meta: { title: { zh_CN: '个人中心', en_US: 'User Center' }, icon: 'user-circle', hidden: true },
    children: [
      {
        path: 'index',
        name: 'UserIndex',
        component: () => import('@/pages/user/index.vue'),
        meta: { title: { zh_CN: '个人中心', en_US: 'User Center' } },
      },
      {
        path: 'my-work',
        name: 'MyWork',
        component: () => import('@/pages/my-work/index.vue'),
        meta: { title: { zh_CN: '我的工作', en_US: 'My Work' } },
      },
    ],
  },
  {
    path: '/my-work',
    name: 'MyWorkStandalone',
    component: LAYOUT,
    redirect: '/my-work/index',
    meta: { title: { zh_CN: '我的工作', en_US: 'My Work' }, icon: 'task', hidden: true },
    children: [
      {
        path: 'index',
        name: 'MyWorkStandaloneIndex',
        component: () => import('@/pages/my-work/index.vue'),
        meta: { title: { zh_CN: '我的工作', en_US: 'My Work' } },
      },
    ],
  },
  {
    path: '/messages',
    name: 'Messages',
    component: LAYOUT,
    meta: { title: { zh_CN: '消息中心', en_US: 'Messages' }, hidden: true },
    children: [
      {
        path: '',
        name: 'MessagesPage',
        component: () => import('@/pages/messages/index.vue'),
        meta: { title: { zh_CN: '消息中心', en_US: 'Messages' } },
      },
    ],
  },
  {
    path: '/r/:model/:id',
    name: 'OdooRecordDetailShell',
    component: LAYOUT,
    meta: { title: { zh_CN: '记录详情', en_US: 'Record Detail' }, hidden: true },
    children: [
      {
        path: '',
        name: 'OdooRecordDetail',
        component: () => import('@/pages/odoo/record/index.vue'),
        meta: { title: { zh_CN: '记录详情', en_US: 'Record Detail' } },
      },
    ],
  },
  {
    path: '/f/:model/:id',
    name: 'OdooRecordFormShell',
    component: LAYOUT,
    meta: { title: { zh_CN: '记录编辑', en_US: 'Record Form' }, hidden: true },
    children: [
      {
        path: '',
        name: 'OdooRecordForm',
        component: () => import('@/pages/odoo/record/index.vue'),
        meta: { title: { zh_CN: '记录编辑', en_US: 'Record Form' } },
      },
    ],
  },
  {
    path: '/s/:sceneKey',
    name: 'SceneRuntime',
    component: LAYOUT,
    meta: { title: { zh_CN: '业务场景', en_US: 'Business Scene' }, hidden: true },
    children: [
      {
        path: '',
        name: 'SceneRuntimePage',
        component: () => import('@/pages/SceneRuntimeView.vue'),
        meta: { title: { zh_CN: '业务场景', en_US: 'Business Scene' } },
      },
    ],
  },
  {
    path: '/operations',
    name: 'Operations',
    component: LAYOUT,
    meta: {
      title: { zh_CN: '运营管理', en_US: 'Operations' },
      icon: 'dashboard',
      orderNo: 90,
      adminOnly: true,
    },
    children: [
      {
        path: 'workbench',
        name: 'OperationsWorkbench',
        component: () => import('@/pages/operations/Workbench.vue'),
        meta: { title: { zh_CN: '系统工作台', en_US: 'System Workbench' } },
      },
      {
        path: 'usage',
        name: 'UsageAnalytics',
        component: () => import('@/pages/operations/Usage.vue'),
        meta: { title: { zh_CN: '使用分析', en_US: 'Usage Analytics' } },
      },
      {
        path: 'scene-health',
        name: 'SceneHealth',
        component: () => import('@/pages/operations/SceneHealth.vue'),
        meta: { title: { zh_CN: '场景健康', en_US: 'Scene Health' } },
      },
      {
        path: 'scene-packages',
        name: 'ScenePackages',
        component: () => import('@/pages/operations/ScenePackages.vue'),
        meta: { title: { zh_CN: '场景包管理', en_US: 'Scene Packages' } },
      },
      {
        path: 'release-operator',
        name: 'ReleaseOperator',
        component: () => import('@/pages/operations/ReleaseOperator.vue'),
        meta: { title: { zh_CN: '产品发布操作台', en_US: 'Release Operator' } },
      },
    ],
  },
  {
    path: '/governance',
    name: 'Governance',
    component: LAYOUT,
    meta: {
      title: { zh_CN: '系统治理', en_US: 'Governance' },
      icon: 'setting',
      orderNo: 91,
      adminOnly: true,
    },
    children: [
      {
        path: 'api-keys',
        name: 'ApiKeys',
        component: () => import('@/pages/governance/ApiKeys.vue'),
        meta: { title: { zh_CN: 'API Key 管理', en_US: 'API Keys' } },
      },
      {
        path: 'business-config',
        name: 'BusinessConfig',
        component: () => import('@/pages/governance/BusinessConfig.vue'),
        meta: { title: { zh_CN: '业务配置', en_US: 'Business Config' } },
      },
      {
        path: 'menu-config',
        name: 'MenuConfig',
        component: () => import('@/pages/governance/MenuConfig.vue'),
        meta: { title: { zh_CN: '菜单配置', en_US: 'Menu Config' } },
      },
      {
        path: 'form-field-config',
        name: 'FormFieldConfig',
        component: () => import('@/pages/governance/FormFieldConfig.vue'),
        meta: { title: { zh_CN: '表单字段配置', en_US: 'Form Field Config' } },
      },
    ],
  },
  {
    path: '/loginRedirect',
    name: 'loginRedirect',
    redirect: '/login',
    meta: { title: { zh_CN: '登录页', en_US: 'Login' }, icon: shallowRef(LogoutIcon), hidden: true },
    component: () => import('@/layouts/blank.vue'),
    children: [
      {
        path: 'index',
        redirect: '/login',
        meta: { title: { zh_CN: '登录页', en_US: 'Login' } },
      },
    ],
  },
] satisfies RouteRecordRaw[];
