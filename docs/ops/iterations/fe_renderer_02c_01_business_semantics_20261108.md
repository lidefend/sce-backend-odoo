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

- 目标与运行登记已建立。
- 产品代码修改：审计完成后开始。
- 审计结果与消费矩阵：
  `docs/architecture/frontend_business_semantics_authority_audit_v1.md`。
- 审计结论：详情金额、Kanban 字段名推断、状态双映射和空值口径是 P1；
  日期展示入口为 P2；时区转换因缺少契约声明不自行推断。
- 最小实施方案：建立共享业务表达模块，改造详情、Kanban、审批与状态/空值消费者，
  增加跨页面一致性测试和静态守卫。
