# 110 · BNVA-019-05 · 权限与 Modifier 边界

> 目标：冻结权限投影与 modifier 求值的边界，防止 sudo 泄漏与错误求值。

## 1. 权限投影边界

| 操作 | 应使用环境 |
| --- | --- |
| 获取用户可见 View Arch | 当前用户 env |
| 获取用户可访问字段元数据 | 当前用户 env |
| 查询经授权业务配置 | 独立受控 su_env |
| 查询业务记录 | 当前用户 env |
| ACL / Record Rules | Odoo 原生权限机制 |

Native View Projection 已改为使用当前用户 env（见 `ui_contract_v2.py` 的
`project_native_view(self.env, ...)`）；`ui.business.config.contract` 配置读取仍用
`su_env`。这条边界必须长期保持，任何下游不得重新用 sudo 补全普通用户视图。

## 2. 契约能/不能携带

能携带：

- 当前用户可见字段。
- 字段 readonly 状态。
- 当前用户允许的操作。
- 服务端已确定的能力状态。

不能：

- 通过契约增加字段访问权。
- sudo 取完整字段后直接返回普通用户。
- 用前端隐藏代替服务端授权。
- 把 Record Rules 转成前端过滤条件后当作安全边界。

## 3. Modifier 求值边界

BNVA-003 已确认：`get_view()` 返回的 modifiers 是原始表达式、未求值。

| 层 | 职责 |
| --- | --- |
| 后端 | 原样投影原始表达式，仅解析静态字面量 |
| 前端 | 按记录运行时求值 invisible/readonly/required |
| Guard | 校验投影不丢失、不改变原始语义 |

记录相关表达式（如 `invisible="not reject_reason"`）依赖当前记录/context/uid，
后端不得用空上下文求值成 false/null。

## 4. 约束

- 权限裁剪后的结构必须与当前用户 `get_view()` 一致。
- 配置读取可有独立授权路径，但用户可见字段必须遵守原生权限边界。

