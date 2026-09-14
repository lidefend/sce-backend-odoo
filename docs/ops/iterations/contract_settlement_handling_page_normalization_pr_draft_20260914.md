# Draft PR：规范化收入、支出合同结算办理页面

English: [contract_settlement_handling_page_normalization_pr_draft_20260914.en.md](contract_settlement_handling_page_normalization_pr_draft_20260914.en.md)

## Summary

本 PR 让收入、支出结算正式入口按权威业务章节呈现项目与相对方、结算依据、明细与金额、办理说明，并让父记录条件列及重复关系 occurrence 使用既有契约语义稳定消费。

不改结算计算、金额值、保存、审批、权限、历史快照或业务数据，不新增结算特判、契约载体、上传能力或 fixture。

## User-visible improvements

- 收入显示“项目与发包人”，支出显示“项目与供应商/分包方”，分类和默认值互不串用。
- 结算明细与金额保持同一区域，名称、数量、单价、金额优先，来源合同后置。
- 普通合同与日常合同列按当前父记录类型互斥；未保存父值变化能立即更新显示。
- 办理说明集中承接既有说明、备注及附件字段，其他执行/追溯区保持折叠可达。
- 导航只指向实际可见 occurrence；同一字段出现在不同有效业务区时不会被误合并。

## Architecture Impact

- Formal Product Layer：P1 行业标准结算页面声明；P0 通用契约传递及共享渲染消费；P4 验证和交付证据。
- 标准 vs 用户特定：所有产品声明属于建设行业标准页面；没有 P2 客户偏好或 P3 运行时配置。
- P0 只接受显式锚点、显式结构组且后代身份唯一的容器；不按模型名、字段名或页面模式推断。
- 前端复用已有 modifier evaluator 和公开 renderer API，按业务区域选择 relation occurrence；无结算模型特判。
- Blast radius：共用结算视图、所有消费显式结构组的原生表单、one2many 父条件列和关系导航。收入合同反例及通用非零测试证明影响收敛。

## Layer Target

- P1：`smart_construction_core` 的 settlement form policy、原生 form view 和聚焦 profile 测试。
- P0 backend：`smart_core` unified page contract V2 assembler 的显式容器角色传递。
- P0 frontend：one2many 动态可见列与 native section navigation occurrence 选择。
- P4：双语迭代报告、PR 草案、生成证据和 exact-head 门禁。

## Affected Modules

- `smart_construction_core`
- `smart_core`
- `frontend/apps/web`
- `docs/ops/iterations`

## Verification

- `make ci.local.iteration`：PASS，16 tests。
- native section navigation、collection semantics、严格类型检查：PASS；父条件 false/true/value-change，以及同区、同 field semantic 跨显式业务区、无锚点不同 semantic 子区、全隐藏和折叠反例均覆盖；根遍历不接受 `forEach` 附加参数。
- `TestPaymentSettlementComponentProfile`：PASS，9 tests；P0 聚焦契约测试非零通过。
- 受管 `local.dev` 增量升级与 health：PASS。
- 收入、支出 a99 浅色/移动/焦点样板已完成人工产品复核，但因缺少运行前后完整指纹绑定，仅作为人工复核/诊断材料。
- 最终产品源候选 `e0d844cd…` 的支出深色 1088×791、390×844 已分别绑定新建与查看运行：新建每视口 5 个导航目标，查看桌面 11 个/移动 12 个目标均唯一且稳定避开吸顶区；before/after 指纹相同，summary/截图哈希绑定，零写入、零错误。
- 冻结准备、唯一一次 Quick 与独立复核由最终 clean HEAD 的仓外 receipt 记录；本草案不为回填 SHA 再改变候选。

## Evidence

- 迭代报告：`docs/ops/iterations/contract_settlement_handling_page_normalization_20260914.md`
- 最终产品源候选支出新建深色：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-create-dark/evidence-binding.json`
- 最终产品源候选支出查看导航：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-navigation/evidence-binding.json`
- a99 浅色、收入点击定位及焦点摘要：只作人工复核/诊断材料，不列为最终 L4 门禁。

## Not included

- 支出草稿编辑态、真实保存、审批、全角色、历史快照和金额计算验收。
- 金额主口径、期间空值修复、正式附件授权扩展或业务数据修正。
- 合同变更、付款、开票、综合工作台、低代码、部署、发布或数据库操作。

## Risk and rollback

- 共享风险受显式、唯一身份和现有 modifier 语义约束；歧义时失败关闭。
- 回滚可按 P0 导航/动态列 → P0 assembler → P1 视图/策略的顺序进行，无需数据回滚。

## Delivery status

`READY_FOR_REMOTE_DELIVERY_DECISION_AFTER_EXACT_HEAD_GATES`。远端 push、建 PR、Ready、合并、部署和发布均需独立授权；发生 HEAD 漂移、冲突或新增阻断时停止。
