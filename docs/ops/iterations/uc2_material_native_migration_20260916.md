# U-C2：材料办理整组原生结构候选

状态：入库、出库和共用出库视图的退库入口已完成整组本地自验，等待一次集中产品浏览器复核。本地兼容消费者口径为 **44**，已发布口径仍为 **46**。本记录不把本地候选表述为已发布结果。

## 候选与边界

- 基线：`main@28b7695dc9f1cebbbe9bd5d715e951c6dec8a4da`。
- 产品自验候选：`36ddc22de8df5a453be8052c8ad0eeb234e23923`；完整指纹 `517584ecec9591f81f330c0ed271a2cf35b4544b6538776e019b815e88be259e`。
- 分支／唯一写入工作树：`feature/uc2-material-native-v1` / `sce-backend-odoo-material-handling-v1-uc2-material-native-v1`。两个无关历史工作树未操作。
- P0：通用原生表单章节导航显露 notebook 目标、定位并同步高亮。
- P1：`smart_construction_core` 材料入库／出库原生视图、分类契约和退库上下文入口。
- P4：受管只读浏览器矩阵、结果索引与台账。
- 业务边界：库存、计价、保存、审批、状态方法和 ACL／record rule 均未修改；供应商退货不在本批。

## 三类入口与状态覆盖

| 入口 | 正式身份 | 原生来源 | 桌面 1440×960 | 移动 390×844 | 未覆盖 |
|---|---|---|---|---|---|
| 入库 | menu 494 / action 546 / `material.inbound` | view 1428 `view_sc_material_inbound_form` | `S80-MIN-001` received 查看；空白新建 | 同左 | 无合法 draft，未做编辑 |
| 出库 | menu 495 / action 547 / `material.outbound` | view 1431 `view_sc_material_outbound_form` | `S80-MOUT-001` issued 查看；空白新建 | 同左 | 无合法 draft，未做编辑 |
| 退库 | menu 496 / action 548 / `material.return` | 共用 view 1431 | 空白新建 | 空白新建 | 无受管现有记录或合法 draft |

没有为补齐查看／编辑态创建、保存或修改业务数据。所有已执行旅程前后业务指纹一致，捕获到的写请求为 0。

退库保留为上下文入口：正式 89 项主导航基线不增项；route authority 仅在既有 Odoo menu 对该用户可见时发布，所以沿用原权限组和 ACL。action 548 不是独立兼容消费者，不重复扣减。

## 唯一结构与兼容退出

三个入口的实际表单契约均为：

- `layoutPolicy=container_tree_authority`；
- `formStructureAuthority=native_authority`；
- `compatibilityDependencies=[]`；
- action 546 解析到 view 1428；action 547、548 分别解析到同一 view 1431；
- 入库旧基础章节、生成字段顺序、P1 业务事实排序和 action 产品化结构按精确 XMLID 停用；
- 出库旧生成结构与 action 产品化结构按精确 XMLID 停用；
- 分类模板只保留字段 required／readonly／visible 等语义，不再提供结构章节。

入库消费者 action 546 和出库消费者 action 547 已从本地剩余数组移除，`46→44`。退库只验证共享原生结构与独立分类／动作身份，不产生第三次扣减。

## 导航、页签、明细与动作结果

- 入库正文页签为“入库明细／说明与附件／来源追溯”；出库、退库为“材料明细／说明与附件／来源追溯”。章节导航和 notebook 标题来自同一原生树。
- 从“来源追溯”点击顶部明细章节时，目标由隐藏 `0` 变为可见 `1`，对应 notebook 页签被激活，关系锚点可定位，活动导航为 `aria-current=location`。
- 隐藏目标通过 notebook 页签的 `data-section-reveal-targets` 显露；不存在目标或显露关系的导航项被判为不可达。
- 新建态明细保留原生“添加”能力；已出入库样本的明细为只读。来源字段在契约中完整保留，页面按实际值与显隐规则展示。
- 新建态备注探针在明细、说明、来源页签之间切换后保持，未触发保存。
- 入库保留提交、确认入库、退回草稿、取消、带入验收明细；出／退库保留提交、确认出库、退回草稿、取消和调拨关联动作。按钮仍由原方法、状态和权限控制。
- P0 非材料反例使用项目档案：点击章节后目标可见，唯一高亮项指向当前可见内容，证明通用修复未绑定材料语义。

## 结果索引

| 层 | 入口／命令 | 状态 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | passed then stale | 早期候选 16 tests；后续 P0／P1／P4 改动没有重跑该宽入口，改动路径由下列定向静态、单元和 Odoo 检查覆盖 |
| L1 | `make verify.frontend.native_section_navigation.unit` | passed | P0 导航单元覆盖非零 |
| L1/P4 | `python3 -m unittest scripts.verify.test_frontend_material_domain_rollout` | passed | 5 tests |
| L2 | `TestUserFeedbackBusinessViews` 的出库／退库结构与契约精确方法 | passed | 2 个非零方法；后续标签与导航变更重验受影响方法 |
| L2 | `TestProjectMemberRoleSurface.test_material_return_is_contextual_for_every_business_role` | passed | 1 个方法；Odoo 报告 1 test，0 failed/error |
| L3 | `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make local.dev.upgrade MODULE=smart_construction_core` | passed | `sc-local-dev` / `sc_dev_demo`；demo authority passed |
| L4 | 三入口桌面组件结果＋当前候选移动矩阵 | passed | 桌面 5 个组合、移动 5 个组合；零写入 |
| L4 | 当前候选非材料导航反例 | passed | 项目档案；零写入 |

直接运行的 `scene_role_surface_consistency_guard.py` 误把其输入中的非角色字典字段识别为角色，属于既有守卫解析问题；它不是本批风险选择入口，失败未被改写为通过，生成报告已恢复到 HEAD。最终阶段若映射门禁包含该脚本，须由其 P4 所有层先修复。

`local.dev.sync_demo` 未执行。既有“期望 280000、实际 0”的结算演示数据问题继续单列，未为本批修改金额或演示事实。action 777 保持原未通过状态。

## 浏览器证据与承接

| 范围 | 证据目录 | 说明 |
|---|---|---|
| 入库桌面 | `tmp/uc2/material-batch-69b9606b/browser-candidate` | 两个入口组合已完成；摘要随后在进入其他范围时停止，入库结果本身无错误、无写入 |
| 出库桌面 | `tmp/uc2/material-batch-7ed5c258/browser-desktop-out-return` | 查看／新建完成；摘要随后在退库入口阶段停止，出库结果本身无错误、无写入 |
| 退库桌面 | `tmp/uc2/material-batch-c1b5369a/browser-desktop-return` | 新建完成；摘要随后在旧反例选择上停止，退库结果本身无错误、无写入 |
| 三入口移动 | `tmp/uc2/material-batch-36ddc22d/browser-mobile` | `pass=true`，15 张完整视口图 |
| P0 非材料反例 | `tmp/uc2/material-batch-36ddc22d/browser-nonmaterial-counterexample` | `pass=true`，项目档案导航 |

桌面结果按确定性影响分析承接：其后提交只改变未运行入口、退库 route authority 或 P4 反例选择，未改变已完成入口的原生视图、action 分类、账号、数据库及浏览器运行配置。当前候选上的移动整组和非材料反例重新覆盖了共用布局与 P0 行为。

这些目录仍是工作树内 ignored 证据，不满足最终外部归档。产品集中复核关闭问题后，第三阶段才执行生成预检、独立复核、一次 exact-head Quick，并把摘要、身份、关键截图和复核报告归档到工作树外；receipt 缺失、HEAD 不匹配、必需角色缺失、文件缺失或哈希不符时清理入口继续拒绝。当前不清理工作树。

## 当前交回与后续门禁

受管候选现场为 `http://127.0.0.1:5176`。当前交回单位是 UC2 整组候选，产品复核可集中检查三入口和上述未覆盖项。

产品复核通过并关闭整批问题后，才进入冻结交付：`ci.delivery.freeze.prepare`、独立复核、一次最终 Quick、外部证据归档验证和远端交付。发布台账只在合入后从 46 更新。
