# 130 · BNVA-019 Stage 3C-02A · 缓存生命周期实施

## 改动

- `native_view_parsed_cache.py`：删除模块级 `_cache` 与 `id(cursor)` 键，改为
  `RequestScopedCarrier` 类。
- `native_view_projection.project_native_view`：增加 `carrier` 参数，命中时复用
  缓存 root，无 carrier 时优雅降级为直接 get_view + fromstring。
- `app_view_config._safe_get_view_data`：增加 `carrier` 参数，解析后写入 carrier。
- `ui_contract_v2`：请求入口创建 carrier，`handle()` finally 清理；
  NCP/LDP 均显式接收同一 carrier。
- `page_assembler`：从 params 读取 `_request_carrier` 传给 `_safe_get_view_data`。

## 验证事实

- form 主视图 get_view 仍为 1 次/请求。
- 请求结束后 `self._request_carrier` 为 None（finally 清理）。
- project 590 / payment 880 契约输出不变。

