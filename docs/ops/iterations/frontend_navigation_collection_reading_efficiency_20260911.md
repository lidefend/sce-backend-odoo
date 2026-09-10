# 导航与集合页面阅读效率（2026-09-11）

## 边界与冻结基线

- Formal Product Layer：P0 平台通用前端表达。
- Layer Target：共享导航外壳与集合渲染器；Module：frontend。
- 基线：干净 `main@10a69c92e1158c5445aff1054fa7fa5c9acdc14b`，分支
  `feature/p0-navigation-collection-reading-efficiency-v1`。
- 完整指纹：`703b8246e72743da44fe586b6be74c9078476d49d4178b55d75042f61f0c2718`
  （7377 paths）。
- 只处理跨模型的导航层级、完整名称访问、集合列宽和列头操作表达；不改菜单树、名称、路由、
  权限、契约、业务动作、数据或个人列偏好。
- 表单对齐、根级 ConfigProvider 和官方图标映射保持冻结。本专题不通过扩大侧栏、隐藏列或缩小
  字号制造通过结果。

## Batch A：受管主线复现

受管运行身份为 project `sc-local-dev`、database `sc_dev_demo`、API `18081`、候选前端 `5176`。
`make verify.frontend.quick.gate` 与 `make local.dev.verify_authority` 均通过。5174 未绑定主线身份，
不计入本批证据。

历史项目地址 `menu_id=679/action_id=859` 在本基线正确落入 `NAVIGATION_AUTHORITY_DENIED`，不作为
产品故障。后续证据全部使用本次 `system.init` 返回的权威入口：

| 样本 | 权威入口 |
|---|---|
| 项目信息编辑 | `/a/861?menu_id=681&action_id=861` |
| 项目启停管理 | `/a/863?menu_id=682&action_id=863` |
| 付款申请 | `/a/809?menu_id=559&action_id=809` |
| 收入合同 | `/a/609?menu_id=660&action_id=609` |

两次只读浏览器运行均为 `pass=true`、`mutationCount=0`、errors/failures empty：

- light：desktop 1440×960、mobile 390×844，摘要
  `artifacts/playwright/navigation-collection-before-light-10a69c92/summary.json`。
- dark：desktop 1088×960、mobile 320×844，摘要
  `artifacts/playwright/navigation-collection-before-dark-10a69c92/summary.json`。

## 可复现问题清单与前图

| 编号 | 条件 | 可复现事实 | 前图 |
|---|---|---|---|
| NAV-01 | light 1440，项目中心 → 项目创建 | 184px 导航树中，三级图标槽和逐层缩进压缩文本；“项目信息编辑”显示为“项目信息…”，“项目启停管理”显示为“项目启停…”。当前选中项无法仅靠可见名称完整辨识。根级横向溢出为 0，故既有 overflow 指标不会发现问题。 | `artifacts/playwright/navigation-collection-before-light-10a69c92/desktop-project-edit.png`、`desktop-project-lifecycle.png` |
| COL-01 | dark 1088，付款申请 | 单据编号、项目名称、收款单位、付款依据等主信息与辅助事实同时省略；所有列头的调整控件占据固定空间，主身份没有获得清晰的阅读优先级。 | `artifacts/playwright/navigation-collection-before-dark-10a69c92/desktop-payment.png` |
| COL-02 | dark 1088，项目信息编辑 | 项目编号存在省略；表头每列均显示同权图标，使主身份列和辅助列操作处于相近视觉权重。 | `artifacts/playwright/navigation-collection-before-dark-10a69c92/desktop-project-edit.png` |

收入合同层级集合和 320/390 移动样本保留为对照：移动端分别采用卡片或明确允许的集合横向浏览，
本批不把它们误判为同一桌面列宽问题。个人列偏好在本次新会话中未主动变更；复现基于默认受管登录
状态，后续必须另验偏好保持，不能把重置偏好当作修复。

## 实施与退出

下一步只修改共享导航与集合实现，并增加非零定向测试。导航需在不扩大侧栏的前提下降低无用途占位，
同时让完整名称可由鼠标、键盘和触屏取得；集合需建立通用主身份/关键事实宽度策略，降低常驻列头控件
的视觉和空间占用，但保留排序、调整宽度和顺序能力。完成后使用相同入口、主题和视口做前后复核，
并验证查询、翻页、详情返回与列偏好；未复现的问题不列入修复。

多公司“我的工作”返回空事项继续归为既有 P1 服务后续，不属于本专题。
