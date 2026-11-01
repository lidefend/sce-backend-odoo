# 194 · BNVA-02B-02C-01 · 配置来源盘点

## 代码种子（Odoo 数据文件）

- 载体：`addons/smart_construction_core/data/*.xml`（49 个文件含
  `ui.business.config.contract` 记录），无 CSV 配置记录。
- 来源戳：`view_orchestration.context.source = smart_construction_core.product_release`，
  `source_status = product_release`。
- 作用域：多数 `company_id=False`（全局默认）。
- noupdate：多数文件 `noupdate="0"`（或默认 0），升级时重写；少数
  `noupdate="1"`（construction_plan / remaining_p2 / remaining_p3 /
  view_orchestration_contract_generated_data）升级时保留。

## 用户配置

- 前端创建 / 草稿修改 / 审批发布；非 su 写入经 `_tenant_write_values` 盖章为
  `smart_core.lowcode.business_config` + `tenant_runtime`。
- 作用域：`company_id=当前公司`，可带 action/view/role 特异与 priority。

## 混合（覆盖）

- 用户不能直接修改全局种子（非 su 写 `company_id=False` 会 AccessError）；
  用户通过同 model 的公司级低代码配置覆盖全局种子。

