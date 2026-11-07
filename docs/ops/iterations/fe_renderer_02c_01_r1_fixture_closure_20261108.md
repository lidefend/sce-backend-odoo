# FE-RENDERER-02C-01-R1：业务语义验收环境闭合

## 批次边界

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：隔离验收 fixture、released-navigation 测试数据和受管 browser evidence。
- Module：`smart_construction_acceptance_fixture`、business-entry matrix、My Work approval browser。
- Standard vs User-Specific：验收测试基础设施，不是产品业务规则。
- Baseline：`6cb2bdeade3aa9ffc9dea40a3a09aafef73f039c`。

## 目标

只修复两个 L4 阻断：

1. 三个正式业务 fixture 角色能通过正常导航进入项目 Kanban，同时保持既有菜单和模型权限。
2. My Work 审批摘要浏览器改用当前受管 5180 profile，并为当前审批步骤分配真实合法审批人。

## 数据库身份

```text
TARGET_DATABASE_ROLE=ISOLATED_ACCEPTANCE
TARGET_TENANT_ID=synthetic_acceptance_fixture
TARGET_ENVIRONMENT_ID=local/sc-fe-r2-p1-01/sc_frontend_acceptance
IS_PLATFORM_CONTROL_DATABASE=false
IS_INDUSTRY_CATALOG_DATABASE=false
IS_CUSTOMER_TENANT_DATABASE=true
IS_ISOLATED_REHEARSAL_DATABASE=false
CUSTOMER_BUSINESS_DATA_ALLOWED=false
FIXTURE_ALLOWED=true
EXACT_DATABASE_FILTER_CONFIRMED=true
FILESTORE_IDENTITY_CONFIRMED=true
```

该数据库只承载合成验收 fixture；不得写入生产、DAILY、平台控制库或客户业务数据。

## 明确排除

不修改 `businessValuePresentation.ts`、Contract V2 Schema、Renderer Extension Protocol、
生产 ACL、Record Rule、菜单权限和审批业务规则；不使用 sudo 绕过审批；不触碰 PR #834；
不部署、不合并；用户时区与 BOQ 金额契约问题继续冻结。

## 只读诊断记录

- 已知 Kanban 403：项目看板动作没有出现在 fixture 角色 released navigation 中。
- 已知审批阻断：fixture 节点审批步骤存在，但当前 pending review 没有可执行审批的合法 reviewer。
- 已知 browser wiring：旧目标依赖 `.env.dev` Compose 变量，而不是当前 5180 managed profile。

## 执行状态

- 当前阶段：L4 主体证据完成，等待 clean final HEAD 的最终静态回执与独立评审。
- 产品代码修改：不允许。
- 证据源候选：`6b377d73d7a5980fb13cf09cfa113c5333f8d62a`。
- 渲染证据：5180 preview base `77447ff3`，entry
  `/assets/index-BXdpOGlL.js`，SHA-256
  `87014c4412941649ec46b5c14fae4aa6a4202198cf5e3b37b4591687b1e16136`。
- 后端证据：18082 `SC_SOURCE_REVISION=6b377d73d`，数据库
  `sc_frontend_acceptance`，artifact digest
  `d58d6d9258ef63c0f3a5332940e8d78e92c8762660a40f427e19e5d6a7d016f5`。

## Kanban 分层定位

只读运行态诊断确认：

- `menu_sc_project_kanban` 属于 `action_project_dashboard`，产品发布状态为 `released`。
- 三个目标角色均有 `project.project` 读 ACL。
- `business.v1:project.management` 在 FE Company A 已启用。
- `menu_sc_project_dashboard` 没有进入当前 release snapshot，不能作为验收替代路线。
- `menu_sc_project_kanban` 原先没有 `sc.product.scenario.entry` 绑定，
  route authority 将 action 以 `BUSINESS_SCENARIO_CONFIGURATION_MISSING` 拒绝。
- PM 和项目成员原先也不含正式菜单组 `group_sc_entry_p01`；配置管理员已经包含。

因此 403 的准确产生层是 **验收场景绑定缺失 + 两个业务 fixture 角色缺少菜单入口组**，
不是模型 ACL、公司启用或生产菜单权限。

## 已实施修复

### Kanban

- acceptance fixture 为已发布的 `menu_sc_project_kanban` 建立
  `project.management` 场景绑定；若已有绑定则复用，绑定到其他场景则 fail-closed。
- 清理早期仅用于诊断的 fixture-owned dashboard 绑定，不删除产品绑定。
- 为 PM 和项目成员补正式菜单入口组 `group_sc_entry_p01`，不授予平台管理员或新增 ACL。
- 菜单导航诊断扩展为三个角色，逐层输出 native visibility、菜单组、模型 ACL、
  scenario location、公司启用、release gate、published authority 和运行时导航结果。

### 审批摘要

- 新增正式业务角色 `fixture_role_finance_reviewer`，持有 finance-manager 审批能力，
  不是平台管理员。
- 当验收公司没有本地/共享 active payment approval policy 时，fixture 创建公司级策略，
  镜像正式标准步骤：`submit -> finance_manager single review`；已有显式禁用策略时拒绝覆盖。
- 审批 fixture 通过 `sc.approval.policy._start_submission_review` 初始化真实 review，
  再把当前步骤 reviewer 分配给 finance reviewer；完成态通过真实审批动作达成。
- `verify.frontend.my_work_approval.runtime/browser` 在 `local` profile 下改由受管
  operation entry 执行，不再启动旧 5175/.env.dev 环境。
- 浏览器入口绑定 5180 preview identity、候选 SHA、运行态 `/api/runtime-version`
  和实际 approval reviewer。

## 验证记录

- `make acceptance.frontend.fixture`：PASS；输出 scenario binding、菜单 release state、
  payment approval policy 和 finance reviewer。
- `make acceptance.frontend.fixture_orm`：PASS，45 tests，0 failed；日志
  `.runtime/acceptance/fixture_orm_20261107T221702Z.log`。
- `make ci.local.iteration`：PASS，7 个必需目标真实执行。
  Receipt：`.runtime/frontend-dev-validation/executions/20261107T222438Z-3802550-74163293/receipt.json`。
- `verify.verification.lane.coverage`：PASS；`standard_preview.unit` 因新接线成为有效目标，
  已通过受管 `--unregister-target` 移除其 stale dead-surface disposition。
- Kanban 三种角色真实浏览器结果：
  - config admin：`ok=true`、`completeness=complete`，4 records，分页、搜索、详情和 workflow actions PASS。
  - PM：`ok=true`、`completeness=complete`，4 records，分页、搜索、详情和 workflow actions PASS。
  - project member：`ok=true`、`completeness=complete`，1 record，分页、搜索、详情和 workflow actions PASS。
  - 三种角色的 negative authority 均为 `checked_entries=1`、`leaked_entries=[]`。
  - 证据目录：`artifacts/frontend-business-entry-matrix/final-6b377d73d/{config-admin,pm,project-member}`。
- `make verify.frontend.my_work_approval.runtime`：PASS；active single
  `fe_acceptance_payment_request_approval` policy，pending review 分配给
  `fixture_role_finance_reviewer`，`can_review=true`，未授权角色矩阵符合预期。
- `make verify.frontend.my_work_approval.browser`：PASS；审批摘要记录身份与金额、
  审批人可办、工作项移除及待办数量 8→7、财务侧状态 `approved`、项目成员拒绝和
  三档响应式均通过；console/page/unexpected HTTP errors 为 0。
  报告：`.runtime/final-acceptance/my-work-approval/report.json`。
- `make acceptance.frontend.fixture_orm`：PASS，45 tests，0 failed；日志
  `.runtime/acceptance/fixture_orm_20261107T224955Z.log`。
- 附件元数据 403 已定位并修复：fixture attachment 原先落在默认 `My Company`，
  与付款申请的 `FE Company A` 不一致；fixture 现显式写入付款单公司并回读校验。

## 后续风险登记

- P1，未在本轮修复：
  - 从结算单点击“新建付款申请”后，`/f/payment.request/new` 请求仍携带
    `render_profile=edit`，得到 409
    `NATIVE_ACTION_GUIDANCE_INVALID / action_guidance.record_identity`。
  - 该问题属于产品表单 create profile 消费缺陷，不属于 R1 已有审批 fixture 验收；
    本轮没有通过放宽契约、吞掉 409 或把该路径计为 PASS 来掩盖它。
- P2，未在本轮修复：
  - 审批成功后工作项、待办数量和财务侧 `approved` 状态均正确更新，但组件声明的
    内联成功提示在刷新后未保留；本轮结果反馈证据使用可观察的权威列表状态更新，
    不宣称 inline feedback 已通过。
- 冻结项继续保持不变：用户时区/日期格式等待契约声明，BOQ 金额等待币种与精度契约。

## 待完成

- 运行 `ci.delivery.freeze.prepare`，审阅并提交生成物。
- 在 clean final HEAD 运行 `ci.local.iteration`，记录精确 receipt。
- 确认工作树 clean 后停止，等待独立评审和发布授权。
