import { describe, expect, it } from 'vitest'

import { normalizeRelationIds, resolveFieldWidget, statusTagType } from './widget'

describe('special field widget helpers', () => {
  it('resolves widgets from nested contract metadata', () => {
    expect(resolveFieldWidget({ widget: 'STATUSBAR' })).toBe('statusbar')
    expect(resolveFieldWidget({ componentConfig: { widget: 'many2many_binary' } })).toBe('many2many_binary')
    expect(resolveFieldWidget({ field_info: { widget: 'json' } })).toBe('json')
    expect(resolveFieldWidget({}, { code: 'state', type: 'selection' })).toBe('statusbar')
    expect(resolveFieldWidget({}, { code: 'attachment_ids', type: 'many2many', relation: 'ir.attachment' })).toBe('many2many_binary')
    expect(resolveFieldWidget({}, { code: 'avatar_128', type: 'binary' })).toBe('image')
  })

  it('maps status semantics to Element tag types', () => {
    expect(statusTagType('approved')).toBe('success')
    expect(statusTagType('draft')).toBe('warning')
    expect(statusTagType('rejected')).toBe('danger')
    expect(statusTagType('running')).toBe('primary')
    expect(statusTagType('已提交')).toBe('info')
    expect(statusTagType('未提交')).toBe('warning')
  })

  it('normalizes relation ids from common Odoo value shapes', () => {
    expect(normalizeRelationIds([7, 9])).toEqual([7, 9])
    expect(normalizeRelationIds([[7, '附件'], { id: 9 }, false])).toEqual([7, 9])
  })
})
