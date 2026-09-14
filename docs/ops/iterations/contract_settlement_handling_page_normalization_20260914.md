# 合同结算办理页面规范化（2026-09-14）

English: [contract_settlement_handling_page_normalization_20260914.en.md](contract_settlement_handling_page_normalization_20260914.en.md)

## 目标与边界

- 唯一产品结果：收入、支出结算正式办理入口能够先核对项目、合同相对方和结算依据，再阅读结算明细、金额、说明及后续追溯。
- 基线：`origin/main@c616b652fa2b7364a5f6629c56750874c5dd6113`；分支：`codex/contract-settlement-page-normalization-v1`。
- P1：`smart_construction_core` 负责收入/支出结算权威分区、字段归属、明细列序和既有附件入口归属。
- P0：`smart_core` 只把显式锚点与单一权威结构角色关联；共享前端只消费父记录 modifier、选择实际可见关系 occurrence，并保持不同业务区域的同名字段独立。
- P4：定向测试、只读/未提交浏览器证据、生成证据、交付文档与最终门禁。
- 排除：结算计算、金额口径、保存、审批、权限、历史快照、业务数据、fixture、合同变更、付款、开票、综合工作台和低代码。

## 已有能力为何未覆盖结算

| 链路 | 收入合同已覆盖方式 | 结算首次偏差 | 原机制修复 |
| --- | --- | --- | --- |
| P1 结构声明 | 原生业务容器拥有稳定锚点，字段角色能归入明确章节 | 结算策略已有字段归属，但原生容器没有与策略组的显式关联；assembler 只标注字段，task floorplan 随后按字段类型/可编辑性重新分类 | P1 只在权威业务组声明 `data-sc-form-structure-group`；P0 assembler 仅在“显式锚点、显式组名、全部后代恰好形成一个结构身份”同时成立时给容器携带该身份，其他布局组失败关闭且继续无标题 |
| 父记录条件列 | 字段 modifier 已有通用解析/求值 | one2many 渲染一直取静态列清单，没有把当前父表单值求得的 `invisible` / `columnInvisible` 用于列投影 | 复用现有 modifier 解析与 `one2manyEffectiveColumn`，按当前父值形成响应式可见列；父值变化重新求值，不永久隐藏 |
| 重复关系 occurrence | 导航只处理实际可呈现字段 | 旧逻辑按字段全局去重；同一业务区的 tag/table 可能选错目标，而两个不同有效业务区的同名字段又会被误合并 | 先过滤不可见 occurrence；同一区域按结构化 subview、one2many、tag 的通用确定性评分选择实际目标；区域身份取最近显式业务锚点或结构 slot/group，不同业务区域分别保留 |

没有增加结算模型或字段名特判，没有复制 floorplan，也没有强制改变 `presentationMode`。

## 页面组织结果

- 收入正式入口命中 `settlement.income`，支出正式入口命中 `settlement.expense`；支出默认值、分类及“项目与供应商/分包方”口径不串用收入策略。
- 两类共用原生视图现在按“项目与合同相对方 → 结算依据 → 结算明细与金额 → 办理说明”组织；有内容的执行、发票、付款申请、扣款、采购订单和系统信息保持默认折叠及可导航。
- 明细依次呈现名称、数量、单价、金额、申请事实，再呈现来源合同；模型没有单位字段，本批没有补造。
- `contract_id` 与 `general_contract_id` 继续按 `parent.contract_source_kind` 动态互斥；未保存编辑中父值变化时复用同一 modifier 求值路径。
- `attachment_ids` 只归入办理说明并消费已有 widget/授权，没有新增上传能力或迁移数据。
- 同一业务区的采购订单 tag/table 只生成指向实际呈现 occurrence 的入口；不同权威业务区若复用同一字段仍保留各自入口；全部隐藏不产生死链接，折叠但有内容仍可定位展开。

## 金额事实与边界

| 字段 | 当前定义/来源 | 本批处理 |
| --- | --- | --- |
| `amount_total` | stored compute，为结算明细 `line_ids.amount` 合计 | 保留现有标签、数值及计算 |
| `settlement_amount` | 独立存储金额字段，无 compute；已审批/完成/取消后只读 | 与明细合计同区展示，但不解释为同一阶段或统一口径 |
| `submitted_amount` / `approved_amount` | 申报及审批阶段金额事实 | 原值、标签、只读条件不变 |

样本中“结算金额 ¥0.00”和“金额合计 ¥1,000,000.00”并列不是本批可推断的计算错误；阶段含义与主金额选择继续作为独立产品决策。

## 验证与证据结转

| 层 | 入口或证据 | 结果 |
| --- | --- | --- |
| L1 | `make ci.local.iteration` | PASS，16 tests |
| L1/L2 | `make verify.frontend.native_section_navigation.unit`、`make verify.frontend.collection_view_semantics.unit`、`make verify.frontend.typecheck.strict` | PASS；覆盖章节保真、父条件 false/true/父值变化、同区重复 occurrence、相同 field semantic 的跨显式业务区、不同无锚点 semantic 子区、全隐藏及折叠有内容；根节点遍历显式只传 node，不接受 `forEach` 的 index/array 泄漏 |
| L2 | `TestPaymentSettlementComponentProfile` 及 P0 聚焦契约测试 | PASS；P1 9 tests，P0 非零聚焦测试通过；收入/支出策略、结构身份、附件归属、明细列序与 parent modifier 已断言 |
| L3 | 既有受管 `local.dev` 增量升级与 health | PASS；复用 `sc-local-dev/sc_dev_demo/18081`，未创建环境或数据 |
| L4 既有人工样板（非最终门禁） | `contract-settlement-*-a99f5da1` 收入/支出浅色、深色、点击定位与焦点摘要 | 已完成人工产品复核且摘要均 pass/零写入；因目录缺少运行前后完整指纹及 artifact binding，降级为诊断/人工复核材料，不作为最终 L4 身份依据 |
| L4 最终产品源候选：支出新建深色 | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-create-dark/evidence-binding.json` | `e0d844cd…` 在 1088×791、390×844 各有 5 个可见章节唯一定位；before/after 完整指纹逐字节相同，summary/6 张截图共 7 个 artifact 哈希已绑定；pass、零写入、零错误 |
| L4 最终产品源候选：支出查看导航 | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-navigation/evidence-binding.json` | 1088×791 的 11 个、390×844 的 12 个实际可见章节逐项 `targetMatchCount=1` 且稳定避开吸顶区；before/after 完整指纹相同，7 个 artifact 哈希已绑定；pass、零写入、零错误 |
| L5 | `make ci.delivery.freeze.prepare`、最终一次 `make ci.local.quick`、独立复核 | 冻结后由仓外 exact-head receipt 与复核结论记录；本文不会为回填结果再次改变候选 |

从收入样板 `a147c7ea…` 到共用支出候选 `a99f5da1…`，产品分区和字段事实未重排；收入与浅色样板结论仅按人工复核边界保留。独立复核后形成产品源候选 `e0d844cd…`，补上显式业务锚点优先和根 `forEach` 参数隔离；两组正式深色 L4 均以 `e0d844cd…` 的运行前后完整指纹及 artifact 哈希绑定。其后最终候选只允许 P4 文档/生成证据变化，独立复核必须逐文件证明 P0/P1 字节不变并同时绑定源/目标完整指纹。

旧深色焦点探针第一次使用了不存在的 `.o2m-readonly-card`，在生成通过证据前失败，归为 `validation_tool_defect`。读取现有 DOM 公开类后改用 `.o2m-readonly-row`，没有修改产品或仓库验证工具；后一次摘要只保留为人工复核材料，不作为最终 L4 身份门禁。

## 已知边界、风险与回滚

- 支出受管样本没有草稿，编辑态未覆盖；不创建 fixture。收入已有样板按此前证据结转，本轮不重跑收入编辑。
- 未执行真实保存、审批、金额计算、全角色或历史快照验收；浏览器只读及新建/草稿未提交交互的写入计数为零。
- 期间空值和金额差异保留为样本/产品定义边界；不改业务记录。
- P0 风险限于显式单一结构身份传递、父 modifier 动态列投影及关系导航 occurrence 选择。反例证明未声明页面继续走原默认规则、歧义结构不被强行标注、跨业务区不误合并。
- 回滚顺序：先回退 P0 导航与动态列消费，再回退 P0 容器身份传递，最后回退 P1 结算策略和原生视图；不需要数据库数据回滚。

## 下一步

- 审阅并提交冻结前文档与生成差异，形成 clean exact-head 候选。
- 仅在该候选上运行一次 Quick，并由独立复核绑定同一 HEAD/Tree/完整指纹；随后等待远端交付授权。
