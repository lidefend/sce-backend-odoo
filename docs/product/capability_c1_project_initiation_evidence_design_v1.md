# C1 项目创建 · 契约与证据闭环设计（CAP-01C-C1-01 Phase 1）

状态：设计冻结候选，待架构复核后进入 Phase 2 测试实施
能力身份：`project.initiation.create`（兼容别名 `project.initiation.enter`）

## 1. 执行链（真实事实）

```text
project.initiation.create
  -> intent: project.initiation.enter
  -> ProjectInitiationEnterHandler
  -> ProjectCreationService.normalize_create_vals + project.project.create + post_create_bootstrap
  -> 真实项目记录 + 初始化结果
```

## 2. 契约声明（已写入 capability_acceptance_contracts_v1.json）

| 维度 | 内容 |
|---|---|
| 能力身份 | `project.initiation.create` |
| Provider | intent `project.initiation.enter` + action `action_project_initiation` + model `project.project`（+ 条件性 `project.task`） |
| 输入 | `name`（必填）、`description`、`date_start`、`date_end`、`partner_id`、`manager_id`、`user_id` |
| 输出 | 真实 project ID + 创建结果 + 初始化结果 |
| 业务规则 | name 非空；manager_id 缺省=user_id/当前用户；phase_key 缺省=initiation；lifecycle_state 缺省=draft |
| 副作用 | project.project 记录（成功必然）；project.task 根节点（条件性）；mail.message 初始化消息 |
| 错误 | MISSING_PARAMS（pm）/ PERMISSION_DENIED（只读角色 general_user）/ BUSINESS_RULE_FAILED |

角色事实（ACL 四个权限位 = 读/写/建/删）：

- `pm` → `group_sc_role_project_manager` → `group_sc_cap_project_manager` = 1,1,1,1（可建）。
- `general_user` → `group_sc_role_general_user` → `group_sc_cap_project_read` = 1,0,0,0（只读，不可建）。
- `project_member`/`group_sc_cap_project_user` = 1,1,1,0（可建），**不是创建拒绝角色**。

授权判定遵循 `capability_authorization_model_v1.md`：角色只是测试主体标识，授权判据是
能力配置（`capability_profile`）+ 原生 ACL/Record Rules + 服务端执行结果。

## 3. Preview / Standard 检查矩阵（五项契约检查为唯一有效标准）

| 检查 | Preview | Standard |
|---|---|---|
| contract_identity_consistency | ✅ | ✅ |
| contract_io_consistency | ✅ | ✅ |
| contract_dependency_consistency | ✅ | ✅ |
| contract_scope_consistency | ✅ | ✅ |
| contract_promise_consistency | — | ✅ |

Standard 包含 Preview 全部用例（contract_promise_consistency 为 Standard 新增）。

> 历史记录：早先的 write_contract / authorization_contract / write_regression 六项
> 业务测试矩阵与三链授权检查矩阵均已废止，不再作为 CAP-01C 的资格条件；仅作为设计
> 历史保留。C1 的授权事实由契约元数据与平台 Provider 注册验证承载，不逐项重测 Odoo ACL。

## 4. 五项契约检查（轻量认证标准，替代旧六项业务测试）

| 检查 | 要证明的事实 | 方式 |
|---|---|---|
| Identity | 能力身份与真实 Provider 对应 | Provider Registry + 注册链 |
| I/O | 输入、输出、错误表达完整 | 契约 JSON Schema |
| Dependency | 依赖及版本范围完整 | 依赖指纹 |
| Promise | 默认值、条件性行为、错误语义与 Provider 一致 | 契约语义比对 |
| Scope | 契约没有承诺 Provider 实际不具备的功能 | 契约-Provider 一致性 |

这些检查通过现有 Python、JSON Schema、Provider Registry 完成，不逐能力跑浏览器。

`business_scenarios` 是契约元数据（声明的授权期望），不是资格证据；资格证据由
`capability_maturity_evidence.py` 的 receipts + artifacts 承载，两者不得混淆。
场景中的 `role_group_xmlid` 是测试主体身份元数据，`capability_group_xmlid` 才是
实际授权输入；执行器不得根据角色组自行推断能力分组。

`business_scenarios` 的字段（role_code / capability_profile / capability_group_xmlid /
role_group_xmlid / expected）不直接传入 `capability_maturity.evaluate_business_handling`，
后者采用严格的场景字段集合校验。若未来需要角色业务处理证据，必须用明确的字段投影适配器
把场景元数据映射为评估器接受的字段，不得修改评估器迁就新结构。本项不影响当前五项契约认证，
只明确边界以避免 C1-02/03 生成错误证据包。

## 5. 依赖文件与指纹范围

product_dependencies（candidate_fingerprint 输入）：

```text
addons/smart_construction_core/handlers/project_initiation_enter.py
addons/smart_construction_core/services/project_creation_service.py
addons/smart_construction_core/models/core/project_core.py
addons/smart_construction_core/views/menu.xml
addons/smart_construction_core/core_extension_intent_handlers.py
```

authorization_dependencies（业务授权验证输入）：

```text
ir.model.access.csv / sc_record_rules.xml / sc_role_groups.xml
identity_resolver.py / core_extension_policy_maps.py
```

任一依赖文件变化 → candidate_fingerprint / maturity_fingerprint 变化 → 旧证据失效。

本清单与 `capability_acceptance_contracts_v1.json` 的 `product_dependencies` 完全一致。

## 6. Receipt 与 Artifact 可信来源链

1. 验收契约冻结（本阶段）。
2. 受控测试执行：指定代码版本 + 真实测试环境，记录执行对象/版本/时间/范围。
3. Artifact：保存实际测试结果、用例状态、业务结果证明。
4. Receipt：由受信任验证执行链生成，禁止人工填通过。
5. 指纹：`capability_maturity.py` 计算 candidate/maturity fingerprint。
6. 评估：`capability_maturity_evidence.py` 验证，输出 Preview / Standard。

约束：不修改 `capability_maturity.py`；哈希正确 ≠ 证据来源可信；标准不降低。

## 7. 条件性副作用声明（重要）

`ProjectInitializationService.bootstrap` 中任务根节点创建是条件性的：仅当
`project.task` 模型可用 + 有 create 权限 + 项目无现有任务时创建。契约不得把它定义为
所有情况下必然成功的副作用；C1-03 验证必须覆盖“不满足条件时不创建任务根节点”的分支。
