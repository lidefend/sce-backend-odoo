# 126 · BNVA-019 Stage 3C-01 · 缓存生命周期审计

## 现状

`native_view_parsed_cache.py` 以 `(id(env.cr), uid, model, view_type, view_id,
context_digest)` 为键，有界 LRU（32），提供 `clear_request` / `clear_all`，
但没有绑定到 cursor 关闭/请求结束的自动清理钩子。

## Odoo cursor 事实

- `odoo.sql_db.Cursor` 有 `_closed` 与只读 `closed` 属性，`close()` 置真。
- 每次 `ConnectionPool.borrow()` 生成新 `Cursor` 对象；`id(cursor)` 在对象被
  GC 后可能被后续对象复用。

## 风险

若请求 A 的 cursor 在结束前未清理，其对象被 GC，请求 B 的新 cursor 恰好复用
同一 `id()`，且 uid/context 相同，则 B 可能命中 A 的旧 `_arch_root`。

## 结论

`id(cursor)` 不适合作为长期稳定请求身份；当前实现不满足发布级生命周期安全性。

## 建议最小修复（3C-02 实施，不在本只读批改动）

1. 缓存条目保存 cursor 对象引用，命中时校验 `entry.cursor is env.cr and
   not env.cr.closed`；或
2. 以 cursor 的 `weakref` 作键（若 Cursor 支持弱引用）；或
3. 显式 request-scoped carrier：在 `ui_contract_v2` 请求入口创建、请求尾清理，
   不依赖 `id()` 复用假设。

优先评估方案 3（显式 carrier），保留有界 LRU 作为兜底，不通过扩大容量解决
生命周期问题。

