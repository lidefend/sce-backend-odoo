# 付款闭环业务事实差距表（2026-11-06）

基线：PR #813 集成后的 main `f79d29f55a22d6dbaec778237fbf710a12b6f4b3`。只核对“付款申请 → 审批 → 支付执行 → 状态回写”，不扩展到全模块。源码调用关系与配置能力已核对；完整付款写入闭环尚未在指定测试记录上执行，不能将表内能力登记记作业务验收。

| 环节 | 事实来源 | 正式维护入口 | 生效与执行消费者 | 差距及最小处理 |
|---|---|---|---|---|
| 申请与提交 | `payment.request` 及关联的项目、合同、资金与结算事实 | 付款申请原生表单 `view_payment_request_pay_form` | `payment_request.py::action_submit` 校验权限、范围和前提；锁资金/结算范围，写提交状态、审计，再调用 `_route_submitted_approval` | 业务输入已有正式载体。资金约束、锁、事务和审计保留模型，不做配置替代 |
| 是否审批、审批模式 | 当前公司适用的 `sc.approval.policy` | **系统参数变更集**：`menu_sc_product_system_parameter_v1` / `action_sc_product_system_parameter_v1`，载体 `ui.business.config.change.set` | `product_system_parameter_change.py::_payment_approval_policy/_approval_mode_from_policy`；发布/回滚修改公司政策，必要时复制共享政策与步骤 | 修正维护指引：付款申请模式不应在审批政策表单随意写。`approval_policy.py::write` 对非 sudo 有明确约束；已有入口，不新建开关 |
| 审批人员、步骤、金额范围 | `sc.approval.policy/step` | `action_sc_approval_policy`、`menu_sc_approval_policy`、`view_sc_approval_policy_form` | `get_active_policy` 先当前公司后共享；`_tier_definition_domain/_tier_definition_vals` 投影顺序、组与金额边界 | 日常岗位/步骤/上下限调整已有配置。申请使用 `amount`、执行使用 `paid_amount` 是业务含义，保留代码，不开放任意字段替换 |
| 实际审批与批准 | `tier.definition` 是政策投影，`tier.review` 是审批实例 | 规则维护仍从审批政策进入；审批意见从当前单据办理 | `_start_submission_review`；`payment_request.action_approval_decision/_complete_payment_approval` 检查当前审批资格与实例；自动批准要求私有提交 token | 在途实例不能被后来政策改动绕过。自动通过文案把“显式无需审批”误说成“未配置审批”，本批只修审计解释，不改执行分支 |
| 申请转付款登记 | 已批准的申请、业务锚点与付款关联 | `payment.request.action_create_payment_execution`；`menu_sc_payment_execution` / `action_sc_payment_execution_actual_outflow` | `_assert_payment_execution_ready` 校验后给出动作与上下文；`sc.payment.execution.create` 校验、规范化关联 | 已有能力，无需新载体；前端消费声明，不按模型自行推断目标 |
| 登记确认及审批 | `sc.payment.execution` 与其独立审批政策/步骤 | 原生付款执行表单 `view_sc_payment_execution_form` 与审批规则入口 | `action_confirm` 检查财务办理、锚点、范围、责任后调用政策服务；`action_on_tier_approved` 接收完整 validated 实例 | 申请通过不代表执行自动免审批。财务办理能力组与审批执行组职责不同，不合并成一套权限配置 |
| 实付、回写与台账 | 执行记录的 `paid_amount`、付款关联、实际台账 | 实付登记动作；状态由模型派生，不设手工 done 配置 | `action_paid` 锁申请、验历史付款身份、confirmed 状态及审批；`_sync_payment_request_done`、`payment.request._ensure_payment_ledger/_compute_payment_totals` 防超付、建台账、计算足额并审计 | 部分支付与足额支付有不同结果。精度、幂等、锁、汇总及状态一致性必须留模型 |
| 页面状态和动作 | 原生按钮、表单政策及 `workflow_contract_service.PROFILE_BY_MODEL` | 已有表单配置与契约；动作执行从服务端模型进入 | `_available_actions` 按状态、审批实例、can_review 及证据门禁投影，执行时再授权 | 状态映射、动作方法与部分组织仍硬编码；本轮未证明具体显示错误，不直接删除映射。后续用指定测试记录对照声明与真实执行 |

## 源码依据

路径前缀均为 `addons/smart_construction_core/`：

- [付款申请提交与审批路由](../../addons/smart_construction_core/models/core/payment_request.py#L3286)、[批准及审计](../../addons/smart_construction_core/models/core/payment_request.py#L3656)。
- [公司审批政策选择与投影](../../addons/smart_construction_core/models/support/approval_policy.py#L345)、[付款申请审批参数的维护边界](../../addons/smart_construction_core/models/support/approval_policy.py#L982)。
- [系统参数变更](../../addons/smart_construction_core/services/product_system_parameter_change.py#L39)。
- [付款执行确认、实付与回写](../../addons/smart_construction_core/models/core/payment_execution.py#L859)。
- [页面动作投影](../../addons/smart_construction_core/models/support/workflow_contract_service.py#L1360)。

## 本批最小修改与不变边界

将自动通过原因表述为“当前适用规则无需审批”，覆盖没有适用政策和适用政策明确关闭审批两种情况；不改变状态、条件、审批实例、权限或事务。其余已支持的规则不盲目改配置：尚无新的审批模式、执行岗位或金额阈值需求，应保留现有事实。

开发库已完成的支付入口运维与本批分离：菜单 339、动作 908、公司 1、`demo_role_finance`，有效快照 12，`payment.capital` 已启用、豁免为 False。前端实看仍由前端完成；实际支付/撤销只用明确指定的测试记录，不改现有六条业务记录。

下一步有价值的验证：同一公司、同一指定测试申请，追踪系统参数发布模式 → 步骤适用 → review 实例 → 部分支付/足额支付回写。未执行前不声称 BE-04/05 或整条写入闭环已验收。
