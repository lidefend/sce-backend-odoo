# 98 · Product State and Ownership Gap (590/1776)

## 当前产品状态

590/1776 已正式进入 Backend-Owned Page Composition：

- pageComposition.class = formal，diagnostics = 0。
- formStructureContract.structureAuthority = native_form_slots，v1.1。
- 5 个 slot：overview / primary_facts / amount_progress / collaboration / details_source。
- 8 个 group：identity、relations、terms、other_facts、amounts、status_dates、
  approval_remarks、details。
- fieldOwnership = 33 条（字段 → slot + group）。
- dataMeta.fieldCount = 43，即 10 个字段尚无归属。

## 10 个无归属字段分类

技术/系统字段（不应有业务归属，建议显式登记为 technical，而非误判为缺失）：

- active、can_review、display_name、message_needaction、write_date

业务字段（应有归属，当前缺失）：

- reject_reason（驳回原因）→ collaboration / approval_remarks
- sc_overview_contract_count（概览合同数）→ overview 或 amount_progress
- source_created_at（来源录入时间）→ details_source / details
- source_created_by（来源录入人）→ details_source / details
- validation_status（校验状态）→ overview 或 primary_facts / other_facts

## 完善方向

1. 为 5 个业务字段补齐 fieldOwnership（P1 声明层）。
2. 将 5 个技术字段显式登记为 technical，避免被当作缺失业务归属误报。

## 根因（已定位）

5 个业务字段均在 `project_overview_views.xml` 中，但放置方式未被归属推导覆盖：

- `validation_status`：`invisible="1"`
- `reject_reason`：`invisible="not reject_reason" readonly="1"`
- `sc_overview_contract_count`：卡片 `<div>` 内只读统计
- `source_created_at` / `source_created_by`：`readonly="1"` 来源审计字段

归属推导只覆盖落入候选列表的可见/常规字段，故这 5 个字段无 slot/group。

## 修复路径

- `reject_reason` → collaboration / approval_remarks
- `sc_overview_contract_count` → overview
- `validation_status` → amount_progress / status_dates
- `source_created_at` / `source_created_by` → details_source / provenance
- 5 个技术字段（active、can_review、display_name、message_needaction、write_date）
  显式登记为 technical

## 实施结果

- top-level fieldOwnership：33 → 38。
- 5 个业务字段已获得归属，落在 `primary_facts / other_facts` 兜底组。
- 5 个技术字段正确排除（TECHNICAL_FIELD_CODES）。
- pageComposition 仍为 formal，diagnostics=0。
- 精确语义映射（reject_reason→approval_remarks 等）留作后续细化；当前先保证
  业务字段不再“无归属”。

## 边界

只改 P1 声明（view_orchestration / form structure config），不改 P0 机制、
权限、数据库；改动后需重建 candidate 并复核 Guard 与页面。
