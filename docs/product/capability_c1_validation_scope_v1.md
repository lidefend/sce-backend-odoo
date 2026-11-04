# C1 认证方式（CAP-01C 统一基线：平台契约认证 + 能力契约一致性验收）

状态：设计冻结

## 1. 三项原则

1. 平台机制认证一次：契约生成、Provider 解析、契约结构校验的通用能力由既有平台测试证明。
2. 具体能力按契约验收：每项能力只需证明自己取得正确契约，且契约与能力承诺一致。
3. 认证结果可复用：同一能力被多场景/多产品引用，不重复认证。

## 1.1 SCE 能力交付模型

```text
Capability Identity（稳定能力身份）
Capability Contract（能力的完整标准化表达）
Provider Binding（契约背后的实际执行提供者）
Frontend Runtime（直接消费契约，完成用户交付）
Product Composition（将能力组织为工作场景和产品）
```

契约不是能力的说明书，契约本身就是能力的标准化表达和交付载体。前端无条件遵循
契约表达的行为，不自行推断、不私自修改、不另造业务规则；但服务端授权不允许时，
执行必须被拒绝；契约不完整或无效不能自行补齐后继续。

## 2. 轻量认证流程

```text
能力声明（project.initiation.create）
  -> SCE 平台解析 Provider（intent -> handler -> service -> model）
  -> 生成能力契约（identity/input/output/error/dependency/provider）
  -> 契约一致性检查
       - identity 对应正确
       - 输入输出完整
       - 能力承诺一致
       - Provider 解析正确
       - 依赖明确
  -> 通过 -> 可复用资格证据 -> 产品场景组合与发布
```

## 3. 契约一致性检查项（映射 capability_maturity criteria）

| 检查 | 用例 | 说明 |
|---|---|---|
| contract_identity_consistency | capability_key_matches_provider / provider_chain_resolves | 能力身份与 Provider 链一致 |
| contract_io_consistency | input_fields_whitelist_declared / output_record_shape_declared / error_codes_declared | 输入输出与错误契约完整 |
| contract_dependency_consistency | product_dependencies_complete / authorization_dependencies_complete | 依赖声明完整 |
| contract_scope_consistency | contract_does_not_exceed_provider_capability | 契约不超出 Provider 实际能力 |
| contract_promise_consistency | defaults_contract_consistent / conditional_bootstrap_contract_consistent / error_mapping_contract_consistent | 承诺与实现语义一致 |

`capability_maturity.py` 是 criteria 驱动（任意 check_id + receipts + artifacts），
可直接表达上述轻量认证，无需修改，也无需为满足旧测试数量要求制造业务测试。

## 4. 不重复验证

- Odoo ORM / 数据库 / 事务。
- Model / Action 原生注册。
- ACL / Record Rules 底层实现。
- 字段与关系机制。
- 平台契约驱动运行时、契约解析、页面渲染（已有平台测试覆盖）。
- 前端运行时消费契约的能力（平台统一契约消费测试覆盖，不逐能力重复）。

## 5. 必要区别

- 平台通用测试可复用；每项能力的契约解析/一致性结果必须有独立记录。
- 契约或 Provider 变化时，只重查对应能力；不同产品引用同一能力不重复检查。
- 只有发现平台机制缺口才增加新测试。
