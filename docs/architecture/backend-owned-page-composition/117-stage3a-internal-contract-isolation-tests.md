# 117 · BNVA-019 Stage 3A · 内部契约隔离测试

## 覆盖矩阵

| # | 场景 | 状态 |
| --- | --- | --- |
| 1 | 原生属性完整保留 | PASS |
| 2 | many2one relation_descriptor | PASS |
| 3 | one2many relation_descriptor | PASS |
| 4 | many2many relation_descriptor | PASS |
| 5 | 普通字段无伪造关系描述符 | PASS |
| 6 | 重复字段 occurrence 保留 | PASS（既有） |
| 7 | 多层容器身份保留 | PASS（既有嵌套 group 测试） |
| 8 | 未命名容器稳定定位 | PASS（既有） |
| 9 | 模型序列化 | PASS（json.dumps） |
| 10 | 内部属性不泄漏到 V2 Contract | PASS |
| 11 | 现有 NCP 单测兼容 | PASS（14 tests） |
| 12 | 现有 LDP 单测兼容 | 见回归报告 |

## 关键断言

- `relation_descriptor` 仅来自 `fields_get()` 元数据，不按 ORM 类型猜测业务角色。
- `build_native_form_structure_contract` 的 slot / group / fieldRole 不含
  `native_attributes` 与 `relation_descriptor`。
- `json.dumps(NativeView.to_dict())` 通过，模型无 lxml Element 引用。

