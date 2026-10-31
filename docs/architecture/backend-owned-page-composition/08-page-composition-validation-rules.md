# 08 · Page Composition Validation Rules

## V1 引用完整性

- 类型：ERROR
- 阶段：contract validation
- 阻断渲染：是
- fieldRef 必须解析到实际字段。

## V2 Slot 完整性

- 类型：ERROR
- ownerSlotRef 必须指向有效 slot。

## V3 Group 完整性

- 类型：ERROR
- ownerGroupRef 存在时必须指向有效 group。

## V4 唯一主归属

- 类型：ERROR
- 同一 `fieldRef` 在同一页面作用域只能有一条 `fieldOwnership` 记录。

## V5 Identity 约束

- 类型：ERROR
- identity 字段必须归属 `slot:identity`，不得由前端字段名推断。

## V6 Section 约束

- 类型：ERROR
- 业务字段必须声明业务 Section 归属。

## V7 重复字段约束

- 类型：ERROR
- 辅助投影必须由 slot 显式声明，不得通过重复 ownership 表达。

## V13 displayRole 显式性

- 类型：ERROR
- 若未来引入 displayRole，Formal Page 必须显式声明；不得存在隐式 primary 默认。

## V8 遗漏字段约束

- 类型：ERROR（Formal Page）
- 正式页面不得将未声明字段自动放入 core / advanced 区域。

## V9 权限边界

- 类型：ERROR
- Schema 不得覆盖服务端字段访问权限、ACL、Record Rules。

## V10 兼容性约束

- 类型：按页面类别
- Formal Page：ERROR。
- Legacy Compatible Page：WARNING，且必须显式标记 `legacyCompatible=true`。

## V11 版本约束

- 类型：ERROR
- 每个 Schema 版本必须声明版本号、变更范围及迁移策略。

## V12 诊断约束

- 类型：ERROR
- 错误必须包含 model、action、view、field、slot、group 信息。

