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

实施只修改共享导航与集合实现，并增加非零定向测试。导航需在不扩大侧栏的前提下降低无用途占位，
同时让完整名称可由鼠标、键盘和触屏取得；集合需建立通用主身份/关键事实宽度策略，降低常驻列头控件
的视觉和空间占用，但保留排序、调整宽度和顺序能力。完成后使用相同入口、主题和视口做前后复核，
并验证查询、翻页、详情返回与列偏好；未复现的问题不列入修复。

多公司“我的工作”返回空事项继续归为既有 P1 服务后续，不属于本专题。

## 共享实现结果

- 导航继续使用公开 `TDesignMenu`、`TDesignSubmenu` 和 `TDesignMenuItem`。深层叶子不再重复投影图标槽；
  完整 label 同时投影为可访问名称和稳定证据属性，现有行高内允许最多两行阅读。没有覆盖官方内部
  selector，也没有扩大 232px 侧栏。
- 列头仍由 `CollectionColumnHeaderControl` 单一接管。排序标题常驻，拖动和调整宽度控件在 hover、
  `focus-within` 时显现，原有 label、拖动和方向键调整事件保持。
- 通用 `row_primary` 获得 208px 自适应 floor，且该 floor 在剩余空间分配阶段继续生效；非主身份、
  关系、日期、金额等仍使用原角色规则。显式用户列宽继续优先，未按项目、付款或合同模型写特殊值。
- 长文本仍通过单元格 title、主身份按钮的官方 Tooltip/可访问名称和移动卡片完整换行取得完整查看路径。
  本批未写入或重置个人列偏好。

产品提交为 `8eb4d5aa`（导航）、`af2e14b4` 与 `92ad5dbb`（集合）；生成清单分别独立提交，P4
浏览器证据增强为 `4bcb5766`、`dc3ca8bd`。组件接管清单最终为 required 35、missing 0、
bridge_only 0、raw 0；官方设计对齐清单 internal vendor selector gap、未知 token、视觉 literal 和
孤立 appearance 均为 0。

## 最终验证与人工复核

- 产品候选：`506d371f2129a8e30942ffa54959331c7f80cd90`，完整指纹
  `b35b2eb1d0a7668623abb5c5a4330a8dbd4bbcabfaadb3ef0d99fffd56f937fb`（7379 paths）。
- 最终证据候选：`dc3ca8bd601f0943aefecf01d144b12ec0b4c2f5`，相对产品候选仅增加 P4 分页/返回探针；
  完整指纹 `fd7fea7a52702f1c3e54e3451898e36fb08037c5c611ccc43750bedbb228c1a1`（7379 paths）。
- `make verify.frontend.quick.gate` 最终通过；严格类型、导航、集合导航控件、列宽契约和官方组件
  清单均非零通过。首次 Quick 失败仅为源摘要变化后的生成清单陈旧；通过受管刷新入口更新后门禁通过。
- 最终 light 1440/390 摘要：
  `artifacts/playwright/navigation-collection-exit-light-dc3ca8bd/summary.json`。
- 最终 dark 1088/320 摘要：
  `artifacts/playwright/navigation-collection-exit-dark-dc3ca8bd/summary.json`。
- 两份摘要各覆盖项目编辑、项目启停、付款、收入合同的 desktop/mobile 共 8 个样本，均
  `pass=true`、`mutationCount=0`、errors/failures empty、root overflow 0。
- 项目和付款在两个桌面主题下均完成 page 1 → page 2 → page 1，`list_offset` 为 0 → 20 → 0；
  查询无结果后清除恢复原记录数。两者在桌面和移动均自动读取首个已渲染记录身份，打开详情再由
  正式返回动作回到集合。收入合同的搜索、详情返回、选择状态和横向滚动位置恢复继续通过。
- 列偏好不通过业务页面写入制造证据：定向契约测试证明显式 column width 仍优先于推导宽度，
  顺序和显隐算法未改；浏览器确认列设置入口、拖动/resize label 和分页 footer 仍存在。

人工同条件对照确认：项目两个入口完整显示并可直接区分；付款主编号从 168px 收缩结果提升到通用
208px floor，前三条完整显示，超长值获得更多阅读空间且仍有完整查看路径；项目名称完整显示，辅助
编号允许按角色省略。移动卡片、收入合同横向集合、表单对齐、根级 Provider 和官方图标未见退化。

本专题本地实现与验证完成，候选服务已停止；结论限于共享前端表达和上述只读样本，不表示已完成
全系统业务验收、远端 CI、合并或发布。下一步可进入独立复核与 PR 交付包整理，不再追加零散美化。
