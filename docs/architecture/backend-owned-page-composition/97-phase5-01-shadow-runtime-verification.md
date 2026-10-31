# 97 · Phase 5-01 Shadow Runtime Verification

## 结论

formal 页面（Action 590 / View 1776）的 legacy 渲染门控在运行时生效：
可见 legacy 表单节点归零，shadow 诊断仍可读。Phase 5-01 的核心验证通过。

## 观测环境

- profile: candidate（前端 5178 / 后端 18088）
- login: fixture_role_pm（项目经理，具备项目台账访问）
- 路径: 项目台账 → Action 590 → 打开项目记录 → 表单

## 观测事实（590 / 1776）

| 指标 | 值 |
| --- | --- |
| formComposition | official-standard-form（formal） |
| detailComposition | official-standard-detail |
| shadowLayoutSource | v2_store |
| shadowFieldOverlap | 43 |
| 可见 FormSection（broad） | 20 |
| FormSection 在 NativeFormTreeRenderer 内（native） | 20 |
| FormSection 在 NativeFormTreeRenderer 外（legacy） | 0 |

## 判定

1. formal 页面可见 legacy 归零：成立（`templateFormSectionOutsideNative = 0`）。
2. shadow 诊断仍可读：成立（`shadowFieldOverlap = 43`，未被 formal 门控归零）。
3. 渲染与诊断分离：成立（渲染走 v2_store / native tree，诊断独立统计 overlap）。

## 与既有文档的差异

`93-pc007-frontend-shadow-contraction.md` 记录 overlap 为 79，本次运行时
观测为 43。以运行时为准，后续按 43 追踪；若 79 来自不同入口或口径，需另行核对。

## 未验证

- Action 652 / View 944（非 formal）：运行时 DOM 复核未完成。menu 397 需要
  Smart Core Admin（group 15），但候选 fixture 角色（pm / config_admin /
  system_admin）经 `/a/652?menu_id=397` 均返回“无权访问”，需先解决 652 的
  运行时入口与适用 fixture 身份，再复核 View 944 行为不变。
  - 代码层面：formal 门控仅对 `pageComposition.class === 'formal'` 生效，
    故 652/944（非 formal）不应受影响；此为静态结论，运行时证据待补。

## 待办

- 枚举 79 与 43 的 overlap 口径差异来源。
- 解决 652/944 的 fixture 入口后补 DOM 复核。

## 状态

Phase 5-01 核心验证通过；652/944 运行时复核与 overlap 口径核对待后续批次。
