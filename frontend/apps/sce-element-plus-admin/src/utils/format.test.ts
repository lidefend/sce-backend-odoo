import { describe, expect, it } from 'vitest'

import { displayFieldValue, displayValue, fieldLabel } from './format'

describe('display adapters', () => {
  it('maps common status values to Chinese labels', () => {
    expect(displayValue('draft')).toBe('草稿')
    expect(displayValue('yes')).toBe('是')
    expect(displayValue('no')).toBe('否')
    expect(displayValue(false)).toBe('否')
  })

  it('prefers selection labels and known field labels', () => {
    expect(displayFieldValue('draft', 'state', [{ value: 'draft', label: '草稿' }])).toBe('草稿')
    expect(displayFieldValue(false, 'date_start', [], 'date')).toBe('-')
    expect(displayFieldValue(false, 'active', [], 'boolean')).toBe('否')
    expect(fieldLabel('validation_status', 'Validation Status')).toBe('校验状态')
    expect(fieldLabel('can_review', 'Can Review')).toBe('允许审核')
  })
})
