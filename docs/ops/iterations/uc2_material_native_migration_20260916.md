# U-C2：材料办理整组原生结构候选

状态：**UC2 正式范围固定为 action 546、547；入库、出库的本地迁移与浏览器自验通过，进入冻结交付。** 本地兼容消费者为 **44**，已发布仍为 **46**。本地 44 记录 action 546、547 已退出兼容结构；合入前不更新已发布数。

## 候选与边界

- 基线：`main@28b7695dc9f1cebbbe9bd5d715e951c6dec8a4da`。
- 产品与取证候选：`f1dbaa9950263f735b0619a08b545f8f199f5982`；完整指纹 `f9780e4b60fb625cdaa8b73a8cdb7a5217dd1069a989b64d4c5721e7290304da`。
- 分支／唯一写入工作树：`feature/uc2-material-native-v1` / `sce-backend-odoo-material-handling-v1-uc2-material-native-v1`。两个无关历史工作树未操作。
- P0：原生 statusbar 在新建态保留节点身份但不显示状态，避免同一状态回落到正文；章节导航显露 notebook 目标、定位并同步高亮。
- P1：`smart_construction_core` 材料入库／出库原生视图与分类契约。
- P4：受管只读浏览器矩阵、退库路径解析、证据和台账。
- 业务边界：库存、计价、保存、审批、状态方法、ACL 与 record rule 均未修改；供应商退货不在本批。

## 实际入口与覆盖

| 范围 | 正式身份与原生来源 | 已覆盖 | 结果／未覆盖 |
|---|---|---|---|
| 入库 | menu 494 / action 546 / `material.inbound` / view 1428 | `S80-MIN-001` received 查看、空白新建；桌面 1440×960、移动 390×844 | 通过；无合法 draft，未做编辑 |
| 出库 | menu 495 / action 547 / `material.outbound` / view 1431 | `S80-MOUT-001` issued 查看、空白新建；桌面、移动 | 通过；无合法 draft，未做编辑 |
| 退库（批外调查） | 内部 XML 定义 action 548 / `material.return` / 共用 view 1431 | 正式菜单、角色路由、action 547 分类、供应商退货边界 | **不在正式 89 项基线；无正式可达用户路径，另立业务能力专题；未把直接 action URL 当成验收路径** |

没有为补齐查看或编辑态创建、保存或修改业务数据。最终 8 个材料组合及非材料反例捕获到的业务写请求为 0，运行前后业务指纹一致。

## 唯一结构与兼容退出

action 546 与 547 的实际契约均满足：

- `layoutPolicy=container_tree_authority`；
- `formStructureAuthority=native_authority`；
- `compatibilityDependencies=[]`；
- action 546 解析到 view 1428，action 547 解析到 view 1431；
- 入库旧基础章节、生成字段顺序、P1 业务事实排序和 action 产品化结构按精确 XMLID 停用；
- 出库旧生成结构与 action 产品化结构按精确 XMLID 停用；
- 分类模板只保留 required、readonly、visible 等字段语义，不再提供章节结构。

因此入库、出库两个技术消费者从本地剩余数组移除，`46→44`。已发布数保持 46；退库不重复计数。

## 信息组织、导航与交互

- 入库现有记录由页头唯一承接“已入库”：状态区 1、状态标签 1、正文状态字段 0。新建页状态区 0、正文状态字段 0，由页面的新建／未修改元信息表达当前模式。
- 入库 `document_status`、`quantity_summary`、`tax_included_amount` 的可见实例均为 0；`total_qty` 与 `amount_total` 各 1。明细继续保留逐行数量、单价、金额与原生合计，未改计算规则。
- 入库正文页签为“入库明细／说明与附件／来源追溯”；出库为“材料明细／说明与附件／来源追溯”。章节导航与 notebook 来自同一原生树。
- 从“来源追溯”点击顶部明细章节后，目标由不可见 0 变为可见 1，正确激活明细页签并定位关系锚点；活动导航为 `aria-current=location`。
- 新建态明细保留原生添加能力；已入库、已出库记录的明细为只读。新建备注探针跨三个页签保持，未触发保存。
- 入库保留提交、确认入库、退回草稿、取消、带入验收明细；出库保留提交、确认出库、退回草稿、取消和调拨关联动作。按钮继续由原方法、状态和权限控制。
- P0 非材料反例为人员档案：章节目标可见且唯一高亮，证明通用修复未绑定材料语义。

## 退库路径调查（UC2 范围外）

退库不属于 action 546、547 的本批正式范围，且当前不能宣称可用，依据如下：

1. 正式 89 项产品导航基线不含退库菜单。
2. `menu_sc_material_return` 的父菜单停用，管理员菜单搜索无“退库”。
3. 角色 route authority 列表为空。
4. action 547 的正式业务分类不包含 `material.return`；模型虽有 return 类型定义，但没有把普通出库入口变成正式退库入口的权威路由。
5. action 548 的 XML 定义或直接 URL 不能替代用户可达路径。
6. action 554“材料退货”对应 `sc.material.supplier.return`，属于供应商退货，明确排除。

后续另立业务能力专题：以可追溯原出库记录为起点，先核实来源关联、可退数量、库存方向和权限，再确定正式入口。该专题不直接放开出库分类，不复活旧菜单。执行者未擅自新增菜单，退库调查结论不阻断 UC2 正式范围冻结。

## 结果索引

| 层 | 入口／命令 | 状态 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | passed | 16 tests；最终 P0/P1 变更的静态与架构入口通过 |
| L1/P4 | XML parse、`node --check`、`python3 -m unittest scripts.verify.test_frontend_material_domain_rollout` | passed | 5 tests；浏览器断言按唯一状态区域取证 |
| L2/P0 | `make verify.frontend.professional_workflow.unit` | passed | 10 模型例、5 Python guards |
| L2/P0 | `make verify.frontend.canonical_form_presenter.unit` | passed | 170 cases；新建 statusbar 保留归属且不显示业务状态 |
| L2/P1 | `TestUserFeedbackBusinessViews.test_material_inbound_form_uses_handling_identity_and_business_first_line_order` | passed | 1 个精确方法，非零；0 failed/error |
| L2/P1 | 出库原生契约与无正式退库角色路径的精确方法 | passed | 既有候选结果复用；相关产品输入未变 |
| L3 | `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make local.dev.upgrade MODULE=smart_construction_core` | passed | `sc-local-dev` / `sc_dev_demo`；demo authority passed；未执行 `sync_demo` |
| L4 | 最终材料矩阵与非材料反例 | passed | 8 个材料组合、1 个非材料反例、25 张截图、0 写请求、0 浏览器错误 |

中间候选曾因两类取证问题失败：一是把新建 statusbar 节点身份清空，导致“草稿”回落正文；二是 Playwright 把组合徽标当作单一文本节点，`exact` 定位不到实际存在的“已入库”。前者由 P0 通用归属修复，后者由 P4 按唯一业务状态区域逐行取证；失败未被改写为通过。

`local.dev.sync_demo` 未执行。既有“期望 280000、实际 0”的结算演示数据问题继续单列，未修改金额或演示事实。action 777 保持原未通过状态。

## 浏览器证据与现场

- 证据摘要：`tmp/uc2/material-batch-f1dbaa99/browser-batch-review/summary.json`。
- 截图：同目录 25 张，摘要记录逐文件 SHA-256。
- 身份：HEAD `f1dbaa9950263f735b0619a08b545f8f199f5982`，完整指纹 `f9780e4b60fb625cdaa8b73a8cdb7a5217dd1069a989b64d4c5721e7290304da`。
- 滚动事实：桌面表单顶部 `formTop=101`、标题 `headingTop=133`；移动 `formTop=135`、标题 `headingTop=155`；实际滚动所有权为 `.router-host`，顶部截图时 `scrollTop=0`。
- 受管现场：`http://127.0.0.1:5176`。提交本记录后的仅文档候选可承接上述浏览器证据，因为产品、脚本、数据库、账号和运行配置输入未变；运行服务仍须绑定最终完整 HEAD。

证据目前仍在工作树内 ignored 目录，不满足最终外部归档。正式范围问题已经关闭；第三阶段执行生成预检、冻结、独立复核、一次 exact-head Quick、外部证据归档验证和远端交付。清理入口继续要求 receipt、HEAD、必需证据角色、文件存在性与哈希全部匹配；当前不清理工作树。

## 当前门禁

UC2 正式范围 action 546、547 已完成本地产品与浏览器自验，可以进入生成预检、冻结、独立复核与一次 exact-head Quick。入库、出库可直接在 5176 复核；合法 draft 编辑仍因无受管样本而明确未覆盖。退库是批外产品能力专题，不作为本批通过项或阻断项；发布数在合入前保持 46。
