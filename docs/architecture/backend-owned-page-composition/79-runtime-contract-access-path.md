# 79 · Runtime Contract Access Path

## 结论

运行时 V2 Contract 获取路径：READY_WITH_CONSTRAINTS

## 本轮失败根因

登录成功（uid=12），但 `POST /api/v1/intent` 返回
`NS_NAMESPACE_REQUIRED`，原因是所有 `/api/` 路径在进入控制器前，由
`ir.http._pre_dispatch` → `enforce_entry_namespace` 校验入口注入的
`X-SC-Namespace` 头。本次直连未携带该头，因此被 400 拒绝。

关键事实（`smart_core/security/namespace_resolver.py`）：

- `declared_namespace(headers)` 读 `X-SC-Namespace`。
- 入口还注入 `X-SC-Audience`、`X-SC-Route-Version`、`X-SC-Entry-Secret`。
- namespace 是唯一数据库选择器；客户端 `db` 提示会被 409 拒绝。
- 前端 `config.tenant`（`x-tenant` 头）与入口注入的 `X-SC-Namespace` 不是同一
  机制。

## 正确获取路径

1. 首选：复用现有前端 API Client（`loadActionContractV2(actionId)` →
   `ui.contract.v2` intent），由前端 5178 同源入口完成 namespace 注入与 Bearer
   授权；不在后端直连中自行重建认证链。
2. 若需直连：必须同时携带 `X-SC-Namespace`（alias）与入口注入头及登录后
   Bearer token；alias 与入口 secret 不在本轮检索或输出。

## 身份绑定

- 590/1776：`loadActionContractV2(590)`，`op=action_open`。
- 652/944：`loadActionContractV2(652)`，`op=action_open`。
- 契约内 `sourceAuthority.governance_source.resolvedActionId/resolvedViewId`
  提供后端解析后的 action/view 身份。

## 边界

不输出、不保存 Token / Cookie / 密码 / 入口共享密钥。
