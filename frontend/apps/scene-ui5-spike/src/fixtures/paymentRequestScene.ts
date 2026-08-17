import type { SceneObjectPageContract } from '@sc/ui';

export const paymentRequestScene: SceneObjectPageContract = {
  identity: {
    productName: '企业业务管理平台',
    companyName: 'FE Company A',
    roleName: '财务主管',
    breadcrumbs: ['财务中心', '付款申请', '新建付款申请'],
    workTabs: [
      { id: 'payment-list', label: '付款申请列表' },
      { id: 'payment-create', label: '新建付款申请', active: true },
    ],
  },
  object: {
    eyebrow: '付款申请 · 新建',
    title: '合同进度款申请',
    subtitle: '华东智造中心项目 · 上海建工材料有限公司',
    status: '草稿',
    statusTone: 'Information',
    lastSavedLabel: '尚未保存',
  },
  actions: [
    { id: 'back', label: '返回列表', tier: 'transparent' },
    { id: 'save-draft', label: '保存草稿', tier: 'secondary' },
    { id: 'submit', label: '提交审批', tier: 'primary' },
  ],
  headerFacts: [
    { id: 'project', label: '项目', value: '华东智造中心', emphasis: true },
    { id: 'payee', label: '收款单位', value: '上海建工材料有限公司', emphasis: true },
    { id: 'basis', label: '付款依据', value: '合同进度款 · 第 3 期结算' },
    { id: 'amount', label: '申请金额', value: '¥ 1,286,400.00', emphasis: true },
    { id: 'account', label: '收款账户', value: '完整', tone: 'Positive' },
    { id: 'invoice', label: '发票', value: '待补 1 张', tone: 'Critical' },
    { id: 'blocking', label: '办理阻断', value: '发票未齐', tone: 'Critical' },
    { id: 'next', label: '下一步', value: '补齐发票后提交' },
  ],
  notices: [
    {
      id: 'invoice-gap',
      title: '提交前需补齐发票',
      detail: '当前待补票金额 ¥ 300,000.00；补齐后系统将自动解除办理阻断。',
      tone: 'Critical',
    },
  ],
  task: {
    title: '本次付款办理',
    description: '只呈现本次必须填写或确认的事项；系统事实在右侧集中展示。',
    groups: [
      {
        id: 'object-and-basis',
        title: '对象与依据',
        description: '先明确钱付给谁、基于什么业务事实。',
        fields: [
          {
            id: 'payment-type',
            label: '付款类型',
            kind: 'select',
            value: 'contract_progress',
            required: true,
            options: [
              { key: 'contract_progress', label: '合同进度款' },
              { key: 'settlement', label: '结算付款' },
              { key: 'material', label: '材料付款' },
            ],
          },
          {
            id: 'project',
            label: '项目',
            kind: 'text',
            value: '华东智造中心项目',
            required: true,
            source: '当前业务上下文',
          },
          {
            id: 'partner',
            label: '收款单位',
            kind: 'text',
            value: '上海建工材料有限公司',
            required: true,
            source: '合同 CT-2026-018',
          },
          {
            id: 'contract',
            label: '合同',
            kind: 'text',
            value: 'CT-2026-018 · 主体结构材料采购合同',
            required: true,
            source: '项目合同库',
          },
          {
            id: 'settlement',
            label: '结算依据',
            kind: 'select',
            value: 'settlement-03',
            required: true,
            options: [{ key: 'settlement-03', label: '第 3 期进度结算 · 已确认' }],
            hint: '合同累计结算 ¥ 4,820,000.00',
          },
          {
            id: 'cost-classification',
            label: '成本分类',
            kind: 'select',
            value: 'direct-material',
            required: true,
            options: [{ key: 'direct-material', label: '直接成本 / 材料费' }],
            source: '合同成本科目',
          },
        ],
      },
      {
        id: 'payment-and-tax',
        title: '金额、账户与开票',
        description: '金额与资金去向同屏确认，降低付款差错。',
        fields: [
          {
            id: 'application-date',
            label: '申请日期',
            kind: 'date',
            value: '2026-08-16',
            required: true,
          },
          {
            id: 'application-amount',
            label: '本次申请金额',
            kind: 'amount',
            value: '1,286,400.00',
            required: true,
            hint: '不超过当前可付余额 ¥ 1,460,000.00',
          },
          {
            id: 'payee-account',
            label: '收款账户',
            kind: 'select',
            value: 'default-account',
            required: true,
            options: [{ key: 'default-account', label: '招商银行上海分行 · 6225 **** 9186' }],
            source: '往来单位默认账户',
          },
          {
            id: 'payment-account',
            label: '付款账户',
            kind: 'select',
            value: 'company-main',
            required: true,
            options: [{ key: 'company-main', label: '建设银行 · FE Company A 基本户' }],
            hint: '可用余额 ¥ 8,721,300.00',
          },
          {
            id: 'invoice-status',
            label: '发票情况',
            kind: 'select',
            value: 'partial',
            required: true,
            options: [
              { key: 'partial', label: '部分到票 · 待补 1 张' },
              { key: 'complete', label: '已全部到票' },
            ],
          },
          {
            id: 'invoice-amount',
            label: '已收票金额',
            kind: 'amount',
            value: '986,400.00',
            required: true,
            hint: '差额 ¥ 300,000.00',
          },
        ],
      },
      {
        id: 'explanation',
        title: '说明',
        fields: [
          {
            id: 'payment-purpose',
            label: '付款用途与说明',
            kind: 'textarea',
            value: '支付主体结构材料第 3 期进度款，扣除质保金后按合同约定支付。',
            required: true,
            span: 'full',
            placeholder: '说明付款用途、特殊约定或需要审批人关注的事项',
          },
        ],
      },
    ],
  },
  context: {
    title: '业务上下文',
    description: '来自合同、结算、项目和财务主数据，不在本次办理中重复编辑。',
    groups: [
      {
        id: 'contract-facts',
        title: '合同与结算',
        facts: [
          { id: 'contract-amount', label: '合同金额', value: '¥ 6,200,000.00' },
          { id: 'settled', label: '累计结算', value: '¥ 4,820,000.00' },
          { id: 'paid', label: '累计已付', value: '¥ 3,360,000.00' },
          { id: 'available', label: '当前可付', value: '¥ 1,460,000.00', tone: 'Positive' },
          { id: 'retention', label: '质保金比例', value: '5%' },
        ],
      },
      {
        id: 'cost-facts',
        title: '资金与成本归属',
        facts: [
          { id: 'company', label: '所属公司', value: 'FE Company A' },
          { id: 'cost-center', label: '成本中心', value: 'CC-3102 / 土建工程' },
          { id: 'budget', label: '预算项', value: '主体材料采购' },
          { id: 'fund-plan', label: '资金计划', value: '2026-08 月度资金计划' },
        ],
      },
      {
        id: 'tax-and-risk',
        title: '开票与风险',
        facts: [
          { id: 'tax-rate', label: '税率', value: '13%' },
          { id: 'invoice-type', label: '发票类型', value: '增值税专用发票' },
          { id: 'invoice-gap', label: '待补票金额', value: '¥ 300,000.00', tone: 'Critical' },
          { id: 'risk', label: '风险提示', value: '补票后可提交', tone: 'Critical' },
        ],
      },
    ],
  },
  relations: {
    title: '本次办理依据与核对明细',
    description: '关系事实保留在独立明细区，不与主表单字段重复。',
    tables: [
      {
        id: 'settlement-payment-calculation',
        title: '结算与付款计算',
        description: '本次申请金额由已确认结算和合同扣款计算形成。',
        columns: [
          { key: 'document', label: '业务单据', width: '36%' },
          { key: 'amount', label: '金额', width: '22%', align: 'right' },
          { key: 'deduction', label: '扣减', width: '20%', align: 'right' },
          { key: 'status', label: '状态', width: '22%' },
        ],
        rows: [
          {
            id: 'settlement-03',
            values: { document: '第 3 期进度结算', amount: '¥ 1,520,000.00', deduction: '¥ 76,000.00', status: '已确认' },
            tone: 'Positive',
          },
          {
            id: 'payment-current',
            values: { document: '本次付款申请', amount: '¥ 1,286,400.00', deduction: '¥ 157,600.00', status: '待提交' },
            tone: 'Information',
          },
        ],
      },
      {
        id: 'invoice-matching',
        title: '发票匹配',
        description: '到票事实独立核对，缺口直接参与提交资格判断。',
        columns: [
          { key: 'document', label: '发票/批次', width: '34%' },
          { key: 'amount', label: '含税金额', width: '24%', align: 'right' },
          { key: 'verified', label: '核验', width: '20%' },
          { key: 'status', label: '状态', width: '22%' },
        ],
        rows: [
          {
            id: 'invoice-batch-01',
            values: { document: '到票批次 INV-0816', amount: '¥ 986,400.00', verified: '已验真', status: '已匹配' },
            tone: 'Positive',
          },
          {
            id: 'invoice-gap-row',
            values: { document: '待补发票', amount: '¥ 300,000.00', verified: '未核验', status: '阻断' },
            tone: 'Critical',
          },
        ],
      },
    ],
  },
  reviewPanel: {
    title: '提交前业务核对',
    description: '以当前合同、结算、账户、资金和发票事实核对提交条件；面板不复制可编辑字段。',
    triggerLabel: '核对办理依据',
    groups: [
      {
        id: 'review-source',
        title: '来源关系',
        facts: [
          { id: 'review-project', label: '项目', value: '华东智造中心项目' },
          { id: 'review-contract', label: '合同', value: 'CT-2026-018' },
          { id: 'review-settlement', label: '结算', value: 'ST-2026-003' },
          { id: 'review-partner', label: '收款单位', value: '上海建工材料有限公司' },
        ],
      },
      {
        id: 'review-money',
        title: '资金核对',
        facts: [
          { id: 'review-payable', label: '当前可付', value: '¥ 1,460,000.00' },
          { id: 'review-amount', label: '本次申请', value: '¥ 1,286,400.00' },
          { id: 'review-account', label: '收款账户', value: '已验证默认账户' },
        ],
      },
    ],
    checklist: [
      { id: 'check-contract', label: '合同与结算状态', value: '通过', tone: 'Positive' },
      { id: 'check-account', label: '收付款账户', value: '通过', tone: 'Positive' },
      { id: 'check-budget', label: '预算与资金计划', value: '通过', tone: 'Positive' },
      { id: 'check-invoice', label: '发票完整度', value: '待补 ¥ 300,000.00', tone: 'Critical' },
    ],
  },
  activities: {
    title: '资料与活动',
    tabs: [
      {
        id: 'evidence',
        label: '业务依据',
        count: 3,
        items: [
          {
            id: 'contract-evidence',
            title: '主体结构材料采购合同',
            meta: 'CT-2026-018',
            detail: '合同状态：执行中 · 当前结算比例 77.7%',
            tone: 'Positive',
          },
          {
            id: 'settlement-evidence',
            title: '第 3 期进度结算',
            meta: 'ST-2026-003',
            detail: '项目经理与成本负责人已确认，结算金额 ¥ 1,520,000.00',
            tone: 'Information',
          },
          {
            id: 'invoice-evidence',
            title: '增值税专用发票',
            meta: '2 / 3 张',
            detail: '已核验金额 ¥ 986,400.00，仍需补齐 ¥ 300,000.00',
            tone: 'Critical',
          },
        ],
      },
      {
        id: 'attachments',
        label: '附件',
        count: 4,
        items: [
          {
            id: 'attachment-1',
            title: '第3期结算确认单.pdf',
            meta: '1.8 MB',
            detail: '李工上传 · 2026-08-15 16:24',
          },
          {
            id: 'attachment-2',
            title: '到票清单.xlsx',
            meta: '246 KB',
            detail: '王会计上传 · 2026-08-16 09:12',
          },
        ],
      },
      {
        id: 'approval',
        label: '审批',
        count: 0,
        items: [],
        emptyText: '保存并提交后生成审批任务',
      },
      {
        id: 'trail',
        label: '业务轨迹',
        count: 2,
        items: [
          {
            id: 'trail-1',
            title: '付款申请已创建',
            meta: '系统',
            detail: '由结算 ST-2026-003 发起，带入项目、合同与往来单位事实。',
            tone: 'Information',
          },
          {
            id: 'trail-2',
            title: '收款账户已解析',
            meta: '主数据',
            detail: '采用往来单位有效默认账户，账户校验通过。',
            tone: 'Positive',
          },
        ],
      },
    ],
  },
};
