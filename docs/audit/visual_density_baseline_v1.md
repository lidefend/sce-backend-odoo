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

## 十三、后续迭代项

1. **worksheet 行高统一（独立组件层任务）**: 89px 行高已终版诊断为 TDesign PrimaryTable 固有行为（穷尽样式/属性/布局/size）。需评估三条路径：深挖 TDesign 渲染算法 / worksheet 绕过 PrimaryTable 自定义渲染 / 接受 89px 为已知特性。不阻塞其他渲染细节。
2. **表单间距 token 扩展**: `field_gap`/`column_gap`/`label_row_gap`/`control_row_gap` 已绑定（见十二）；剩余 `field-inline-config` 与 `.label` 内 gap 6px 语义如需独立契约可再拆 token
3. **readonly 值 weight**: 已统一 400（见八修正）——如设计意图强调关键值（状态等）可再评估 550，需设计确认
4. ~~基线自动化~~: 已完成（见十一 `verify.frontend.density.baseline`）
5. **公司支出空态**: 数据归属（bc16 vs bc20）与 action domain 是否对齐，需业务确认
