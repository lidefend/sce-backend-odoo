# contracts

本目录为当前系统的权威契约源，按分层职责管理。

- `product/`: 产品能力与能力路由（供导航、菜单、系统初始化投影）
- `domain/`: 领域语义（状态机、动作、转移与业务字段语义）
- `schemas/`: 可复用结构定义（引用到 domain/api）
- `api/`: API 契约（OpenAPI + 接口分片）
- `extensions/`: 交叉横向扩展（权限/工作流/UI语义提示）
- `generated/`: 由契约生成/脚本产物（当前保留空位）

核心原则：

1. 以契约为源，不以文档/TypeScript 类型/Odoo 模型作为同等权威。
2. 上层契约变更优先，后端/前端按契约实现。
3. 当前阶段仅建立基础结构与支付申请样板，不作业务行为重构。

## 契约版本规则（R6，PRODUCTIZATION-P1）

1. **每个契约文档必须带版本**：`product/`、`domain/`、`extensions/` 文档顶层必须声明
   `version`（正整数，破坏性变更 +1）；`api/openapi.yaml` 以 `info.version` 为准。
2. **`registry.yaml` 为权威版本登记表**：`contracts/` 下所有 yaml（`generated/` 与
   registry 自身除外）必须登记 path/kind/version，`verify.contract.lint` 双向校验
   文档版本与登记表一致，未登记文件视为 lint 失败。
3. **`generated/contract-registry.json`** 由 `make contract.registry.export` 从登记表
   再生成，作为下游（导航/前端/守卫）可消费的机读版本清单，禁止手改。
4. **schemas/ 为纯结构映射**：顶层键即 schema 名，不插入版本键，版本只登记在 registry。

## 域契约覆盖（R6 后为 8 个核心域）

| 域契约 | 实体模型 | 语义来源 |
|--------|----------|----------|
| payment-request | payment.request | 原有样板 |
| payment-execution | sc.payment.execution | 模型状态机 + action_* 方法 |
| general-contract | sc.general.contract | 模型状态机 + action_* 方法 |
| settlement | project.settlement | ScStateMachine.SETTLEMENT |
| expense-claim | sc.expense.claim | 模型状态机 + action_* 方法 |
| invoice-registration | sc.invoice.registration | 模型状态机 + action_* 方法 |
| receipt-income | sc.receipt.income | 模型状态机 + action_* 方法 |
| project-lifecycle | project.project | ScStateMachine.PROJECT |
