# 产品菜单台账 V1

本台账由运行时 Odoo 菜单事实生成，只读取 `ir.ui.menu`、动作、权限组和 XMLID，不从用户确认历史数据反推产品菜单。

## 运行时来源

- database: `sc_ten_center_clean`
- generated_at: `2026-08-11T12:55:40.472453+00:00`
- roots: `smart_construction_core.menu_sc_root, smart_core.menu_smart_core_platform_root`
- visible_login_probe: `admin`

## 总览

- menu_count: `425`
- active_menu_count: `318`
- inactive_menu_count: `107`
- action_menu_count: `344`
- needs_review_count: `0`
- internal_history_business_visible_count: `0`
- ordinary_business_system_config_visible_count: `0`
- business_config_legacy_count: `0`
- business_config_legacy_active_count: `0`
- runtime_user_menu_without_xmlid_count: `0`
- formal_center_inactive_history_count: `2`

## 分层定义

- `formal_product`: 正式产品办理入口，用于日常施工业务的新增、编辑、查询、分析和继续办理。
- `system_config`: 系统/产品配置入口，包括低代码恢复入口、字典、规则、定额、审批和管理配置。
- `user_config`: 租户或用户自主管理的偏好、个性化和运行时配置入口。
- `history_acceptance`: 历史数据承载、用户核对、历史来源事实、迁移连续性和验收过渡入口。
- `dev_governance`: 平台内核、场景治理、发布运维、诊断和开发治理入口。

## 分层统计

| Layer | Count |
| --- | ---: |
| `formal_product` | 361 |
| `system_config` | 32 |
| `user_config` | 0 |
| `history_acceptance` | 5 |
| `dev_governance` | 27 |

## 正式产品入口概览

| 入口 | XMLID | 可见性探针用户 |
| --- | --- | --- |
| 智慧施工管理平台 / 产品配置 | `smart_construction_core.menu_sc_business_config_center` |  |
| 智慧施工管理平台 / 会计账务中心 | `smart_construction_core.menu_sc_accounting_center` |  |
| 智慧施工管理平台 / 合同中心 | `smart_construction_core.menu_sc_contract_center` |  |
| 智慧施工管理平台 / 工作台 | `smart_construction_core.menu_sc_workspace_center` |  |
| 智慧施工管理平台 / 成本中心 | `smart_construction_core.menu_sc_cost_center` |  |
| 智慧施工管理平台 / 报表中心 | `smart_construction_core.menu_sc_data_center` |  |
| 智慧施工管理平台 / 税务中心 | `smart_construction_core.menu_sc_tax_center` |  |
| 智慧施工管理平台 / 行政中心 | `smart_construction_core.menu_sc_hr_admin_center` |  |
| 智慧施工管理平台 / 财务中心 | `smart_construction_core.menu_sc_finance_center` |  |
| 智慧施工管理平台 / 项目中心 | `smart_construction_core.menu_sc_project_center` |  |

## 顶层菜单

| Menu | Layer | Visible Probe Logins | XMLID |
| --- | --- | --- | --- |
| 平台内核 | `dev_governance` | admin | `smart_core.menu_smart_core_platform_root` |
| 平台内核 / 产品发布 | `dev_governance` | admin | `smart_core.menu_smart_core_release_root` |
| 平台内核 / 公司访问 | `dev_governance` | admin | `smart_core.menu_smart_core_company_access_root` |
| 智慧施工管理平台 | `formal_product` | admin | `smart_construction_core.menu_sc_root` |
| 智慧施工管理平台 / 产品配置 | `formal_product` |  | `smart_construction_core.menu_sc_business_config_center` |
| 智慧施工管理平台 / 会计账务中心 | `formal_product` |  | `smart_construction_core.menu_sc_accounting_center` |
| 智慧施工管理平台 / 合同中心 | `formal_product` |  | `smart_construction_core.menu_sc_contract_center` |
| 智慧施工管理平台 / 工作台 | `formal_product` |  | `smart_construction_core.menu_sc_workspace_center` |
| 智慧施工管理平台 / 成本中心 | `formal_product` |  | `smart_construction_core.menu_sc_cost_center` |
| 智慧施工管理平台 / 报表中心 | `formal_product` |  | `smart_construction_core.menu_sc_data_center` |
| 智慧施工管理平台 / 税务中心 | `formal_product` |  | `smart_construction_core.menu_sc_tax_center` |
| 智慧施工管理平台 / 系统管理（内部） | `system_config` | admin | `smart_construction_core.menu_sc_config_center` |
| 智慧施工管理平台 / 行政中心 | `formal_product` |  | `smart_construction_core.menu_sc_hr_admin_center` |
| 智慧施工管理平台 / 财务中心 | `formal_product` |  | `smart_construction_core.menu_sc_finance_center` |
| 智慧施工管理平台 / 项目中心 | `formal_product` |  | `smart_construction_core.menu_sc_project_center` |

## 产品菜单树

- 平台内核 [`dev_governance`]
  - 产品发布 [`dev_governance`]
    - 产品策略 [`dev_governance`] -> `sc.product.policy`
    - 发布动作 [`dev_governance`] -> `sc.release.action`
    - 发布快照 [`dev_governance`] -> `sc.edition.release.snapshot`
    - 场景快照 [`dev_governance`] -> `sc.scene.snapshot`
  - 公司访问 [`dev_governance`]
    - 授权快照 [`dev_governance`] -> `sc.entitlement`
    - 用量统计 [`dev_governance`] -> `sc.usage.counter`
    - 统一登录路由 [`dev_governance`] -> `sc.login.route`
    - 订阅套餐 [`dev_governance`] -> `sc.subscription.plan`
    - 订阅实例 [`dev_governance`] -> `sc.subscription`
    - 运营任务 [`dev_governance`] -> `sc.ops.job`
- 智慧施工管理平台 [`formal_product`]
  - 产品配置 [`formal_product`]
    - 业务基础数据 [`formal_product` inactive]
      - 业务分类字典 [`system_config`] -> `sc.business.category`
      - 审批岗位人员 [`system_config`] -> `sc.approval.scope`
      - 数据字典 [`system_config`] -> `sc.dictionary`
      - 阶段要求配置 [`system_config`] -> `sc.project.stage.requirement.item`
      - 预算类型 [`system_config`] -> `project.cost.code`
    - 低代码系统配置 [`system_config` inactive]
      - 新增表单字段 [`system_config` inactive] -> `ui.form.custom.field.wizard`
      - 菜单配置 [`system_config`] -> `ui.menu.config.policy`
    - 字段管理 [`formal_product`] -> `ui.form.field.policy`
    - 工作流运行数据 [`dev_governance` inactive]
      - 工作流实例 [`dev_governance`] -> `sc.workflow.instance`
      - 工作流日志 [`dev_governance`] -> `sc.workflow.log`
      - 工作项 [`dev_governance`] -> `sc.workflow.workitem`
    - 数据权限 [`formal_product`] -> `ui.business.config.contract`
    - 流程审批配置 [`system_config`] -> `sc.approval.policy`
    - 系统参数 [`system_config`] -> `ui.business.config.contract`
    - 编码规则 [`system_config`] -> `ui.business.config.contract`
    - 表单配置 [`formal_product`] -> `ui.business.config.contract`
  - 会计账务中心 [`formal_product`]
    - 分析分配模型 [`formal_product`] -> `account.analytic.distribution.model`
    - 分析账户 [`formal_product`] -> `account.analytic.account`
    - 日记账 [`formal_product`] -> `account.journal`
  - 合同中心 [`formal_product`]
    - 合同办理 [`formal_product` inactive] -> `construction.contract`
    - 合同办理 [`formal_product` inactive] -> `construction.contract`
    - 合同变更 [`formal_product`] -> `sc.contract.change`
    - 合同管理 [`formal_product` inactive] -> `sc.expense.contract.ledger`
      - 一般合同（公司） [`formal_product`] -> `sc.general.contract`
      - 其他合同 [`formal_product`] -> `construction.contract.expense`
      - 分包合同 [`formal_product`] -> `construction.contract.expense`
      - 劳务合同 [`formal_product`] -> `construction.contract.expense`
      - 支出合同台账 [`formal_product`] -> `sc.expense.contract.ledger`
      - 支出合同执行 [`formal_product`] -> `construction.contract.expense`
      - 支出合同签证 [`formal_product`] -> `sc.settlement.adjustment`
      - 支出合同结算 [`formal_product`] -> `sc.settlement.order`
      - 材料合同 [`formal_product`] -> `construction.contract.expense`
      - 正常合同 [`formal_product`] -> `construction.contract.expense`
      - 租赁合同 [`formal_product`] -> `construction.contract.expense`
      - 补充合同 [`formal_product`] -> `construction.contract.expense`
    - 履约与预警（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 待我审批（一般合同（公司）） [`formal_product` inactive] -> `sc.general.contract`
    - 待我审批（项目合同） [`formal_product` inactive] -> `construction.contract`
    - 支出合同 [`formal_product`] -> `construction.contract.expense`
    - 支出结算 [`formal_product`] -> `sc.settlement.order`
    - 收入合同 [`formal_product`] -> `construction.contract.income`
    - 收入合同台账 [`formal_product` inactive] -> `sc.income.contract.ledger`
      - 合同履约事件 [`formal_product`] -> `sc.contract.event`
      - 收入合同台账 [`formal_product`] -> `sc.income.contract.ledger`
      - 收入合同执行 [`formal_product`] -> `construction.contract.income`
      - 收入合同签证 [`formal_product`] -> `sc.settlement.adjustment`
      - 收入合同结算 [`formal_product`] -> `sc.settlement.order`
      - 施工合同 [`formal_product` inactive] -> `construction.contract.income`
      - 项目收入合同 [`formal_product`] -> `construction.contract.income`
    - 收入结算 [`formal_product`] -> `sc.settlement.order`
    - 日常合同 [`formal_product`] -> `sc.general.contract`
    - 日常合同结算 [`formal_product`] -> `sc.settlement.order`
  - 工作台 [`formal_product`]
    - 待办事项 [`formal_product`] -> `sc.workbench.item`
    - 我的审批 [`formal_product` inactive] -> `sc.workbench.item`
    - 我的项目 [`formal_product` inactive] -> `project.project`
    - 数据总览 [`formal_product`] -> `sc.operating.metrics.project`
    - 消息通知 [`formal_product`] -> `mail.activity`
    - 项目看板 [`formal_product`] -> `project.project`
  - 成本中心 [`formal_product`]
    - WBS/分部分项 [`formal_product` inactive] -> `construction.work.breakdown`
    - 动态成本 [`formal_product` inactive]
      - 成本台账 [`formal_product`] -> `project.cost.ledger`
      - 进度计量 [`formal_product`] -> `project.progress.entry`
    - 成本分析 [`formal_product` inactive]
      - 成本汇总 [`formal_product`] -> `project.cost.compare`
      - 经营利润 [`formal_product`] -> `project.profit.compare`
    - 成本归集 [`formal_product`] -> `project.cost.ledger`
    - 成本计划编制 [`formal_product`] -> `project.cost.plan`
    - 成本预测（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 现金流预测（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 目标与预算 [`formal_product` inactive]
      - 成本计划 [`formal_product` inactive] -> `project.cost.plan`
      - 施工执行范围 [`formal_product`] -> `construction.execution.scope`
      - 标段结构 [`formal_product`] -> `construction.contract.section`
      - 清单执行分配 [`formal_product`] -> `project.boq.allocation`
      - 清单明细 [`formal_product`] -> `project.boq.line`
      - 清单版本 [`formal_product`] -> `project.boq.version`
      - 目标成本计划 [`formal_product`] -> `project.cost.plan`
      - 空间位置 LBS [`formal_product`] -> `construction.location.breakdown`
      - 综合单价分析 [`formal_product`] -> `project.boq.analysis`
      - 预算清单分摊 [`formal_product`] -> `project.budget.cost.alloc`
    - 项目盈亏分析 [`formal_product`] -> `project.profit.compare`
    - 项目预算 [`formal_product`] -> `project.cost.plan`
    - 项目预算 [`formal_product` inactive]
      - 预算清单 [`formal_product`] -> `project.cost.plan`
  - 报表中心 [`formal_product`]
    - 业务核算主体 [`formal_product` inactive] -> `sc.business.entity`
    - 劳务分包报表 [`formal_product`] -> `sc.labor.usage`
    - 成本报表 [`formal_product` inactive]
    - 成本报表 [`formal_product`] -> `sc.comprehensive.cost.summary`
      - 发票分析报表 [`formal_product`] -> `sc.invoice.registration`
      - 发票分类汇总表 [`formal_product`] -> `sc.invoice.category.summary`
      - 工资统计表 [`formal_product`] -> `sc.salary.summary`
      - 库存统计表（新） [`formal_product`] -> `sc.material.stock.summary`
      - 报销统计 [`formal_product`] -> `sc.expense.reimbursement.summary`
      - 进项发票明细表 [`formal_product`] -> `sc.invoice.registration`
    - 税务报表 [`formal_product`] -> `sc.invoice.registration`
    - 经营分析 [`formal_product` inactive]
      - 合同执行表 [`formal_product`] -> `construction.contract`
      - 项目经营分析 [`formal_product`] -> `sc.operating.metrics.project`
    - 经营报表 [`formal_product` inactive]
      - 公司经营情况表 [`formal_product`] -> `sc.company.operation.summary`
      - 应收应付报表 [`formal_product` inactive] -> `sc.ar.ap.company.summary`
    - 综合看板 [`formal_product` inactive]
      - 成本大屏 [`formal_product`] -> `sc.dashboard.cockpit.fact`
      - 成本驾驶舱 [`formal_product`] -> `sc.dashboard.cockpit.fact`
      - 经营大屏 [`formal_product`] -> `sc.operating.metrics.project`
      - 经营指标 [`formal_product` inactive]
      - 资金驾驶舱 [`formal_product`] -> `sc.dashboard.cockpit.fact`
    - 财务分析 [`formal_product` inactive]
      - 付款统计表 [`formal_product`] -> `sc.treasury.ledger`
      - 供应商账款 [`formal_product`] -> `sc.ar.ap.company.summary`
      - 客户账款 [`formal_product`] -> `sc.ar.ap.project.summary`
      - 收款统计表 [`formal_product`] -> `sc.treasury.ledger`
      - 资金台账 [`formal_product`] -> `sc.treasury.ledger`
    - 资金报表 [`formal_product`] -> `sc.fund.daily.summary`
    - 项目报表 [`formal_product`] -> `sc.operating.metrics.project`
    - 预测预警（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
  - 税务中心 [`formal_product`]
    - 发票查验（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 发票管理 [`formal_product` inactive]
      - 进项税额上报 [`formal_product`] -> `sc.invoice.registration`
    - 发票红冲 [`formal_product`] -> `sc.output.invoice.adjustment`
    - 外经证 [`formal_product`] -> `sc.tax.certificate.registration`
    - 开票申请 [`formal_product`] -> `sc.invoice.registration`
    - 税务申报 [`formal_product`] -> `sc.invoice.registration`
    - 税务申报（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 税额抵扣 [`formal_product`] -> `sc.tax.deduction.registration`
    - 进项发票 [`formal_product`] -> `sc.invoice.registration`
    - 销项开票 [`formal_product`] -> `sc.invoice.registration`
    - 项目专项抵扣 [`formal_product`] -> `sc.tax.deduction.registration`
    - 预缴登记 [`formal_product`] -> `sc.invoice.registration`
  - 系统管理（内部） [`system_config`]
    - 历史验收归档（内部） [`history_acceptance` inactive]
    - 场景与能力 [`dev_governance`]
      - 交付包安装记录 [`dev_governance`] -> `sc.pack.installation`
      - 交付包注册表 [`dev_governance`] -> `sc.pack.registry`
      - 场景版本 [`dev_governance`] -> `sc.scene.version`
      - 场景编排 [`dev_governance`] -> `sc.scene`
      - 能力分组 [`dev_governance`] -> `sc.capability.group`
      - 能力目录 [`dev_governance`] -> `sc.capability`
    - 定额字典 [`system_config`]
      - 专业 [`system_config`] -> `project.dictionary`
      - 全部定额字典 [`system_config`] -> `project.dictionary`
      - 四川定额导入 [`system_config`] -> `quota.import.wizard`
      - 子目 [`system_config`] -> `project.dictionary`
      - 定额项目 [`system_config`] -> `project.dictionary`
      - 章节 [`system_config`] -> `project.dictionary`
    - 定额库 [`system_config`]
      - 定额中心（左树右明细） [`system_config`] -> `project.dictionary`
      - 定额子目 [`system_config`] -> `project.dictionary`
      - 定额层级 [`system_config`] -> `project.dictionary`
    - 定额引擎 [`system_config`] -> `sc.norm.item`
      - 专业维护 [`system_config`] -> `sc.norm.specialty`
      - 定额库 [`system_config`] -> `sc.norm.item`
      - 定额库版本维护 [`system_config`] -> `sc.norm.catalog`
      - 定额项维护 [`system_config`] -> `sc.norm.item`
      - 导入定额 [`system_config`] -> `sc.norm.import.wizard`
      - 章节维护 [`system_config`] -> `sc.norm.chapter`
      - 适用地区维护 [`system_config`] -> `sc.norm.region`
    - 工作流 [`dev_governance`]
      - 工作流定义 [`dev_governance`] -> `sc.workflow.def`
    - 项目内部结构 [`formal_product`]
      - 执行结构 [`formal_product`] -> `ir.actions.server`
    - 项目管理（后台） [`dev_governance`] -> `project.project`
  - 行政中心 [`formal_product`]
    - 人事薪酬 [`formal_product` inactive]
      - 奖金 [`formal_product` inactive] -> `sc.hr.payroll.document`
      - 社保人员登记 [`formal_product` inactive] -> `sc.hr.payroll.document`
      - 社保登记 [`formal_product` inactive] -> `sc.hr.payroll.document`
      - 补助 [`formal_product` inactive] -> `sc.hr.payroll.document`
      - 项目管理人员工资登记 [`formal_product` inactive] -> `sc.hr.payroll.document`
    - 人员档案 [`system_config`] -> `res.users`
    - 人员生命周期（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 制度文件 [`formal_product`] -> `sc.document.admin.document`
    - 办公资产 [`formal_product`] -> `sc.office.admin.document`
    - 基础资料 [`formal_product` inactive]
    - 岗位管理 [`formal_product`] -> `hr.job`
    - 工资薪酬 [`formal_product`] -> `sc.hr.payroll.document`
    - 油卡管理 [`formal_product` inactive]
      - 充值登记 [`history_acceptance`] -> `sc.fund.account.operation`
      - 油卡登记 [`history_acceptance`] -> `sc.fund.account.operation`
    - 社保公积 [`formal_product`] -> `sc.hr.payroll.document`
    - 行政审批 [`formal_product` inactive]
      - 印章使用审批表 [`formal_product` inactive] -> `sc.office.admin.document`
      - 请假/休假审批单 [`formal_product` inactive] -> `sc.office.admin.document`
    - 证书管理 [`formal_product`] -> `sc.document.admin.document`
    - 资料证照 [`formal_product` inactive]
      - 借阅申请 [`formal_product` inactive] -> `sc.document.admin.document`
      - 公司资料存档 [`formal_product` inactive] -> `sc.document.admin.document`
    - 资源能力（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 部门管理 [`formal_product`] -> `hr.department`
  - 财务中心 [`formal_product`]
    - 付款事实 [`formal_product` inactive]
      - 付款申请 [`formal_product` inactive] -> `payment.request`
      - 付款申请明细 [`formal_product` inactive] -> `payment.request.line`
      - 付款申请残余事实 [`formal_product` inactive] -> `sc.payment.execution`
    - 付款申请 [`formal_product`] -> `payment.request`
    - 付款管理 [`formal_product` inactive]
      - 支付申请 [`formal_product`] -> `payment.request`
    - 保证金管理 [`formal_product` inactive]
      - 付款保证金退回 [`formal_product`] -> `sc.expense.claim`
      - 付款还保证金 [`formal_product`] -> `sc.expense.claim`
      - 付款还保证金退回 [`formal_product`] -> `sc.expense.claim`
      - 保证金收取 [`formal_product`] -> `sc.expense.claim`
      - 自筹保证金 [`formal_product` inactive] -> `sc.expense.claim`
      - 自筹保证金退回 [`formal_product` inactive] -> `sc.expense.claim`
    - 借还款办理 [`formal_product` inactive]
    - 公司&项目扣款 [`formal_product`] -> `sc.expense.claim`
    - 公司&项目退款 [`formal_product`] -> `sc.expense.claim`
    - 公司支出 [`formal_product`] -> `sc.payment.execution`
    - 公司收入 [`formal_product`] -> `sc.receipt.income`
    - 到款确认表 [`formal_product` inactive] -> `sc.receipt.income`
    - 历史付款 [`history_acceptance` inactive] -> `sc.historical.payment.fact`
    - 发票台账 [`formal_product` inactive]
      - 发票总台账 [`formal_product`] -> `sc.invoice.registration`
      - 收款发票 [`formal_product`] -> `sc.receipt.invoice.line`
      - 销项发票 [`formal_product`] -> `sc.output.invoice.ledger`
      - 销项调整记录 [`formal_product`] -> `sc.output.invoice.ledger`
    - 备用金 [`formal_product`] -> `sc.expense.claim`
    - 实付登记 [`formal_product`] -> `sc.payment.execution`
    - 往来款登记 [`formal_product`] -> `sc.fund.account.operation`
    - 待我审批（付款申请） [`formal_product` inactive] -> `tier.review`
    - 扣款 [`formal_product` inactive]
    - 扣款与非现金 [`formal_product` inactive]
    - 扣款税费核对 [`history_acceptance` inactive]
    - 收付款办理 [`formal_product` inactive]
      - 工程进度款收入登记 [`formal_product`] -> `sc.receipt.income`
      - 往来单位付款 [`formal_product`] -> `sc.payment.execution`
      - 收款申请 [`formal_product`] -> `payment.request`
      - 结算中心 [`formal_product`]
        - 结算单 [`formal_product`] -> `sc.settlement.order`
        - 结算调整 [`formal_product`] -> `sc.settlement.adjustment`
    - 收支 [`formal_product` inactive]
    - 收款 [`formal_product` inactive]
    - 收款登记 [`formal_product`] -> `sc.receipt.income`
    - 账户资金 [`formal_product` inactive]
    - 账户资金 [`formal_product` inactive]
      - 余额调整 [`formal_product`] -> `sc.fund.account.operation`
      - 借款申请 [`formal_product`] -> `sc.financing.loan`
      - 借款申请 [`formal_product` inactive] -> `sc.financing.loan`
      - 承包人借项目款 [`formal_product`] -> `sc.financing.loan`
      - 承包人还项目款 [`formal_product`] -> `sc.expense.claim`
      - 自筹垫付办理 [`formal_product`] -> `sc.self.funding.registration`
      - 自筹退回办理 [`formal_product`] -> `sc.self.funding.registration`
      - 账户间资金往来 [`formal_product`] -> `sc.fund.account.operation`
      - 贷款登记 [`formal_product`] -> `sc.financing.loan`
      - 资金划拨 [`formal_product`] -> `sc.fund.account.operation`
      - 资金对账 [`formal_product`] -> `sc.treasury.reconciliation`
      - 资金日报 [`formal_product` inactive]
      - 资金日报表 [`formal_product`] -> `sc.fund.account.operation`
      - 资金调拨 [`formal_product`] -> `sc.fund.account.operation`
      - 还款登记 [`formal_product`] -> `sc.expense.claim`
      - 项目借公司款登记 [`formal_product`] -> `sc.financing.loan`
      - 项目还公司款登记 [`formal_product`] -> `sc.expense.claim`
    - 费用与保证金 [`formal_product` inactive] -> `sc.expense.claim`
      - 借款单 [`formal_product`] -> `sc.financing.loan`
      - 公司扣款 [`formal_product`] -> `sc.expense.claim`
      - 公司支出 [`formal_product`] -> `sc.payment.execution`
      - 公司收入 [`formal_product`] -> `sc.receipt.income`
      - 合同保证金支付 [`formal_product`] -> `sc.expense.claim`
      - 合同保证金退回 [`formal_product`] -> `sc.expense.claim`
      - 扣款实缴登记 [`formal_product`] -> `sc.expense.claim`
      - 扣款实缴退回 [`formal_product`] -> `sc.expense.claim`
      - 投标保证金支付 [`formal_product`] -> `sc.expense.claim`
      - 投标保证金退回 [`formal_product`] -> `sc.expense.claim`
      - 费用报销单 [`formal_product`] -> `sc.expense.claim`
      - 还款单 [`formal_product`] -> `sc.expense.claim`
      - 项目费用报销单 [`formal_product`] -> `sc.expense.claim`
    - 费用报销 [`formal_product`] -> `sc.expense.claim`
    - 资金分析 [`formal_product` inactive]
      - 借款还款与调拨明细 [`formal_product`] -> `sc.interfund.movement.fact`
      - 公司-承包人资金责任余额 [`formal_product`] -> `sc.company.contractor.responsibility.summary`
      - 公司-承包人资金责任明细 [`formal_product`] -> `sc.company.contractor.responsibility.fact`
      - 往来对象资金总览 [`formal_product`] -> `sc.finance.counterparty.position.summary`
      - 项目与对象资金往来 [`formal_product`] -> `sc.finance.project.counterparty.position`
      - 项目借还调拨汇总 [`formal_product`] -> `sc.interfund.movement.project.summary`
      - 项目收付款来源明细 [`formal_product`] -> `sc.finance.business.fact`
      - 项目收付款汇总 [`formal_product`] -> `sc.finance.business.project.summary`
      - 项目资金总览 [`formal_product`] -> `sc.finance.project.capital.position`
    - 资金汇总 [`formal_product`] -> `project.funding.baseline`
    - 资金计划 [`formal_product` inactive]
      - 资金计划申报 [`formal_product`] -> `project.funding.baseline`
    - 资金计划实际付款分配 [`formal_product` inactive] -> `project.funding.actual.event.allocation`
    - 资金预测（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 项目资金 [`formal_product` inactive]
  - 项目中心 [`formal_product`]
    - 分包成本 [`formal_product`]
      - 分包成本登记 [`formal_product`] -> `sc.subcontract.register`
      - 分包签证费用 [`formal_product`] -> `sc.site.variation`
    - 劳务成本 [`formal_product`]
      - 劳务实名制 [`formal_product`] -> `sc.labor.worker`
      - 劳务成本登记 [`formal_product`] -> `sc.labor.usage`
      - 劳务扣款明细 [`formal_product`] -> `sc.labor.deduction`
    - 客商管理 [`formal_product`]
      - 供应商档案 [`formal_product`] -> `res.partner`
      - 客商黑名单 [`formal_product`] -> `res.partner`
      - 客户档案 [`formal_product`] -> `res.partner`
    - 招投标管理 [`formal_product`]
      - 中标管理 [`formal_product`] -> `tender.bid`
      - 开标记录 [`formal_product` inactive] -> `tender.opening`
      - 投标保证金 [`formal_product`] -> `tender.guarantee`
      - 投标准备 [`formal_product` inactive] -> `tender.bid`
      - 投标报名管理 [`formal_product` inactive] -> `tender.bid`
      - 投标报名费申请 [`formal_product` inactive] -> `tender.doc.purchase`
      - 投标项目 [`formal_product`] -> `tender.bid`
      - 招标信息 [`formal_product`] -> `tender.opportunity`
      - 标书管理 [`formal_product`] -> `tender.document`
    - 施工管理 [`formal_product`]
      - BIM协同（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
      - 安全检查 [`formal_product`] -> `sc.safety.issue`
      - 安全管理 [`formal_product` inactive]
        - 危险源 [`formal_product`] -> `sc.hazard.source`
        - 安全交底 [`formal_product`] -> `sc.safety.disclosure`
        - 安全复验 [`formal_product`] -> `sc.safety.recheck`
        - 安全巡检 [`formal_product`] -> `sc.safety.patrol.task`
        - 安全整改 [`formal_product`] -> `sc.safety.rectification`
        - 安全方案 [`formal_product`] -> `sc.safety.plan`
        - 风险库 [`formal_product`] -> `sc.risk.library`
      - 工程资料 [`formal_product`] -> `sc.project.document`
      - 施工日志 [`formal_product`] -> `sc.construction.diary`
      - 施工进度 [`formal_product`] -> `project.progress.entry`
      - 现场移动（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
      - 签证变更 [`formal_product`] -> `sc.site.variation`
      - 质量管理 [`formal_product` inactive]
        - 现场影像 [`formal_product`] -> `sc.site.photo.batch`
        - 质量复验 [`formal_product`] -> `sc.quality.recheck`
        - 质量整改 [`formal_product`] -> `sc.quality.rectification`
        - 质量标准 [`formal_product`] -> `sc.check.standard`
        - 质量检查 [`formal_product`] -> `sc.quality.issue`
      - 质量验收 [`formal_product`] -> `sc.quality.acceptance`
      - 进度与施工 [`formal_product` inactive]
        - 计划汇报 [`formal_product`] -> `sc.plan.report`
        - 计划管理 [`formal_product`] -> `sc.plan`
    - 施工资料 [`formal_product` inactive]
      - 现场资料 [`formal_product`] -> `sc.project.document`
    - 机械成本 [`formal_product`]
      - 机械台班登记 [`formal_product`] -> `sc.equipment.usage`
    - 材料成本 [`formal_product`]
      - 专业分包 [`formal_product` inactive]
        - 分包方单 [`formal_product`] -> `sc.subcontract.request`
        - 分包申请 [`formal_product`] -> `sc.subcontract.request`
        - 分包登记 [`formal_product`] -> `sc.subcontract.register`
        - 分包结算 [`formal_product`] -> `sc.subcontract.settlement`
        - 分包计划 [`formal_product`] -> `sc.subcontract.plan`
      - 供应链协同（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
      - 劳务管理 [`formal_product` inactive]
        - 劳务申请 [`formal_product`] -> `sc.labor.request`
        - 劳务结算 [`formal_product`] -> `sc.labor.settlement`
        - 劳务计划 [`formal_product`] -> `sc.labor.plan`
        - 方单 [`formal_product`] -> `sc.labor.usage`
        - 考勤记录 [`formal_product`] -> `sc.attendance.checkin`
        - 零星用工 [`formal_product`] -> `sc.labor.usage`
      - 周转材料租赁 [`formal_product` inactive]
        - 租赁单 [`formal_product`] -> `sc.material.rental.order`
        - 租赁结算 [`formal_product`] -> `sc.material.rental.settlement`
        - 租赁计划 [`formal_product`] -> `sc.material.rental.plan`
      - 待我审批（物资计划） [`formal_product` inactive] -> `tier.review`
      - 机械设备 [`formal_product` inactive]
        - 机械台班记录 [`formal_product`] -> `sc.equipment.usage`
        - 设备使用登记 [`formal_product`] -> `sc.equipment.usage`
        - 设备申请 [`formal_product`] -> `sc.equipment.request`
        - 设备结算 [`formal_product`] -> `sc.equipment.settlement`
        - 设备计划 [`formal_product`] -> `sc.equipment.plan`
      - 材料入库 [`formal_product`] -> `sc.material.inbound`
      - 材料出库 [`formal_product`] -> `sc.material.outbound`
      - 材料管理 [`formal_product` inactive]
        - 报价单 [`formal_product`] -> `sc.material.rfq`
        - 材料价格库 [`formal_product`] -> `sc.material.price`
        - 材料损耗 [`formal_product`] -> `sc.material.outbound`
        - 材料档案 [`formal_product`] -> `sc.material.catalog`
        - 材料结算 [`formal_product`] -> `sc.material.settlement`
        - 材料计划 [`formal_product`] -> `project.material.plan`
        - 材料调拨 [`formal_product`] -> `sc.material.outbound`
        - 材料进场验收 [`formal_product`] -> `sc.material.acceptance`
        - 询比价 [`formal_product`] -> `sc.material.rfq`
        - 退库办理 [`formal_product`] -> `sc.material.outbound`
        - 采购申请 [`formal_product`] -> `sc.material.purchase.request`
        - 采购订单 [`formal_product`] -> `purchase.order`
      - 材料退货 [`formal_product`] -> `sc.material.supplier.return`
    - 班组借/扣款 [`formal_product`]
      - 班组借/扣款登记 [`formal_product`] -> `sc.expense.claim`
    - 里程碑管理（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 项目创建 [`formal_product`]
      - 快速创建项目 [`formal_product` inactive] -> `project.project`
      - 新项目立项 [`formal_product`] -> `project.project`
      - 项目信息编辑 [`formal_product`] -> `project.project`
      - 项目启停管理 [`formal_product`] -> `project.project`
    - 项目协同（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 项目台账 [`formal_product` inactive]
      - 项目台账 [`formal_product`] -> `project.project`
    - 项目总览 [`formal_product` inactive]
      - 项目驾驶舱 [`formal_product`] -> `project.project`
      - 项目驾驶舱 [`formal_product`] -> `project.project`
    - 项目收尾（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 项目组织（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`
    - 项目薪资 [`formal_product`]
      - 薪资发放登记 [`formal_product`] -> `sc.hr.payroll.document`
      - 薪资核算清单 [`formal_product`] -> `sc.hr.payroll.document`
    - 项目计划 [`formal_product` inactive]
      - WBS 版本 [`formal_product`] -> `construction.wbs.plan`
      - WBS 计划 [`formal_product`] -> `construction.work.breakdown`
    - 项目资料 [`formal_product` inactive]
    - 风险与问题（后续上线） [`formal_product` inactive] -> `sc.project.capability.roadmap`

## 待复核队列

未检测到需要人工复核的模糊菜单。
