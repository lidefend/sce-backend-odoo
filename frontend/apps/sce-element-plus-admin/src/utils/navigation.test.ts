import { describe, expect, it } from 'vitest'

import type { NavNode } from '@/types/contracts'
import { findMenuByKey, firstExecutableRoute, navigationToMenus, resolveNavigationTarget } from './navigation'

describe('backend navigation contract mapping', () => {
  it('keeps a synthetic targetless navigation group expand-only', () => {
    const node: NavNode = {
      key: 'group:construction.合同中心',
      label: '合同中心',
      menu_id: 883881237,
      meta: { node_kind: 'navigation_group', synthetic: true },
      children: [{
        key: 'contract.list',
        label: '合同台账',
        menu_id: 660,
        action_id: 685,
        model: 'sc.general.contract',
        route: '/a/685?menu_id=660',
      }],
    }

    const [group] = navigationToMenus([node])
    expect(group.executable).toBe(false)
    expect(group.route).toBe('')
    expect(group.menuId).toBeUndefined()
    expect(group.children[0].route).toBe('/action/685?menu_id=660&action_id=685&model=sc.general.contract')
    expect(firstExecutableRoute(findMenuByKey([group], 'group:construction.合同中心'))).toBe(
      '/action/685?menu_id=660&action_id=685&model=sc.general.contract',
    )
  })

  it('drops targetless leaves instead of inventing an action route', () => {
    expect(navigationToMenus([{ key: 'group:empty', label: '空目录', menu_id: 889000001 }])).toEqual([])
  })

  it('preserves an explicit backend group entry target', () => {
    const target = resolveNavigationTarget({
      key: 'group:construction.norm',
      label: '定额引擎',
      menu_id: 616,
      action_id: 829,
      model: 'sc.norm.item',
      route: '/a/829?menu_id=616',
      meta: { node_kind: 'navigation_group', explicit_group_entry_target: true },
      children: [{ key: 'norm.item', label: '定额子目', menu_id: 619, action_id: 830 }],
    })

    expect(target.executable).toBe(true)
    expect(target.route).toBe('/action/829?menu_id=616&action_id=829&model=sc.norm.item')
  })

  it('uses the backend scene entry target as the primary route authority', () => {
    const target = resolveNavigationTarget({
      key: 'project.dashboard',
      label: '项目驾驶舱',
      menu_id: 500,
      meta: {
        entry_target: {
          type: 'scene',
          scene_key: 'construction.project_dashboard',
          route: '/s/construction.project_dashboard',
          compatibility_refs: { menu_id: 500, action_id: 700, model: 'project.project' },
        },
      },
    })

    expect(target.executable).toBe(true)
    expect(target.route).toBe('/scene/construction.project_dashboard?menu_id=500')
  })

  it('routes the backend notification menu to the frontend message center', () => {
    const target = resolveNavigationTarget({
      key: 'message.notifications',
      label: '消息通知',
      menu_id: 557,
      action_id: 806,
      model: 'mail.notification',
      route: '/a/806?menu_id=557',
    })

    expect(target.route).toBe('/notifications?action_id=806&menu_id=557')
  })
})
