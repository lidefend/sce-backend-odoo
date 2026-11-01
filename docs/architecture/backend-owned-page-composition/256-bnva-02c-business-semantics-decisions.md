# 256 · BNVA-02C · 业务语义裁定与优先页面核实

## 决策（已采纳）

1. `identity_fields` 表达**页面身份摘要（Identity Summary）**，不是严格数据库唯一标识；
   以 project 590 为参照样板，不同模型可有不同组合。
2. project 590 保留现有配置作回归基准；project 652 先核实 Action/View 关联，再决定
   是否复用 590 的 Identity 定义（同 Model 可共享身份、页面区域仍可不同）。
3. sc.payment.execution / sc.receipt.income 是否首版正式功能，待产品范围裁定。

## 三项只读核实

### payment.request `name` 语义

`payment_request.py:128`：`name = fields.Char(string="申请单号", required=True,
default="New", copy=False)`。故 `name` 是**申请单号**（对象标识），不是显示标题。
Identity 候选等级从 C 升为 B：`name` 作为对象标识有明确字段定义证据。

### project 652 Action/View 关联

652/944 是运行时数值 ID，仓库无静态引用，需隔离库解析 `ir.model.data` 才能定
action/view XML ID。另发现伴生 Identity 配置 `project_overview_form_structure_v1`
绑定在 `action_sc_project_list`（列表 action），而非表单详情 action——该关联本身
可疑，需在 652 核实中一并澄清。

### execution / receipt 首版证据

两者均出现在正式财务产品面：`menu_product_finance_wave1.xml`（菜单）、
`finance_document_tier_actions.xml`（层级动作）、`approval_policy_seed.xml`
（审批策略）、`receipt_invoice_line_views.xml`（收款发票行视图）等。
证据支持“属于首版财务功能”，但其表单结构（Identity/Section）需依据原生 View 与
真实流程重建，不恢复 retired 旧配置。

## 状态

46 条批量补齐不批准；payment.request 可作第二个样板推进；execution/receipt 待产品
范围裁定；project 652 待隔离库 Action/View 解析。

