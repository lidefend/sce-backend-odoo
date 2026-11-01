# 415 · BNVA-04 Quality Issue DOM Consumption

## 结果

sc.quality.issue 浏览器 DOM 消费 NOT_RUN。

## 原因

fixture_role_finance 登录 clean 后导航 `/a/744?menu_id=523` 被前端拒权：

`access-denied?from=/a/744?menu_id=523&reason=NAVIGATION_AUTHORITY_DENIED`

sc.quality.issue 属项目中心域，财务角色发布导航不含该入口；sc_clean 仅有 fixture_role_finance
一个夹具用户，无项目夹具角色，且本轮禁止创建用户/记录，故无法以授权角色打开该页。

## 已确认

- Action 744 / Menu 523 存在，ORM 读权限 finance 具备。
- L2 Contract 已发布（sc_quality_issue_handling_form_v1，native_semantic_surface）。
- Form View 绑定已加载（action_sc_quality_issue_form_view_v1）。

## 结论

quality.issue 的 L3 浏览器 DOM 需项目域夹具角色后补验；当前如实 NOT_RUN，不伪造 DOM 证据。
