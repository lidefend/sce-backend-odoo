# 共享表单反馈与付款申请可选明细闭环（2026-09-14）

## 交付摘要

本批从 `origin/main@90f1434bab4180a721b26eb4a8f5ea0ff6871c29` 开始，在唯一写入工作树和分支 `codex/shared-form-help-error-consistency-v1` 上完成两组相互关联、但分别验收的结果：

1. 共享表单的标签、帮助、错误和无效状态通过既有 TDesign 桥接组件投射到真实可操作控件；页面级反馈、动作阻断、字段错误和普通业务资料不再由同一兜底章节混排。
2. 付款申请可以直接填写申请金额，也可以选择“按明细填写”。使用有效明细后，后端以明细合计作为申请金额权威；不使用明细时仍保留直接填写能力。

独立复核前检查点为 `08325c1ea75dcf16c8e718b031df814f61c4963e`，Tree `a8d05b90d56d016776b10f13b7d0d18f4bf18307`，完整工作树指纹 `b8c1c807236979ff6d843d26c80573a880cc7f5891656c8e89c12ded5f8b9082`（7440 paths）。复核随后要求把跨币种约束下沉到模型层、恢复权威名称搜索、按逐行舍入计算前端比例预览，并为专用旅程补齐中断清理；这些修复均已进入候选。最终真实闭环在 `084f576239bff5f56831e68863b6f0abaeae0682` 上重新执行并整体通过；交付文档和生成证据提交后另行冻结最终 HEAD。

## 产品与架构边界

| 层级 | 所有权与修改 | 未做事项 |
| --- | --- | --- |
| P0 平台内核 | `smart_core` 只负责原生优先结构合成、受约束语义增强和冲突报告；共享前端负责同一有效结构的正文/导航消费、控件语义投射、反馈区域和可选集合披露 | 不按付款模型、字段名或中文文案猜测；不新增 DSL、布局替换模式或私有 TDesign DOM 依赖 |
| P1 行业标准 | `smart_construction_core` 负责付款申请入口专用原生视图、字段业务归属、可选明细与申请金额规则、币种权威和后端约束 | 不改审批权限、付款登记、会计写入或历史记录数值 |
| P4 交付工具 | 聚焦 guard、候选浏览器和专用 fixture 旅程；清理只作用于登记的付款申请 fixture | 不新建数据库、端口、卷、凭据或临时 fixture，不用记录 621 做写入 |

Formal Product Layer：P0 + P1 + P4。Standard vs User-Specific：平台通用消费和建设行业标准付款规则；没有 P2 客户特判或 P3 运行时布局配置。详细结构权威决策见 [native_first_form_structure_authority_v1.md](../../architecture/native_first_form_structure_authority_v1.md)。

## 用户可见结果

- 普通输入、文本域、日期、关系选择和明细单元格使用桥接组件公开能力，将稳定唯一的 `id`、`aria-describedby` 和 `aria-invalid` 投射到真实可操作控件；帮助与错误可同时关联，错误解除后不保留失效引用。
- 普通只读文本不再逐项重复“只读”；状态、金额、日期和关系值保留各自既有展示语义。页面摘要不会生成第二套编辑控件。
- 正文和章节导航共同消费一次合成后的有效章节树；原生内部布局组不会自动升级为一级章节，辅助反馈不冒充业务章节。
- 付款申请按基本信息、付款依据、申请金额、收付款信息、付款申请明细、说明与附件以及既有协作/审计能力组织。申请金额先于可选明细出现。
- “按明细填写”初始折叠；展开后集合跨满当前业务区域，表格、引入/添加入口、合计和金额来源说明位于同一区域；再次收起后不残留内容边框或空白，也不改变金额来源。
- 无明细时可直接填写申请金额；有有效明细时申请金额随合计同步并不可独立形成另一数值。删除最后一行需要明确确认，确认后退出明细权威但保留最后合计供用户核对，不静默清零。
- 空白或零金额明细不会被静默忽略，而是明确判为无效；历史不一致可见且阻止提交，不会因打开页面、onchange 或无关字段写入而自动修数。
- 从结算单引入只接受同币种来源，前后端都使用契约给出的币种名称、符号、精度和舍入，不固定假设人民币或两位小数。

## 结构权威收敛

既有付款配置曾与正式原生视图同时维护章节、字段顺序和动作展示。本批按原生视图复用规范收敛为：

`正式 action 选择的最终合成原生视图 → 后端保真解析与受约束增强 → 唯一有效页面结构 → 前端正文与导航共同消费`

`layoutContract` 可以保留原生树用于追溯，`formStructureContract` 只承载展示模式和增强投影。配置中的摘要、帮助、风险和动作说明仍可使用；基础章节、字段归属、顺序、按钮条件和 modifiers 不再由第二棵 JSON 结构覆盖。结构键冲突或未知字段引用显式失败，不静默择一。

## 金额与明细规则

| 场景 | 最终行为 | 权威层 |
| --- | --- | --- |
| 无明细 | 申请金额直接填写，`amount_uses_details=false` | P1 模型和原生表单 |
| 有有效明细 | 明细合计按记录币种精度生成申请金额，`amount_uses_details=true` | P1 后端约束；P0 即时反馈 |
| 明细增删改 | 合计发生变化时同步主金额；无关字段写入不触发修数 | P1 模型 |
| 删除最后一行 | 先取消/确认；取消保留行，确认删除并保留最后金额 | P0 交互 + P1 权威回读 |
| 空白或零金额行 | 明确无效，不参与“看似成功”的部分创建或保存 | P1 模型/handler |
| 历史不一致 | 显示差异并阻止提交；读取、onchange、无关写入不自动修复 | P1 模型 |
| 结算单引入 | 同币种才允许；金额按契约币种精度/舍入处理 | P1 handler + P0 对话框 |

## 验证分层与结果

Changed paths 涉及 P0 契约合成及共享前端、P1 付款视图/模型/handler、P4 guard/受管旅程和本报告。风险等级为高：金额权威与共享表单消费。最早有效层为 L1；完成非零 L2、受管 L3 和聚焦 L4。完整 Quick 仅在最终 clean HEAD 运行一次。

| 层 | 入口与结果 | 覆盖口径 |
| --- | --- | --- |
| L0 | 源检查点 HEAD/Tree/完整指纹一致，工作树 clean | 7440 paths；最终冻结后重新生成 exact-head 身份 |
| L1 | `make ci.local.iteration` PASS，16 tests；严格类型、语法和 `git diff --check` PASS | 不把 L1 当作交付 receipt |
| L2 前端 | professional component registry 43 cases + 3 guards；X2Many guard 4 个反例；相关 presenter/navigation/detail collection 测试均非零 PASS | `props.adapter.one2manyColumns(props.field.name)` 与等价局部 adapter 调用均通过；缺失调用和错误参数均失败 |
| L2 后端 | 选择 4 个方法，实际执行 4 个方法，框架统计 6 tests，失败/错误 0；后续受影响 2 方法与 1 方法分别非零 PASS；最终跨币种/搜索方法再次实际执行 1 个方法，框架统计 3 tests，失败/错误 0 | 无明细、有明细、零金额、历史不一致、引入同步、handler/模型跨币种拒绝、权威名称搜索和币种元数据 |
| L3 | 受管 `local.dev` 增量升级 `smart_construction_core`、重启和 authority health PASS | 仅 `sc-local-dev/sc_dev_demo`；没有手工拼接 Compose/DB/profile |
| L4 只读布局 | 621，1088×791 与 390×844；初始折叠、展开稳定态、再次收起均 PASS，`mutationCount=0` | 展开 grid/field 宽度比均为 1；收起 contentCount=0，ownerHeight=54 |
| L4 写入闭环 | 候选 `084f576239bff5f56831e68863b6f0abaeae0682`；登记 XMLID `smart_construction_demo.payment_request_floorplan_demo_record`，finance demo user | 受管完整旅程 PASS：引入并保存/权威回读金额 2400；取消删除保留行；确认删除后回读 0 行且金额仍为 2400；随后专用 reset PASS |

后端测试统计统一解释为：选择目标是测试方法；Odoo 统计行还包含框架阶段计数，不能把 `6 tests` 宣称为 6 个独立业务用例。浏览器 DOM 断言只证明语义关联，未实际使用读屏器，因此不宣称完整读屏体验通过。

## 证据与结转

- 可选明细布局：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/shared-form-payment-621-optional-detail-states-1f96aac5/summary.json`。
- 专用真实闭环：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/payment-optional-detail-real-closure-084f5762/introduce-summary.json` 与 `remove-summary.json`，两份摘要均绑定完整候选 `084f576239bff5f56831e68863b6f0abaeae0682` 且 `pass=true`。
- 621 全程只读；真实写入仅作用于受管付款 fixture。最终专用 reset 后，权威回读为草稿、金额 10000、0 行、`amount_uses_details=false`。
- 布局证据源候选 `1f96aac5…` 到产品源检查点的后续变更只涉及后端金额/币种规则、引入对话框币种表达和 P4 工具，不改变已验收的 Disclosure 全宽/销毁内容实现。
- 最终 P4 旅程绑定明确的 S69 settlement/line XMLID，并以浏览器财务用户、公司、币种、项目和合同验证来源；`EXIT` trap 在任何已进入可变阶段的中断路径执行专用 reset，正常结束则显式解除 trap。该最终实现已在 `084f5762…` 上由完整受管入口验证，未沿用旧候选结果。
- 第一次冻结 Quick 在 `tenant_product_legacy_boundary` 发现无效明细错误标签仍以历史行 ID 作回退，立即失败且未签发 receipt。P1 随后改为“来源单号，否则业务行序号”；该守卫与对应零金额/历史不一致方法均非零通过，并重新完成模块升级。此变更只影响无效明细的错误标签，最终真实闭环使用的有效明细、金额同步、删除确认、resolver 和 reset 输入均未变化，因此 L4 结果按确定性影响分析结转，不重复写入 fixture。

## 风险、边界与回滚

- 未运行付款审批、付款登记、会计写入、全角色或生产数据旅程；未修改记录 621。
- 未创建新 fixture。真实闭环使用现有受管 demo fixture，并通过同一治理入口恢复。
- 不自动修复既有历史金额差异；不处理批准结算旧发票快照问题。
- P4 验证提交依赖 P0/P1 行为，回滚顺序为 P4 旅程/guard → P0 可选集合与共享反馈消费 → P1 付款原生结构和金额权威。后端金额权威与前端可选明细不能只回退一侧后继续交付。
- 数据库无需迁移回滚；若撤销功能，应先停止前端明细入口，再撤销后端规则，最后撤销原生页面声明，并保留已有历史记录原值。

## 下一步

完成生成证据预检、冻结最终 clean HEAD、运行一次 Quick 并取得同候选独立复核。通过后仅进入远端交付决策；本批不再追加页面美化、审批流程或新的金额口径专题。
