# 86 · Back to Mainline Productization（回主线产品化建议）

## 本轮突破

取得项目详情（590/1776）的实时 DOM 运行时证据：

```text
composition          = official-standard-form（contract-record-view）
detail               = official-standard-detail
shadowLayoutSource   = v2_store
shadowFieldOverlap   = 79
nativeTree           23（可见 5）
legacyFormSection    22（可见 5）
```

结论：

- 主组合已经是官方标准表单（official-standard-form），不是 legacy。
- legacy 以 shadow 诊断方式并行渲染（22 个 FormSection、79 个字段重叠），
  证明 `buildLegacyLayoutNodes` 运行时仍被执行并进入 DOM，但不再是主结构。
- 由此 590/1776 的 PC-007 从 NOT_VERIFIED 升为 WARNING（有运行时证据）。

## 这对产品化意味着什么

1. 前端渲染面已经切到官方标准表单；真正缺的不是前端，而是后端业务组合声明
   （slots=0、fieldOwnership 缺失）。
2. 一旦后端声明 identity / business section slots 与 fieldOwnership，
   PC-001/002/003/004 将由 NOT_VERIFIED 转 PASS，页面才具备 Formal 准入基础。
3. legacy shadow 在正式页面补齐后可收缩，不再需要继续建设 Guard。

## 最快回到主线产品化的路径（建议）

1. 批准 PC-01 后端配置治理：为项目详情契约声明 slots + fieldOwnership
   （这是产品代码/配置变更，需解除 PC-01 冻结）。
2. 声明完成后重跑 Guard：预期 PC-001/002/003/004 PASS。
3. 补齐 PC-008（双身份权限测试）、PC-009（旧消费者回归）、PC-010（运行视图
   occurrence 映射）三项证据，关闭 Phase 4。
4. 进入 Phase 5 Legacy 收缩：在正式页面证明不依赖隐式补齐后收缩 legacy shadow。

## 仍需证据

- PC-008：pm 与负样本身份的只读权限对比。
- PC-009：新增旧消费者回归并运行。
- PC-010：1776/944 的 occurrence_index 与 before/after 映射。
- 652/944 需独立 DOM 观察（本轮只覆盖 590/1776）。

## 约束

本轮仍为只读取证；后端配置治理属产品变更，待解除冻结后另行执行。
