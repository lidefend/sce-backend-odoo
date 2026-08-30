import { describe, expect, it } from 'vitest'
import { resolveRelationDomain, resolveRuntimeDomain, runtimeFieldState } from './modifiers'

describe('contract modifier runtime', () => {
  it('evaluates Odoo domains and onchange patches', () => {
    const values = { state: 'draft', amount: 120, partner_id: [7, '客户'] }
    expect(runtimeFieldState({ invisible: [['state', '!=', 'draft']], readonly: [['amount', '>', 100]] }, {}, values)).toEqual({ invisible: false, readonly: true, required: false })
    expect(runtimeFieldState({}, { required: { kind: 'field_compare', field: 'state', operator: '=', value: 'draft' } }, values).required).toBe(true)
  })

  it('resolves field and context tokens inside relation domains', () => {
    expect(resolveRuntimeDomain([['project_id', '=', '$project_id'], ['company_id', '=', 'context.company_id']], { project_id: 9 }, { company_id: 1 })).toEqual([['project_id', '=', 9], ['company_id', '=', 1]])
  })

  it('normalizes string domains and scopes published BOQ versions to the selected project', () => {
    expect(resolveRelationDomain(
      "[('project_id', '=', project_id), ('state', '!=', 'archived')]",
      { project_id: 10 },
      {},
      'boq_version_id',
    )).toEqual([
      ['project_id', '=', 10],
      ['state', '=', 'published'],
    ])
  })

  it('blocks project-scoped relation options until a project is selected', () => {
    expect(resolveRelationDomain([['project_id', '=', '$project_id']], {}, {}, 'boq_version_id')).toEqual([
      ['project_id', '=', 0],
      ['state', '=', 'published'],
    ])
  })
})
