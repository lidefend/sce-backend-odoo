import { describe, expect, it } from 'vitest'

import {
  buildWritableFormValues,
  decodePageContract,
  formSourceContext,
  normalizeFieldWriteValue,
  resolveActions,
  resolveFieldSpecs,
  resolveListFieldSpecs,
  resolveSemanticFormModel,
} from './contract'

const backendContract = decodePageContract({
  pageInfo: { model: 'project.project', viewType: 'form', contractVersion: '2.2.0' },
  layoutContract: {
    containerTree: [{
      type: 'sheet',
      children: [{
        type: 'group',
        children: [
          { type: 'field', name: 'name', label: '项目名称', fieldInfo: { name: 'name', type: 'char' } },
          {
            type: 'field',
            name: 'manager_id',
            label: '项目负责人',
            fieldInfo: { name: 'manager_id', type: 'many2one', relation: 'res.users' },
          },
        ],
      }],
    }],
  },
  dataContract: {
    dataSource: { primary: { params: { fields: ['id', 'name', 'manager_id', 'operation_strategy'] } } },
    dataMeta: {
      visibleFields: { fields: ['name', 'manager_id', 'operation_strategy'] },
      businessOperationProfile: { field_labels: { operation_strategy: '经营方式' } },
    },
  },
  searchContract: {
    custom: { filters: { fields: [{ field: 'operation_strategy', type: 'selection', label: '经营方式' }] } },
  },
})

describe('backend page contract field mapping', () => {
  it('uses fieldInfo type instead of the structural field node type', () => {
    const fields = resolveFieldSpecs(backendContract)
    expect(fields.map((field) => [field.code, field.type])).toEqual([
      ['name', 'char'],
      ['manager_id', 'many2one'],
    ])
  })

  it('uses dataSource params as list column order and fills missing metadata', () => {
    const fields = resolveListFieldSpecs(backendContract)
    expect(fields.map((field) => [field.code, field.label, field.type])).toEqual([
      ['name', '项目名称', 'char'],
      ['manager_id', '项目负责人', 'many2one'],
      ['operation_strategy', '经营方式', 'selection'],
    ])
  })

  it('honors list profile default visibility and sortable capability', () => {
    const contract = decodePageContract({
      layoutContract: {
        listProfile: { hidden_columns: ['email'] },
        containerTree: [{
          type: 'section',
          widgetList: [
            { type: 'field', name: 'name', label: '名称', capabilities: ['sortable'] },
            { type: 'field', name: 'email', label: '电子邮件', capabilities: ['sortable'] },
          ],
        }],
      },
      dataContract: { dataSource: { primary: { params: { fields: ['id', 'name', 'email'] } } } },
    })
    const fields = resolveListFieldSpecs(contract)
    expect(fields.find((field) => field.code === 'name')).toMatchObject({ defaultVisible: true, sortable: true })
    expect(fields.find((field) => field.code === 'email')).toMatchObject({ defaultVisible: false, sortable: true })
  })

  it('reads list widget metadata from fieldCode nodes', () => {
    const contract = decodePageContract({
      layoutContract: {
        containerTree: [{
          type: 'section',
          widgetList: [{
            fieldCode: 'name',
            label: '名称',
            capabilities: ['sortable'],
            componentConfig: { optional: 'show', fieldType: 'char' },
            fieldDescriptor: { name: 'name', type: 'char' },
          }],
        }],
      },
      dataContract: { dataSource: { primary: { params: { fields: ['id', 'name'] } } } },
    })
    expect(resolveListFieldSpecs(contract)[0]).toMatchObject({ code: 'name', type: 'char', sortable: true })
  })

  it('normalizes Odoo relation display values to write ids', () => {
    const relationField = {
      code: 'company_id', label: '公司', type: 'many2one', required: true, readonly: false,
      relation: 'res.company', selection: [], config: {},
    }
    expect(normalizeFieldWriteValue([1, 'My Company'], relationField)).toBe(1)
    expect(normalizeFieldWriteValue('8,收入合同', relationField)).toBe(8)
  })

  it('preserves all ids from Odoo many2many commands when writing', () => {
    const relationField = {
      code: 'category_id', label: '标签', type: 'many2many', required: false, readonly: false,
      relation: 'res.partner.category', selection: [], config: {},
    }
    expect(normalizeFieldWriteValue([[6, 0, [3, 6, 9]]], relationField)).toEqual([[6, 0, [3, 6, 9]]])
  })

  it('excludes readonly fields and preserves the backend source context', () => {
    const fields = [
      { code: 'company_id', label: '公司', type: 'many2one', required: true, readonly: true, relation: 'res.company', selection: [], config: {} },
      { code: 'partner_id', label: '发包人', type: 'many2one', required: true, readonly: false, relation: 'res.partner', selection: [], config: {} },
      { code: 'amount_total', label: '金额', type: 'monetary', required: false, readonly: false, relation: '', selection: [], config: {} },
    ]
    expect(buildWritableFormValues(fields, {
      company_id: [1, 'My Company'], partner_id: [22, '客户'], amount_total: '100.50',
    })).toEqual({ partner_id: 22, amount_total: 100.5 })

    const contract = decodePageContract({
      dataContract: { dataMeta: { sourceContext: { context: { allowed_company_ids: [1], default_type: 'out' } } } },
    })
    expect(formSourceContext(contract)).toEqual({ allowed_company_ids: [1], default_type: 'out' })
  })

  it('applies backend buttonStatus to form actions', () => {
    const contract = decodePageContract({
      actionContract: { actionRuleList: [{ actionKey: 'approve', label: '审批通过', targetScope: 'form', sourceChannel: 'native_form_button', button: { name: 'action_approve', type: 'object' } }] },
      statusContract: { buttonStatus: [{ key: 'approve', visible: true, disabled: true, reasonCode: 'STATE_BLOCKED' }] },
    })
    expect(resolveActions(contract, 'form')).toMatchObject([{ key: 'approve', enabled: false, reasonCode: 'STATE_BLOCKED' }])
  })

  it('keeps grouped business actions and their backend navigation targets', () => {
    const contract = decodePageContract({
      actionContract: {
        actionGroups: [{
          key: 'project_tools',
          label: '项目工具',
          actions: [{
            key: 'open_tender',
            label: '投标管理',
            intent: 'ui.contract',
            target: { action_id: 862, model: 'tender.opportunity' },
            sourceChannel: 'buttons',
            targetScope: 'form',
          }],
        }],
      },
    })
    expect(resolveActions(contract, 'form')).toMatchObject([{
      key: 'open_tender',
      label: '投标管理',
      intent: 'ui.contract',
      target: { action_id: 862, model: 'tender.opportunity' },
    }])
  })

  it('preserves execute button authority metadata from the backend contract', () => {
    const contract = decodePageContract({
      actionContract: {
        actionRuleList: [{
          actionId: 'action.validate_tier',
          actionKey: 'validate_tier',
          backendIdentity: 'button:object:validate_tier',
          sourceWidgetId: 'page.header',
          label: '审批通过',
          intent: 'execute',
          button: { name: 'validate_tier', type: 'object' },
          targetScope: 'form',
          sourceChannel: 'native_form_header',
        }],
      },
    })
    expect(resolveActions(contract, 'form')).toMatchObject([{
      actionId: 'action.validate_tier',
      backendIdentity: 'button:object:validate_tier',
      sourceWidgetId: 'page.header',
    }])
  })

  it('applies native form and intake action presentation gates', () => {
    const button = { name: 'run_action', type: 'object' };
    const contract = decodePageContract({
      actionContract: {
        actionRuleList: [
          { actionKey: 'header', label: '页头操作', sourceWidgetId: 'page.header', targetScope: 'form', button },
          { actionKey: 'root_header', label: '根页头操作', sourceWidgetId: 'page.root', targetScope: 'header', button },
          { actionKey: 'body', label: '原生表单操作', sourceWidgetId: 'container.sheet', targetScope: 'form', button },
        ],
      },
    });
    expect(resolveActions(contract, 'form', { nativeTree: true }).map((action) => action.key)).toEqual(['header', 'root_header']);
    expect(resolveActions(contract, 'form', { intakeMode: true })).toEqual([]);
  })

  it('does not expose body actions when a native container tree is present', () => {
    const contract = decodePageContract({
      layoutContract: { containerTree: [{ type: 'sheet', children: [] }] },
      actionContract: {
        actionRuleList: [
          { actionKey: 'body', label: '正文动作', sourceWidgetId: 'container.sheet', targetScope: 'form', button: { name: 'run', type: 'object' } },
        ],
      },
    });
    expect(resolveActions(contract, 'form', { nativeTree: true })).toEqual([]);
  })

  it('only exposes page row actions in list row action menus', () => {
    const contract = decodePageContract({
      actionContract: {
        actionRuleList: [
          { actionKey: 'row_open', label: '打开', sourceWidgetId: 'page.row', targetScope: 'row', button: { name: 'open', type: 'object' } },
          { actionKey: 'body_action', label: '正文动作', sourceWidgetId: 'container.sheet', targetScope: 'row', button: { name: 'run', type: 'object' } },
        ],
      },
    });
    expect(resolveActions(contract, 'row').map((action) => action.key)).toEqual(['row_open']);
  })

  it('hides technical form actions whose label is only their key', () => {
    const contract = decodePageContract({
      actionContract: {
        actionRuleList: [
          { actionKey: 'project_update_all_action', label: 'project_update_all_action', targetScope: 'form', sourceWidgetId: 'page.header', button: { name: 'project_update_all_action', type: 'object' } },
          { actionKey: 'human_label', label: '刷新项目', targetScope: 'form', sourceWidgetId: 'page.header', button: { name: 'refresh_project', type: 'object' } },
        ],
      },
    });
    expect(resolveActions(contract, 'form').map((action) => action.key)).toEqual(['human_label']);
  })

  it('does not inject action-only native buttons into the semantic form tree', () => {
    const contract = decodePageContract({
      layoutContract: {
        containerTree: [{
          type: 'header',
          children: [{
            type: 'button',
            action: {
              actionKey: 'share_readonly',
              label: '共享只读',
              sourceWidgetId: 'page.header',
              targetScope: 'form',
              button: { name: 'share_readonly', type: 'object' },
            },
          }],
        }],
      },
      actionContract: {
        actionRuleList: [{
          actionKey: 'share_readonly',
          label: '共享只读',
          sourceWidgetId: 'page.header',
          targetScope: 'form',
          button: { name: 'share_readonly', type: 'object' },
        }],
      },
    });
    const model = resolveSemanticFormModel(contract);
    const actionNodes = [...model.primaryNodes, ...model.subordinateNodes].flatMap(function collect(node): any[] {
      return [node, ...node.children.flatMap(collect)];
    }).filter((node) => node.action);
    expect(actionNodes).toEqual([]);
  })

  it('preserves semantic form structure instead of flattening the container tree', () => {
    const contract = decodePageContract({
      pageInfo: { model: 'project.project', viewType: 'form' },
      layoutContract: {
        formStructureContract: {
          presentationMode: 'task',
          slots: [{ slot: 'overview', title: '办理总览', role: 'summary', fieldRefs: ['name'] }],
        },
        containerTree: [{
          type: 'sheet',
          semanticRole: 'task',
          children: [{
            type: 'notebook',
            children: [{
              type: 'page',
              title: '基本信息',
              children: [{
                type: 'field',
                name: 'name',
                semanticRole: 'summary',
                componentKey: 'sc.input.text',
                fieldInfo: { name: 'name', type: 'char' },
              }],
            }],
          }],
        }],
      },
    })
    const model = resolveSemanticFormModel(contract)
    expect(model.presentationMode).toBe('task')
    expect(model.primaryNodes[0].kind).toBe('slot')
    expect(model.primaryNodes[0].title).toBe('办理总览')
    expect(model.primaryNodes[0].fields[0]).toMatchObject({
      code: 'name',
      semanticRole: 'summary',
      widgetKey: 'sc.input.text',
    })
    expect(model.primaryNodes.some((node) => node.kind === 'sheet')).toBe(false)
  })

  it('keeps native notebook tabs when an empty children placeholder is present', () => {
    const contract = decodePageContract({
      pageInfo: { model: 'project.project', viewType: 'form' },
      layoutContract: {
        containerTree: [{
          type: 'sheet',
          children: [{
            type: 'notebook',
            children: [],
            tabs: [
              { type: 'page', name: 'tender', title: '投标管理', children: [{ type: 'field', name: 'tender_bid_ids', fieldInfo: { name: 'tender_bid_ids', type: 'one2many', relation: 'tender.bid' } }] },
              { type: 'page', name: 'contract', title: '合同', children: [{ type: 'field', name: 'contract_ids', fieldInfo: { name: 'contract_ids', type: 'one2many', relation: 'construction.contract' } }] },
            ],
          }],
        }],
      },
    })
    const model = resolveSemanticFormModel(contract)
    const notebook = model.primaryNodes[0].children[0]
    expect(notebook.kind).toBe('notebook')
    expect(notebook.children.map((page) => page.title)).toEqual(['投标管理', '合同'])
    const codes = (node: any): string[] => [
      ...node.fields.map((field: any) => field.code),
      ...node.children.flatMap((child: any) => codes(child)),
    ]
    expect(codes(notebook.children[0])).toContain('tender_bid_ids')
    expect(codes(notebook.children[1])).toContain('contract_ids')
  })

  it('keeps relational cards inside native notebook pages on task forms', () => {
    const contract = decodePageContract({
      pageInfo: { model: 'project.project', viewType: 'form' },
      layoutContract: {
        formStructureContract: {
          presentationMode: 'task',
          slots: [{ slot: 'details_source', title: '明细与来源', role: 'provenance', groups: [{ name: 'details', title: '业务明细', role: 'details', fieldRefs: ['contract_ids'] }] }],
        },
        containerTree: [{
          type: 'sheet',
          children: [{
            type: 'notebook',
            children: [],
            tabs: [{ type: 'page', name: 'contracts', title: '合同', children: [{ type: 'field', name: 'contract_ids', fieldInfo: { name: 'contract_ids', type: 'one2many', relation: 'construction.contract' } }] }],
          }],
        }],
      },
    })
    const model = resolveSemanticFormModel(contract)
    const findNotebook = (nodes: any[]): any => {
      for (const node of nodes) {
        if (node.kind === 'notebook') return node
        const nested = findNotebook(node.children)
        if (nested) return nested
      }
      return null
    }
    const notebook = findNotebook(model.primaryNodes)
    const pageCodes = (node: any): string[] => [
      ...node.fields.map((field: any) => field.code),
      ...node.children.flatMap((child: any) => pageCodes(child)),
    ]
    expect(pageCodes(notebook.children[0])).toContain('contract_ids')
    expect(model.primaryNodes.some((node) => node.kind === 'slot' && JSON.stringify(node).includes('contract_ids'))).toBe(false)
  })

})
