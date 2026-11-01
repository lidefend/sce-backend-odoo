# 121 · BNVA-019 Stage 3B · 单次解析验证

## 计数

| 指标 | 结果 |
| --- | --- |
| form 主 arch get_view | 1 次/请求 |
| form 主 arch fromstring | 1 次/请求 |
| Canonical Model 构建 | 1 次 |
| Adapter 消费 | 2 次（NCP + LDP，允许） |
| 内联子视图/tree/search | 各自解析（不同 arch，非重复） |

## 验证方法

monkeypatch `project.project.get_view` 统计 `view_type="form"` 调用，验证完整
`ui.contract.v2` 请求内 form get_view 为 1。

