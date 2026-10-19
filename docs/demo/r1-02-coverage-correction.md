# R1-02 覆盖清单六项误判纠正与 43 项逐入口分类

> 依据 DEMO-R1-01 dispatcher-review.md。对 43 项缺口逐入口区分：
> 业务持久·待运行态回读 / 计算投影·隐式供给 / 会计原生 / 产品配置入口 /
> 专业委托视图 / 无模型聚合入口。运行态一律 not_run。

## 纠正一：86/43 是静态线索，不是已证实覆盖或缺口

- coverage.json 的 86 项「seed_covered」只证明菜单模型集合与 demo XML model 引用存在
  交集，未证明运行时记录存在、可读或已办理。
- 43 项「gap」按模型性质逐入口分类（见下），其中报表/分析/会计原生/配置入口并非都能
  机械补种子；需运行态回读确认，不能把「静态交叉未命中」当作「产品缺陷」。
- 90 standard / 129 preview 是菜单策略声明数，不是「当前已发布能力数」；发布态与
  声明态分开标注，current_runtime 保持 not_run。

## 纠正二：7 棵工作树不等于 7 棵活跃写入树

- git worktree list 的 7 棵为历史交接/部署/同步树，旧调度已停止，不要求退役或破坏证据。
- 本轮复用 local-env 单棵产品写入树；主仓只读；不新建工作树。

## 纠正三：不填写 PostgreSQL 用户 odoo 冒充数据库治理职责

- 数据库角色/TENANT/filestore 身份未决即 SAFE_STOP；本轮不授权猜测身份落库。
- local sc_dev_demo 与 daily sc_demo 的 filestore/tenant 身份不得混填。

## 纠正四：local.dev.rebuild_demo 不是数据库回滚

- 恢复入口必须精确核实；本轮不落库，也不以重建代替恢复。
- 恢复/快照入口仅登记待核实，不宣称已具备恢复点。

## 纠正五：XX/某公司不满足自然中文

- 本批将占位式名称替换为完整虚构名称并登记合成来源（见 r1-02-realistic-core-chain.md §1）。

## 纠正六：action 脚本以角色调用只证明后端动作

- 后端 action 调用不是浏览器真实办理；真实 UI 办理留后续验收，当前 not_run。

## 43 项逐入口分类

分类口径与 DEMO-R1-01 的静态交叉清单一一对应（覆盖项见 R1-01 coverage.json.gaps）：

### A. 业务持久模型 · 待运行态回读（23）

这些是真实业务模型（persistent），静态交叉未证明有无样例；是否已有业务种子/计算供给需
Odoo 运行态探针回读，本批不落库，故归 not_run。

| # | 组 | 入口 | 模型 |
|---|----|------|------|
| 4 | 项目中心 | 招标信息 | tender.opportunity |
| 5 | 项目中心 | 标书管理 | tender.document |
| 6 | 项目中心 | 质量验收 | sc.quality.acceptance |
| 7 | 项目中心 | 签证变更 | sc.site.variation |
| 8 | 项目中心 | 劳务实名制 | sc.labor.worker |
| 9 | 项目中心 | 劳务扣款明细 | sc.labor.deduction |
| 10 | 项目中心 | 材料退货 | sc.material.supplier.return |
| 11 | 项目中心 | 分包签证费用 | sc.site.variation |
| 12 | 项目中心 | 薪资发放登记 | sc.hr.salary.payment |
| 13 | 项目中心 | 班组借/扣款登记 | sc.team.loan.deduction.workspace |
| 16 | 合同中心 | 合同变更 | sc.contract.change |
| 17 | 成本中心 | 项目预算 | project.cost.plan |
| 18 | 成本中心 | 成本计划编制 | project.cost.plan |
| 20 | 财务中心 | 往来款登记 | sc.current.account.workspace |
| 21 | 财务中心 | 公司&项目退款 | sc.company.project.refund.workspace |
| 22 | 税务中心 | 外经证 | sc.tax.certificate.registration |
| 23 | 税务中心 | 税务申报 | sc.tax.filing |
| 30 | 报表中心 | 税务报表 | sc.tax.filing |
| 33 | 行政中心 | 办公资产 | sc.office.asset |
| 39 | 项目中心 | 质量整改 | sc.quality.rectification |
| 40 | 项目中心 | 质量复验 | sc.quality.recheck |
| 41 | 项目中心 | 安全整改 | sc.safety.rectification |
| 42 | 项目中心 | 安全复验 | sc.safety.recheck |

### B. 计算投影/汇总模型 · 隐式供给（6）

`_auto=False` 投影/汇总模型，由业务事实计算供给；其中两个在 `INTENTIONALLY_EMPTY_MODELS`
（可选投影需租户事实提供方）为「空即正确」。需运行态确认，非演示种子缺口。

| # | 组 | 入口 | 模型 | 备注 |
|---|----|------|------|------|
| 2 | 工作台 | 数据总览 | sc.operating.metrics.project | 可选投影 |
| 27 | 报表中心 | 项目报表 | sc.operating.metrics.project | 可选投影 |
| 19 | 成本中心 | 项目盈亏分析 | project.profit.compare | 投影 |
| 28 | 报表中心 | 成本报表 | sc.comprehensive.cost.summary | 可选投影，空即正确 |
| 29 | 报表中心 | 资金报表 | sc.fund.daily.summary | 可选投影，空即正确 |
| 31 | 报表中心 | 劳务分包报表 | sc.labor.subcontract.report | 投影 |

### C. 会计原生/基础设施（6）

原生 account/HR/序列/消息模型，由系统动作或原生主数据供给，非「演示种子缺失」。

| # | 组 | 入口 | 模型 |
|---|----|------|------|
| 3 | 工作台 | 消息通知 | mail.notification |
| 24 | 会计账务中心 | 日记账项目 | account.move.line |
| 25 | 会计账务中心 | 分析账户 | account.analytic.account |
| 26 | 会计账务中心 | 分析分配模型 | account.analytic.distribution.model |
| 32 | 行政中心 | 岗位管理 | hr.job |
| 38 | 产品配置 | 编码规则 | ir.sequence |

### D. 产品配置/低代码管理入口（5）

配置/管理表面，有意为空或由管理员配置；不是演示业务样例缺口，不补业务种子。

| # | 组 | 入口 | 模型 | 备注 |
|---|----|------|------|------|
| 34 | 产品配置 | 表单配置 | ui.business.config.contract | 低代码配置 |
| 35 | 产品配置 | 流程审批配置 | sc.approval.policy | 配置 |
| 36 | 产品配置 | 字段管理 | ui.form.field.policy | 无覆盖即安全默认 |
| 37 | 产品配置 | 系统参数 | sc.product.system.settings | 配置 |
| 43 | 产品配置 | 菜单配置 | ui.menu.config.policy | 配置；关联 F01 |

### E. 专业委托视图 · 由主合同样本隐式供给（2）

`construction.contract.income` / `.expense` 通过 `_inherits` 委托 `construction.contract`；
本批已补 `sc_demo_contract_out_010`（type=out）。静态交叉按菜单 model 字面未命中，但运行时
委托视图会展示同一主合同记录。需运行态确认，非缺失。

| # | 组 | 入口 | 模型 |
|---|----|------|------|
| 14 | 合同中心 | 收入合同 | construction.contract.income |
| 15 | 合同中心 | 支出合同 | construction.contract.expense |

### F. 无模型聚合入口（1）

| # | 组 | 入口 | 模型 |
|---|----|------|------|
| 1 | 工作台 | 角色首页 | （无 res_model，聚合/动作首页） |

## 可复算汇总

| 分类 | 数量 | 处置 |
|------|-----:|------|
| A 业务持久·待运行态回读 | 23 | not_run，需 Odoo 探针确认样例 |
| B 计算投影·隐式供给 | 6 | not_run，计算/可选投影供给 |
| C 会计原生/基础设施 | 6 | 原生供给，非种子缺口 |
| D 产品配置/低代码管理入口 | 5 | 有意为空/管理员配置 |
| E 专业委托视图 | 2 | 由主合同样本隐式供给，需回读 |
| F 无模型聚合入口 | 1 | 角色聚合页，无模型 |
| **合计** | **43** | |

23 + 6 + 6 + 5 + 2 + 1 = 43，与 coverage.json.gaps 逐项一一对应，无遗漏、无重复。

## 实际受影响键（本批增量）

- 工作台/项目台账/项目看板：项目与客户名称展示受影响。
- 合同中心（收入合同）：sc_demo_contract_out_010 及明细。
- 收款申请/付款申请：sc_demo_pay_req_010_001、sc_demo_payment_020_001、
  sc_demo_pay_req_030_001。
- 结算单：sc_demo_settlement_020_001、sc_demo_settlement_030_001、
  sc_demo_settlement_030_bad_001 及其明细。

未受影响键不重跑；运行态覆盖仍为 not_run。

## 用户反馈缺口记录（F01–F05）

状态：F01–F04 待复现，无修复/验收；F05 已在本批落实。四组反馈不取代 Demo 主线，按是否
阻断当前用户路径插入；跨层项仅登记，不擅自修改产品层。

| 编号 | 现象 | 对应 43 入口 | 归属层 | 本批处置 |
|------|------|-------------|--------|---------|
| F01 | 业务全能角色不可见 产品配置→菜单配置 | #43 菜单配置 | 跨层（能力声明/发布过滤/消费） | 仅登记；禁止角色名推定授权，禁止前端强显 |
| F02 | 工作台项目看板项目状态英文 | 工作台 角色首页/数据总览 | 跨层（声明→翻译→渲染） | 仅登记；不硬编码映射 |
| F03 | 项目台账卡片经营方式非中文、状态中英混杂 | 项目中心 | 跨层（声明→翻译→渲染） | 仅登记；不硬编码映射 |
| F04 | 工作台项目看板与项目中心台账功能重叠，项目表单未收敛 | 工作台/项目中心 | 跨层（菜单职责/表单职责） | 仅登记；对照用户任务/契约/页面职责，不擅删菜单 |
| F05 | 主样本适用字段/明细/附件/负责人/日期金额/关联需尽量完整 | 本批种子范围 | P4 演示种子 | 已处理：补齐经办人/日期/币种/结算期间/录入人，不适用与尚未发生项写明理由（见 chain §字段完整性） |

跨层项（F01–F04）给总调度的精确修复建议：
- F01：核对 `ui.menu.config.policy` 菜单的能力声明、发布过滤与实际消费三段的身份；
  以运行时 capability closure 回读为准，不凭角色名推定授权。
- F02/F03：定位经营方式/项目状态字段的声明翻译与前端渲染，统一走契约翻译表，不在
  前端硬编码映射。
- F04：先对照用户任务、契约与页面职责给出收敛结论，再决定是否调整菜单/表单；禁止
  未经批准删除菜单。
