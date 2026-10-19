# R1-02 项目—合同—结算/付款真实中文种子增量

> 批次记录（living record）。性质：本地代码增量与离线定向验证，不做运行态验收。
> 运行态/UI 一律 `not_run`；禁止以静态种子冒充业务办理或终态审批。

## 0. 身份与边界

- 分支：feature/demo-r1-realistic-data-20261019
- 基线：76aa6705685d60ca00b12184f0e1c8aa64a571a7
- Formal Product Layer：P4（demo delivery carrier）
- Layer Target：smart_construction_demo 种子场景链
- Module：smart_construction_demo
- 归属理由：演示数据是演示交付载体的种子层职责，不承载 P0/P1 产品语义。
- 不改：smart_core、smart_construction_core、前端、用户模块、Makefile、compose、凭据、数据库。
- 明确排除：运行态落库、部署、审批终态伪造、附件伪造、对暂停专题（用户模块/平台首页闭环）的任何恢复。

## 1. 合成来源登记

以下企业/人员/项目名称为系统合成的虚构演示数据，不对应任何真实企业或个人：

- 自身演示公司：Demo演示公司（所有者既定演示身份，沿用）。
- 业主/客户：德阳市高新智造产业投资有限公司（虚构）。
- 商砼供应商：德阳蜀新商砼有限公司（虚构）。
- 钢材供应商：德阳蓉钢供应链有限公司（虚构）。
- 通用合同相对方：四川恒立建设工程有限公司（虚构）。
- 通用业主：德阳新科置业发展有限公司（虚构）。
- 通用供应商：成都聚力物资供应有限公司（虚构）。
- 项目：德阳智能制造产教融合项目（虚构项目名，沿用既有 XMLID）。

## 2. 核心链（按用户顺序，起始态）

谁发起 → 前置 → 动作 → 结果 → 下一步：

1. 项目经理 pm1：客户档案已建立 → 项目立项（既有 sc_demo_project_001）。
2. 合同管理员 ct1：项目已立项、客户档案存在 → 新建收入合同
   sc_demo_contract_out_010「德阳智能制造产教融合项目施工总承包合同」，
   两条明细：主体结构工程 18,600,000.00 + 机电安装工程 8,000,000.00，
   未税合计 26,600,000.00（draft，未强写确认/审批）。
3. 财务 fin1：合同为 draft 且已关联项目/客户 → 发起收款申请
   sc_demo_pay_req_010_001（5,000,000.00，依据合同付款条款）。
4. 成本/财务：依据形象进度编制收入结算单 sc_demo_settlement_020_001
   （结算金额 5,000,000.00，两条明细 3,000,000.00 + 2,000,000.00，draft）。
5. 财务 fin1：依据结算单发起收款申请 sc_demo_payment_020_001，并通过
   settlement_id 回链结算单。
6. s30 工作流样本 sc_demo_settlement_030_001（1,000,000.00）与
   sc_demo_settlement_030_bad_001（0.00，保留 draft 供门禁验证）。

上述记录全部保持模型默认 draft，真实办理由后续 R1-03 通过正式 action +
真实审批 tier 推进；禁止直接写 state。

### 2.1 结算审批前置（S20/S30 收款申请）

S20/S30 收款申请（sc_demo_payment_020_001 / sc_demo_pay_req_030_001）通过
settlement_id 回链的结算单在本批均为 draft，该回链仅代表「数据关联准备」，不代表可以
提交或审批。真实前置按 payment.request._check_settlement_state（
addons/smart_construction_core/models/core/payment_request.py:1993）与 settlement_id
域约束（state=approve）：

1. 结算办理角色（user_sc_settlement_user_cap）提交结算单（sc.settlement.order.action_submit）；
2. 结算审批座位（sc.approval.policy 复核 + validate_tier，座位见
   scenario_loader._DEMO_APPROVAL_ACTORS）把结算单推进到 approve/done；
3. 财务经办 fin1（user_sc_fin_01）在结算单 approve/done 后发起收款申请草稿；
4. 收款申请按付款申请四段审批（财务经办确认 → 项目负责人审核 → 财务审核 → 管理层终审）推进。

本批不落库、不伪造审批终态；上述动作留 R1-03 受管运行态按真实角色办理。

## 2.2 主样本字段完整性核对（F05）

逐项核对本批主样本的适用字段、负责人、日期、明细与关联；不适用/尚未发生/附件缺失写明理由：

| 主样本 | 已声明字段 | 负责人 | 日期 | 明细/关联 | 未填与理由 |
|--------|-----------|--------|------|-----------|-----------|
| sc_demo_contract_out_010（合同） | subject/name_short/type/project/partner/currency/date_contract/date_start/date_end/handler_id/note | handler_id=合同管理员 ct1 | 订立 2025-02-01，开工 2025-03-01，竣工 2025-12-31 | 两条明细（主体结构 18,600,000.00 + 机电安装 8,000,000.00） | tax_id 不显式声明（默认税率机制在运行态解析，not_run）；attachment_ids 不伪造；合同变更/发票/收款累计等执行结果尚未发生不填 |
| sc_demo_pay_req_010_001（收款申请，合同依据） | type/project/contract/partner/currency/amount/date_request/note | 申请人由 create_uid 记录，种子不声明；真实办理由 fin1 发起 | date_request 2025-04-01 | 关联合同（payment_basis_type=contract），无结算单 | 无结算依据（合同依据口径）；附件不伪造；审批/支付结果尚未发生不填 |
| sc_demo_settlement_020_001（结算单） | name/title/project/contract/partner/currency/settlement_type/settlement_amount/period_start/period_end/date_settlement/document_date/entry_user_id/description | entry_user_id=结算办理角色 | 结算期间 2025-03-01→03-31，结算日 2025-03-31 | 两条明细 3,000,000.00 + 2,000,000.00 | 申报/审定/付款日期与金额尚未发生不填；附件不伪造 |
| sc_demo_payment_020_001（收款申请，结算依据） | type/project/contract/settlement/partner/currency/amount/date_request/note | 同上，真实办理 fin1 | date_request 2025-04-01 | settlement_id 回链结算单（draft 准备数据） | 提交前置=结算单 approve/done（§2.1）；附件不伪造 |
| sc_demo_settlement_030_001（结算单） | 同 020 + period/entry_user | entry_user_id=结算办理角色 | 结算期间 2025-04-01→04-05 | 一条明细 1,000,000.00 | 同 020 未填理由 |
| sc_demo_settlement_030_bad_001（门禁样本） | name/project/contract/partner/currency/settlement_type/settlement_amount=0 | 无（故意不完整门禁样本） | 无（故意） | 无明细/无付款关联 | 故意保留不完整，供门禁验证，不补值 |
| sc_demo_pay_req_030_001（收款申请，结算依据） | type/project/contract/partner/currency/amount/date_request/settlement/note | 同上 | date_request 2025-04-06 | settlement_id 回链（draft 准备数据） | 提交前置=结算单 approve/done（§2.1） |

公司/人员/项目名称均为合成虚构（§1）。附件一律不伪造：本批无 ir.attachment 记录，相关
attachment_ids 留空并在上面记录理由；尚未发生的结果（审批、支付、审定、发票）一律不填值。

## 3. 静态缺陷修正（本批）

- 结算单不再写入计算字段 amount_total 与只读字段 payment_request_ids；
  改为写入可编辑 settlement_amount，结算明细只写 qty/price_unit（amount 由计算给出）。
- 结算明细金额 = 数量 × 单价，与结算金额一致。
- s20 场景文件顺序调整为「结算单 → 收款申请 → 结算明细」，使收款申请能通过
  settlement_id 回链先加载的结算单。
- 主合同链日期自洽：以合同开工 2025-03-01 为锚点，首期形象进度形成于 2025 年 3 月；
  S10 收款申请 date_request 调整为 2025-04-01，S20 结算期间调整为 2025-03-01→03-31
  （结算日/单据日 2025-03-31），S20 收款申请 2025-04-01；S30 月度结算顺延为
  2025-04-01→04-05（结算日 2025-04-05），S30 收款申请 2025-04-06。进度描述同步
  写明「2025年3月形成/完成形象进度」，不再出现早于开工的申请与结算。

## 4. 验证

实际命令与结果（dirty 阶段，非冻结候选）：

- L1 `make ci.local.iteration`：PASS change_state=dirty coverage=L1_only receipt=none；
  变更路径全部在 run scope 内，outside_scope=[]，并标记两条 L2 为 stale 需重跑。
- L2 `make verify.demo.supplemental.unit`：Ran 80 tests，OK（新增
  test_core_chain_dates_are_cross_record_consistent 跨记录日期关系断言，并将原固定
  日期字面断言改为解析后断言日期关系）。
- L2 `make verify.demo.lifecycle.unit`：Ran 30 + 5 + 80 = 115 tests，OK。
- XML 良构校验：本批 10 个 XML 全部可被 stdlib xml.etree 解析。
- 占位符扫描：企业/人员名不再含 某/XX/示例/测试；仅项目描述内部保留「各有一条示例」
  （非实体名称，见 data/base/20_projects.xml，未在本次实体命名范围）。
- F01–F05 缺口记录已并入 r1-02-coverage-correction.md（43 项逐入口分类 + 可复算汇总）；
  跨层项 F01–F04 仅登记，F05 在本批落实（见 §2.2 字段完整性核对）。

运行态/UI：not_run（本执行器不可导入 Odoo，本批不落库、不部署）。

## 5. 回滚

git 工作树保留 dirty，不回退他人工作；回滚即丢弃本批未提交文件（基线 HEAD 为
76aa6705685d60ca00b12184f0e1c8aa64a571a7）。

## 6. 未验证项

- 结算单/收款申请在 Odoo convert 下是否零缺陷装载：not_run（需受管运行态）。
- settlement_id 反向链接与 computed amount 的真实取值：not_run。
- 浏览器 UI 真实办理：not_run（后续验收）。
