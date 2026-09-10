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
全系统业务验收、远端 CI、合并或发布。独立复核补项和本地 PR 交付包见下文，不再追加零散美化。

## 独立复核补项：列头阅读与操作隔离

- 独立复核指出隐形列头按钮仍可命中、标题与左侧拖动区可能重叠、无悬停触屏入口及真实行为证明不足。
  P0 修复将辅助控件放入标题右侧固定控制带；静止态同时使用 `opacity: 0` 与
  `pointer-events: none`，hover、`focus-within` 和无悬停/粗指针分别恢复公开交互。标题占位恒定，显隐
  不改变文字几何。移动“列设置”触控尺寸由 `ScButton` 的 `column-settings` appearance 统一负责，
  不使用页面深层选择器。
- 最终候选 `d4cecd1cdadbaf343f98915ac19bb23d2e34436d`，完整指纹
  `43decc3a68e985386f97536edf086eec12230338985bacc398a3a5c1ad554b7a`（7379 paths）。最终
  `make verify.frontend.quick.gate`、严格类型、构建、14 项集合导航控件测试及官方设计清单均通过；
  internal vendor selector、未知 token、visual literal 缺口均为 0。
- 浅色 1440/390 摘要：
  `artifacts/playwright/navigation-collection-header-light-d4cecd1c/summary.json`；暗色 1088/320 摘要：
  `artifacts/playwright/navigation-collection-header-dark-d4cecd1c/summary.json`。每份覆盖项目、付款和收入
  合同的桌面/移动 6 个样本，均 `pass=true`、`mutationCount=0`、errors/failures empty。
- 付款桌面实测静止、hover、真实 Tab 焦点三态：隐藏 resize 不命中，显现后可操作，标题边界不移动且
  与控制带不重叠；一次排序仅产生 1 个 `api.data list` 请求，方向键将声明/实际列宽从 80px 调到
  90px，详情返回并刷新后仍为 90px，恢复后回到 80px。偏好 set/get 由浏览器影子响应承载，未写数据库。
  付款移动“列设置”为 44×44px，面板可通过触屏打开和关闭。
- 项目与付款的正式 `preference_policy.allow_order=false`，运行态正确提供 0 个拖动句柄。因此代表页面的
  “实际拖动”不适用，未通过篡改契约或 DOM 制造通过；固定顺序保持不变，允许顺序时的通用算法仍由
  既有非零定向测试覆盖。收入合同继续验证既有横向工作区、范围抽屉和滚动恢复，不把它冒充共享列头。
- 人工复核最终付款桌面、付款/项目移动和收入合同横向工作区截图，未见标题遮挡、触屏入口裁切或新的
  横向退化。本补项不改导航、208px 主身份策略、契约、字段、权限、业务动作或业务数据。

## PR 交付包

状态：`LOCAL_PR_PACKAGE_READY`。本节只整理已冻结候选和整分支差异，没有修改产品代码、重新运行
浏览器矩阵、推送分支或创建 PR。

### 完整身份与范围审计

| 身份 | 值 | 说明 |
|---|---|---|
| 权威远端 | `origin=https://github.com/lidefend/sce-backend-odoo.git` | 只读刷新并核对 |
| 目标主线 | `origin/main@10a69c92e1158c5445aff1054fa7fa5c9acdc14b` | 与专题登记基线一致 |
| 共同基线 | `10a69c92e1158c5445aff1054fa7fa5c9acdc14b` | `merge-base(origin/main, HEAD)` |
| 产品冻结候选 | `d4cecd1cdadbaf343f98915ac19bb23d2e34436d` | 后续只允许交付文档变化 |
| 交付整理源 HEAD | `d81453e77e9c573bcf8ef69db7d6e0dcb1f1c2e4` | 相对产品候选仅 3 个治理文档 |

交付整理前的完整分支差异为 23 commits、22 paths、672 additions、39 deletions。路径全部归类，
没有 `addons/`、`contracts/`、数据库、fixture、Compose/profile、acceptance 恢复或发布实现。

| 分类 | 路径数 | 完整路径与审阅重点 |
|---|---:|---|
| P0 产品前端 | 7 | `ScButton.vue`；`CollectionColumnHeaderControl.css/.vue`；`ListSurfaceHeader.vue`；`CanonicalNavigationMenuNode.vue`；`ListPage.vue`；`listColumnWidth.ts`。审阅导航名称、208px 主身份、列头稳定控制带、触屏尺寸和显式列宽优先级。 |
| P4 验证工具 | 6 | `frontend_collection_navigation_controls_guard.py`、`frontend_list_optional_columns_contract_test.ts`、`frontend_navigation_shell_guard.py`、`local_dev_candidate_visual_smoke.mjs`、`test_frontend_collection_navigation_controls_guard.py`、`test_local_dev_candidate_frontend.py`。审阅非零断言、请求计数、键盘路径和影子偏好边界。 |
| 生成清单 | 4 | `component-driver-takeover-inventory-v1.json`、`component-professionalization-inventory-v1.json`、`official-design-alignment-inventory-v1.json`、`visual-projection-inventory-v1.json`。均由受管刷新入口生成。 |
| 治理文档 | 5 | 本目标、本报告、上下文日志，以及既有官方图标目标和报告。后两者只把 PR #457/main 落地状态从“待草稿 PR”更新为“已合并、未发布”，不包含图标产品差异。 |
| 未分类 | 0 | 无。 |

产品代码集中在 6 个提交：`8eb4d5aa`、`af2e14b4`、`92ad5dbb`、`b3ce2174`、
`68783987`、`cf4e30fc`；其余提交均为 P4 基线、清单、验证或治理记录。完整产品回滚边界为共同基线
`10a69c92…`；交付文档可单独回退，不需要数据库、契约或运行环境回滚。

### 行为边界

- **按字段排序**由列的 `sortable` 能力和排序请求控制。付款桌面实际点击一次只产生一次
  `api.data list` 请求，该能力已验证。
- **调整列顺序**由 `preference_policy.allow_order` 控制。项目与付款的正式契约均为 `false`，因此运行态
  正确不渲染拖动句柄；这不等于禁止按字段排序，也不应通过篡改契约制造拖动通过。
- **调整列宽**继续允许，并保持显式用户列宽优先。浏览器中的影子 preference set/get 只证明前端
  “调宽 → 详情返回 → 刷新恢复”链路，不证明后端已持久化列宽；后端持久化验收保持未覆盖。
- 收入合同是层级工作区，仅用于范围抽屉、横向滚动和返回恢复回归，不冒充共享列表列头样本。

### 候选证据索引

不同候选的结果分别登记，不相加为一次“全量最终重跑”：

| 候选 | 证据 | 结论边界 |
|---|---|---|
| 基线 `10a69c92…` | `navigation-collection-before-light-10a69c92/summary.json`；`navigation-collection-before-dark-10a69c92/summary.json` | 复现导航截断和集合阅读问题；不是修复后证据。 |
| 首轮产品候选 `506d371f…` | 指纹 `b35b2eb1…` | 导航与集合产品实现冻结点；浏览器退出证据在后续仅含 P4 探针的 `dc3ca8bd…` 上取得。 |
| 首轮退出候选 `dc3ca8bd…` | `navigation-collection-exit-light-dc3ca8bd/summary.json`；`navigation-collection-exit-dark-dc3ca8bd/summary.json` | 项目编辑/启停、付款、收入合同，light 1440/390 与 dark 1088/320；每份 8 个桌面/移动样本，零业务写入。 |
| 列头补项候选 `d4cecd1c…` | `navigation-collection-header-light-d4cecd1c/summary.json`；`navigation-collection-header-dark-d4cecd1c/summary.json` | 项目、付款、收入合同，light 1440/390 与 dark 1088/320；每份 6 个样本，验证列头三态、排序一次、键盘调宽/恢复及 44px 触屏入口。 |
| 交付文档 HEAD | 产品候选之后仅目标和报告 | 没有重新运行无变化的浏览器矩阵。 |

产品候选 `d4cecd1c…` 的完整指纹为
`43decc3a68e985386f97536edf086eec12230338985bacc398a3a5c1ad554b7a`（7379 paths）。

### PR 草稿

建议标题：

`refactor(frontend): improve navigation and collection readability`

建议正文：

#### Summary

- 在不扩大侧栏的前提下减少深层导航的重复图标占位，使当前入口完整名称可由鼠标、键盘和触屏访问。
- 为共享集合建立通用 208px 主身份宽度下限，同时保持显式用户列宽优先，不按业务模型写特殊宽度。
- 将列头辅助操作收进稳定的右侧控制带；隐藏态不响应指针，hover、键盘焦点和无悬停设备均可发现，标题几何不随显隐变化。
- 通过 `ScButton` 公共 appearance 提供移动列设置 44×44px 触控尺寸，并补齐共享守卫和受管浏览器证据。

#### Scope and architecture

- Formal Product Layer：P0 通用前端表达；P4 只承载守卫、浏览器证据、生成清单和交付文档。
- 不修改菜单树、名称、路由、权限、contract/schema、业务动作、字段、数据或个人偏好事实来源。
- `allow_order=false` 只禁止列顺序拖动；按字段排序仍由 `sortable` 与排序请求独立控制。
- 表单对齐、根级 ConfigProvider 和官方图标映射保持冻结。

#### Verification

- `make verify.frontend.collection_navigation_controls.unit`：PASS，14 项 Python 守卫及 12 个集合分页用例非零通过。
- `make verify.frontend.quick.gate`：PASS，包含严格类型、lint、production build 和官方组件清单。
- `make local.dev.verify_authority`：PASS。
- 首轮退出候选 `dc3ca8bd…` 的两份 8 样本矩阵，以及列头补项候选 `d4cecd1c…` 的两份 6 样本矩阵，均分别 PASS、零业务写入、errors/failures empty；未合称同一候选全量重跑。
- 列宽影子响应只证明前端恢复链路，后端偏好持久化未验收。

#### Risk and rollback

- 整分支属于 `HIGH_RISK` fail-closed 路由，应按产品前端、验证工具、生成清单和治理文档四组审阅。
- 共享导航、列宽推导和列头交互影响跨模型列表；回滚可按列头 → 集合 → 导航的提交边界逆序执行，或整体回退到 `10a69c92…`。
- 不包含数据库或契约变更，回滚不需要模块升级、fixture 或数据操作。

#### Not included

- 后端列偏好持久化、多角色、真实业务写入、acceptance、旧版本升级兼容和发布验收。
- 项目/付款正式契约禁止的列顺序拖动不计为已通过的页面能力；允许顺序时的通用算法仅由定向测试覆盖。
- 图标专题的两处文档变化只登记 PR #457 已合入主线，不重新打开图标迁移。

### PR/CI 状态与未执行项

本地分类器绑定 `10a69c92…d81453e7` 得到：`lane=HIGH_RISK`、`frontend_mode=standard`、
`professional_mode=full`、`frontend_changed=true`、`backend_changed=true`、
`frontend_full_required=false`，原因为 `unknown_path_fail_closed`。净差异没有后端产品文件；
`backend_changed=true` 是分类器的 fail-closed 路由结果，不能手工降级。

| 项目 | 状态 | 说明 |
|---|---|---|
| `public_guard` | `not_run` | 尚未推送或创建 PR。 |
| `professional_quality_gate` | `not_run` | HIGH_RISK 要求 full。 |
| `frontend_release_gate` | `not_run` | exact-head PR 检查。 |
| `merge_policy_gate` | `not_run` | exact-head 聚合/合并门禁。 |
| `release_candidate_gate` | `not_run` | 后续显式候选发布资格，不能冒充 draft PR 或合并检查。 |
| `make pr.push` / `make pr.create` | `not_run` | 本轮明确禁止远端写入。 |
| 后端偏好持久化、acceptance、发布验收 | `not_run` | 不在本专题授权范围。 |

`make pr.status` 只读确认当前分支没有关联 PR。下一步仅在单独授权后，重新核对 clean worktree、
`origin/main` 和最终 HEAD，再通过 `make pr.push` 与 `make pr.create` 发布草稿；ready、merge 和 release
继续分别授权。
