# 13 · Integrity Guard Architecture

## Principle

Guard 不重复实现 assembler 业务逻辑，只验证：

- assembler 输出。
- 前端消费链。
- Legacy fallback 使用。
- 服务端权限边界。

## Components

1. Rule executor：独立、可重复执行。
2. Evidence collector：读取 V2 输出、页面分类、fallback 调用点和权限声明。
3. Report writer：机器可读 JSON + 可读 Markdown。
4. Gate adapter：接入现有 `scripts/verify` 门禁体系。

## Result model

```text
rule_id
status: PASS | FAIL | WARNING | NOT_VERIFIED | NOT_APPLICABLE
evidence
scope
diagnostic_locations
```

## Constraints

- 不自动补齐配置。
- 不自动迁移历史页面。
- 不修改产品页面或权限。
- 不把 WARNING / NOT_VERIFIED 提升为 PASS。

