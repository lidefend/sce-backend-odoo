# PC-02 · 收入/支出合同双模型产品映射（代码事实审计）

结论类型：CODE_FACT（只读审计）。

## 1. 模型继承关系

- `construction.contract`：项目合同基础模型（`contract_center.py`，`_name="construction.contract"`）。
- `construction.contract.professional.mixin`：专业合同公共逻辑抽象模型。
- `construction.contract.income`：收入合同（`contract_professional.py`）。
- `construction.contract.expense`：支出合同（`contract_professional.py`）。

income / expense 的定义：

```python
_name = "construction.contract.income"   # 或 .expense
_inherits = {"construction.contract": "contract_id"}   # 委托继承
_inherit = "construction.contract.professional.mixin"
_contract_type = "out"   # income；expense 为 "in"
```

结论：两个子模型是 `construction.contract` 的**委托包装模型**，通过 `contract_id`
委托继承基础模型的全部字段，并 `_inherit` 公共 mixin。方向由 `_contract_type` 固定
（income=out、expense=in），创建/写入时强制 `type` 不变。

## 2. 字段归属

P1 身份字段与 P2 金额字段**全部**由 `construction.contract` 声明，并通过
`_inherits` 委托给两个子模型。审计确认每个模型都具备 22 个身份/金额字段，无缺失。

`type` 在基础模型中表达方向，但子模型自身方向已由 `_contract_type` 固定，表单上
`type` 为只读且不可见，不应重复展示。

## 3. 金额字段口径

全部金额计算在基础模型 `construction.contract` 中完成（`_compute_final_amount`、
`settlement_balance = amount_final - settlement_amount` 等）。两个子模型复用同一计算链。
方向差异只在履约表达：out（收入）突出开票/收款，in（支出）突出付款/未付款。

三个 NOT_VERIFIED 边界继续冻结，不因模型拆分改变。

## 4. 视图归属（关键差异）

三个模型各有一套独立表单 arch，**互不继承**：

- `view_construction_contract_form`（基础项目合同，PC-02 P1/P2 此前改动落点）。
- `view_construction_contract_income_form`（收入合同，独立 arch）。
- `view_construction_contract_expense_form`（支出合同，独立 arch）。

已发布导航的合同中心实际绑定 income（action 680）/ expense（action 681），不绑定基础
`construction.contract`。因此此前对基础表单的改动不会自动反映到两个真实产品入口。

收入表单现状（`view_construction_contract_income_form`）已具备：`state` statusbar、
`validation_status`（invisible）、`type`（只读 invisible）、身份组（`business_category_id`、
`subject`、`project_id`、`partner_id`）、合同范围、合同明细与金额、说明与附件、履约信息、
来源与系统追溯（`name` 只读）。

## 5. P1/P2 需要重新落点

- P1 身份带：在 income / expense 两套表单上分别核对 `subject` 主标题、`name` 只读编号、
  `document_status` 独立单据状态、`business_category_id`、`partner_id`/`project_id` 分层，
  且 `state` / `document_status` / `validation_status` 不合并；`type` 不重复展示。
- P2 金额带：在 income / expense 两套表单上分别按五层组织金额字段，并按方向适配履约表达。

统一产品标准 + 两个业务投影：同一套身份/金额/质量/响应式标准，两个模型各自字段映射。
