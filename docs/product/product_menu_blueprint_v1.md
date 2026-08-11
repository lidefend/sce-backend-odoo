# 产品菜单蓝图 V1

本蓝图由运行时菜单台账生成，用于回答“正式产品菜单长什么样”。历史验收、系统配置、开发治理不并入正式产品菜单，只作为边界列示。

## 当前结论

- 正式产品一级中心：`10` 个
- 正式产品 active 菜单：`260` 个
- 系统配置菜单：`32` 个，其中 active `30` 个
- 用户配置菜单：`0` 个，其中 active `0` 个
- 历史验收菜单：`5` 个，其中 active `2` 个
- 正式中心下 inactive 历史残留：`2` 个
- 开发治理菜单：`27` 个，其中 active `26` 个
- 待复核菜单：`0` 个

## 正式产品一级中心

| 中心 | 正式子入口 | 历史验收子入口 | 系统配置子入口 | 隐藏项 | XMLID |
| --- | ---: | ---: | ---: | ---: | --- |
| 工作台 | 4 | 0 | 0 | 2 | `smart_construction_core.menu_sc_workspace_center` |
| 项目中心 | 90 | 0 | 0 | 27 | `smart_construction_core.menu_sc_project_center` |
| 合同中心 | 25 | 0 | 0 | 8 | `smart_construction_core.menu_sc_contract_center` |
| 成本中心 | 18 | 0 | 0 | 8 | `smart_construction_core.menu_sc_cost_center` |
| 财务中心 | 64 | 0 | 0 | 29 | `smart_construction_core.menu_sc_finance_center` |
| 税务中心 | 10 | 0 | 0 | 3 | `smart_construction_core.menu_sc_tax_center` |
| 会计账务中心 | 3 | 0 | 0 | 0 | `smart_construction_core.menu_sc_accounting_center` |
| 报表中心 | 23 | 0 | 0 | 9 | `smart_construction_core.menu_sc_data_center` |
| 行政中心 | 7 | 2 | 1 | 16 | `smart_construction_core.menu_sc_hr_admin_center` |
| 产品配置 | 3 | 0 | 9 | 4 | `smart_construction_core.menu_sc_business_config_center` |

## 正式产品菜单结构

### 工作台

- formal_active: `4`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 数据总览 -> `sc.operating.metrics.project`
- 项目看板 -> `project.project`
- 待办事项 -> `sc.workbench.item`
- 消息通知 -> `mail.activity`

### 项目中心

- formal_active: `90`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 项目创建
  - 新项目立项 -> `project.project`
  - 项目信息编辑 -> `project.project`
  - 项目启停管理 -> `project.project`
- 客商管理
  - 客户档案 -> `res.partner`
  - 供应商档案 -> `res.partner`
  - 客商黑名单 -> `res.partner`
- 招投标管理
  - 招标信息 -> `tender.opportunity`
  - 投标项目 -> `tender.bid`
  - 标书管理 -> `tender.document`
  - 投标保证金 -> `tender.guarantee`
  - 中标管理 -> `tender.bid`
- 施工管理
  - 安全检查 -> `sc.safety.issue`
  - 质量验收 -> `sc.quality.acceptance`
  - 工程资料 -> `sc.project.document`
  - 施工日志 -> `sc.construction.diary`
  - 施工进度 -> `project.progress.entry`
  - 签证变更 -> `sc.site.variation`
- 劳务成本
  - 劳务实名制 -> `sc.labor.worker`
  - 劳务成本登记 -> `sc.labor.usage`
  - 劳务扣款明细 -> `sc.labor.deduction`
- 材料成本
  - 材料入库 -> `sc.material.inbound`
  - 材料出库 -> `sc.material.outbound`
  - 材料退货 -> `sc.material.supplier.return`
- 机械成本
  - 机械台班登记 -> `sc.equipment.usage`
- 分包成本
  - 分包成本登记 -> `sc.subcontract.register`
  - 分包签证费用 -> `sc.site.variation`
- 项目薪资
  - 薪资核算清单 -> `sc.hr.payroll.document`
  - 薪资发放登记 -> `sc.hr.salary.payment`
- 班组借/扣款
  - 班组借/扣款登记 -> `sc.expense.claim`

### 合同中心

- formal_active: `25`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 收入合同 -> `construction.contract.income`
- 支出合同 -> `construction.contract.expense`
- 合同变更 -> `sc.contract.change`
- 日常合同 -> `sc.general.contract`
- 收入结算 -> `sc.settlement.order`
- 日常合同结算 -> `sc.settlement.order`
- 支出结算 -> `sc.settlement.order`

### 成本中心

- formal_active: `18`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 项目预算 -> `project.cost.plan`
  - 预算清单 -> `project.cost.plan`
- 成本计划编制 -> `project.cost.plan`
- 成本归集 -> `project.cost.ledger`
- 项目盈亏分析 -> `project.profit.compare`

### 财务中心

- formal_active: `64`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 收款登记 -> `sc.receipt.income`
- 付款申请 -> `payment.request`
- 实付登记 -> `sc.payment.execution`
- 费用报销 -> `sc.expense.claim`
- 往来款登记 -> `sc.fund.account.operation`
- 公司收入 -> `sc.receipt.income`
- 公司支出 -> `sc.payment.execution`
- 公司&项目扣款 -> `sc.expense.claim`
- 公司&项目退款 -> `sc.expense.claim`
- 备用金 -> `sc.expense.claim`
- 资金汇总 -> `project.funding.baseline`

### 税务中心

- formal_active: `10`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 外经证 -> `sc.tax.certificate.registration`
- 预缴登记 -> `sc.invoice.registration`
- 开票申请 -> `sc.invoice.registration`
- 销项开票 -> `sc.invoice.registration`
- 发票红冲 -> `sc.output.invoice.adjustment`
- 进项发票 -> `sc.invoice.registration`
- 税额抵扣 -> `sc.tax.deduction.registration`
- 项目专项抵扣 -> `sc.tax.deduction.registration`
- 税务申报 -> `sc.invoice.registration`

### 会计账务中心

- formal_active: `3`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 日记账 -> `account.journal`
- 分析账户 -> `account.analytic.account`
- 分析分配模型 -> `account.analytic.distribution.model`

### 报表中心

- formal_active: `23`
- history_active_under_center: `0`
- system_config_active_under_center: `0`

- 项目报表 -> `sc.operating.metrics.project`
- 成本报表 -> `sc.comprehensive.cost.summary`
  - 库存统计表（新） -> `sc.material.stock.summary`
  - 进项发票明细表 -> `sc.invoice.registration`
  - 发票分析报表 -> `sc.invoice.registration`
  - 发票分类汇总表 -> `sc.invoice.category.summary`
  - 报销统计 -> `sc.expense.reimbursement.summary`
  - 工资统计表 -> `sc.salary.summary`
- 资金报表 -> `sc.fund.daily.summary`
- 税务报表 -> `sc.invoice.registration`
- 劳务分包报表 -> `sc.labor.usage`

### 行政中心

- formal_active: `7`
- history_active_under_center: `2`
- system_config_active_under_center: `1`

- 部门管理 -> `hr.department`
- 岗位管理 -> `hr.job`
- 证书管理 -> `sc.document.admin.document`
- 社保公积 -> `sc.hr.payroll.document`
- 工资薪酬 -> `sc.hr.payroll.document`
- 办公资产 -> `sc.office.admin.document`
- 制度文件 -> `sc.document.admin.document`

### 产品配置

- formal_active: `3`
- history_active_under_center: `0`
- system_config_active_under_center: `9`

- 表单配置 -> `ui.business.config.contract`
- 字段管理 -> `ui.form.field.policy`
- 数据权限 -> `ui.business.config.contract`

## 系统配置边界

| 边界入口 | active 子入口 | action 子入口 | XMLID |
| --- | ---: | ---: | --- |
| 智慧施工管理平台 / 产品配置 / 业务基础数据 / 业务分类字典 | 0 | 0 | `smart_construction_core.menu_sc_business_category` |
| 智慧施工管理平台 / 产品配置 / 业务基础数据 / 审批岗位人员 | 0 | 0 | `smart_construction_core.menu_sc_approval_scope` |
| 智慧施工管理平台 / 产品配置 / 业务基础数据 / 数据字典 | 0 | 0 | `smart_construction_core.menu_sc_dictionary` |
| 智慧施工管理平台 / 产品配置 / 业务基础数据 / 阶段要求配置 | 0 | 0 | `smart_construction_core.menu_sc_project_stage_requirement_items` |
| 智慧施工管理平台 / 产品配置 / 业务基础数据 / 预算类型 | 0 | 0 | `smart_construction_core.menu_sc_project_cost_code` |
| 智慧施工管理平台 / 产品配置 / 低代码系统配置 / 菜单配置 | 0 | 0 | `smart_construction_core.menu_ui_menu_config_policy_business_config` |
| 智慧施工管理平台 / 产品配置 / 流程审批配置 | 0 | 0 | `smart_construction_core.menu_sc_approval_policy` |
| 智慧施工管理平台 / 产品配置 / 系统参数 | 0 | 0 | `smart_construction_core.menu_sc_product_system_parameter_v1` |
| 智慧施工管理平台 / 产品配置 / 编码规则 | 0 | 0 | `smart_construction_core.menu_sc_product_numbering_rule_v1` |
| 智慧施工管理平台 / 系统管理（内部） | 19 | 17 | `smart_construction_core.menu_sc_config_center` |
| 智慧施工管理平台 / 行政中心 / 人员档案 | 0 | 0 | `smart_construction_core.menu_sc_runtime_user_management` |

### active 明细

- 智慧施工管理平台 / 产品配置 / 业务基础数据 / 业务分类字典 -> `sc.business.category`
- 智慧施工管理平台 / 产品配置 / 业务基础数据 / 审批岗位人员 -> `sc.approval.scope`
- 智慧施工管理平台 / 产品配置 / 业务基础数据 / 数据字典 -> `sc.dictionary`
- 智慧施工管理平台 / 产品配置 / 业务基础数据 / 阶段要求配置 -> `sc.project.stage.requirement.item`
- 智慧施工管理平台 / 产品配置 / 业务基础数据 / 预算类型 -> `project.cost.code`
- 智慧施工管理平台 / 产品配置 / 低代码系统配置 / 菜单配置 -> `ui.menu.config.policy`
- 智慧施工管理平台 / 产品配置 / 流程审批配置 -> `sc.approval.policy`
- 智慧施工管理平台 / 产品配置 / 系统参数 -> `ui.business.config.contract`
- 智慧施工管理平台 / 产品配置 / 编码规则 -> `ui.business.config.contract`
- 智慧施工管理平台 / 系统管理（内部）
- 智慧施工管理平台 / 系统管理（内部） / 定额字典
- 智慧施工管理平台 / 系统管理（内部） / 定额字典 / 专业 -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额字典 / 全部定额字典 -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额字典 / 四川定额导入 -> `quota.import.wizard`
- 智慧施工管理平台 / 系统管理（内部） / 定额字典 / 子目 -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额字典 / 定额项目 -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额字典 / 章节 -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额库
- 智慧施工管理平台 / 系统管理（内部） / 定额库 / 定额中心（左树右明细） -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额库 / 定额子目 -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额库 / 定额层级 -> `project.dictionary`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 -> `sc.norm.item`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 / 专业维护 -> `sc.norm.specialty`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 / 定额库 -> `sc.norm.item`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 / 定额库版本维护 -> `sc.norm.catalog`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 / 定额项维护 -> `sc.norm.item`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 / 导入定额 -> `sc.norm.import.wizard`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 / 章节维护 -> `sc.norm.chapter`
- 智慧施工管理平台 / 系统管理（内部） / 定额引擎 / 适用地区维护 -> `sc.norm.region`
- 智慧施工管理平台 / 行政中心 / 人员档案 -> `res.users`

## 用户配置边界

无。

## 历史验收边界

| 边界入口 | active 子入口 | action 子入口 | XMLID |
| --- | ---: | ---: | --- |
| 智慧施工管理平台 / 行政中心 / 油卡管理 / 充值登记 | 0 | 0 | `smart_construction_core.menu_sc_legacy_fuel_card_recharge_fact_acceptance` |
| 智慧施工管理平台 / 行政中心 / 油卡管理 / 油卡登记 | 0 | 0 | `smart_construction_core.menu_sc_legacy_fuel_card_fact_acceptance` |

### active 明细

- 智慧施工管理平台 / 行政中心 / 油卡管理 / 充值登记 -> `sc.fund.account.operation`
- 智慧施工管理平台 / 行政中心 / 油卡管理 / 油卡登记 -> `sc.fund.account.operation`

## 开发治理边界

| 边界入口 | active 子入口 | action 子入口 | XMLID |
| --- | ---: | ---: | --- |
| 平台内核 | 12 | 10 | `smart_core.menu_smart_core_platform_root` |
| 智慧施工管理平台 / 产品配置 / 工作流运行数据 / 工作流实例 | 0 | 0 | `smart_construction_core.menu_sc_workflow_instance` |
| 智慧施工管理平台 / 产品配置 / 工作流运行数据 / 工作流日志 | 0 | 0 | `smart_construction_core.menu_sc_workflow_log` |
| 智慧施工管理平台 / 产品配置 / 工作流运行数据 / 工作项 | 0 | 0 | `smart_construction_core.menu_sc_workflow_workitem` |
| 智慧施工管理平台 / 系统管理（内部） / 场景与能力 | 6 | 6 | `smart_construction_core.menu_sc_scene_root` |
| 智慧施工管理平台 / 系统管理（内部） / 工作流 | 1 | 1 | `smart_construction_core.menu_sc_workflow_root` |
| 智慧施工管理平台 / 系统管理（内部） / 项目管理（后台） | 0 | 0 | `smart_construction_core.menu_sc_project_manage` |

### active 明细

- 平台内核
- 平台内核 / 产品发布
- 平台内核 / 产品发布 / 产品策略 -> `sc.product.policy`
- 平台内核 / 产品发布 / 发布动作 -> `sc.release.action`
- 平台内核 / 产品发布 / 发布快照 -> `sc.edition.release.snapshot`
- 平台内核 / 产品发布 / 场景快照 -> `sc.scene.snapshot`
- 平台内核 / 公司访问
- 平台内核 / 公司访问 / 授权快照 -> `sc.entitlement`
- 平台内核 / 公司访问 / 用量统计 -> `sc.usage.counter`
- 平台内核 / 公司访问 / 统一登录路由 -> `sc.login.route`
- 平台内核 / 公司访问 / 订阅套餐 -> `sc.subscription.plan`
- 平台内核 / 公司访问 / 订阅实例 -> `sc.subscription`
- 平台内核 / 公司访问 / 运营任务 -> `sc.ops.job`
- 智慧施工管理平台 / 产品配置 / 工作流运行数据 / 工作流实例 -> `sc.workflow.instance`
- 智慧施工管理平台 / 产品配置 / 工作流运行数据 / 工作流日志 -> `sc.workflow.log`
- 智慧施工管理平台 / 产品配置 / 工作流运行数据 / 工作项 -> `sc.workflow.workitem`
- 智慧施工管理平台 / 系统管理（内部） / 场景与能力
- 智慧施工管理平台 / 系统管理（内部） / 场景与能力 / 交付包安装记录 -> `sc.pack.installation`
- 智慧施工管理平台 / 系统管理（内部） / 场景与能力 / 交付包注册表 -> `sc.pack.registry`
- 智慧施工管理平台 / 系统管理（内部） / 场景与能力 / 场景版本 -> `sc.scene.version`
- 智慧施工管理平台 / 系统管理（内部） / 场景与能力 / 场景编排 -> `sc.scene`
- 智慧施工管理平台 / 系统管理（内部） / 场景与能力 / 能力分组 -> `sc.capability.group`
- 智慧施工管理平台 / 系统管理（内部） / 场景与能力 / 能力目录 -> `sc.capability`
- 智慧施工管理平台 / 系统管理（内部） / 工作流
- 智慧施工管理平台 / 系统管理（内部） / 工作流 / 工作流定义 -> `sc.workflow.def`
- 智慧施工管理平台 / 系统管理（内部） / 项目管理（后台） -> `project.project`

## 混入正式中心的历史入口

这些入口仍挂在正式产品中心下，但分类属于历史验收。下一步应逐项决定：迁到用户验收/用户核对入口、转成正式产品入口，或隐藏。

| 中心 | 菜单 | 模型 | XMLID |
| --- | --- | --- | --- |
| 行政中心 | 智慧施工管理平台 / 行政中心 / 油卡管理 / 充值登记 | `sc.fund.account.operation` | `smart_construction_core.menu_sc_legacy_fuel_card_recharge_fact_acceptance` |
| 行政中心 | 智慧施工管理平台 / 行政中心 / 油卡管理 / 油卡登记 | `sc.fund.account.operation` | `smart_construction_core.menu_sc_legacy_fuel_card_fact_acceptance` |

## 正式中心下的隐藏历史残留

这些入口已经 inactive，不影响业务用户可见菜单，但仍挂在正式产品中心路径下。后续应逐项迁到历史验收/系统内部边界，或确认删除运行时承载入口。

| 中心 | 菜单 | 模型 | XMLID |
| --- | --- | --- | --- |
| 财务中心 | 智慧施工管理平台 / 财务中心 / 历史付款 | `sc.historical.payment.fact` | `smart_construction_core.menu_sc_historical_payment_fact` |
| 财务中心 | 智慧施工管理平台 / 财务中心 / 扣款税费核对 | `` | `smart_construction_core.menu_sc_expense_tax_adjustment_fact_group` |

## 收口信号

- 当前无待复核菜单。
- 当前无独立用户配置入口；产品配置中心属于正式产品，受保护的低代码与管理子项仍归入系统配置边界。
- `行政中心` 下存在非正式产品子入口：history=2 system=1，需要确认是否应继续对业务用户可见。
- `产品配置` 下存在非正式产品子入口：history=0 system=9，需要确认是否应继续对业务用户可见。
- 共 `2` 个历史入口混在正式产品中心下，建议作为下一轮菜单收口清单。
- 共 `2` 个 inactive 历史入口仍挂在正式产品中心路径下，建议后续迁出正式中心。
