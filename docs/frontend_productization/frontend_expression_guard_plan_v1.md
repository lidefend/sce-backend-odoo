# 前端表达静态守卫计划 v1

状态：EXP-02 设计产物。目标是把 `frontend_semantic_expression_matrix_v1.md` 变成可执行、可失败的静态守卫，而不是只停留在文档。

## 守卫原则

- 允许适配器，不允许语义分叉。
- 允许行业扩展，不允许行业实现污染平台。
- fail-closed：无法判定时按违反处理，宁可让差异显性化，也不要静默放过。

## 守卫清单

| # | 守卫 | 检查方式 | 违规示例 |
| --- | --- | --- | --- |
| G1 | 金额格式化唯一来源 | 静态：除 `utils/money.ts` 外，任何 `.ts/.vue` 禁止声明 `fmtMoney`/金额格式化函数 | `PaymentSettlementIntroduceDialog.vue:271` |
| G2 | 表单日期单一权威 | 静态：v2 表单字段类型为 date/datetime 时，只允许经 `ScDateField`；禁止业务组件内联 `TDesignDatePicker` | 业务组件自建日期控件 |
| G3 | 状态语义单一来源 | 静态：禁止组件内硬编码 status→label/tone 映射；只能消费 `statusContract` | 业务组件自写 `draft→草稿` 映射 |
| G4 | 空值唯一常量 | 静态：禁止新空值字面量（`'-'`/`'--'`/`'暂无'`）；数值空只能使用已登记的 `COLLECTION_NUMERIC_EMPTY_TEXT` | 页面内联 `|| '-'` |
| G5 | 关系只经 relation_entry | 静态：业务组件不得直接读写关系模型或自建关系弹窗；只能消费 `relation_entry` | 结算弹窗自建搜索 |
| G6 | 只读来自契约 | 静态：禁止前端按模型/字段名硬编码 readonly | `model==='payment.request' && field==='amount'` |
| G7 | 权限来自契约 | 静态：禁止未登记的前端权限判断站点（复用 `frontend_contract_basis_guard.py` 机制） | `if (method==='approve')` |
| G8 | 校验单错误源 | 静态：禁止第二套 `fieldErrors` 生产者；摘要只经 `ProductFormErrorSummary` | 页面自建错误聚合 |
| G9 | 动作只经 registry | 静态：禁止未登记动作分发；同一动作必须唯一入口 | 组件内直接 `intent('execute')` |
| G10 | 行业边界 | 静态：`components/professional-fields` 与平台层禁止引用行业模型/行业组件 | `paymentSettlement*` 位于通用层 |

## 与现有守卫的关系

- 复用 `scripts/verify/frontend_contract_basis_guard.py` 的“前端判断即停机”台账，G6/G7 并入该台账。
- 新增一个轻量 AST/文本守卫（建议 `scripts/verify/frontend_expression_guard.py`），覆盖 G1/G4/G5/G8/G9/G10，登记于 `docs/architecture/frontend_expression_ledger.json`。
- 守卫只报“语义分叉/越界”，不禁止布局、文案、适配器形态差异。

## 基线登记

- 首次运行会标记当前已存在偏差（金额局部 `fmtMoney`、结算弹窗越界等），先登记为已知偏差并给出收敛批次，不立即 FAIL 阻断交付。
- 新增违规 FAIL；已登记偏差修复后转为 PASS。

## 实施边界

EXP-02 本轮只产出设计与守卫清单，不新增产品代码。守卫脚本的落地与挂入 `ci.local.iteration` 在得到确认后再做。
