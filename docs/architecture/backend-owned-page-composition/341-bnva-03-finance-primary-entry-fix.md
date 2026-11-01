# 341 · BNVA-03 Finance Primary Entry Fix

## 根因修正

`menu_sc_company_expense`（→ action 709 付款执行主入口）此前在 finance 角色的
`contextual_menu_xmlids`，不在 `primary_menu_xmlids`，因此主入口投影缺失。

## 最小修复

- 将 `menu_sc_company_expense` 从 contextual_menu_xmlids 移入 primary_menu_xmlids。
- 保留 `menu_sc_payment_execution`（→ 908 实付登记）在 primary。
- 无重复显示：709 菜单已不在 contextual。
