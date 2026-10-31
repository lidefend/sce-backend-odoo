# 54 · Structural Authority Decision（页面结构权威来源最终裁定）

## Status

READY_WITH_CONSTRAINTS

本裁定完成架构职责边界的正式冻结；约束在于布局契约（containerTree）尚未进入
Integrity Guard、Legacy fallback / 权限 / 旧消费者 / 历史节点身份仍为
NOT_VERIFIED，以及页面资产全集仍为 partial_known_samples。

## Evidence baseline

- backend_owned_page_composition_v1.md
- 06-v2-minimal-schema-decision.md
- 07-field-ownership-schema-design.md
- 08-page-composition-validation-rules.md
- 09-schema-compatibility-policy.md
- 10-schema-decision-record.md
- 12-integrity-guard-rule-matrix.md
- 14-page-composition-current-compliance-report.md
- 19-phase-4c-real-page-validation.md
- 42-runtime-evidence-consolidated-matrix.md
- 43-five-page-structure-differential-analysis.md
- 45-phase-4e-03-final-decision.md
- 46-project-page-composition-provenance.md
- 47-project-action-view-differential-trace.md
- 48-project-runtime-layout-source-report.md
- 49-phase-4f-01-acceptance.md
- 50-payment-request-composition-provenance.md
- 51-payment-execution-composition-provenance.md
- 52-payment-execution-structural-differential.md
- 53-phase-4f-02-acceptance.md

另有既有架构决策作为上位约束：

- `.agent/decisions/contract-first.yaml`（ARCH-DECISION-001）
- `.agent/decisions/contract-driven-runtime-authority.yaml`（ARCH-DECISION-002）
- `.agent/decisions/layout-contract-ownership.yaml`（ARCH-DECISION-003）

## 文档间结论冲突核验

核验结果：未发现不可调和的结论冲突，但存在四处需要显式对齐的表述差异。

1. `backend_owned_page_composition_v1.md` 治理约束第 1 条只把
   `formStructureContract` / `field_groups` / `page_orchestration` 列为结构来源，
   未提及 `layoutContract.containerTree`。46/48/50/51 号文档证明 containerTree
   是实际被 `NativeFormTreeRenderer` 消费的布局来源。

   对齐：该条约束针对“业务组合权威”，containerTree 属于“布局权威”，两者是不同
   层次而非同层竞争，因此不是事实冲突，但 v1 治理边界必须补充布局层。

2. 10 号文档 Formal Page 准入要求 `slots` 非空；46/48 号文档证明项目页面在
   `slots=[]` 时仍能通过 containerTree 渲染。

   对齐：渲染能力 ≠ Formal 准入。布局契约可以在业务组合缺失时支撑渲染，但
   不能因此认定页面具备 Formal 资格。两者不冲突。

3. 12 号文档 PC-004 标为 `PASS（assembler V4）`，14 号文档标为
   `NOT_APPLICABLE`，当前 Guard 实现（16 号文档）在无 ownership 时输出
   `NOT_VERIFIED`。

   对齐：PC-004 的“PASS”是规则单测能力，不是页面合规结果；无 ownership 时的
   页面级判定统一为 `NOT_VERIFIED`（唯一性无法被验证），不再使用
   `NOT_APPLICABLE` 描述“缺少 ownership”。

4. 50/51/52 号文档确认 fieldGroups 存在静态消费链但运行时影响未验证；
   08 号文档把 fieldGroups 视为 V2 结构通道。

   对齐：fieldGroups 是“业务分组事实”，其“是否参与最终 DOM”仍为
   NOT_VERIFIED，不能因通道存在就认定它是第二布局权威。

## 正式架构决策记录（ADR）

```text
ARCH-DECISION-004
Structural Authority of Backend-Owned Page Composition v1
Status: ACCEPTED（本轮冻结，纳入 54-58 号交付文档）
Date: 2026-10-31
Supersedes: 无（精化 backend_owned_page_composition_v1.md 的治理边界）
Aligns with: ARCH-DECISION-001 / 002 / 003
```

### Context

真实运行时证据表明：页面最终结构不是单一来源。

- `formStructureContract.slots` 表达业务区域与字段引用。
- `dataContract.dataMeta.fieldGroups.groups` 表达字段分组。
- `fieldOwnership` 表达字段唯一主展示归属。
- `layoutContract.containerTree` 表达布局拓扑，且已被 `NativeFormTreeRenderer`
  实际消费（RUNTIME_VERIFIED）。

项目详情在 `slots=[]`、`fieldGroups=false` 时仍能渲染，证明“业务组合权威”与
“布局权威”是两套独立事实，不能相互替代。

### Decision

1. Backend-Owned Page Composition v1 采用两层后端权威，职责不重叠：

   - 业务组合权威：`formStructureContract.slots` + `fieldGroups` +
     `fieldOwnership`。决定页面有哪些业务区域、字段属于哪个区域/分组、字段的
     唯一主展示归属。
   - 布局权威：`layoutContract.containerTree`。决定容器层级、布局拓扑与渲染
     组织，不承载业务语义。

2. 前端 Renderer 是表现权威，只做组件投影、交互与响应式映射，不得自行决定
   业务区域、字段归属或布局拓扑。

3. 服务端权限独立于以上各层，是最终授权权威，任何结构声明不得改变授权结果。

4. `containerTree` 与 `slots` 不是重复 Schema，而是需要建立显式引用/映射关系
   的两个层次。当前映射关系未建立，判定为 NOT_VERIFIED。

5. `fieldGroups` 不改变其“字段业务分组事实”职责；其运行时渲染参与度在取得
   运行证据前保持 NOT_VERIFIED。

6. `fieldOwnership` 不承载 `displayRole`，不新增第二条 ownership 表达辅助投影。

### Consequences

- Integrity Guard 需要新增布局一致性检查（建议 PC-011），验证 containerTree
  引用有效性、与 slots/fieldOwnership 的一致性、以及多结构来源是否冲突。
  本轮不实施。
- `slots=0` 且 containerTree 存在时，页面可以渲染但不得获得 Formal 资格；
  分类保持 unclassified_historical 或显式 legacy_compatible。
- 需要建立 slots ↔ containerTree 的显式映射校验，防止同一字段的业务归属被
  两个来源分别决定。
- Phase 4 不关闭，Phase 5 不启动。

## 五个裁定的最终回答

1. containerTree 与 slots 是否重复？

   不重复。slots 是业务组合权威，containerTree 是布局拓扑权威。两者必须共存，
   且必须建立显式映射；当前映射缺失，NOT_VERIFIED。

2. fieldGroups 是否属于页面渲染权威？

   fieldGroups 是字段业务分组事实，不是独立布局权威。运行时是否参与最终 DOM
   仍为 NOT_VERIFIED。不得仅凭字段存在认定其参与渲染。

3. slots=0 时如何处理？

   containerTree 不能替代 slots。Formal Page 必须 slots 非空；slots=0 时页面
   可渲染但不得获得 Formal 资格，归为 unclassified_historical 或显式
   legacy_compatible。

4. containerTree 是否需要进入 Integrity Guard？

   需要。建议以独立规则（PC-011 布局一致性）纳入，验证容器引用有效、与业务
   区域一致、无多来源冲突。本轮只记录建议，不修改 Guard。

5. 不同页面是否允许不同结构成熟度？

   允许。布局可渲染不等于业务组合完整；成熟度差异不得降低 Formal Page 准入
   标准。

## 对 Backend-Owned Page Composition v1 的调整结论

需要调整的是“治理边界表述”，不是 Schema：

- 明确“业务组合权威”与“布局权威”两层，分别由 slots/fieldGroups/fieldOwnership
  与 containerTree 承担。
- 将 containerTree 纳入 Guard 证据域（建议 PC-011），但不新增平行 Schema。
- `fieldOwnership` 的既有 minimal schema 保持不变。
