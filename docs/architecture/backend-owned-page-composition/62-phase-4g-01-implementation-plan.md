# 62 · Phase 4G-01 Implementation Plan（最小改造方案）

## 定位

本文件是 Phase 4G-02 的实施方案；Phase 4G-01 只做审计与设计，不实施。
PC-011 必须先完成独立设计与测试（60 号文档），不得直接在 Guard 中加未经论证的
判断。

## 实施顺序

### Step 1 · 修复阻断性缺陷

- 在 `page_composition_integrity_guard.py` 内定义 `_text`（安全字符串提取），
  修复 PC-005 在 slots 非空时的 `NameError`。
- 补充一个 slots 非空的最小回归样例，证明 PC-005 可执行。

### Step 2 · 证据契约扩展

为 evidence payload 增加：

```text
evidence.legacy_fallback_sources[].grade   # source / static_chain / runtime
evidence.permission_evidence[].type         # runtime_test / static_chain / declaration
evidence.version_compatibility_evidence[].grade
evidence.historical_node_identity_evidence[].kind  # before_after_mapping / declaration
page.layoutContract.containerTree
evidence.layout_consumption
evidence.slot_container_mapping
evidence.allowed_slot_roles                 # Schema 派生，非 Guard 硬编码
```

### Step 3 · 实现独立 evidence collector

- 新增 collector，产出上述 payload；不复制 assembler 业务解析。
- 缺少采集能力的字段显式 NOT_VERIFIED，不伪造 PASS。

### Step 4 · 拆分 PC-001，新增 PC-011

- PC-001：只判定业务组合权威（slots）唯一性。
- PC-011：按 60 号文档实现布局一致性，跨层映射缺失即 NOT_VERIFIED。

### Step 5 · 强化归属与引用校验

- PC-002：Identity 字段 `ownerSlotRef == slot:identity` 才 PASS。
- PC-003：业务字段的 `ownerSlotRef` + `ownerGroupRef` 可解析。
- PC-004：移除死代码重复检测，校验每条 ownership 记录引用有效性。

### Step 6 · PC-005 Schema 驱动

- 辅助 role 集合改从 `evidence.allowed_slot_roles` 读取；不在 Guard 硬编码。
- 未知 role 保持 NOT_VERIFIED；role 超出 Schema 集合才 FAIL。

### Step 7 · 证据等级门禁

- PC-007：formal + runtime fallback = FAIL；source/static 仅 = NOT_VERIFIED。
- PC-008：只有 `type=runtime_test`（或等价独立证据）可 PASS；declaration 不得 PASS。
- PC-009：只有真实旧消费者回归（grade=runtime）可 PASS。
- PC-010：只有 before_after_mapping 且一致才 PASS。

### Step 8 · 报告补齐

- JSON 增加 `execution_timestamp`、`page_classification_summary`、
  `evidence_summary`。
- Markdown 增加各状态数量、NOT_VERIFIED 清单、FAIL 清单、风险与整改建议。

### Step 9 · Shadow 接入与回归

- Shadow 不改变现有 verify 退出码。
- Guard 执行异常必须记录，不得伪装 PASS。
- 回归四个已取证据样本 + Action 590，对比 Phase 4C 基线。

## 测试矩阵（非穷尽）

1. `_text` 修复后 slots 非空可执行。
2. 证据缺失 / 不完整 → NOT_VERIFIED。
3. PASS / FAIL 判定正确。
4. NOT_VERIFIED 不被转 PASS。
5. 权限声明不能替代权限证据。
6. Identity 错误归属 → FAIL。
7. 重复主展示入口 → FAIL。
8. Legacy 分类正确。
9. 正式页面隐式 fallback → FAIL。
10. 历史节点身份证据缺失 → NOT_VERIFIED。
11. Shadow 不改变原 verify 退出码。
12. Guard 执行异常被记录。
13. JSON 与 Markdown 一致。
14. 重复执行结果可追溯。
15. PC-011 十项专项（见 60 号文档）。

## 执行边界

- 只允许改造 Guard、新增 collector 与测试。
- 不修改 assembler、Schema、Renderer、业务配置、权限、数据库。
- 不删除 Legacy fallback，不迁移页面，不重建 Candidate。
- 不改变发布门禁阻断策略（Shadow）。

## 门禁条件

进入 Phase 4G-02 前必须满足：

- 60 号文档 PC-011 设计经评审冻结。
- Step 2 证据契约经 Schema 权威确认。
- 测试矩阵经独立评审。
- 未提交工作树继续保留。
