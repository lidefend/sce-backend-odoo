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
观测为 43。79 为 fieldOwnership 合并前的旧观测；合并后 V2 结构覆盖更多字段，
overlap 收敛为 43，属正向收敛，非门控隐藏。后续按 43 追踪。

## 652 / 944 观测

以 fixture_role_pm 观测：

| 路由 | formComposition | shadowLayoutSource | overlap | 可见 legacy |
| --- | --- | --- | --- | --- |
| /f/project.project/1 | official-standard-form | v2_store | 62 | 0 |
| /r/project.project/1 | legacy-form-section | none | 0 | 0（页面仍加载中） |

`/f/project.project/1` 在 fieldOwnership 合并后解析为 formal（与 92 号文档
旧记录“解析到 View 944”不一致），说明视图解析已随合并变化；`/r/project.project/1`
（无 action 上下文）仍为 legacy-form-section。该变化需归入 652/944 双入口
追踪独立核查，不改变本批次 590/1776 的 shadow 收缩结论。

根因线索：PC-01 在
`addons/smart_construction_core/data/view_orchestration_form_section_contract_data.xml`
注册了 `business_config_contract_project_overview_form_structure_v1`（绑定
Action 590，identity_fields = name/project_code/user_id/manager_id/owner_id，
priority 700）。该声明使项目标准表单入口解析到 formal overview（View 1776），
因此 `/f/project.project/1` 从 legacy 变为 formal。Action 652 的后台入口是否仍
绑定 View 944，需在双入口追踪中继续核对。

## 待办

- 枚举 79 与 43 的 overlap 口径差异来源。
- 解决 652/944 的 fixture 入口后补 DOM 复核。

## 状态

Phase 5-01 核心验证通过；overlap 口径已收敛为 43（79 为合并前旧值）；
652/944 视图解析变化待归入双入口追踪独立核查。
