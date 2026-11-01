# 167 · BNVA-02A · 配置作用域与生命周期

## 作用域字段

`ui.business.config.contract`：`model`（必填）、`view_type`、`action_id`、
`view_id`、`role_key`、`company_id`、`priority`。

## 匹配规则（`_effective_view_orchestration_contracts`）

- 只取 `active=True` 且 `status=published`。
- 公司范围：`company_id=False`（全局）或当前公司。
- 空 `action_id` / `view_id` / `role_key` 为通配；非空必须精确匹配。
- 最终按 `view_orchestration_apply_order_key` 排序：
  `边界层 > action 特异 > view 特异 > role 特异 > priority > version_no > id`。
  更特异者排后、覆盖通配者。

## 生命周期

| 字段 | 语义 |
| --- | --- |
| active | 软删除开关 |
| status | draft / published |
| version_no | 版本号，发布时递增 |
| published_at | 发布时间 |
| contract_json | 配置载荷 |
| payload_sha256 | 载荷摘要 |
| definition_sha256 | 定义字段摘要 |
| source_authority_json | 来源权威标识 |

运行时只消费 published + active；预览走 change_set（preview_token + 目标版本）。
版本历史由 `ui.business.config.contract.version` 承载。

## 发现

- `payment_request_form_sections_v1`：published，但 `views.form = {}`（空对象）——
  是占位配置，未声明结构。
- `sc_receipt_income_form_sections_v1`：`active=False` 已退役，注释指向原生视图
  1644 拥有结构，但运行时未解析出 authority/class，说明原生视图尚未完整声明
  Identity/Section/Ownership。

