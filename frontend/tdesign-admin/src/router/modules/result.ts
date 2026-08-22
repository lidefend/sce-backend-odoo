import type { RouteRecordRaw } from 'vue-router';

import { LAYOUT } from '@/utils/route/constant';

export default [
  {
    path: '/result',
    name: 'result',
    component: LAYOUT,
    redirect: '/result/404',
    meta: {
      hidden: true,
      title: {
        zh_CN: '结果页',
        en_US: 'Result',
      },
      icon: 'check-circle',
    },
    children: [
      {
        path: 'network-error',
        name: 'ResultNetworkError',
        component: () => import('@/pages/result/network-error/index.vue'),
        meta: {
          title: {
            zh_CN: '网络异常',
            en_US: 'Network Error',
          },
        },
      },
      {
        path: '403',
        name: 'Result403',
        component: () => import('@/pages/result/403/index.vue'),
        meta: { title: { zh_CN: '无权限', en_US: 'Forbidden' } },
      },
      {
        path: '404',
        name: 'Result404',
        component: () => import('@/pages/result/404/index.vue'),
        meta: { title: { zh_CN: '访问页面不存在页', en_US: 'Not Found' } },
      },
      {
        path: '500',
        name: 'Result500',
        component: () => import('@/pages/result/500/index.vue'),
        meta: { title: { zh_CN: '服务器出错页', en_US: 'Server Error' } },
      },
    ],
  },
] satisfies RouteRecordRaw[];
