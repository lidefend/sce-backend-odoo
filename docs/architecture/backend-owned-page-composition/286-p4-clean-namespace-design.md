# 286 · P4 Clean Namespace Design

## 目标

为 `local.clean`（`sc-local-clean` / `sc_clean`）建立独立的 `clean → sc_clean`
命名空间绑定，使浏览器经过 Nginx 入口后真正进入全新安装数据库，而不是回退到
`demo → sc_demo`。

## 设计结论

- 命名空间 alias：`clean`（path 类型）。
- `namespace_id`：沿用仓库既有派生规则 `ns_` + sha256("sc_clean") 前 12 位 =
  `ns_c6fed472e939`。
- 目标数据库：`sc_clean`，`duty_key=local_clean`，`audience=tenant`。
- 不修改 P0 命名空间种子，不修改 `demo` / `platform` 绑定。
- 入口声明复用 `daily.runtime.entry.v1` 结构，新增 clean 实例文件。

## 边界

| 项目 | 结果 |
| --- | --- |
| `demo → sc_demo` | 不变 |
| `platform → sc_platform_control` | 不变 |
| 命名空间缺失时 | 拒绝，不回退 demo |
| 错误命名空间 | 404 `NS_UNKNOWN_NAMESPACE` |
| 客户端数据库提示（db header/query） | 409 `NS_DATABASE_HINT_CONFLICT` |

## 授权

所有者批准方案 A：clean 专属入口，不扩展产品级命名空间种子。
