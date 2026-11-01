# 119 · BNVA-019 Stage 3B · 统一解析入口实施记录

## 目标

让 NCP 与 LDP 在同一请求内共享同一份 L0 原生事实，不合并职责。

## 实施

- 新增 `core/native_view_parsed_cache.py`：请求级共享解析视图缓存。
  键 = (live cursor 身份, uid, model, view_type, view_id, context digest)。
  上下文只取 lang / tz / allowed_company_ids / contract_action_id；有界 LRU，
  只做内部优化，非权限权威。
- `native_view_projection.project_native_view` 增加可选 `root`，并在无显式 root
  时优先读取请求缓存；缓存命中即跳过 `get_view()` + `etree.fromstring()`。
- `app_view_config._safe_get_view_data` 在解析出 `_arch_root` 后写入请求缓存。

## 效果

同一请求内 form 主 arch 的 `get_view` 由 2 次降为 1 次、`fromstring` 由 2 次降为
1 次。内联子视图、tree/search 等其它视图仍各自解析（不同 arch，非重复）。

