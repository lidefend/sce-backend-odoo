import type { SceneCollectionContract, SceneHierarchyContract } from '@sc/ui';

const identity = {
  productName: '企业业务管理平台',
  companyName: 'FE Company A',
  roleName: '财务主管',
  breadcrumbs: ['财务中心', '付款申请'],
  workTabs: [
    { id: 'workspace', label: '我的工作' },
    { id: 'payment-list', label: '付款申请列表', active: true },
  ],
};

export const paymentCollectionScene: SceneCollectionContract = {
  identity,
  eyebrow: 'COLLECTION · PAYMENT REQUEST',
  title: '付款申请',
  description: '按状态、对象与风险聚合待办；列表只呈现判断和进入办理所需的信息。',
  actions: [
    { id: 'export', label: '导出', tier: 'transparent' },
    { id: 'create', label: '新建付款申请', tier: 'primary' },
  ],
  summaries: [
    { id: 'pending', label: '待我处理', value: '8 笔', tone: 'Information' },
    { id: 'amount', label: '本月申请', value: '¥ 6,842,300' },
    { id: 'blocked', label: '存在阻断', value: '2 笔', tone: 'Critical' },
    { id: 'ready', label: '可生成付款登记', value: '3 笔', tone: 'Positive' },
  ],
  filters: [
    { id: 'mine', label: '范围', value: '我的待办', active: true },
    { id: 'state', label: '状态', value: '办理中' },
    { id: 'month', label: '申请月份', value: '2026-08' },
    { id: 'risk', label: '风险', value: '全部' },
  ],
  table: {
    id: 'payment-request-list',
    title: '付款申请业务列表',
    description: '同一字段语义可由 Native、TDesign 或 UI5 表格驱动呈现。',
    columns: [
      { key: 'document', label: '单号 / 事项', width: '25%' },
      { key: 'project', label: '项目', width: '18%' },
      { key: 'partner', label: '收款单位', width: '20%' },
      { key: 'amount', label: '申请金额', width: '14%', align: 'right' },
      { key: 'next', label: '下一步', width: '14%' },
      { key: 'status', label: '状态', width: '9%' },
    ],
    rows: [
      {
        id: 'pr-001',
        values: { document: 'PR-2026-0816 / 合同进度款', project: '华东智造中心', partner: '上海建工材料有限公司', amount: '¥ 1,286,400', next: '补齐发票', status: '有阻断' },
        tone: 'Critical',
      },
      {
        id: 'pr-002',
        values: { document: 'PR-2026-0815 / 材料结算款', project: '浦东科创园', partner: '华新建材有限公司', amount: '¥ 842,000', next: '提交审批', status: '草稿' },
        tone: 'Information',
      },
      {
        id: 'pr-003',
        values: { document: 'PR-2026-0812 / 劳务结算款', project: '临港产业基地', partner: '安筑劳务有限公司', amount: '¥ 2,160,000', next: '生成付款登记', status: '已批准' },
        tone: 'Positive',
      },
      {
        id: 'pr-004',
        values: { document: 'PR-2026-0808 / 设备租赁款', project: '华东智造中心', partner: '鼎盛设备租赁', amount: '¥ 315,600', next: '财务审批', status: '审批中' },
        tone: 'Information',
      },
    ],
  },
  rowPresentation: {
    accessibilityLabel: '付款申请记录',
    titleField: 'document',
    statusField: 'status',
    mobileFields: ['project', 'partner', 'amount', 'next'],
  },
  selectionMode: 'multiple',
  readonly: false,
};

export const costHierarchyScene: SceneHierarchyContract = {
  identity: {
    ...identity,
    breadcrumbs: ['成本中心', '项目成本层级'],
    workTabs: [
      { id: 'payment-list', label: '付款申请列表' },
      { id: 'cost-hierarchy', label: '项目成本层级', active: true },
    ],
  },
  eyebrow: 'HIERARCHY · COST POSITION',
  title: '项目成本与资金归属',
  description: '按公司、项目、成本中心和合同逐级定位业务事实，不在树中直接编辑付款。',
  actions: [
    { id: 'collapse', label: '收起全部', tier: 'transparent' },
    { id: 'open-position', label: '查看资金位置', tier: 'primary' },
  ],
  summaries: [
    { id: 'projects', label: '在建项目', value: '12 个' },
    { id: 'contracts', label: '执行中合同', value: '86 份' },
    { id: 'payable', label: '当前可付', value: '¥ 18,420,000', tone: 'Positive' },
    { id: 'risks', label: '资金风险', value: '3 项', tone: 'Critical' },
  ],
  nodes: [
    {
      id: 'company-a',
      label: 'FE Company A',
      meta: '公司 · 12 个在建项目',
      value: '可付 ¥ 18,420,000',
      status: '正常',
      tone: 'Positive',
      children: [
        {
          id: 'project-east',
          label: '华东智造中心项目',
          meta: '项目 · 进度 68%',
          value: '可付 ¥ 4,820,000',
          status: '1 项风险',
          tone: 'Critical',
          children: [
            {
              id: 'cost-civil',
              label: 'CC-3102 / 土建工程',
              meta: '成本中心 · 18 份执行合同',
              value: '已用 71%',
              status: '正常',
              tone: 'Positive',
              children: [
                { id: 'contract-material', label: 'CT-2026-018 / 主体材料采购', meta: '合同', value: '可付 ¥ 1,460,000', status: '待补票', tone: 'Critical' },
                { id: 'contract-labor', label: 'CT-2026-011 / 主体劳务分包', meta: '合同', value: '可付 ¥ 980,000', status: '正常', tone: 'Positive' },
              ],
            },
            { id: 'cost-install', label: 'CC-3201 / 安装工程', meta: '成本中心 · 9 份执行合同', value: '已用 54%', status: '正常', tone: 'Positive' },
          ],
        },
        { id: 'project-port', label: '临港产业基地', meta: '项目 · 进度 42%', value: '可付 ¥ 3,260,000', status: '正常', tone: 'Positive' },
      ],
    },
  ],
};
