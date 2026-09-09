# 前端付款旅程表达收口

日期：2026-09-09

状态：付款样板本地候选验收通过并冻结；未执行正式发布、推送或合并

起始 HEAD：`281530827bf2d6297834261e4bf79226ac9bc579`

冻结候选 HEAD：`59212c7940a30006cdac35fca5ab11a5afeded2c`

## 1. 交付结论

本批保留既有 B3+B4 成果，并完成付款申请旅程的最后一次表达收口。记录 `payment.request/15`（`SHOW-PR-04`）贯穿首页、我的工作、付款列表、只读详情和编辑详情。

“我的工作”收起时继续在 1440×900 完整显示四条事项；展开后直接呈现后端提供的完整原始标题，桌面通过键盘、移动端通过触屏均可展开和收起。实现没有按斜杠拆解标题，也不依赖悬停 title 提示。

同一申请金额在首页、我的工作、付款列表和只读详情统一显示为 `¥50.00`；编辑页保持一个 `amount` 字段实例，输入值为 `50.00`，步进为 `0.01`。移动列表仍把金额作为默认关键事实，其余事实完整保留在展开区。

列表查询完成 `70 → 0 → 70`；从 `list_offset=60` 的移动列表打开记录 15 后返回，菜单、排序、页码和真实滚动容器位置均保持。只读和编辑使用独立首次进入路由验收，未以其中一种模式替代另一种模式。

## 2. 分层与归因

- Formal Product Layer：通用契约消费、金额展示、集合返回上下文属于 P0；候选验证器和本报告属于 P4。
- Layer Target：Contract V2 canonical presenter、通用 money formatter/field renderer、标准集合移动卡、工作事项 disclosure、集合上下文运行时和受管候选证据工具。
- Standard vs User-Specific：只消费既有 `fieldDescriptor.currency_field`、Contract V2 `mainData.currency_id`、列 money 角色及原始 `record.label`；没有新增行业默认值、客户偏好或运行时配置。
- Why Here：P1 已提供 `amount → currency_id` 及 `[6, "CNY"]`。缺口发生在 P0：表单 hydration 将 many2one 运行值归一化为数值 ID 后，presenter 错把 ID 当成可展示币种；集合返回也只保存 `window.scrollY`，没有保存实际内部滚动容器。
- Why Not Elsewhere：无需修改付款契约、审批或支付机制；没有猜币种、精度、字段名或标题结构，也没有写业务数据。
- Blast Radius：消费相同货币 descriptor 的通用表单，以及使用标准集合上下文的列表。canonical presenter、集合语义、strict typecheck、完整 Quick 门禁和真实候选旅程共同验证边界。

金额权威链为：原生字段 descriptor 的 `currency_field=currency_id` → Contract V2 `mainData.currency_id=[6, "CNY"]` → canonical presenter 保留带显示标签的权威值 → formatter 由 CNY 得到两位小数和货币符号。若运行态只包含归一化 ID `6`，不得覆盖主契约中的显示标签；若运行态本身带显示标签，则仍可作为更新后的权威值。

## 3. 实现结果

- 工作事项展开区增加“完整事项身份”，值直接等于原始 `record.label`；原有七项辅助/审计事实仍可访问。
- 首页和我的工作统一使用通用货币 formatter；标准列表根据 money 角色和契约货币依赖格式化，依赖字段不泄漏为可见列。
- 只读金额通过 ScMoney 的正式展示标记核验；编辑金额沿用同一权威币种/精度，保持单一字段实例。
- canonical presenter 在运行 many2one 值只有数值 ID 时回退到 Contract V2 主数据的显示值，避免丢失 `CNY`；对应单元用例明确覆盖 `{currency_id: 6}` 与 `[6, "CNY"]` 的组合。
- 集合上下文在打开记录时定位记录所在的真实可滚动祖先，保存其 scrollTop；返回后在同一容器恢复位置，并用锚点恢复焦点。
- P4 浏览器工具使用 ScDropdown/ScButton 的正式语义身份操作移动“更多”菜单，并等待 TDesign 弹层稳定；验证器不通过提高容差掩盖返回偏差。

## 4. 冻结候选与验证证据

冻结候选完整工作树指纹：`b9949ab6ecf5c738ea8093637ea8c3762c2459c6219c353518042c456786334a`，scope manifest `5981d56c5bfa6f8dd531213f76b5bbd3793b56bd1df0d84d51542f94112cf6a7`，共 7327 路径；baseline 为 `3d3975b3d45c1462677df0abcbb5708e4b53e0b1`。

候选绑定既有受管 `local.dev`：project `sc-local-dev`、database `sc_dev_demo`、前端 `127.0.0.1:5176`、API proxy `127.0.0.1:18081`。

静态与受管检查：

- `make verify.frontend.canonical_form_presenter.unit`：PASS，142 cases。
- `make verify.frontend.collection_view_semantics.unit`：PASS，含非零 TS/Python 用例及 guard。
- `make verify.local.dev.frontend.quick.gate`：PASS，含 strict typecheck、5166 modules build、组件/状态/主题/生成清单门禁。
- `make verify.frontend.style_system.guard`：PASS，hardcoded color refs 0。
- `make verify.local.dev.payment_request.floorplan.readonly`：PASS，regions 9、blocked primary 0、mobile overflow 0、business fingerprint unchanged。

冻结 HEAD 的浏览器证据：

| 范围 | 结果 |
| --- | --- |
| 1440×900 明色“我的工作” | 4 条事项完整可见，第四条底部 884px；每条 1 项关键事实、7 项可展开事实 |
| 完整事项身份 | 桌面 keyboard、移动 touch 均完成 false → true → false；原始值与展开值完全相等并包含 `SHOW-PR-04` |
| 跨页金额 | 首页、我的工作、桌面/移动列表、只读详情均为 `¥50.00` |
| 编辑金额 | `amount` 可见实例数 1；value `50.00`；step `0.01` |
| 查询恢复 | 70 → 0 → 70，清除后搜索值为空 |
| 移动返回 | `menu_id=559`、`order=id desc`、`list_offset=60` 均保持；scrollTop `1279 → 1279`，同一容器 maxScrollTop 2894 |
| 390px 明色 | 全部路由 `overflow=0`，主题解析 light；pass=true |
| 320px 暗色 | 首页、工作、列表、只读、编辑均 `overflow=0`，主题解析 dark；pass=true |
| 两组联合 | `mutationCount=0`、`errors=[]`、`failures=[]` |

明色证据位于 `artifacts/playwright/frontend-payment-journey-closure-light-390/summary.json`，暗色证据位于 `artifacts/playwright/frontend-payment-journey-closure-dark-320/summary.json`；同目录含桌面和移动截图，artifact 不作为产品源码提交。

`verify.frontend.professional.extensions.unit` 在 Quick 输出中仍报告 `targets=0`，因此仅登记为 restricted grammar 诊断，不把零测试项单独计为通过；本批的通过结论来自上述非零用例、guards 和真实候选旅程。

## 5. 限制与下一步

本批没有保存、提交审批、支付、删除、关注或配置发布，没有修改数据库、fixture、运行 profile 或业务状态。只验证当前 system_admin 会话，未覆盖其他角色、登录旅程或独立移动端。

正式 `verify.frontend.release.local`、独立评审、推送、PR、合并和发布均未执行，发布状态仍为 `verification_pending`。付款样板至此冻结；下一独立产品批次可以按既定策略进入 C1 层级工作区对齐，但本批没有开始 C1。
