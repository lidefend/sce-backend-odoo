# 334 · BNVA-03 Role Navigation Matrix

## 角色 → 组 → 主入口（静态）

| 角色 | 显式组 | 主入口示例 |
| --- | --- | --- |
| 项目经理 pm | group_sc_role_project_manager / user | menu_sc_project_initiation（已修复）、menu_sc_project_project、boq、wbs、plan、settlement |
| 项目成员 project_member | group_sc_cap_project_read | menu_sc_project_project、daily_contract、plan、construction_diary |
| 业务配置管理员 business_config_admin | group_sc_cap_business_config_admin | 配置管理入口 |
| 财务主管 finance | group_sc_role_finance_manager / user | menu_sc_receipt_income、menu_sc_user_payment_apply、menu_sc_payment_execution、invoice |
| 管理层 executive | group_sc_role_executive | 经营总览入口 |

## 发现

财务角色主入口含 `menu_sc_payment_execution`（→ action 908 实付登记），未直接列出 action 709
付款执行主入口。709 需经 `menu_sc_company_expense` 到达，与 908 的职责区分需在 03-04 治理。
