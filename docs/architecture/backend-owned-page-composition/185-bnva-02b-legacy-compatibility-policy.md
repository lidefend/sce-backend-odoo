# 185 · BNVA-02B-02B · 历史兼容策略

## 原则

Legacy Compatible 是显式声明的兼容状态，不是校验失败后的自动降级通道；
`legacyCompatible=true` 不得成为通用绕过开关。

## 必填声明

compatibilityReason / compatibilityScope / unresolvedDiagnostics / owner /
migrationStatus。缺任一则发布阻断（reason=incomplete_legacy_declaration）。

## 状态独立

published / active / 结构完整性彼此独立；published 不证明完整，active 不等于
已发布，结构完整不等于已发布。

## 字段重复判定

FIELD_MULTIPLE_SECTION 保持 WARNING；判定依据：跨 Section 重复、唯一 primary
owner、辅助投影是否显式声明、是否多主编辑入口。合法只读摘要不误判为非法重复。

