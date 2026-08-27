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

### 2. 公司支出列表空态（数据归属）
迁移至 company 1 的 25 条 `sc.payment.execution` 全部属于 business_category「往来单位付款」（code=`finance.payment.execution.partner`，id=16），而「公司支出」action 774 的默认 domain 要求 `finance.payment.execution.company`（id=20「公司财务支出」）。数据类别与入口不匹配 → 空态。非渲染缺陷。

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

## 八、后续迭代项

1. **worksheet 行高统一**: 定位 `HierarchicalWorksheet.vue` 表格行高 89px 来源，使其消费密度 token（46px）——纯样式层不可达，需组件层（`ScTable`/bridge 传参或渲染路径）
2. **覆盖更多表面**: 卡片、分页器、弹窗/抽屉内表单、详情展示面（read-only）的 TDesign 组件 token 落地审计
3. **表单间距 token**: `--sc-component-form-field-gap` / `--sc-component-form-control-gap` 未定义，字段行距由布局层决定——确认设计意图后补 token 并绑定
4. **基线自动化**: 将密度测量脚本固化为 `make` target + 门禁（复用 `verify.frontend.all_list_visual.audit` 基础设施），并扩展覆盖 form surface
5. **公司支出空态**: 数据归属（bc16 vs bc20）与 action domain 是否对齐，需业务确认
