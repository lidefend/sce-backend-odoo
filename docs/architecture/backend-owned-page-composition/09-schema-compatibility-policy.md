# 09 · Schema Compatibility Policy

## Page classes

### Formal Page

- 必须有完整 formStructureContract + fieldOwnership。
- 不启用 Legacy fallback。

### Legacy Compatible Page

- 必须显式声明 `legacyCompatible=true`。
- 记录缺失的 fieldOwnership。
- 运行 Legacy fallback 时输出 WARNING。

### Incomplete Configuration

- 引用缺失、slot/group 无效或归属冲突。
- 不得静默降级为另一套页面结构。

## Migration rule

历史配置缺少 `fieldOwnership` 时：

- 不得按字段名推断。
- 不得自动进入 Formal Page。
- 必须在迁移清单中显式补齐。

## Node binding

低代码节点、历史 action/view 关系在迁移后必须保持稳定身份。

