# FE-RENDERER-02C-01-R2A：dataType 状态类型边界

## 批次边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：业务表达字段类型归一。
- Module：`businessValuePresentation`、共享业务语义测试和静态守卫。
- Baseline：`603f8d16ded69afe4c5b613cafb2ac01571a3a20`。

## 审查发现

当前 fail-closed 检查只调用 `normalizeFieldType(type/ttype)`。当字段仅声明
`dataType: 'selection'` 且 selection 缺失或为空时，类型归一结果为 `unknown`，可绕过
selection-backed status 的拒绝逻辑。

## 修复原则

- `ttype/type` 明确声明始终优先。
- 只有原生类型归一为 `unknown` 时，才回退读取 `dataType`。
- dataType-only selection 必须提供有效 selection。
- char-status 不受影响。
- 不修改 Contract V2 Schema、行业 Renderer 或 FE-PAYMENT-ENTRY-01。

## 状态

- 实现：PASS。
  - `ttype/type` 明确声明仍为第一权威。
  - 只有原生类型归一为 `unknown` 时，才读取 `dataType`。
- dataType-only selection：
  - 缺失 selection：`ContractGapError`。
  - `selection: []`：`ContractGapError`。
  - 有效 selection：正常显示契约标签。
- 冲突优先级：
  - `type=char` + `dataType=selection`：char-status 可读值路径生效。
  - `type=selection` + `dataType=char`：selection 规则生效并 fail-closed。
- char-status：PASS。
- 业务语义：PASS，`money=6 status=13 temporal=4 empty=3`。
- 静态守卫：PASS，10 tests；dataType 覆盖原生类型会 FAIL。
- BOQ 消费回归：PASS。
- Lint：PASS，0 errors。
- Strict Typecheck：PASS。
- `ci.local.iteration`：PASS，5/5 targets，无 blocked/not-run/unmapped。

Receipt：
`.runtime/frontend-dev-validation/executions/20261108T003920Z-308954-596527590/receipt.json`

## 未覆盖

- FE-PAYMENT-ENTRY-01 的 409 继续独立处理。
- 不重新执行已通过的 Kanban、审批和金额表达 L4；本次变更只影响 status 字段类型归一。
