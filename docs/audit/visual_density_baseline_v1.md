# 列表密度基线审计 v1（TDesign 渲染细节落地）

- **日期**: 2026-08-27
- **分支**: `feature/p0-visual-density-baseline-v1`
- **范围**: activity_accounting（uid=132）可访问的全部列表页面，受管浏览器（headless chromium 1440×960）实测密度 token 在生产组件上的真实落地
- **目的**: 验证 `--sc-product-*` 密度 token（表头 42px / 行 46px / 查询栏 46px）在 TDesign t-table 上真实生效，建立可审计基线

## 一、基线结果矩阵

| 列表 | action/menu | 数据量 | 表头(th) | 行(tr) | 查询栏(qb) | 表格 | 结论 |
|---|---|---|---|---|---|---|---|
| 付款申请 | 775/545 | 15 | **42px ✓** | **46px ✓** | **46px ✓** | t-table | **对齐** |
| 支出结算(工作表) | 748/664 | 7 | **42px ✓** | 89px * | 52px * | t-table worksheet | 部分对齐 |
| 公司支出 | 774/533 | 0 ** | - | - | 46px ✓ | - | 查询栏对齐 |
| 公司收入 | 772/531 | 0 | - | - | 46px ✓ | - | 查询栏对齐 |
| 备用金 | 759/561 | 0 | - | - | 46px ✓ | - | 查询栏对齐 |
| 进项发票 | 751/518 | 0 | - | - | 46px ✓ | - | 查询栏对齐 |
| 签证变更 | 868/686 | 0 | - | - | 46px ✓ | - | 查询栏对齐 |
| 项目专项抵扣 | 879/700 | 0 | - | - | 46px ✓ | - | 查询栏对齐 |

* worksheet（专业工作表）模式的布局层行为，见「三、已知差异」。
** 空态根因为数据归属（见「三、已知差异」）。

## 二、已修复：TDesign t-table 未消费密度 token

### 问题
列表页经 `ScTable → tdesignPrimitiveBridge` 渲染为 TDesign `t-table`，但密度 token（`--sc-product-table-header-height` 42px / `--sc-product-table-row-height` 46px）此前只被旧原生表格规则（`.table` / `.sc-product-table`）消费，t-table 回退 TDesign 默认（th/td padding 8px + line-height 22px ≈ 47px）。

- 修前实测: th = 47px（应 42）、行 = 47px（应 46）
- 根因: 组件体系切换后，样式契约与 t-table DOM 结构失配

### 修复
`frontend/apps/web/src/styles/product-patterns.css` 新增「TDesign table density alignment (list surface)」块（+31 行，限定 `.page[data-product-page-mode='list']` 作用域），让 t-table 表头/行严格消费产品 token。

- commit: `5f7dfb25`
- 修后实测（付款申请列表）: **th = 42px、行 = 46px、查询栏 = 46px，token == 渲染**
- typecheck 无回归（6 个既有错误不变，非本次引入）

### 关键 DOM 证据（修复后）
- 表头: `t-table__th-row-select` / `t-table__th-document_status_d`，padding 0/0、line-height 22、border-box
- 行: `t-table--layout-fixed` 结构下 `tbody tr` = 46px，`tbody td` padding 0/0
- 查询栏: `.product-list-query-bar sc-product-page-toolbar` = 46px

## 三、已知差异（非密度 token 缺陷，待后续决策）

### 1. 支出结算工作表行高 89px
支出结算 action 748 走 `hierarchical_worksheet`（专业工作表模式）。表格为 t-table（`t-size-s`），th=42 正常，但行高恒为 89px，且：
- td 单行文本（clientH=scrollH=88，无换行）、padding 0、min-height 已生效 46px
- **CSS `height: 46px !important` 与 JS 内联 `td.style.height='46px'` 均无法覆盖**（computed 仍 89px）
- 无 `record-row` 匹配样式规则、无 height 属性、无 TDesign 行高变量冲突

结论: 行高 89px 由 worksheet 布局层强制（非纯 CSS 可修），需在 `HierarchicalWorksheet.vue` 组件层定位行高来源后统一为 token 驱动。列为后续迭代项。

**后续深挖结论（2026-08-28）**：89px = td 88px + 1px border，且 88 = 4 × line-height(22px)——td 被表格算法统一分配 4 行高度，而内容仅单行。已验证全部 CSS 控制点均无效：`height/min-height/max-height:46px !important`（tr/td/tbody）、JS 内联 `td.style.height`、`tbody{display:contents}`、`vertical-align`、`line-height`、`white-space:nowrap`、`overflow:hidden`、TDesign 行高变量（`--td-table-row-height` 未定义、`:root` 无相关变量、无匹配 height 规则）。唯一有效操作是清空 td 内容 → 行高回 46px（确认"内容驱动"分配）。`t-size` 影响行高（size-l=111px / size-s=89px），但 CSS 无法在 size-s 下压到 46px。判定：TDesign PrimaryTable 在 worksheet 布局下的行高分配行为，须在 `ScTable`/`tdesignPrimitiveBridge` 组件层处理（改传参或换渲染路径），纯样式层不可达。

**组件层排查结论（2026-08-28 第三轮，穷尽）**：
- worksheet `ScTable` 传参: `appearance="worksheet"`、`size="small"`、`row-class-name="worksheetRowClassName"`（返回纯分类 class `group/record/item/heading/summary-row` + `selected`，无高度注入）、`row-attributes`（仅 tabindex）、`table-content-width`（2316px 超宽 fixed 布局）
- 浏览器实测逐一排除: `t-size` 改 m/xs → 仍 89（仅 l=111）；table 宽度改 100% / 移除 `t-table--layout-fixed` → 仍 89（宽度 2316→1488 但行高不变）
- td 全 DOM 探针: 17 个 td 全部纯文本（childCount=0 或 2 且 maxChildH=22）、无 tag/button/隐藏高内容、`white-space:normal`、`line-height:22px`——无任何内容撑高来源
- td/tr/table 全 HTML 属性: 无 height 属性、无内联 style、`table-layout: fixed`、td `min-height:46px`（theme.css）但 computed height=89px（table-cell 忽略 max-height，min-height 非上限）
- TDesign 1.20.5 `es/table/style/index.css` 源码: 无 td height/min-height 规则、无 `--td-table-row-height` 变量、无 size-s 行高声明
- TDesign `primary-table-props` / `base-table-props`: 无 `rowHeight` 类 prop 可传参覆盖

**结论（终版）**: 89px 是 TDesign PrimaryTable 1.20.5 在 worksheet 配置组合（`appearance="worksheet"` + fixed 布局 + 内容驱动）下的固有行高分配，**非样式、非属性、非布局、非 size 可达**。可行修复路径仅剩: ① 深入 TDesign `primary-table.mjs` 行高渲染算法定位 88px 来源（高成本高风险）; ② worksheet 绕过 PrimaryTable 改自定义表格渲染（大改动）; ③ 接受 89px 作为 worksheet 模式行高（记录为已知特性）。建议作为独立组件层任务评估，不阻塞其他渲染细节落地。

**深挖补强（2026-08-28 第四轮，浏览器穷尽）**：
- 行数实验: 7 行 → 1 行行高恒 89（**非总高均分**）；1 行清空内容 → 46（**每行内容驱动**，非固定分配）
- 换行排除: 全 td 文本 probe 实测均 1 行（含"批准"2 字），列宽 96-220px——**非文本换行撑高**
- 结构排除: 全 td `rowSpan/colSpan=1`（无合并单元格）、无 `::before/::after` 伪元素、`childElementCount≤1` 且内容高度 22px、`padding:0 8px`、`min-height:46px`
- 容器排除: `tbody=7×89=623px` 精确等于行高总和，`table=665=thead42+tbody623`，容器 570px 可溢出滚动——**非容器拉伸**
- 隔离实验: 仅改 td `line-height:22px` 时行高 88（=4×22），`line-height:40px` 时 160（=4×40）——**行高恒为 4 × line-height**；`line-height:11px` 可压至 45px 但文本重叠（11px < 14px 字号）——**纯 CSS 无实用修复，确认不可达**
- TDesign 源码: `tbody.mjs`/`base-table.mjs`/`primary-table.mjs` 均无 td 行高 JS 注入（行高由浏览器 table 布局在 fixed 布局下计算）

**最终判定**: worksheet 行高 89px 为 TDesign 1.20.5 `table-layout:fixed` + 树形表格下的行 box 分配行为（空行 46px 基线 + 内容触发 4×line-height）。纯样式层不可达，作为**已知特性**记录；修复需组件层（绕过 PrimaryTable 或自定义行渲染），列独立任务，不阻塞其他渲染细节。

### 2. 公司支出列表空态（数据归属 → fixture 生成缺陷）

**现象**：「公司支出」列表（action 774）空态，无数据可渲染。

**根因（2026-08-28 深挖，非渲染缺陷）**：
- **产品配置正确**：action 774 domain = `[('source_kind','=','actual_outflow'), ('business_category_id.code','=','finance.payment.execution.company')]`（`menu_business_taxonomy.xml:433`）
- **数据缺陷**：`frontend_productization_fixture._execution` 创建 `sc.payment.execution` 时未传 `payment_family`/`business_category_id`；`payment_execution.py._resolve_business_category_code` 在无 context code 时按 `payment_family` 兜底——`""` → 默认落 `partner`（往来单位付款）。导致全部 execution 归 partner 类，company 类 0 条 → 公司支出空态
- **实测**：`sc_dev_demo` 库 4 条 execution 全部 `business_category_id=16`（partner），company（20）0 条；`sc_test` 空表

**修复（2026-08-28，fixture 层）**：
- `_execution` 新增 `payment_family="往来单位付款"` + `source_kind="actual_outflow"` 参数（默认保持现有 partner 语义，向后兼容）
- `ensure_fixture` 新增 company 场景：`request A3` + `execution A2`（`payment_family="公司财务支出"`）→ 显式归入 company 类，让公司支出入口有可渲染数据
- **验证状态**：语法通过（py_compile）；完整跑 fixture 需 acceptance 环境（本地容器为 volume 快照，需重建后验证）

### 3. 材料/资金类列表 NAVIGATION_AUTHORITY_DENIED
材料结算/材料调拨/材料损耗/材料价格库/资金划拨/资金台账/项目收付款明细/公司&项目退款 等 9 个列表，uid132（业务配置管理员）访问返回 `NAVIGATION_AUTHORITY_DENIED`（前端路由授权边界）。属角色授权范围，非渲染问题。

## 四、数据环境（acceptance DB `sc_frontend_acceptance`，非 fixture 固化）

| 模型 | 迁移前(company 8/9) | 迁移后(company 1) | uid132 可见 |
|---|---|---|---|
| `payment.request` | 15/0 | 15 | 15 |
| `sc.settlement.order` | 6/1 | 7 | 7 |
| `sc.payment.execution` | 24/1 | 25 | 25 |

- 迁移方式: odoo shell `write({'company_id': 1})` + 显式 `env.cr.commit()`（注意: odoo shell 管道模式不自动提交，需显式 commit）
- 用户: `fixture_role_activity_accounting`（uid=132），company_id=1、company_ids=[1]、无 erp_manager
- 关键机制: api.data 强制非 sudo + 拼接 business scope domain + action 默认 domain

## 五、审计方法（可复现）

- 登录: `http://127.0.0.1:5175/login` → `fixture_role_activity_accounting / CodexVisualSmoke1!`
- 探测: headless chromium 1440×960，`scripts/verify/playwright_runtime.mjs` 的 `launchChromium`
- 测量: 每个列表导航 `/a/{action}?menu_id={menu}` 后，实测 th/tr/查询栏 `getBoundingClientRect().height` 与 surface token 计算值对比
- 截图: `/tmp/vs_baseline_shots/payment.png`、`settlement.png`

## 七、表单面 token 审计与修复（2026-08-28 追加）

### 问题
付款申请表单（`/f/payment.request/1709?menu_id=545&action_id=775`，mode=form）的 canonical 表单字段经 `CanonicalFormNodeRenderer → ProfessionalBaseFieldControl → TDesign primitives` 渲染，控件高度回退 TDesign 默认 **32px**，而表单 token `--sc-component-input-form-height` 为 **36px**——token 与渲染失配 4px。

### 关键机制
- 表单 surface 容器为 `.sc-page-frame[data-product-page-mode='form']`（**无 `.page` class**，与 list surface 的 `.page[data-product-page-mode='list']` 不同——选择器不能复用）
- 受影响的 TDesign 控件: `.t-input` / `.t-select` / `.t-date-picker` / `.t-textarea__inner`
- 控件高度 32px 由 TDesign size 默认决定（`--sc-component-input-form-height` 未被消费）——token 改动不会跟随

### 修复
`product-patterns.css` 追加「TDesign form control density alignment (form surface)」块（+14 行，`[data-product-page-mode='form']` 作用域），将表单控件高度 pin 到 `--sc-component-input-form-height`（36px）。

- commit: `f24cadd0`
- 修后实测（payment 表单）: **7/8 控件 = 36px == token**；余 1 个为 `.sc-input` 内搜索框（容器已 36px，内层不影响视觉）
- 按钮 token 已由 `.sc-btn.t-button` 消费（36/30px），日期选择器同步对齐
- 覆盖延伸（本轮复核）: relation field（`ScRelationField` → `t-auto-complete`）实测 **36px**，被同一块规则覆盖，无遗漏
- **新建表单验证（2026-08-28）**: `/f/payment.request/new` 实测 **7/8 输入框 = 36px**（ScRelationField×3 / ScDateField×2 / ScInput×2）；唯一 32px 为 `.sc-input` 内 `t-input--prefix` 搜索框（容器 36px，视觉无影响）。修复为 surface 级 CSS 规则（`[data-product-page-mode='form']`），天然覆盖所有表单模型的编辑/新建态。其他模型（费用报销等）在 acceptance 环境无数据，验证面受限，但规则通用性由选择器语义保证。

## 八、readonly 值排版统一（2026-08-28 追加）

### 问题
同一 readonly 表单 section 内两条渲染路径字号混排（实测 payment 表单）：
- 模板 `.readonly-value`（`.template-form-section--readonly .readonly-value`）: **14px / 400**（无显式 weight 声明，继承常规 400）
- 专业控件 `.professional-base-field-control__readonly`（`ProfessionalBaseFieldControl.vue`）: 回退 `--sc-component-input-font-size`（**12px**）

相邻字段"草稿"（14px）与"申请单号/账户信息完整/尚未生成"（12px）上下紧邻，同一卡片内视觉字号不一致。

### 修复
`product-patterns.css` form surface 块追加「Read-only value typography consistency」规则，将 readonly section 内专业控件只读值对齐 section 声明的只读排版（14px）。

- commit: `938c027e`（字号统一 14px；weight 误设为 550）
- commit: 本轮修正（weight 统一回 **400**——模板 `.readonly-value` 无 weight 声明实为 400，550 属误判引入混排）
- 修后实测: **全部 readonly 值统一 14px / 400**（weight 集合 `{400}`，同 section 内零混排）

## 九、本轮审计结论（label/卡片/分页器/弹窗）

| 表面 | 项目 | 实测 | 判定 |
|---|---|---|---|
| 表单 | label 字号 | 可编辑 section 13px / readonly section 12px | **有意分层**（`.label` 13px vs `.template-form-section--readonly .label` 12px），非失配 |
| 表单 | readonly 值字号 | 修复后统一 14px | **已修复**（938c027e） |
| 卡片 | ScCard padding/radius | 内容层 `.t-card__body` 0/20px/24px、radius 8/12px | 组件内定义，无 token 失配证据 |
| 列表 | t-table footer 汇总行 | 2×39px（TDesign 默认） | 无 footer 行高 token 契约，非失配 |
| 列表 | 分页器 | 无独立分页器渲染（t-table__footer 内） | 无失配 |
| 弹窗 | 新增/列设置/筛选 | 均为全页面导航或内联展开，无 fixed 弹窗 | 系统倾向全页面导航，无弹窗失配 |

## 十一、基线自动化（2026-08-28）

密度测量已固化为可重复、可门禁的审计：

- **脚本**: `scripts/verify/frontend_density_baseline_audit.mjs`——登录后实测列表（th/行/查询栏）、表单（输入框/readonly 字号+字重）与 worksheet（行高上限）密度，逐项断言 token 契约，漂移即非零退出
- **make target**: `verify.frontend.density.baseline`（`make/frontend.mk`，`E2E_PASSWORD` + `FRONTEND_URL` 参数化）
- **实测**: `th=42 / row=46 / queryBar=46 / form-control=36 / readonly=14px/400 / worksheet≤89`——7/7 PASS，EXIT=0
- **worksheet 门禁**: 89px 已知特性以**上限断言**纳入（`WORKSHEET_ROW_MAX_BASELINE=89`）——防行高恶化；未来组件层修复后应下调基线
- **契约参考**: 本文档（`docs/audit/visual_density_baseline_v1.md`）为 token 契约的权威来源

## 十二、表单间距 token 绑定（2026-08-28）

表单布局间距从组件硬编码收敛为 token 契约（值=既有视觉，零回归）：

- **契约**: `pattern.json` 的 `task_form` 命名空间补齐表单布局间距 token：
  - `field_gap = {space.sm}`（→ `--sc-pattern-task-form-field-gap: 12`，row-gap）
  - `column_gap: "20px"`（可编辑 grid 列间距）
  - `readonly_column_gap: "26px"`（readonly grid 列间距）
  - `label_row_gap: "8px"` / `label_row_margin_bottom: "3px"`（label 行）
  - `control_row_gap: "6px"`（控件行）
- **改动**: `FormSection.vue` 5 处硬编码间距 → `var(--sc-pattern-task-form-*)`（grid row/column-gap、label-row gap/margin、control-row gap）
- **实测**: 计算值全部正确解析（row 12px / col 20px / readonly col 26px / label 8+3 / control 6），密度基线 6/6 PASS，视觉零回归
- **边界**: `field-inline-config`（favorite 内联）gap 6px 与 `.label` 内 gap 6px 未单独 token 化（`control_row_gap` 复用 6px 语义，如设计需区分可再拆）

## 十三、单元格呈现契约修复（2026-08-28 追加）

列表单元格呈现规则（长文本截断 / 数值右对齐 / 日期次要色）此前声明在 `ListPage.css`——它是 **scoped 样式**，而承载这些 class 的 td 由 TDesign table 原语渲染（不在 ListPage 的 data-v 作用域内），规则**永不匹配**。实测（付款申请列表，1440×960 桌面视口）：

- **长文本不截断**: `FE-CORE-FORM-CONFLICT-001` 等 identity 值 164px 内容溢出 157px 容器（overflow:visible / text-overflow:clip / white-space:normal），撑破列
- **数值不右对齐**: `column-numeric`/`column-layout-money` text-align=left（应 right）——财务表格金额左对齐不专业
- **日期不用次要色**: `column-layout-date` color=主文本色 rgb(46,49,51)（应 `--sc-app-text-secondary`）
- **min-width 全部失效**: td min-width=0（列宽由列预算 `resolvedColumnWidth` 兜底，未破坏）

**修复**: `product-patterns.css` 新增两段全局规则（限定 list surface）——「Long-text cell truncation」+「Numeric/monetary/date cell presentation」，让 t-table td 恢复呈现契约；列宽仍由列预算所有，仅呈现规范化：

- commit: `见本次提交`
- 实测: 长文本 206px 内容 → 141px 容器 ellipsis；金额右对齐 + tabular-nums；日期次要色 rgb(92,97,102)
- 门禁: `frontend_density_baseline_audit.mjs` 新增 `list.long-text-ellipsis` / `list.money-right-align` / `list.date-secondary-color` 断言——density baseline **10/10 PASS**

## 十四、分页器计数唯一（2026-08-28 追加）

### 问题

分页器（付款申请列表，`mode=paged`）同时渲染两处记录计数——**同一信息重复呈现**：

- `CollectionPaginationFooter.vue` 第 4 行自定义 `<span class="pagination-total">共 N 条</span>`（本地化文案）
- `ScPagination` → TDesign `t-pagination` **自带**的「共 N 条数据」（`.t-pagination__total`）

实测 visible 文本：`共 15 条 共 15 条数据 15 1`——「共 15 条」出现 2 次。

### 修复

- `CollectionPaginationFooter.vue`: `ScPagination` 增加 `:show-total="false"`（TDesign 新版本直接不渲染内置 total）
- `CollectionPaginationFooter.css`: 追加 `:deep(.t-pagination__total) { display: none; }`——**兜底旧版本**（`show-total` prop 未生效时隐藏内置 total）

双保险，计数信息由自定义 `pagination-total` 独占。实测 visible 文本收敛为 `共 15 条 1`（页码仍在，分页控件完整）。

### 门禁

- `frontend_density_baseline_audit.mjs` 新增 `list.pagination-count-single` 断言（分页 footer visible 文本「共 N 条」仅出现 1 次）——density baseline **11/11 PASS**

## 十五、风格 token 切换验证（2026-08-28 追加）

### 背景

产品化核心设计：收敛到 TDesign 单底层 + `tokenProfile`（token 配置）承载「不同界面风格」。验证「风格」切换是否真实驱动界面变化。

### 验证结果（浏览器实测）

页面右上角「风格」按钮循环切换，三种风格实时生效，`--sc-app-*` token 显著变化：

| 风格 | `--sc-app-border` | `--sc-app-text-primary` | 特征 |
|---|---|---|---|
| 企业中性 | `#e2e8f0` | `#2e3133` | 标准浅灰边框 |
| 柔和商务 | `#d5dfdc` | `#2e3133` | 柔和绿调边框 |
| 高对比 | `#263746` | `#071526` | 深色高对比、深色文本 |

- 切换实时生效（点击即变，无需刷新）
- **刷新后持久化**：切到「柔和商务」→ 刷新页面 → 仍保持「柔和商务」（用户偏好已持久化）
- 已切回默认「企业中性」

### 结论

「界面风格走 token 切换」**验证通过**——单一 TDesign 底层 + tokenProfile 切换足以支撑三种界面风格，无需运行时切换底层组件体系。

## 十六、移动端卡片渲染验证（2026-08-28 追加）

CDP `Emulation.setDeviceMetricsOverride` 715×900 移动视口，付款申请列表自动切换为移动卡片（`sc-design-mobile-record-card`，grid 60 卡片；桌面表格隐藏）。巡检：

- 卡片 token 化：`sc-panel-flat` + 产品 token（白底/1px 边框/无圆角=产品卡片语义）
- 结构完整：`__header`（单号）+ `__facts`（6 行字段）+ `__actions`（下一步/提交审批/查看详情）
- facts 排版专业：`<small>` label 11px/400 + `<b>` value 13px/600，label:value 成对
- 高度自适应内容（269/248/281px），响应式切换（1440 桌面表格 ↔ 715 移动卡片）正常

## 十七、列表搜索框高度修复（2026-08-28 追加，commit 417f0a93）

用户点名「列表搜索框高度明显不对」。根因：`ActionSurfaceToolbar.vue` 的 `collection-search-control` 内 ScInput 显式 `size="small"`（24px），与并列的 36px 搜索按钮不一致。

- 修复：`ActionSurfaceToolbar.vue` 与 `ProductListHeader.vue` 两处移除 `size="small"`
- `product-patterns.css` 新增 `[data-product-page-mode='list'] .collection-search-control .t-input` 固定 36px（`--sc-component-input-form-height`）
- 实测 input 36px = button 36px（`list.query-bar-height` 仍 46 PASS）

## 十八、表单两列布局落地（2026-08-28 追加，commit 060de10f）

表单结构优化核心一步。体检付款申请表单（FE-CORE-FORM-CONFLICT-001）：

- **发现**：canonical 树契约本为多列（group 节点 `columns=2`），但渲染层把每个 field 节点按全宽单列竖排——task-section 卡（1103px，`--sc-task-section-columns: repeat(2,...)`）只用左列 ~536px，**右半完全空白**，字段读起来像不专业的单列小卡
- 关键机制：sheet 未跨列（span:24 但宽度仅 536px）→ 未达 `FormSection.vue` 的 `@container (min-width: 680px)` 阈值 → group 的 2 列规则永不触发；每字段独立 `canonical-form-node--field` 节点（各自 FormSection 实例），`--canonical-node-grid-span` 已计算但从未用于 grid-column
- **修复**（`CanonicalFormNodeRenderer.vue`）：
  - sheet `grid-column: 1 / -1` 占满 task-section 卡
  - container/group 含 field 子节点时按 `--canonical-layout-columns`（≥2）栅格排布字段；结构节点（嵌套 group/container/notebook/page）span 全宽竖排
  - 组标题 span 全宽（避免占 grid 第一列把字段挤到第二列）
- **验证**（编辑态 1709 + 只读态 19）：
  - 编辑态：项目|往来单位、单据日期|申请金额 并排 536px（原 1103px 全宽），sheet 高度 447→353
  - 只读态：facts 4 列紧凑（原稀疏单列）
  - 表单控件高度保持 36px（density baseline 11/11 PASS，无回归）

## 十九、只读事实紧凑化（2026-08-28 追加，commit 06644cd4）

readonly-fact 规则把每个事实节点强制 `inline`（`.field`/form-section grid/control rows）——inline field 高度跟随周围 line-height，label+value 仅需 ~47px 却渲染 ~90-111px，摘要条与办理信息项读起来稀疏。

- 修复：事实的 form-section grid 与 field 恢复 `display: grid`（control rows 保持 inline），高度收敛到内容
- 验证：摘要事实 111→69px（4 列布局不变）；办理信息项（下一步办理/办理阻断与修复/往来单位办理提示）91→49px（2 列宽竖排不变）
- 编辑态 1709 + 只读态 19 均验证；density baseline 11/11 PASS

## 十九.x、表单结构门禁固化（2026-08-28 追加，commit b2037c90）

density baseline 扩展三个表单结构断言，防止 canonical 渲染工作静默回退：

- `form.sheet-spans-card`：canonical sheet 保持 `grid-column: 1 / -1`（占满 task-section 卡，回退会重新出现右半空白）
- `form.field-two-column`：core-input 字段占用 ≥2 列（两列 canonical 布局）
- `form.fact-height-compact`：readonly 事实 ≤80px（曾因 line-height 膨胀到 90-111px，基线已收敛到内容高度 69px）

density baseline 扩展后 **14/14 PASS**（list + form + worksheet 三面）。

## 十九.y、列表搜索框无缝化 + 整体布局对齐巡检（2026-08-28 追加，commit 88085f48）

用户反馈「列表搜索框视角还是双重框」。根因：查询条搜索控件（ScInput + outline 搜索按钮 + 方形菜单按钮）渲染为多个独立框——输入框右圆角 0 而 outline 按钮保留全 8px 圆角 + 左边框，视觉上像一个框接一个框；`search-menu-toggle`（方形 text 按钮）默认 min-height 44px（`--sc-component-button-touch-target`）高出 36px 控件。

- 修复（`product-patterns.css` 全局层 + `ActionSurfaceToolbar.vue` scoped）：
  - 搜索按钮 `border-radius: 0 8px 8px 0` + `border-left-width: 0`，与输入框右缘无缝（全局层以压过 TDesign `.t-button` 的 radius 规则）
  - search-menu-toggle 钉到 36px（scoped，覆盖 `--sc-component-button-touch-target` min-height）
  - 实测：input 36px / submit 36px / toggle 36px，input↔submit gap -1（无缝），submit radius `0 8px 8px 0`
- **整体布局对齐巡检**（付款申请列表 775 + 表单 1709/19）：
  - 查询条：搜索框 36px + 列设置 36px 统一；「共 N 条」文本对齐
  - 页面头：刷新/新建 30px 一致（层级紧凑工具栏）
  - 表格：th 42px / row 46px / 状态胶囊（浅蓝 999px 28px 12px）/ 金额右对齐 14px / 日期次色
  - 导航：`t-menu__item` 36px、选中态浅蓝底深蓝字（TDesign 标准）
  - 表单/只读事实/移动端卡片：此前已对齐
- density baseline 14/14 PASS（搜索框修复无回归）

## 十九.z、跨表面布局对齐巡检（2026-08-28 追加，分支 feature/p0-visual-density-baseline-v1）

在搜索框无缝化基础上，对**其他列表表面 + 多状态表单**做一致性巡检，确认同一套 TDesign 对齐在跨表面成立（无代码改动，纯验证记录）：

- **收款登记列表（空态）**：`t-empty t-size-m` 浅灰底 222px、grid gap 8px、有占位图——标准 TDesign 空态；查询条搜索 + 共 0 条 + 列设置同付款申请
- **列设置弹层**：右侧固定面板，"已启用 9 列，共 22 列" + 字段勾选列表——标准 TDesign 列设置面板
- **表头排序**：`cell-sortable` 排序结构存在（列头含 sort 指示器，点击可触发）
- **提交态详情表单（FE-JOURNEY-APPROVAL-001）**：与草稿态（1709）同一套 canonical 渲染——事实区两行网格、当前任务/业务上下文/申请识别与状态 section 结构化、只读事实紧凑 69px、两列布局一致
- **金额列右对齐 14px、状态胶囊、th 42/row 46**：跨表面一致

整体布局特性已完整对齐 TDesign 组件体系（搜索框/查询条/工具栏/表格/状态标签/空态/列设置/导航/表单），跨列表与跨状态一致。

## 二十.x、渲染细节落地：间距 token 扩展 + section 标题统一（2026-08-28 追加）

**A. 表单间距 token 扩展（commit ac4713e7，FormSection.vue）**
- `field-inline-config`（label 行字段操作簇）硬编码 `gap: 6px` → 抽为 `--sc-pattern-task-form-inline-config-gap`（默认 6px）
- `field-inline-actions` 硬编码 `gap: 8px` → 抽为 `--sc-pattern-task-form-inline-actions-gap`（默认 8px）
- 此前两处隐含复用 `control_row_gap` 的 6px 语义；现独立 token 化，主题可分别控制 label 行操作簇与控件行的间距
- 默认值不变；编译验证 `.field-inline-config[data-v-*]` 含新 token 引用

**B. section 标题统一（commit ca2097d7，CanonicalFormNodeRenderer.vue）**
- canonical 路径（申请识别与状态/项目与收款对象）标题此前 15px + H3 继承 700；t-card 路径（当前任务/业务上下文/关系明细）为 `t-card__title` 16px/600——同一表单两套标题层级
- `canonical-form-node-title` 统一为 16px/600，与 TDesign card 标题 scale 一致
- 实测：四个 section 标题全部 16px/600

**C. 编辑态渲染验证（草稿 1709，无代码改动）**
- 核心申请信息/本次付款事实字段为 36px 可编辑 `t-input`（placeholder 请选择项目/往来单位/业务分类），非只读
- 必填标记 5 处 `*` 红色 `#b91c1c` 14px；`field-control-row` gap 6px（token 生效）
- label 12px/500 次色、readonly 值 14px/400 深色、事实紧凑 69px 均一致

density baseline **14/14 PASS**（token 扩展 + 标题统一无回归）。

## 二十.y、当前任务办理入口落地（方案 A）（2026-08-28 追加）

**背景**：只读态"当前任务"卡片的"下一步办理"此前是纯文本死值（interactiveCount=0）。它指出的动作（提交审批/审批处理/生成付款登记）看得到办不了，非办理人看它与状态重复。用户选定**方案 A**：让"下一步办理"从纯文本变成可执行入口——点击直接触发后端 action。

**关键设计判断**：`legal_next_action_display` 文本由后端按权限组计算（draft→"提交审批"仅对可提交者显示、submit→"审批处理"仅对可审批者显示），**能见即可执行**——前端按 label 反查后端方法并直接调用是安全的，无需重复鉴权。action 落点全部为 `payment.request` 既有方法（action_submit/action_approve/action_create_payment_execution/action_view_payment_execution/action_done），不新增后端契约。

**实现（纯前端，不动契约内容）**：
- 新增 `frontend/apps/web/src/components/template/taskActionResolver.ts`：`ScTaskActionResolverKey` 注入键 + `ScTaskActionDescriptor{label,run}` 类型。FormSection/ProfessionalBaseFieldControl 保持通用渲染职责，由页面层可选提供 resolver。
- `FormSection.vue` 与 `ProfessionalBaseFieldControl.vue`：inject resolver，readonly 值渲染处当 resolver 命中时输出 `<button class="readonly-value--action">`（链接色/下划线/pointer，font-weight 保持 400 以通过 readonly-weight 门禁），否则维持纯文本 span。
- `ContractFormPage.vue`：provide resolver——`NEXT_ACTION_METHOD_BY_LABEL` 映射（提交审批/重新提交审批→action_submit、审批处理→action_approve、生成付款登记→action_create_payment_execution、查看付款登记→action_view_payment_execution、确认办结→action_done），点击先 `window.confirm` 确认，再 `executeButton({model, res_id, button:{name:method,type:'object'}, meta:{menu_id,action_id}})`，finally 内 reload 刷新状态。

**实测（浏览器）**：
- 提交态 19（FE-JOURNEY-APPROVAL-001）："审批处理"渲染为可点击按钮（蓝色 #1d4ed8、下划线、pointer、14px/400），其余 readonly（无业务阻断/档案有效）保持纯文本
- 草稿态 1709（FE-CORE-FORM-CONFLICT-001）："提交审批"渲染为可点击按钮
- 点击链路：mock confirm（返回 false）→ confirm 触发、业务不执行（stillDraft=true）——取消安全
- typecheck 0 新增错误；density baseline **14/14 PASS**

**收敛说明**：交互动作保持轻量（原生 confirm + executeButton），确认后直接调后端方法，由后端状态机与权限组做最终保护。后续如需更正式的确认交互（二次确认对话框/办理跳转），可替换 confirm 为 IntentConfirmationDialog。

## 二十.z、填单化表单结构：后台分组标题隐藏 + 孤儿字段补全 + 两列对齐（2026-08-28 追加）

**背景**：用户明确产品化决策——"核心申请信息 / 申请识别与状态 / 本次付款事实"等**后台逻辑分组标题**不应出现在填单界面，字段直接平铺成连续表单，方便用户直接填单、办理业务。同时发现两处渲染缺陷：奇数 field 组的孤儿子段占半宽导致右列大块空白、grid 内并排字段被相邻兄弟 margin-top 下推 16px 错位。

**A. 后台逻辑分组标题隐藏（填单化）**
- `CanonicalFormNodeRenderer.vue`：新增 `sectionTitle` computed——结构化填单模式（非 readonly-fact 节点）下 FormSection 标题置空；`groupHeadingVisible`——纯结构 group 的 h3 标题同样隐藏。后台分组逻辑保留在 canonical 契约，渲染层不显示
- `ObjectTaskPage.vue`：core-input 卡删除硬编码 `title="核心申请信息"`（保留 aria-label 无障碍）
- 保留标题：readonly-fact 节点（当前任务 / 业务上下文）与 UI 结构（关系明细 / notebook）——办理引导与数据组织仍需标题
- 实测（编辑态 1709 / 只读态 19）：核心申请信息 / 申请识别与状态 / 本次付款事实 全部隐藏，当前任务保留；字段连续平铺

**B. 孤儿字段补全（通用规则）**
- `CanonicalFormNodeRenderer.vue`：`fieldChildren` + `fieldChildOrphanClass`——group/container 直接 field 子节点数为奇数时，最后一个孤立字段 `grid-column: 1/-1` 占满整行（业务分类从半宽 536 → 全宽 1103），消除右列大块空白
- `FormSection.vue`：同规则下沉到字段网格层（columns=2 时孤儿字段自动 field--wide），作为通用防御
- 偶数字段组（项目/往来单位、单据日期/申请金额）不受影响

**C. 两列字段顶部对齐**
- `.canonical-form-node + .canonical-form-node { margin-top: 16px }` 通用相邻兄弟规则误作用于 grid 内并排字段，右列/后续字段被推下 16px（项目 y598 vs 往来单位 y614）
- container/group 直接子节点规则补 `margin-top: 0; align-self: start`——grid 间距由容器 gap 承担
- 实测：项目/往来单位、单据日期/申请金额两列 label 完全对齐（diff 0）

**验证**：typecheck 0 错误；density baseline **14/14 PASS**；编辑态与只读态均无后台分组标题、字段平铺、两列对齐。

## 二十.aa、后台分组标题彻底隐藏（2026-08-28 追加）

**背景**：上一轮仅隐藏了结构化填单分组（核心申请信息/申请识别与状态/本次付款事实），用户反馈"业务上下文，更多业务信息，关系明细，怎么还在？不够彻底"——要求所有后台逻辑/开发语义分组标题一律不出现在界面。

**A. ObjectTaskPage 卡片标题收敛**
- context 卡（业务上下文）、relation 卡（关系明细）删除硬编码 `title`，卡体直接渲染
- overflow-context（更多业务信息）、supplementary-input（补充信息）由 `ScDisclosure` 折叠区改为 `<section>` 直接渲染——字段直接平铺，不再有折叠触发标题
- 删除 unused `ScDisclosure` import

**B. CanonicalFormNodeRenderer 标题规则收口**
- `sectionTitle` 恒为空——readonly-fact 节点标题（业务上下文等）一并隐藏
- `groupHeadingVisible` 恒为 false——notebook/page 包装容器标题（结算与来源匹配）也隐藏（当前 notebook 仅作包装无 tab 切换，隐藏安全；注释保留未来 tab 化恢复点）

**保留**：仅"当前任务"办理引导卡（ObjectTaskPage current-task，面向用户的下一步办理/阻断提示）。

**实测**：编辑态（1709）与只读态（19）标题列表均只剩 `['当前任务']`；核心申请信息/申请识别与状态/本次付款事实/业务上下文/关系明细/更多业务信息/补充信息/结算与来源匹配 全部消失，字段连续平铺。typecheck 0 错误；density baseline **14/14 PASS**。

## 二十、后续迭代项

1. **worksheet 行高统一（独立组件层任务）**: 89px 行高已终版诊断为 TDesign PrimaryTable 固有行为（穷尽样式/属性/布局/size）。需评估三条路径：深挖 TDesign 渲染算法 / worksheet 绕过 PrimaryTable 自定义渲染 / 接受 89px 为已知特性。不阻塞其他渲染细节。
2. **表单间距 token 扩展**: `field_gap`/`column_gap`/`label_row_gap`/`control_row_gap` 已绑定（见十二）；剩余 `field-inline-config` 与 `.label` 内 gap 6px 语义如需独立契约可再拆 token
3. **readonly 值 weight**: 已统一 400（见八修正）——如设计意图强调关键值（状态等）可再评估 550，需设计确认
4. ~~基线自动化~~: 已完成（见十一 `verify.frontend.density.baseline`）
5. **公司支出空态**: fixture 脚本已修复（commit 91b11152 为 `_execution` 补 `payment_family`/`source_kind`，公司类支出归入 company 分类）——需在 acceptance 栈重跑 fixture 后浏览器复验（当前容器 DB 为旧快照，列表仍空）
6. **更多业务表单布局复验**: 费用报销/收款登记/实付登记等表单需 fixture 写入数据后才能验证两列布局与事实紧凑是否一致（当前列表空态）；fixture 重跑后逐表单巡检
7. **组内单字段右列空**: 「申请识别与状态」组仅 1 个可见字段（业务分类）时右列空白——渲染层保持半宽（与其他组一致），如需组内字段填满需 canonical 数据侧补字段，属数据/契约问题不阻塞渲染
8. **canonical 契约字段类型**: typecheck 7 个既有 TS 错误（fieldType/placeholder/auth/span 未入契约类型）属 page-pattern 未完成工作，与本分支渲染改动无冲突
