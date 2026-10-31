# 96 · Phase 5-01 Shadow Contraction Arrangement

## 状态

Phase 4 结构侧与 fieldOwnership 生产链路已合并 GitHub main（PR #789，
合并提交 `795f9fc10ed8fca2d7e8444cf92fa5e391609fb0`）。本批次解冻 Phase 5，
并安排其第一个批次 Phase 5-01：PC-007 前端 shadow 收缩的运行时验证与收口。

## Formal Product Layer

- 前端 · 通用契约渲染：formal 页面 legacy 渲染门控（表现层，不承载业务语义）。
- P4 · ops_delivery_tool：shadow 诊断证据与浏览器复核。

## Layer Target

- 前端：`frontend/apps/web/src/pages/contractForm/useRecordFormFieldSchemas.ts`
  以及 `useContractV2ShadowDiagnostics.ts` 的诊断消费。
- 证据：`docs/architecture/backend-owned-page-composition/`、`.runtime/`。

## 已知事实

- 门控代码已存在于 main：`useRecordFormFieldSchemas.ts:106` 对
  `pageComposition.class === 'formal'` 返回空 `layoutNodes`。
- 观测基线（View 1776 正式入口）：legacyFormSection 总数 22、可见 5、隐藏 17；
  nativeTree 总数 23、可见 5。
- 79 个 overlap 是真实迁移信号，诊断依赖 `formFields`，不依赖 `layoutNodes`。

## 待验证（本批次核心）

1. View 1776（formal）运行时可见 legacy 归零：经
   项目中心 → 项目台账 → 打开项目 的真实菜单路径复核 DOM。
2. shadow 诊断仍可读：overlap 计数不因 formal 门控归零。
3. 渲染与诊断确实分离：渲染侧不消费 legacy `layoutNodes`，诊断侧继续计算 overlap。
4. View 944（legacy_compatible / 非 formal）不受影响。

## 交付

- `97-phase5-01-shadow-runtime-verification.md`：运行时 DOM 证据。
- 更新项目 590/1776 的 shadow/legacy 证据 bundle。
- 79 个 overlap 字段清单（从 View 1776 正式入口枚举，落到证据 bundle）。

## 执行限制

- 不修改后端结构、权限、业务配置、数据库。
- 不删除 legacy fallback；仅验证 formal 页面的渲染门控。
- shadow 诊断保留到 overlap 归零后再整体退役。

## 验收

- View 1776 formal 可见 legacy 归零，且 overlap 诊断仍为 79（或记录未归零原因）。
- View 944 行为不变。

## 完成后

停止，等待统一调度；不并行扩大调查范围。
