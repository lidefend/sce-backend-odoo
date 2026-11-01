# 129 · BNVA-019 Stage 3C-02A · Request Carrier 设计

## 目标

用显式请求级载体替换 `id(cursor)` 缓存身份，保证 Canonical Native View Model
只在当前请求内共享，不同请求绝不共享权限裁剪后的 arch。

## RequestScopedCarrier

```text
RequestScopedCarrier(env)
  - 绑定一个 cursor 对象（非 id）
  - 绑定 uid / su 状态
  - 绑定 lang / tz / allowed_company_ids / contract_action_id digest
  - 有界 OrderedDict（32）LRU
  - store(env, model, view_type, view_id, view_data)
  - fetch(env, model, view_type, view_id)
  - close()
```

命中校验（不只依赖哈希）：`env.cr is bound_cursor` 且 `not cursor.closed`，且
uid / su / context digest 一致。

## 生命周期

- `ui_contract_v2._handle_contract` 在 `projection_env` 建立后创建 carrier，
  存 `self._request_carrier`。
- `handle()` 的 `finally` 调用 `carrier.close()` 并清引用，正常/异常均清理。
- 通过显式函数参数传递，无模块级全局、无隐式线程局部。

