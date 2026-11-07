# FE-RENDERER-02C-01：业务语义单源收敛

## 批次边界

- Formal Product Layer：P0 平台内核产品。
- Layer Target：Contract V2 前端语义解释与跨页面表达。
- Module：canonical presentation、FormSection、列表、详情、Kanban、审批摘要、
  ProfessionalBusinessValueControl 和行业专业组件。
- Standard vs User-Specific：平台工程标准。
- Baseline：`5d184f4831ddbc4819bc5540341b05cd6fb413bb`。

## 目标

让同一种金额、日期、状态和空值事实在表单、列表、详情、Kanban、审批与行业组件中共享同一
契约来源、语义解析器和合法展示适配器。

## 明确排除

不修改 Contract V2 Schema、Renderer Extension Protocol，不新增行业 Renderer，不大规模重写
`@sc/ui` 或 Sc 组件，不删除原生 View 兼容链，不修改 PR #834，不部署、不合并。

## 第一阶段：只读审计

审计必须覆盖：

1. Contract V2 字段解释与 canonical form model。
2. FormSection 的字段、状态、金额和空值呈现。
3. listCellPresentation、详情 FieldValue、Kanban 卡片与看板列。
4. 审批摘要、ProfessionalBusinessValueControl、ScMoney、ScStatusBadge、日期与空值原语。
5. 行业专业组件中的复用或旁路路径。

审计先输出声明来源、解析器、权威组件、合法适配器、重复实现和真实消费者，不先修改产品代码。

## 当前状态

- 目标与运行登记已建立，审计先于产品实现提交。
- 产品实现已完成，等待冻结候选上的受管 L4 浏览器证据与最终收口。
- 审计结果与消费矩阵：
  `docs/architecture/frontend_business_semantics_authority_audit_v1.md`。
- 审计结论：详情金额、Kanban 字段名推断、状态双映射和空值口径是 P1；
  日期展示入口为 P2；时区转换因缺少契约声明不自行推断。
- 最小实施方案：建立共享业务表达模块，改造详情、Kanban、审批与状态/空值消费者，
  增加跨页面一致性测试和静态守卫。

## 实施结果

### 业务语义权威

- 新增 `app/presentation/businessValuePresentation.ts`，统一金额、百分比、状态、
  日期/时间和普通空值的声明式展示。
- 金额格式化从表单专用 mapper 提升为跨页面权威；表单、列表、详情、Kanban、审批、
  活动视图、层级工作表与付款结算行业组件统一消费。
- 状态 label 只从字段 selection 取得；tone 只由平台
  `collectionStatusPresentation.ts` 策略解释，不再保留页面或 Professional 组件内的第二套 tone 表。
- 普通空值统一为 `FIELD_VALUE_EMPTY_TEXT = '--'`；契约显式
  `readonly_empty_text` 仍优先。列表缺失数值不再显示成业务零值。
- 删除 `utils/semantic.ts`，移除字段名驱动的金额/百分比/状态推断。

### 跨页面消费矩阵

| 业务事实 | 表单 | 列表 | 详情 | Kanban | 审批 / 行业适配 | 单一语义来源 |
| --- | --- | --- | --- | --- | --- | --- |
| 金额 | `FormSection`、Professional 控件消费字段 `digits/currency_field` | `ListPage` 消费列 `digits/currency_field`，汇总同源 | `FieldValue` 消费透传的币种值和精度 | `listColumnOptions` 驱动 `presentCollectionKanbanCell` | 审批 money fact、付款结算和层级表消费共享金额工具 | `businessValuePresentation.ts` + 契约字段元数据 |
| 日期/时间 | 输入归一后由字段类型进入统一时间适配 | `formatTemporalFieldValue(..., 'compact')` | `formatTemporalFieldValue(..., 'full')` | 列声明类型驱动 compact | 审批、活动和行业只读展示消费同一时间适配 | `fieldSemantics.ts` |
| 状态 | `sc.display.status` + selection | `cellRole/status_field` + selection | selection label，tone 由共享策略解释 | `status_field`/列声明消费同一 adapter | 审批状态 key 消费共享 tone adapter | selection/`statusContract` + `collectionStatusPresentation.ts` |
| 空值 | 平台默认或契约显式文案 | 平台默认，缺失数值不再变 `0` | 平台默认 | 平台默认 | 审批、明细集合、关系选择、BOQ 预览、付款结算统一 | `FIELD_VALUE_EMPTY_TEXT` |

### 最小修复批次

- Kanban 改为声明消费列类型、`componentKey`、selection、币种和精度，不再用字段名推断。
- 详情 `FieldValue` 与原生 View / canonical form 透传金额元数据。
- Professional 状态、审批摘要和列表状态统一到共享 tone 策略。
- 原生表单画布、明细集合、关系搜索、BOQ 行业预览和付款结算的空值旁路统一到平台规则。
- 增加跨页面语义一致性测试、静态守卫和增量调度映射。

## 验证记录

- `make verify.frontend.business_semantics.unit`：PASS；覆盖金额、状态、日期、空值、
  Kanban 声明消费、审批摘要和行业空值。
- `make verify.frontend.boq_import_preview.unit`：PASS；包含 10 个 Python 测试、22/27 项
  readonly-block 检查及模型断言。
- `make verify.frontend.localized_display.unit`：PASS。
- `make verify.frontend.collection_status_presentation.unit`：PASS，15 cases。
- `make ci.local.iteration`：PASS，真实执行 18 个必需目标，零 blocked/not-run/unmapped。
  Receipt：`.runtime/frontend-dev-validation/executions/20261107T204921Z-3336201-702268851/receipt.json`。
- 执行中发现的旧测试失效已修复并纳入调度：删除 `utils/semantic.ts` 后，
  localized-display 与 collection-status 两个既有目标仍然引用旧模块；增量规则此前未选择它们。
  本轮已更新测试与映射，`registrationMissingTargets=[]`。
- Lint：0 errors，保留 4 个既有 warning。
- Strict typecheck：PASS。

## L4 真实浏览器与运行态证据

候选：`77447ff333f6b5e890e7ef21df743ec70d1c5e5d`。

- 5180 预览构建：PASS。`base_sha` 为候选 SHA，`dirty_scope` 为空，入口为
  `/assets/index-BXdpOGlL.js`，entry SHA256 为
  `87014c4412941649ec46b5c14fae4aa6a4202198cf5e3b37b4591687b1e16136`。
- 18082 验收后端：PASS，`SC_SOURCE_REVISION` 与候选 SHA 一致。
- 契约回执：PASS；approved/recomputed semantic SHA256 均为
  `a44e0db0fe92a870b910e8ca46e92831dba095ca4a99436f64f1bd27cf57e28b`。
- 项目只读表单：PASS，1 target，0 mutations，0 errors；证据
  `.runtime/final-acceptance/frontend-presentation/header.json`。
- 合同表单/详情：PASS，覆盖 1440/1024/768/390 四个视口，0 overflow、0 errors；
  证据 `.runtime/final-acceptance/contract-form-presentation/contract/summary.json`。
- 付款申请列表：PASS，覆盖 1440/1024/768/521/520/390 六个视口；records 30/30、
  gated 316/316、negative fixtures 5/5、runtime errors 0；证据
  `.runtime/final-acceptance/list-surface-structure.json`。
- Evolution 记录：PASS，`frontend_presentation` 与 `list_surface_structure`
  已绑定候选 SHA。

### L4 阻断项

- Kanban：BLOCKED。真实矩阵在 `fixture_role_config_admin`、`fixture_role_pm`、
  `fixture_role_project_a_member` 三个已登记身份上均观察不到
  `smart_construction_core.action_project_dashboard` 的发布导航，并出现一次 403。
  归类为 acceptance fixture/发布导航基线缺陷，不记为本轮看板 PASS。
- 审批摘要 browser：NOT_RUN。既有 `verify.frontend.my_work_approval.browser`
  入口在当前 5180 managed profile 上要求旧 `.env.dev` 的 Compose 变量，无法由
  当前受管 5180 环境直接执行。
- 审批 runtime：BLOCKED。执行 `acceptance.frontend.fixture` 后，
  `verify.business_config.approval_runtime` 已完成 enabled submission 与配置不绕过检查，
  但在 `_approve_existing_reviews` 报 `no authorized reviewer for current step`；
  归类为 acceptance fixture 审批人分配缺陷，不记为审批 PASS。
- 审批摘要的纯函数/跨页面语义仍由 L2 一致性测试覆盖，但不能替代缺失的真实浏览器证据。

## 未完成与契约限制

- 用户时区/日期格式：NOT_RUN。当前 Contract V2 页面输入没有用户时区与日期格式声明；
  本轮只统一原始日期/时间字符串解释，不宣称完成时区转换。
- BOQ 导入预检金额：只统一了空值；payload 未声明币种、精度，仍保留仅分组展示，
  不将未知金额语义伪装成已完成。
- `@sc/ui`、TDesign 核心驱动完整属性接管和 Renderer 协议不在 02C-01 范围。

## 批次状态

- 开发批次：代码与 L2 完成；L4 部分完成，Kanban 与审批摘要仍有外部 fixture 阻断，
  因此批次状态为 `verification_pending`，不宣称完整验收完成。
- 主线集成：未合并。
- 部署：未执行。
- 用户交付：未验收。
