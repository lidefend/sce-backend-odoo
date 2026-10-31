# 15 · Phase 4B Implementation Plan

## Goal

实现独立 `Page Composition Integrity Guard`，接入现有验证体系。

## Steps

1. 实现规则执行器。
2. 采集 V2 输出和页面分类。
3. 检查前端 fallback 调用点。
4. 检查服务端权限边界证据。
5. 输出机器可读报告。
6. 接入 `scripts/verify`，先以 shadow 模式运行。

## Initial gate result

Phase 4B 完成后，Guard 默认：

- 正式页面：未迁移页面保持 NOT_VERIFIED。
- 不阻断历史页面。
- 只在明确启用后阻止新 Formal Page 不合规发布。

## Entry criteria for Phase 5

- Guard 可执行。
- V7 至少具备可解释的 NOT_VERIFIED 证据路径。
- Legacy fallback 使用点可审计。
- 权限边界检查不依赖单一布尔声明。

