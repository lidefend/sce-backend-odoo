# 34 · Page Universe Discovery Method

## Sources

- `ir.actions.act_window`
- `ir.ui.view`
- `ir.ui.menu`（action 非空）

## Filters / exclusions

- 排除无 res_model 的 action。
- 技术/qweb 视图未归类为产品页面。
- 未做自定义前端路由全量发现。
- 分页和权限未展开，Discovery Unverified 保留。

## Page identity

`model + action_id + view_id`

缺少身份时不自行补齐。

