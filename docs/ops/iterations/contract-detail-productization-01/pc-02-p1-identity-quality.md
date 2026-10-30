# PC-02 · P1 合同身份带页面配置质量检查报告

结论类型：DESIGN_PROPOSAL + STATIC_VERIFICATION（静态已核验；运行时项标记为 RUNTIME）。

## 1. 候选身份

- 分支：`feature/contract-detail-productization-01`
- 完整 HEAD：`1d29c58c31ce1901a46b7d8861d70f726a2c160c`
- 基线 main：`c6880a1cb39b3f6b522fbb46377ba912106c2c15`
- 目标模型/视图：`construction.contract` / `view_construction_contract_form`

## 2. 配置变更范围

本轮仅重排 `addons/smart_construction_core/views/core/contract_views.xml`
（18 增 / 14 删）。未改动模型、ACL、record rule、金额计算、审批逻辑。
33 个原字段全部保留，仅调整分组与顺序。

## 3. 静态验证结果

| 检查 | 结果 | 说明 |
| --- | --- | --- |
| XML 良构 | PASS | ElementTree 解析通过 |
| 字段存在性 | PASS | 33/33 字段均声明于 `construction.contract` 模型 |
| 字段完整性 | PASS | 重排前后字段集合一致，无缺失 |
| 结构锁定 | PASS | `verify.contract.structure_lock` domains=14 fingerprint=current |
| 空白/格式 | PASS | `git diff --check` 干净 |
| 新增重复字段 | PASS | P1 未新增重复字段；5 个既有双声明为历史项 |

## 4. 十维配置质量门禁

| 维度 | P1 状态 | 判定 |
| --- | --- | --- |
| 页面身份 | `subject` 主标题、`name` 只读编号、`type` 方向、`state` 生命周期、`document_status` 单据状态独立 | 静态 PASS |
| 信息结构 | 身份带 → 主体与关联项目 → 基本信息/系统信息 → 金额/审批/明细 | 静态 PASS |
| 字段声明 | 33 字段完整、无混淆、语义独立 | 静态 PASS |
| 金额表达 | P1 不涉及；金额概览保持原字段（P2 处理） | 静态 PASS（P2 范围） |
| 权限 | 未改任何 `groups`/ACL/record rule | 静态 PASS |
| 组件 | 沿用原生 `field`/`group`/`statusbar`，未新建 Vue 组件 | 静态 PASS |
| 关系 | `partner_id`/`project_id` 独立分组 | 静态 PASS |
| 响应式 | 四视口几何 | RUNTIME（需真实浏览器） |
| 空态 | 未新增伪数据空态；`attachment_text` 等仍按契约渲染 | 静态 PASS |
| 交互 | `state` statusbar 与 header 按钮保持原状 | 静态 PASS（运行时复核按钮可见性） |

## 5. 最小运行时验收范围

以下项无法由静态检查证明，需在隔离 candidate 载体（`sc-fe-candidate-770` /
`sc_frontend_acceptance_candidate`）上一次性完成：

1. 真实 Odoo 视图加载：`view_construction_contract_form` 升级后无 XML/字段错误。
2. 真实字段值：选择既有合法合同，核验主标题唯一、编号只读、方向/状态/单据状态区分。
3. 浏览器几何：1440 / 1024 / 768 / 390 四视口布局达标。
4. 权限与交互回归：审批按钮可见性与原 ACL 一致，无越权可写入口。

不创建业务数据，不修改合同金额与审批状态。

## 6. 结论

PC02-P1 属于纯页面配置变更，静态质量门禁全部通过。剩余运行时验收点集中在
真实视图加载、真实字段值与四视口几何，待隔离 candidate 载体就绪后一次性执行。
