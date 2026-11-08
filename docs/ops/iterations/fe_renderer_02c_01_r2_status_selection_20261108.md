# FE-RENDERER-02C-01-R2：状态选择项缺失 fail-closed

## 批次边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：Contract V2 前端业务状态解释。
- Module：`businessValuePresentation` 与共享业务语义测试。
- Standard vs User-Specific：平台工程标准。
- Baseline：`a4ec6e8f7f87d912d148ea7f076d79026ad1169e`。

## 目标

修复 selection-backed status 在 selection 元数据缺失或为空时静默显示原始 key 的
fail-open 行为。char-status 的合法可读值路径保持不变。

## 明确排除

不修改 Contract V2 Schema、后端 selection 投影、行业 Renderer、Kanban 语义、审批反馈、
FE-PAYMENT-ENTRY-01、PR #834；不部署、不合并。

## 状态

- 审查发现：CONFIRMED；`selection=[]` 或缺失时，status 分支跳过校验并返回原始 key。
- 实现：PASS；规范化字段类型为 `selection` 且有效选择项为空时抛 `ContractGapError`。
- 负向测试：PASS；缺失 selection、空 selection、未映射值均 fail-closed。
- char-status：PASS；未携带 selection 的契约可读值继续直接展示。
- 静态守卫：PASS；新增守卫自测，删除 fail-closed 条件会使守卫 FAIL。
- BOQ 消费回归：PASS。
- Lint：PASS，0 errors；仅既有 warning。
- Strict Typecheck：PASS。
- `ci.local.iteration`：PASS，5/5 required targets；`testsRun=true`、`blocked=0`、
  `not_run=0`、`registration_missing=0`、`unmapped=0`。

Receipt：
`.runtime/frontend-dev-validation/executions/20261108T001424Z-186701-112694394/receipt.json`

## 未覆盖

- 本批不重新执行 Kanban、审批或金额表达的已通过 L4；这些输入未被本次 status
  validation 修改。
- FE-PAYMENT-ENTRY-01 的 409 和审批内联反馈 P2 仍为独立后续任务。
