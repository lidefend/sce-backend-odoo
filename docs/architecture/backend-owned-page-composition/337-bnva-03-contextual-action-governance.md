# 337 · BNVA-03 Contextual Action Governance

## 事实

- 角色面声明 `contextual_menu_xmlids` + `contextual_action_authorities`（menu_xmlid / action_xmlid /
  allowed_operation / required_capability / source）。
- 上下文动作最终映射到服务端 action xmlid，由模型 ACL / Record Rules 决定实际授权。

## 结论

上下文动作有服务端身份与授权边界，不以前端隐藏按钮替代权限。运行时 NOT_RUN（无多角色 fixture）。
