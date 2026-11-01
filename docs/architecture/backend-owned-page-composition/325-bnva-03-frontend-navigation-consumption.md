# 325 · BNVA-03 Frontend Navigation Consumption

## 链路

routeAuthority（fail-closed）→ canonicalNavigation → useWorkspaceHome → sceneRegistry。

## 证据

- test_route_authority_single_consumer：13 项 OK。
- clean 浏览器导航 dump：fixture_role_finance 发布导航 15 条，列表面消费 3 个 `ui.contract.v2`。

## 结论

前端未发现自行构造业务入口或绕过后端导航权威的路径；表单面路由消费 NOT_RUN。
