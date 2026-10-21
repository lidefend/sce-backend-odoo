# 产品能力迭代 V2 · Batch 7 批次记录（2026-10-20）

## 边界声明

- Formal Product Layer：P1（施工行业标准产品），运行时承载 P3（低代码配置/变更集）。
- Layer Target：`smart_construction_core`（参数目录、审批策略、付款申请动作面）。
- Module：`smart_construction_core`（本批不触碰 `smart_core`、`smart_construction_custom`、`frontend` 产品语义）。
- Standard vs User-Specific：行业标准默认值 + 运行时配置；不含客户专属偏好。
- Why Here：`approval_mode` / `default_payment_terms` 是施工行业标准业务规则，
  值域、影响预览、变更集、审计与回滚由 P1 声明并落到 `res.company` 权威字段；
  审批提示/组织负责人路由/金额范围条件由 `tier.review` 与 `sc.approval.policy` 的
  `APPROVAL_SCOPE_*` 声明驱动。
- Why Not Elsewhere：不得在 `smart_core` 写行业语义；不得在前端按参数名硬编码审批分支；
  不得直写 `ir.config_parameter`。
- Blast Radius：参数目录投影、受控参数发布/回滚、付款申请可用动作与审批提示；
  验证以参数服务/守卫/定向测试 + 受管运行时冒烟收口。

## 本批目标（单一目标）

让 `approval_mode` 与 `default_payment_terms` 走通
「声明 → 服务端值域校验 → 影响预览 → 变更集发布 → 审计 → 回滚」纵向闭环；
随后把审批岗位提示与组织负责人路由从静态 `_ACTION_ROLE_HINTS` 改为 `tier.review` 驱动。

## 范围

- `config/product_system_parameter_catalog_v1.json`（与模块副本保持逐字节一致）
- `addons/smart_construction_core/data/product_system_parameter_catalog_v1.json`
- `addons/smart_construction_core/models/support/res_company.py`
- `addons/smart_construction_core/services/product_system_parameter_change.py`
- `addons/smart_construction_core/handlers/product_system_parameter_catalog.py`
- `addons/smart_construction_core/tests/test_product_system_parameter_catalog_service.py`
- `addons/smart_construction_core/tests/test_product_system_parameter_change.py`
- 本记录文件

## 不做

- 不修改 demo 工作树、demo timer、reset、数据清理或体验重置实现。
- 不新增数据库/租户/Compose/凭据/生产权限。
- 不直写 `ir.config_parameter`，不暴露密钥/数据库地址/认证信息。
- 不合并 main；Batch 12 与用户验收完成前不发布候选。
- 本批第一个子步不接入 `tier.review` 审批提示替换（列为下一子步）。

## 阶段身份

- Branch：`feature/product-iteration-v2-20261020`
- Baseline main：`74063688e928d25c8e65037ac3306956c954244d`
- 交接起点 HEAD：`da3d84ed17dad608691730dccefc25fac0df7978`（clean，计划提交）
- Run：`.agent/runs/PRODUCT-ITERATION-V2-20261020/run.json`（planned → active）

## 回滚

- 回退本批 commit；参数变更记录保留审计。
- 参数值回滚走 `sc.product.system.parameter.rollback`，恢复发布前 `previous_value`。

## 验证结果（子步 1：参数声明 + 校验 + 影响预览 + 变更集）

| 层级 | 命令 | 状态 | 测试数 |
|---|---|---|---|
| L0 | 身份预检（分支/HEAD/clean） | passed | - |
| L1 | `python3 -m py_compile`（变更 .py） | passed | - |
| L1 | `make ci.local.iteration` | passed | 47 |
| L1 | `make verify.agent.ledger.unit` | passed | 18 |
| L2 | `make verify.docs.product_boundary` | passed | 7 |
| L2 | `make verify.product_system_parameter_catalog` | passed | 23（guard 8 + service 15） |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core`（CODEX_NEED_UPGRADE=1） | passed | - |
| L3 | `make verify.product_system_parameter_change` | passed | 9 post-tests |

- `config/…/product_system_parameter_catalog_v1.json` 与模块副本逐字节一致。
- `approval_mode` / `default_payment_terms` 已声明 available，权威字段分别为
  `res.company.sc_approval_mode`、`res.company.sc_default_payment_terms`；
  发布写公司权威字段并记录 `sc.product.system.parameter.change`，回滚恢复 `previous_value`。

## 验证结果（子步 2：审批提示改为 tier.review 驱动）

| 层级 | 命令 | 状态 | 测试数 |
|---|---|---|---|
| L1 | `python3 -m py_compile`（handler + 2 测试文件） | passed | - |
| L1 | `make ci.local.iteration` | passed | 47 |
| L3 | `make local.dev.test … TEST_TAGS=payment_request_available_actions_backend` | passed | 8 post-tests |
| L3 | `make local.dev.test … TEST_TAGS=payment_request_action_surface_backend` | passed | 6 post-tests |
| L3 | `make local.dev.test … TEST_TAGS=/smart_construction_core:TestP1PaymentRequestCapability.test_available_actions_use_model_capabilities_not_role_names` | passed | 1 post-test |

- 删除静态 `_ACTION_ROLE_HINTS`；approve/reject 岗位事实取自待审 `tier.review` 的
  `reviewer_group_id`，经 `sc.approval.policy` 的 `APPROVAL_SCOPE_*` 映射为岗位键与标签；
  无待审实例时回退到策略首个启用步骤/默认审批岗位；submit/done 用其声明的授权能力组 +
  对应组织岗位标签。
- 修复真实 ACL 回归：策略查询补 `sudo()`（与既有 `_next_state_hint` 的配置投影口径一致），
  普通业务用户不再因 `sc.approval.policy` 不可读而 AccessError。
- 未覆盖：`approval_mode` / `default_payment_terms` 的业务链消费接线、前端消费、浏览器验收
  （`not_run`）。

## 下一步

- 子步 3：把 `approval_mode`、`default_payment_terms` 接进业务链（`approval_mode`
  到付款申请审批策略的语义映射；`default_payment_terms` 到新建单据默认付款条件的映射），
  再进入前端消费与浏览器验收。

## 验证结果（子步 3：参数业务链消费接线）

| 层级 | 命令 | 状态 | 测试数 |
|---|---|---|---|
| L1 | `python3 -m py_compile`（变更 .py） | passed | - |
| L1 | `make ci.local.iteration` | passed | 47 |
| L2 | `make verify.product_system_parameter_catalog` | passed | 23 |
| L1 | `make verify.agent.ledger.unit` | passed | 18 |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core`（CODEX_NEED_UPGRADE=1） | passed | - |
| L3 | `make verify.product_system_parameter_change` | passed | 11 post-tests |

- `approval_mode` 改为直接背书 `payment.request` 审批策略：disabled→`none`、
  single→`single`、multi→`linear`（`approval_required` 同步），发布写策略、回滚恢复策略；
  移除 `res.company.sc_approval_mode` 占位字段，目录权威改为 `sc.approval.policy`。
- `default_payment_terms` 经 `services/default_payment_terms.py` 映射到真实
  `account.payment.term`（net30→30 Days、net60→新增 60 Days、advance→Immediate、
  custom→无默认），新采购单 `payment_term_id` 默认取自公司参数。
- 未覆盖：前端消费与浏览器验收（`not_run`）。

## 下一步

- 子步 4：前端配置工作台/参数目录只消费声明、付款申请动作面消费 `tier.review` 岗位事实，
  浏览器验收「配置→影响预览→变更集发布→付款申请链实际生效→回滚恢复→无权限拒绝」；
  Batch 12 与用户验收完成前不合并 main。

## 验证结果（子步 4：付款链浏览器验收通过）

`make verify.local.dev.payment_request.full_chain` PASS：登录 → 创建 → 提交 →
审批链逐级通过 → 付款执行（创建/提交/审批/登记付款）→ 台账 posted 对账 →
重复回放守卫 → 390px 无横向溢出。

车道收口期间发现并修复一个真实 P1 契约缺口：`smart_construction_core` 正式列表锁的
`preference_policy` 缺少 `allow_width`，前端 fail-closed 报 `ContractGapError`；
已在声明层补齐（`core_extension.py`）。

历史子步状态：上述实现和当时付款链通过，不代表参数变更后的付款链验收完成；以 run.json 与下方续跑复核为准。

## 验证结果（子步 4：浏览器验收车道修复）

- 已修复（P4 车道工具，分别提交）：`local_dev_payment_request_full_chain.sh`
  缺 `/t/demo` 命名空间前缀；`local_dev_demo_credentials_prepare.sh` 的固定凭据
  与 demo 种子发布的 `123456` 不一致；`local_dev_payment_request_floorplan_submit.mjs`
  的 S69 项目与合作伙伴 fixture 标签过期（PR #689 重组后改名）。
- 当前阻塞（`validation_tool_defect`，非本批产品问题）：前端 Select 选项的可访问名称
  已变为拼接串（`S69-PAY-2025-001支付台账项目OdooBotin_progress是`），车道共享的
  `chooseUniqueRelationOption` 仍用 `getByRole('option', { name, exact: true })` 精确匹配
  纯名称，定位失效。
- 待办：将 `chooseUniqueRelationOption` 与当前前端 Select 渲染对齐后再重跑浏览器验收。

## 验证结果（子步 4：车道连续修复，持续到登录/创建/状态变体）

- 继续修复并重跑，车道已能走通：登录 → 创建付款申请（id=469）→ 状态变体只读校验。
- 已修复（分别提交）：inline 下拉按名称搜索（项目查询由编码 `S69` 改为名称
  `支付台账项目`）；URL 路由断言容忍 `/t/demo` 命名空间前缀（floorplan 与 full_chain）。
- 当前阻塞：blocked 单据断言仍期望 `.workflow-evidence-block` 渲染
  「办理前置条件 / 请先选择关联合同」，但当前只读表单已不渲染该块（实测为空，
  阻断信息分散在「依据口径 无可解释依据」「收款账户完整度 账户信息待补充」等字段）。
- 结论：验收车道整体已偏离当前前端渲染，继续点修会沿整条旅程逐个失效；建议对
  `local_dev_payment_request_full_chain` 做一次系统性的前端渲染对齐（独立 P4 车道收口），
  而不是继续通过多次分钟级浏览器重跑逐个发现漂移。

## 2026-10-21 续跑产品复核

候选为 `55fdb711c7ffd42f6da4c4300bc37d5032a6bbe3` 加 run 登记的未提交范围，未冻结。
本次修复前端参数草稿状态：重新读取目录后清除暂存值；选择改变后旧预览失效，迟到响应不能重新启用发布。
20 项前端参数测试、严格类型检查及两参数浏览器循环通过；页面回滚值与权威回读一致。
付款账期的采购默认值、审批模式的路由判断及审批定义状态均验证变化并恢复；审计保留。
异常恢复验证覆盖发布后程序捕获异常并调用正式回滚接口，不覆盖进程强杀。

对照计划的实际验收口径，仍须补参数变化后的付款申请链，以及无权限角色参数页面和直写边界证据。
因此本次为局部缺口修复通过，Batch 7 尚未验收完成，不能开始依赖它的 Batch 8。
精确命令、回读、报告与后续动作只维护在 run.json；主线、部署和用户验收均未完成。


## 2026-10-21 集中产品复核结论（continue25）

Batch 7 的本地范围验收通过。本节为当前结论，上文失败及缺口条目保留为历史记录；
精确身份、命令、原始证据和恢复结果以同一 run 的 `batch7_consolidated_product_review`
及 `parameter_payment_chain` 为准。候选仍为 HEAD 加未提交范围，不是冻结发布候选。

最终范围包含 P0 的统一声明组授权服务、P1 参数生命周期约束、前端既有参数状态消费修复和
P4 受管验收工具。P0 只承担通用授权；参数值域、审批语义和只读声明仍归 P1，前端不推导权限。

- 两参数的目录、预览、发布、审计、回滚及页面恢复值通过；付款条件由采购默认值实际消费。
- 统一权限服务的 35 项纯单测、参数后端 19 项测试、无权限角色 4 项 HTTP/页面拒绝检查通过。
  无变更集直接写入由非 sudo ORM 测试验证，受信服务 sudo 写入保留；未另跑通用写 API 的 HTTP 用例。
- 本轮正式发布单级审批后，付款申请 782 生成的审批实例均进入 pending；按实际审批人完成全部实例，
  付款执行 189 到 paid、申请到 done、台账 posted，金额一致为 10,000；79 项链路断言通过。
- 首次执行暴露验证工具“一次只完成一个岗位”的假设。已改为回读每个 tier.review 的状态和 done_by，
  只跳过本轮已观察到完成的实例；该失败的参数已恢复，原记录保留。37 项工具回归通过。
- 参数变更 163 经正式接口回滚为 rolled_back；参数值、采购默认值、审批策略/步骤/定义和旧审计均恢复或保持。
  已完成付款和审计事实不删除。运行前后源码指纹一致；随后只有复核文档更新。

边界：审批关闭模式已覆盖后端和运行时路由/定义，未声称另有关闭模式完整付款浏览器链；
异常恢复覆盖捕获错误后的正式回滚，不覆盖进程强杀。未将采购默认值回读说成采购订单提交验收。

下一步进入 Batch 8 的就绪权威与契约盘点。主线集成、部署、daily 用户验收及首版发布仍未完成；
历史迁移退役的种子安装覆盖和最终审计继续保留待办。
