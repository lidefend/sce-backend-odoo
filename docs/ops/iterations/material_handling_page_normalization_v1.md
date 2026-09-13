# 材料办理页面规范化实施清单 v1

## 候选与范围

- 专题分支：`codex/material-handling-page-normalization-v1`
- 实际基线：`097f0deadf800d51a8527836d4a67a946e68ea6a`（执行时与 `origin/main` 一致）
- 基线完整指纹：`b65a777dc2a4ce17970b4e731020285fa849de745fd34b7cc89b25c4e2a00dc8`
- 产品范围：材料入库、材料出库、材料退货的列表、新建、查看及已有编辑态。
- 排除范围：综合工作台、低代码配置器、其他业务扩展、库存/计价/审批/权限/状态流转/业务写入规则、数据修复、推送、PR、合并。
- Formal Product Layer：P1 页面与元数据声明为主；仅修复本专题证实的 P0 通用契约传递或渲染消费缺陷。

## 源码与运行候选身份

- 初次现状观察时，`local.dev` 后端源码挂载、Nginx 静态目录和 Vite 进程均指向主仓库 `dbf1e171281bd920c39099be7085718c892b10f4`，且 `SC_SOURCE_REVISION=unknown`；该观察仅用于发现问题，不作为候选验收。
- `dbf1e171` 是专题基线 `097f0dea` 的两代祖先。本专题 P1 模型、视图和表单策略模板在两者间无差异；相关前端差异仅是一对多关系候选项保持逻辑，不影响本清单所述分区、隐藏列或只读行状态问题。
- 已通过 `make local.dev.frontend`、`make local.dev.up`、`make local.dev.health` 将日常开发载体重新绑定到专题工作树；只读挂载核对为：
  - `/mnt/source-addons <- /home/lidefend/workspace/sce-backend-odoo-material-handling-v1/addons`
  - `/usr/share/nginx/html <- /home/lidefend/workspace/sce-backend-odoo-material-handling-v1/frontend/apps/web/dist-dev`
- 运行身份固定为 `sc-local-dev` / `sc_dev_demo` / `^sc_dev_demo$` / `sc_local_dev_*` / `18081`。入库样板已通过受管 `smart_construction_core` 增量升级刷新 P1 契约和视图；未重建环境、未修改业务记录。

## 三个正式入口映射

| 办理事项 | 正式菜单 / 路径 | action / 模型 | 最终视图根与合成关系 | 入口身份结论 |
|---|---|---|---|---|
| 材料入库 | `menu_sc_material_inbound`；项目中心 / 材料成本 / 材料入库 | `action_sc_material_inbound_handling`；`sc.material.inbound` | tree：`view_sc_material_inbound_tree` 后叠加审计字段扩展；form：仅 `view_sc_material_inbound_form`；search：仅 `view_sc_material_inbound_search` | 运行菜单“材料入库”、治理菜单基线“入库单”、action/pageName“入库办理”、tree/form/navigation“入库单”指向同一事项。既有正式集成矩阵明确保留 `sc.material.inbound 入库办理`；不改菜单树，样板仅把 tree/form/search 页面标题对齐为“入库办理”。 |
| 材料出库 | `menu_sc_material_outbound`；项目中心 / 材料成本 / 材料出库 | `action_sc_material_outbound`；`sc.material.outbound`，domain 限定 `outbound_type=issue` 与 `material.outbound` 分类 | tree：`view_sc_material_outbound_tree` 后叠加审计字段扩展；form：仅 `view_sc_material_outbound_form`；search：仅 `view_sc_material_outbound_search` | 未改菜单树；action、tree、form、search 已统一为“出库办理”，记录页标题仍使用业务对象“出库单”。 |
| 材料退货 | `menu_sc_product_material_return_v1`；项目中心 / 材料成本 / 材料退货 | `action_sc_material_supplier_return`；`sc.material.supplier.return` | tree/form/search 均只有各自 `view_sc_material_supplier_return_*` 根视图 | menu/action/tree/form/search 已统一表达“材料退货”。它不同于 `sc.material.outbound` 的内部“退库办理”，后者不在本专题第三页面范围内。 |

## 关键事实、分区与明细（实施前基线）

| 办理事项 | 关键事实及权威来源 | 当前源分区 | 当前运行契约与渲染偏差 | 明细声明与目标顺序 |
|---|---|---|---|---|
| 入库 | `name` 单号；`state` 状态；`project_id` 项目；`inbound_date` 日期；`supplier_id` 供应商；`warehouse_id` / `dest_location_id` 仓库库位；`amount_total` / `tax_included_amount` 金额；均来自 `sc.material.inbound` | 原生 form 正文双列 group 已声明上述事实，notebook 承载入库明细、说明、附件、来源追溯。P1 `material.inbound` 策略另声明“办理类型 / 项目与业务对象 / 入库明细 / 办理说明 / 来源与系统追溯”。 | 同一候选的运行库 P1 策略已是正式分区，但 `ui.contract.v2` 输出被改写成 `核心信息 / 高级信息`；floorplan 最终首屏“基本资料”只剩重复状态，其他事实进入“更多业务信息”。首次偏差位于 P0 策略注入后的治理归一化传递链。 | XML 当前为来源验收明细 → 材料档案 → 隐藏技术产品 → 规格 → 单位 → 数量 → 单价 → 金额 → 备注 → 默认提示。目标为材料档案 → 规格 → 单位 → 数量 → 单价 → 金额 → 来源验收明细 → 辅助信息。 |
| 出库 | `name`、`state`、`project_id`、`outbound_date`、`receiver_id`（领用单位）、`warehouse_id` / `source_location_id`、`amount_total`；均来自 `sc.material.outbound` | 原生正文双列 group；notebook 承载出库明细、说明、来源追溯。P1 策略有办理类型、项目对象、出库明细、办理说明、执行结果、来源追溯。 | create/readonly 运行契约同样被通用 `core/advanced` 覆盖；日期、用途、领用单位以及查看态金额落入 advanced。金额为 0 是当前记录事实，不归类为页面缺陷。 | XML 的 issue 场景仍携带仅 return 适用的来源列表达；技术产品已声明隐藏但最终列投影泄漏。后续按材料身份/规格单位/数量/价格金额优先，条件适用的来源关系与累计退货信息后置。 |
| 退货 | `name`、`state`、`project_id`、`return_date`、`supplier_id`、`warehouse_id` / `source_location_id`、`amount_total`、`source_inbound_id`；均来自 `sc.material.supplier.return` | 原生正文双列 group，另有“退货说明”group；notebook 为退货明细与办理提示。运行库当前 `form_policy_json={}`，契约退化为 `core/advanced`。 | 普通 many2one 资料可能经通用角色向上归纳显示为“关系明细”；必须以“原始分组 → 契约角色 → 父节点归纳 → 标题”定位。`state` 模型字段没有中文 `string`，已证实 P1 标签源缺口。当前 demo 无正式退货记录，只能核对创建态，不能伪造查看态金额或来源。 | XML 当前为来源入库明细 → 材料档案 → 技术产品 → 规格 → 单位 → 数量 → 单价 → 金额 → 备注。后续确认技术产品是否需业务可见；材料身份优先，来源关系后置。 |

### 材料档案与技术产品

- `material_catalog_id` 是 P1 材料档案事实；`product_id` 是 Odoo 库存产品技术关联。二者不是可直接删除的同义字段。
- 入库和出库 XML 已把 `product_id` 声明为静态不可见；契约 `columns_schema` 与 `column_occurrences` 仍保留 `invisible=true`，但最终 `tree.columns` 再次包含该字段，属于 P0 可见列投影缺陷。
- 本专题修复隐藏声明传递，不删除模型字段、不由前端推断两个事实的等价性。

### 来源关系显示名

- 入库样本 `acceptance_line_id=2` 的权威 `display_name` 当前为 `sc.material.acceptance.line,2`；前端只是消费该值，没有拼造名称。
- `sc.material.acceptance.line` 没有业务 `_rec_name` 或显示名计算，因此入库 M5 首次偏差属于 P1 元数据表达。
- 样板将由来源明细模型基于既有验收单号与材料身份形成权威显示名；不新增前端模型/字段特判，不修改来源关系或业务数据。

## 办理动作既有条件

| 事项 | 保存与草稿 | 提交 | 确认 | 退回 / 取消 |
|---|---|---|---|---|
| 入库 | 保存沿用 `form.save` 与现有 required/onchange；终态 `received` 当前记录由有效能力降级为 readonly | `action_submit`：仅 `draft`；材料用户或经理 | `action_receive`：仅 `submitted`；材料经理；沿用既有库存校验/写入 | `action_reset_draft`：仅 `cancel` 且经理；`action_cancel`：`draft/submitted` 且经理 |
| 出库 | 保存沿用现有字段修饰、校验与草稿行为 | `action_submit`：仅 `draft` | `action_issue`：仅 `submitted` 且经理；不改审批、库存、计价和成本台账 | `action_reset_draft`：仅 `cancel` 且经理；`action_cancel`：`draft/submitted` 且经理 |
| 退货 | 保存沿用现有 required/onchange 与 `line_ids` 草稿可编辑条件 | `action_submit`：仅 `draft` | `action_confirm_return`：仅 `submitted` 且经理 | `action_reset_draft`：`submitted/cancel` 且经理；`action_cancel`：`draft/submitted` 且经理 |

## 首次偏差与修复归属

| 现象 | 首次偏差位置 | 归属 | 样板处理 |
|---|---|---|---|
| P1 正式章节变成 core/advanced | `UiContractV2Handler` 注入策略后调用通用 contract governance；既有 `field_groups` 被通用分组覆盖，随后才被当成“业务策略分组”保存 | P0 契约传递 | 在治理前冻结已注入的权威业务分组，治理后恢复并生成 form structure；增加非材料反例测试，证明不引入字段名特判。 |
| 已声明静态隐藏的明细列重新可见 | tree parser 生成 `columns_schema.invisible=true` 后，`_business_x2many_tree_columns` 仍只按字段类型生成最终列 | P0 契约投影 | 最终列排除静态隐藏与 handle 列，保留条件隐藏列供运行时判断；增加通用解析测试。 |
| 查看态“行变更 / 未变更”固定占首列与移动卡片 | `X2ManyRelationRenderer` 对任意非空 `one2manyRowStateLabel` 插入只读状态列；未变更持久行也返回标签 | P0 渲染消费 | 只读态不展示草稿变更列；编辑态保留清晰的新建/修改/删除/未变更表达。 |
| 只读且部分空值的资料整体进入更多信息 | `composeCanonicalFormFloorplan` 以整块“所有可见字段都有值”为直接展示条件；块内一个空字段会连带降级后续已有值事实 | P0 表达策略 | 改为逐字段按可呈现值投影，已有值事实直出、空事实进入溢出区；不改 required、不按字段名加权。 |
| 新建态的可编辑日期、供应商变为只读 | `p1_daily_business_form_orchestration_contract_data.xml` 的模型级只读事实契约显式覆盖原生可编辑性；action 级 `noupdate=1` 契约未声明反向覆盖 | P1 契约声明 | 模型级事实契约不再强制这两个原生办理字段只读，交回原生视图/状态修饰符决定；运行库记录经受管升级验证。 |
| P1 已声明“基本资料 → 入库明细 → 办理说明”，新建态却把全部可编辑字段放到明细前 | floorplan 只按 required/editable 分类，`ObjectTaskPage` 再把整个 supplementary region 放到 relation 前，丢失 formal form structure 的槽位顺序 | P0 契约消费 | presenter 传递权威槽位序号；floorplan 以首个业务明细槽位为边界，关键事实留在明细前，明确声明在后的说明/附件进入明细后补充区；无声明时仅按原规范化顺序保守回落。 |
| 页头状态已完整承接，正文仍重复状态 | 页头的精确 statusbar 节点认领只传给 native bridge，task floorplan 未消费 | P0 渲染消费 | 同一精确节点身份传入 floorplan；只排除被页头认领的节点，不按字段名或状态值猜测，其他状态字段仍保留。 |
| “入库明细”连续出现两次 | floorplan 容器标题与 `FormSection` 外部字段标签、明细组件内部标题均可能同时持有同一名称 | P0 标题所有权 | 同名单一关系容器让位于明细集合；专业明细在读写态统一拥有标题、数量与操作区，外部字段标签不再重复。 |
| 后置来源名称换行撑高明细 | 一对多表格只给首列和金额列稳定宽度，后置 many2one 被压缩；只读文本没有完整值访问承载 | P0 列呈现 | 通用 many2one 列使用 260px 呈现宽度；只读文本单行省略并以公开单元格 slot 的 `title` 保留完整权威值，金额列仍为 140px 右对齐；不使用组件内部选择器。 |
| 入库标题不一致、明细来源列靠前 | action/form/tree/search 与 XML 明细顺序 | P1 视图组织 | 保留正式 action“入库办理”并对齐 tree/form/search 页面标题；不改菜单树；材料事实优先、来源关系后置。 |
| 来源显示 `模型名,ID` | 来源明细模型缺少业务显示名 | P1 元数据 | 增加权威显示名计算，前端只消费结果。 |
| 退货显示 `State` | `sc.material.supplier.return.state` 缺少中文 `string` | P1 元数据 | 已补 `string="状态"`，不改状态值或流转。 |

## Batch-A 入库样板实施与验证（历史阶段记录）

1. P0：保留权威业务分组跨 contract governance；修复静态隐藏一对多列；移除只读“行变更”主列。所有修复均按通用契约/渲染能力实现，无材料模型或字段名判断。
2. P1：对齐材料入库入口标题；把基本事实与 `line_ids` 分章；重排可见明细列；为验收来源明细提供权威显示名。
3. L1：`make ci.local.iteration`，再运行受影响的 Python/TypeScript/Vue 纯测试；不运行完整 Quick。
4. L2：运行非零的 P0 契约边界、native parser、canonical floorplan/X2Many，以及 `smart_construction_core` 入库模型/视图定向测试。
5. L3：L1/L2 通过后，才运行受管 `make local.dev.upgrade MODULE=smart_construction_core`；随后复核 `sc-local-dev/sc_dev_demo` 权威和同一记录契约。
6. 产品样板：同一 `S80-MIN-001`、同一 1440×960 视口生成修改前后首屏、明细、底部对照；新建态执行未提交交互，不触发业务写入。1088、390、320 与 light/dark 矩阵在样板复核通过后随三页覆盖执行。
7. 入库样板提交人工复核后，才把已验证规则推广到材料出库与材料退货。完整 Quick、冻结候选、独立复核与交付收据后置。

### 入库样板运行结果

| 核对点 | 源声明 | 最终契约 | 渲染结果 |
|---|---|---|---|
| 入口身份 | menu `menu_sc_material_inbound`；action `action_sc_material_inbound_handling`；form/tree/search 均指向 `sc.material.inbound` | `pageName=入库办理`，form navigation 保留既有记录标题“入库单” | 菜单“材料入库”、办理页签“入库办理”、记录页“入库单 / S80-MIN-001”均明确指向同一事项；未改菜单树。 |
| 查看关键事实 | P1 `material.inbound` 策略明确 `business_identity`、`business_facts`、`document_lines`、`handling` | `fieldRoles` 将项目、日期、供应商、仓库、金额归入 `business_facts`；readonly profile 的已有值不再因同块空字段整体降级 | 首屏直接显示单号、状态、项目、日期、供应商、仓库/库位、金额和来源验收单；“基本资料只有重复状态”已消除。 |
| 新建顺序与可编辑性 | 原生 XML 的日期、供应商可编辑；模型级 P1 事实契约不再覆盖 readonly | create 契约中 `inbound_date`、`supplier_id` 为可编辑；`createFieldCodes` 无缺失关键事实 | 基本信息及日期/来源/供应商/仓管员先于入库明细；日期不折叠，添加明细和保存/提交入口可达。 |
| 明细列与来源显示 | XML：材料档案、规格、单位、数量、单价、金额、来源、备注、默认提示；技术产品静态隐藏 | 最终列与源顺序一致，排除 `sequence`、`product_id`；来源关系由 P1 `display_name` 提供业务值 | 查看态无固定“行变更”列；来源显示“验收单号 / 材料 / 规格”，不再显示 `sc.material.acceptance.line,ID`。 |
| 终态动作 | 记录 `S80-MIN-001` 为 `received`；权限模型仍有 write，记录有效能力为 `write=false` | `effectiveRenderProfile=readonly`，editable fields/save/edit transition 均为 0 | 显示“查看/已入库”，不暴露保存或编辑入口；未改变状态流转与动作条件。 |

证据位置：

- 修改前，同一记录/同一视口（首屏、加载中的明细与底部协作区同屏）：`artifacts/playwright/material-handling-page-normalization/before-exact-097f0dea/material-inbound-terminal-readonly.png`
- 修改后首屏：`artifacts/playwright/phase10-material-domain/material-inbound-terminal-readonly-top.png`
- 修改后明细：`artifacts/playwright/phase10-material-domain/material-inbound-terminal-readonly-detail.png`
- 修改后底部：`artifacts/playwright/phase10-material-domain/material-inbound-terminal-readonly-bottom.png`
- 修改后未提交新建态：`artifacts/playwright/phase10-material-domain/material-inbound-create-top.png`
- 运行摘要：`artifacts/playwright/phase10-material-domain/summary.json`，`pass=true`、`mutations=[]`，action 546、menu 494、记录 1。

样板阶段没有既有可编辑入库记录；以 create profile 验证可编辑规则，以 received 记录验证查看规则，不为编辑态伪造数据。当时完整视口/主题矩阵、出库、退货、冻结 HEAD、Quick receipt 与独立复核尚未开始；后续结果见 Batch-B/C。

### 入库样板人工复核补项

- P1 最终契约已经按 `business_identity → business_facts → document_lines → handling` 明确分区，因此说明与附件前置首次偏差归属 P0，不改 P1 字段必填性。修复后 1440 诊断中五项关键事实绝对顶部均小于明细顶部 `677.39px`，明细后补充区顶部为 `832.39px`，`note` 与 `attachment_ids` 各只出现一次。
- 首次真实复核按门禁在 1440 停止：正文状态已为 0、来源行高已为 39px，但关系区仍发现两个“入库明细”。DOM 证据显示它们分别由 `FormSection` 外部 `label` 与集合内部 `.o2m-title` 持有；因此进一步修正专业明细标题所有权，而不是隐藏文本或加页面 CSS。
- 修正后 1440 聚焦复核通过：正文状态 0、关系区标题 1、来源完整业务名保存在单元格 `title`、行高 39px；新建关键事实全部在明细前，说明/附件都在明细后的“补充信息”。浏览器前后业务指纹一致，未触发 create/write/unlink/action/upload。
- 本轮只运行受影响区域的 1440/1088 聚焦复核。列表、安全反例、完整材料旅程、390/320、明暗主题、出库/退货和 Quick 均按人工复核节奏后置，不能把该证据称作完整浏览器验收。

## 当前明确不推断的业务语义

- 不把出库样本金额 0 解释为页面错误，不修数。
- 不为退货缺少 demo 记录创建业务值或截图数据；查看态需要后续已有权威记录或受管 fixture 能力。
- 不决定材料档案与技术产品的业务合并；只执行已有静态隐藏声明。
- 不改变动作禁用原因、字段校验、草稿写入、审批、库存、计价、权限或状态流转。
- 不把 many2one 类型本身解释为“关系明细”章节；章节身份以源分区和契约显式语义为准。

## Batch-B/C 出库、退货推广结果

### 源声明—契约—渲染闭环

| 页面 / 模式 | P1 源声明 | 最终运行契约 | 最终渲染与首次偏差归属 |
|---|---|---|---|
| 出库查看 | 原生 form 与 P1 category policy 均按办理身份、基本资料、出库明细、办理说明组织；XML 明细把材料、规格、单位、数量、单价、金额置前，来源领用与备注置后 | `presentationMode=task`、`effectiveRenderProfile=readonly`；`sourceSectionTitles` 为办理身份、基本资料、出库明细、办理说明 | 关键事实先于明细；状态仅由页头承接；列头为材料档案、规格型号、单位、出库数量、出库单价、出库金额，原领用明细和备注后置。P1 负责标题/列序，P0 负责状态认领、隐藏列和明细呈现。 |
| 出库新建 | 原生 XML 的“出库主信息 / 项目与仓库 / 出库明细 / 说明与附件”顺序明确，已有 action-scoped orchestration 仍是该创建入口的结构权威 | 运行候选保持 `business_view_orchestration` 权威；`sourceSectionTitles` 保留出库明细先于说明与附件 | 项目、日期、仓库、库位、领用单位等先于明细；说明/附件进入明细后补充区。没有把全部可编辑字段机械前置，也没有由前端猜业务字段。 |
| 退货新建 | 新增 P1 category policy，明确办理身份、基本资料、退货明细、退货说明与附件；XML 把普通资料移出明细页，把材料/数量/金额置前、来源入库明细后置，并声明 `state` 三模式只读 | `presentationMode=task`、`effectiveRenderProfile=create`；`sourceSectionTitles` 为办理身份、基本资料、退货明细、退货说明与附件；状态标签为“状态”，最终状态策略保持只读 | 页面身份为“材料退货”；项目、退货仓库/库位、来源入库单、供应商、日期、经办人先于明细；新建状态不提供可编辑正文控件；说明/附件在后；空态紧凑且“添加退货明细”可达。P1 修标签/分区/列序，P0 只消费显式槽位和只读策略。 |

退货在受管 `sc_dev_demo` 中没有现有记录，因此未补造查看态数据。出库现有记录为终态查看，创建态用未提交表单验证编辑表达；未执行保存、提交、fixture reset 或业务数据修改。

### 实际改动分类

| 分类 | 主要文件 | 所有权说明 |
|---|---|---|
| P1 页面与元数据 | `smart_construction_core/models/core/material_acceptance.py`、`material_supplier_return.py`、`models/support/business_form_policy_templates.py`、两份材料视图 XML、两份既有 orchestration 数据 XML、模块版本与 P1 测试 | 建筑行业标准页面身份、字段标签、正式章节、列顺序和权威关系显示名。未改库存、计价、审批、权限、状态流转或写入规则。 |
| P0 契约与通用渲染 | native tree/form parser、`ui_contract_v2.py`、canonical presenter/render model/floorplan、`FormSection`、`ObjectTaskPage`、`X2ManyRelationRenderer` 及对应测试/guards | 修复已声明分区/隐藏/状态身份的传递和消费；实现不包含材料模型名或字段名判断。 |
| P4 只读证据 | `local_dev_material_domain_ids.py`、材料 browser shell/MJS 与证据 guard 测试 | 复用 `local.dev/sc_dev_demo/18081`，绑定业务记录指纹与完整工作树指纹；只读或未提交交互，无自建环境/数据库/fixture。 |

### 开发期浏览器证据

| 视口 / 主题 | 完整 dirty 工作树指纹 | UTC 时间 | 结果与证据 |
|---|---|---|---|
| 入库人工复核样板 1440/1088 浅色 | `5a761e9780fe6c43391c56c1b35e04120bdaec7243d1905a9971374b7d26aefe` | 2026-09-13 09:53:09—09:53:28 | PASS；`artifacts/playwright/material-handling-page-normalization/inbound-refinement-5a761e9780fe/summary.json`。正确的新建明细链接为 `material-inbound-refinement-1088-create-detail.png`。 |
| 三页 1440×960 / 1088×791 浅色 | `d406e8160b568d5aeab77935b32dc03234aa6b631f6e335f765e29a8c38a25da` | 2026-09-13 10:33:58—10:34:48 | PASS，30 张首屏/明细/底部截图；`outbound-return-desktop-d406e8160b56/summary.json`。 |
| 三页 390×844 浅色 | `fe698b6d58a4be09d123fd036f3d03a3be394976a75eaa1e7db3187fe580e1a6` | 2026-09-13 10:37:15—10:37:40 | PASS，移动卡片前六项为主事实，辅助事实触摸展开可达；`mobile-390-light-fe698b6d58a4/summary.json`。 |
| 三页 320×720 深色 | 同上 | 2026-09-13 10:37:51—10:38:15 | PASS；提交/保存动作可达，空明细添加入口清楚；`mobile-320-dark-fe698b6d58a4/summary.json`。 |
| 人员档案、项目台账、付款详情共享反例 1440 | `7a9016154d0a1157b0b59faa1d8f4a48c3d548461f662749ef51a114e08b1bc8` | 2026-09-13 10:51:02—10:51:18 | PASS；普通事实未被 task Floorplan 错归关系区，workspace 保持 native authority，付款 task 页分区正常；`shared-regression-7a9016154d0a/summary.json`。 |

所有成功摘要均为 `mutations=[]`，shell 前后比较的材料、项目、人员、付款业务指纹一致。最终干净候选的完整指纹和最终矩阵在 tracked 文档冻结后记录到生成证据，避免以文档自引用改变指纹。

### 已解决、未覆盖、契约缺口

已解决：

- 三页入口/页头身份、关键事实首读、明细前后顺序、状态重复、明细标题重复、隐藏技术列、只读行变更列、来源显示名、退货中文状态及不可直接编辑、空态与移动辅助事实访问。
- 长关系名称保持权威值；桌面通过公开 popover/按钮访问完整值，移动通过现有 disclosure 访问后置事实。
- P0 修复经人员档案、项目台账 workspace 反例和付款 task 页验证，没有把行业语义写入平台层。

未覆盖：

- 受管库没有供应商退货现有记录，故无退货查看/既有编辑态截图。
- 入库、出库没有可安全修改的现有草稿记录；本批只用未提交 create 表单验证编辑表达，用终态记录验证 readonly，不测试保存链。
- workspace 页面本身已有重复“基本资料/关系明细”标题；它们不经过本轮 task Floorplan，作为既有其他页面问题记录，不在材料专题扩修。

契约缺口：

- 出库创建入口继续由既有 action-scoped orchestration 合同承接，而查看态由业务分类 form policy 承接；两者当前语义顺序一致，但权威载体不同，不能表述为三模式同一份契约。
- 1088 和移动查看态会省略桌面内层明细 heading；业务明细名称仍存在于 `sourceSectionTitles`，关系区域有可访问身份，且页面没有重复标题。本批未新增响应式标题 DSL。
- 退货缺少现有权威记录属于验收数据能力缺口；按治理要求不在业务专题临时制造 fixture。

### 分层验证记录

- L0：开发期完整工作树指纹随每组截图记录；业务记录浏览器前后指纹一致。
- L1：`make ci.local.iteration` 11 项通过；XML/Python/Node 语法、`git diff --check`、严格 TypeScript 检查通过。
- L2：canonical presenter 162 项、professional detail collection 6 + 7 个模型矩阵/反例及 6 + 33 个 guards、collection semantics 11 + 31 个 guards 通过；P0 parser/contract 两项宿主 unittest 通过；P1 七项 Odoo 定向方法（统计 9）通过。
- L3：`smart_construction_core` 受管增量升级、`local.dev.demo.authority`、restart/health 通过，运行挂载指向本专题工作树。
- L4：上述 1440、1088、390、320 与 light/dark 实际样本通过；退货仅 create，未伪造记录；共享反例通过。
- L5：生成报告与组件接管清单已通过既有刷新入口更新，`ci.generated_evidence.preflight` 通过；仅在 tracked 内容提交并形成干净候选后执行一次完整 Quick 与独立复核。

付款专题旧的 `verify.local.dev.payment_request.floorplan.readonly` 要求空 relation/audit 区域必须占位，与当前“只读空关系不占主阅读空间”的通用规则不一致，运行按旧断言停止但业务指纹未变；本专题没有修改该脚本，也不把这项旧专题全链门禁算作通过。付款相关区域改由上表的窄范围只读共享反例完成。

失败分类记录：P0 两项测试首次误用 Odoo tagged runner 得到 0 tests，按硬锁判失败；随后包路径 unittest 又因宿主无 Odoo 包产生导入错误。改用源码自带的文件级 unittest runner 后各实际运行 1 项并通过，未重试未变化的失败入口。

### 独立复核 S1 与补项

- 首次冻结候选的独立只读复核发现 S1：退货 P1 策略已声明 `state` 在 create/edit/readonly 均只读，但最终 native occurrence modifier hydration 把已投影的 `readonly=true` 放宽为原生节点的 `readonly=false`；页面因此出现可编辑状态 selection，存在绕过既有提交/确认动作条件的风险。旧候选、指纹、截图和 Quick receipt 均降为历史证据。
- P0 修复分两跳完成：通用 governance 前冻结并在 governance 后恢复权威 `business_form_policy`、`field_policies` 与既有业务分组；最终 modifier hydration 对只读/必填采用单调收紧合并，native modifier 仍可增加限制，但不能放宽已投影策略。实现没有材料模型或 `state` 字段名特判。
- 新增通用契约边界测试模拟 governance 把三模式只读降为仅 readonly profile，要求恢复源策略；新增最终 hydration 纯测试证明原生 `readonly=false` 不覆盖更严格策略；材料浏览器检查新增“新建态可见流程状态必须只读”断言。
- 第一次补项浏览器回归按新增断言准确失败，退货状态为 `data-field-state=required`；第二跳修复后同一 1440 浅色三页聚焦回归通过，退货新建正文不再暴露可编辑状态，业务指纹前后不变。受管重启后的首次 health 两次命中 `starting`，容器健康事实变化后复查均通过；未重复重启或改业务数据。
- 完整 `test_ui_contract_v2_boundaries.py` 文件级诊断中 100 项运行、95 项通过，5 项因既有测试调用 `_build_form_structure_contract` 缺少已有必需参数 `field_label` 报错；它们不在本改动路径，按硬锁记录后不重试、不顺修。受影响策略与 hydration 子集均为非零通过。
- 第一版 S1 修复候选的完整 Quick 在末段 `ui_contract_v2_responsibility_map_guard` 按行预算失败（`4334 > 4312`），因此没有 receipt。策略快照/恢复随后下沉到既有 `ui_contract_v2_projection.py`，handler 只保留调用编排；责任映射门禁、策略保留 1 项、final hydration 5 项和 iteration 11 项均通过。该搬移不改变运行契约或前端输入，浏览器产品结果可按确定性影响分析保留，但最终 HEAD、完整指纹与 Quick 必须重新冻结。
- 第二轮独立复核发现新的 P0 S1：final hydration 用裸布尔 OR 保留策略时，也会把依赖缺失阶段的临时 fail-closed `readonly/required=true` 永久锁住。修复改为两阶段：先让 final hydration 用补齐依赖后的 native verdict 覆盖临时回退，再以 `tighten_only` 仅重放业务字段策略的 readonly/required；可见性和 disabled 不在该末段重放。新增反例覆盖 unresolved → resolved false，并证明 native readonly 不被放宽。
- 第一次两阶段浏览器回归又准确发现 `tighten_only` 过度包含 visible，导致出库新建说明/附件被隐藏；业务指纹未变。收窄到 readonly/required 后，三页 1440 聚焦回归通过：出库后置补充区恢复，退货流程状态仍不提供可编辑正文控件。该失败不重试未变化输入，修复后才重新运行。
- 冻结桌面矩阵曾先因执行会话中断只产出 7/10 场景，后又遇到一次 `ERR_NETWORK_CHANGED`；两次业务指纹均未变化，受管 health 恢复后才重启最早失效的 L4 项。随后 1088 出库只读检查在明细截图已完整显示表头的同时，过早读取动态表头得到空数组；390/320 首轮也在移动事实标签出现前读取。P4 检查现按视口等待既有桌面 `thead` 或移动事实标签可见后取值，不改变 P0/P1 产品代码。修复后的 1088 聚焦检查 5/5 场景通过。
