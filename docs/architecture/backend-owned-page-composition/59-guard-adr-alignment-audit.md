# 59 · Guard ↔ ADR Alignment Audit（Phase 4G-01）

## Status

只读审计完成。Guard 与 ARCH-DECISION-004 存在系统性不一致，需要 Phase 4G-02
按 62 号文档的最小方案改造；本轮不修改 Guard。

## Baseline

- `.agent/decisions/ARCH-DECISION-004.yaml`
- 12-integrity-guard-rule-matrix.md
- 54-structural-authority-decision.md
- 55-slots-fieldgroups-containertree-responsibility.md
- 56-structural-conflict-resolution-matrix.md
- 57-formal-page-composition-entry-criteria.md
- `scripts/verify/page_composition_integrity_guard.py`（实际源码，非文档推断）

## 逐条审计

### PC-001 页面结构权威

- 当前实现：仅检查 `slots` 非空即 PASS；空则 NOT_VERIFIED。
- ADR-004 要求：两层权威（业务组合 + 布局拓扑），且“唯一权威”指同层不存在
  第二来源。
- 判定：PARTIAL。
- 问题：不覆盖 `layoutContract.containerTree`；把“业务组合权威”与“布局权威”
  混在同一规则；未检查同层是否有多来源。

### PC-002 Identity 归属

- 当前实现：仅检查存在 `slot.id == "identity"`。
- ADR-004 要求：Identity 字段必须真正归属 `slot:identity`（ownerSlotRef 解析）。
- 判定：PARTIAL。
- 问题：不交叉验证 Identity 主展示字段的 `ownerSlotRef == slot:identity`。

### PC-003 Business Section 归属

- 当前实现：检查存在非 identity slot 且 groups 非空。
- ADR-004 要求：业务字段必须有明确 slot + group 归属。
- 判定：PARTIAL。
- 问题：不验证业务字段实际绑定到 section slot 与 group（引用有效性）。

### PC-004 Ownership 唯一性

- 当前实现：遍历 `fieldOwnership`（dict），检测重复 key。
- ADR-004 要求：每字段唯一 primary owner，且引用有效。
- 判定：MISALIGNED。
- 问题：dict 的 key 天然唯一，重复检测是死代码；PASS 仅代表“ownership 非空”，
  不校验 ownerSlotRef / ownerGroupRef 是否存在与可解析。

### PC-005 重复投影

- 当前实现：基于 slots.fieldRefs / groups.fieldRefs / fieldOwnership 判定多 slot
  字段；辅助 role 集合硬编码 `{summary, context, relation, detail, activity, audit}`。
- ADR-004 / 4D-01 约束：辅助 role 合法集合必须以真实 Schema 定义为准，Guard
  不得自行扩大或缩小。
- 判定：MISALIGNED + 缺陷。
- 问题：
  1. `_text` 未在文件中定义；`slots` 非空时 PC-005 会抛 `NameError`，当前样本
     slots=[] 才未触发。
  2. 辅助 role 集合硬编码，违反“以 Schema 为准”。
  3. 保守判定逻辑（无证据 → NOT_VERIFIED）本身正确，予以保留。

### PC-006 Legacy 分类

- 当前实现：`pageComposition.class` 必须在
  `{formal, legacy_compatible, unclassified_historical, incomplete}`。
- ADR-004：分类语义一致。
- 判定：ALIGNED。

### PC-007 Legacy fallback

- 当前实现：formal + fallback → FAIL；有 fallback → WARNING；无 fallback →
  NOT_VERIFIED。
- ADR-004：正式页面禁止隐式补齐；必须区分源码存在 / 调用链可达 / 运行时执行。
- 判定：PARTIAL。
- 问题：不携带证据等级，任何被列为 fallback 的来源都算 WARNING，无法区分
  源码存在与运行时实际执行。

### PC-008 权限边界

- 当前实现：`permission_evidence` 非空即 PASS。
- ADR-004：服务端最终授权；`permissionSemanticsPreserved=true` 仅声明，不得单独
  判定 PASS。
- 判定：MISALIGNED。
- 问题：以“证据列表非空”为 PASS 条件，不校验证据类型；若采集器把布尔声明放入
  `permission_evidence`，会误判 PASS。

### PC-009 版本兼容

- 当前实现：`version_compatibility_evidence` 非空即 PASS。
- ADR-004：旧消费者必须检查实际消费链，不能仅凭新增字段未改旧 Schema。
- 判定：PARTIAL。
- 问题：不区分证据等级，不校验是否为真实旧消费者回归。

### PC-010 历史节点身份

- 当前实现：`historical_node_identity_evidence` 非空即 PASS。
- ADR-004：必须有稳定身份及迁移前后对照证据。
- 判定：PARTIAL。
- 问题：不校验对照证据的存在与一致性。

### PC-011 布局一致性（缺失）

- 当前实现：不存在。
- ADR-004：需要 containerTree 布局一致性规则。
- 判定：GAP。

## 跨规则发现

1. `_text` 未定义：slots 非空的页面（payment.request slots=9）会运行时崩溃。
2. 无独立 evidence collector：doc 13/16 描述的采集器没有对应脚本，Guard 假定存在
   受信采集器并直接消费手写 JSON。
3. 报告缺口：缺少 `execution_timestamp`、`page_classification_summary`、
   `evidence_summary`；Markdown 只有 overall + 规则/状态两列，缺少状态计数、
   NOT_VERIFIED 清单、FAIL 清单与整改建议。
4. `overall_status` 计算（FAIL > NOT_VERIFIED > WARNING > PASS）方向正确，
   NOT_VERIFIED 不会被转成 PASS，保留。
5. PC-007/008/009/010 的 PASS 均建立在“证据存在”而非“证据充分”，与
   ARCH-DECISION-004 的证据边界要求不一致。

## 结论

Guard 与 ARCH-DECISION-004 尚未对齐。需要：

- 修复 `_text` 缺陷。
- 明确证据等级并让 PC-007～PC-010 只在独立/运行时证据下 PASS。
- 强化 PC-002/003/004 的归属与引用校验。
- PC-005 改为 Schema 驱动辅助 role 集合。
- 新增 PC-011（见 60 号文档）。
- 补齐报告字段与 Markdown 结构。
