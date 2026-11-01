# 133 · BNVA-019 Stage 3C-02B-01 · fallback_parse 迁移

## 原状

`app_view_config._fallback_parse` 在 `view_data._arch_root` 缺失时，再次
`etree.fromstring(arch)` 重试。

## 判定

`view_data` 来自 `_safe_get_view_data`，其 `_arch_root` 已在入口解析。只有当
arch 本身解析失败时 `_arch_root` 才缺失，此时重试必然再次失败，属于冗余解析。

## 迁移

移除重试，直接使用 `view_data._arch_root`；缺失时回退到最小结构（原有分支已
正确处理 `arch_root is None`）。

## 结果

- 同请求 Form 主 arch 不再出现第二次 fromstring。
- Legacy 页面渲染行为不变。

