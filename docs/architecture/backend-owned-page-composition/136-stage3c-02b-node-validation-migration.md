# 136 · BNVA-019 Stage 3C-02B-04 · node_component_validation 迁移

## 判定

`validate_final_nodes` → `native_feedback_fields` 在页面装载的契约组装期间
`record.get_view()` + `ET.fromstring`，与 Form 主 arch 重复。

## 迁移

- `native_feedback_fields` 增加 `parsed_view`；命中时复用 Carrier 缓存的
  `_arch_root`，仍校验 `_source_view_id` 与 ir.ui.view 的 model/type。
- `validate_final_nodes` 透传 `parsed_view`。
- `assemble_unified_page_contract_v2` 增加 `carrier`，从 Carrier 取 parsed_view。
- `ui_contract_v2` 传入 `carrier=self._request_carrier`。

## 隔离

保留 View 身份校验；不跨用户/公司/请求复用；无 carrier 时回退独立 get_view。

