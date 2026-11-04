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

## 3. Preview / Standard 检查矩阵

| 检查 | 用例 | Preview | Standard |
|---|---|---|---|
| write_contract | native_action_target | ✅ | ✅ |
| write_contract | required_name_validation | ✅ | ✅ |
| write_contract | allowed_field_whitelist | ✅ | ✅ |
| write_contract | permission_denied_contract | ✅ | ✅ |
| write_contract | missing_param_contract | ✅ | ✅ |
| authorization_contract | create_requires_native_access | ✅ | ✅ |
| authorization_contract | record_rule_scope_applied | ✅ | ✅ |
| write_regression | create_produces_project_record | — | ✅ |
| write_regression | default_manager_phase_lifecycle | — | ✅ |
| write_regression | bootstrap_conditional_task_root | — | ✅ |
| write_regression | missing_name_rejected_no_record | — | ✅ |
| write_regression | permission_denied_no_side_effect | — | ✅ |
| write_regression | validation_failure_data_consistent | — | ✅ |

Standard 必须包含 Preview 全部用例（已满足）。

授权检查拆为三个独立维度（已写入契约）：

1. `capability_entitlement`：项目创建能力是否被授予。
2. `native_resource_authorization`：原生 ACL（create=1）与 Record Rules（公司/数据范围）。
3. `execution_authorization`：真实服务端请求是否通过全部授权。

## 4. 六类真实业务结果测试（Phase 2 实施）

| 测试 | 预期 | 判定 |
|---|---|---|
| C1-01 正常创建 | 数据库产生真实 project 记录 | ORM 创建成功 |
| C1-02 默认值 | manager/phase/lifecycle 符合规则 | 归一化结果正确 |
| C1-03 初始化 | 条件性任务根节点 + 初始化消息 | bootstrap 结果正确 |
| C1-04 缺名称 | 拒绝，不产生记录 | MISSING_PARAMS |
| C1-05 权限不足 | 拒绝，无业务副作用 | PERMISSION_DENIED |
| C1-06 数据异常 | 业务校验失败，数据一致 | BUSINESS_RULE_FAILED |

必须区分：接口返回成功 ≠ ORM 创建成功 ≠ 初始化成功 ≠ 完整业务结果正确。
写入能力必须验证失败时不留不完整业务数据。

C1-03 初始化必须覆盖全部条件分支（不得只断言“任务根节点存在”）：

1. 满足条件（project.task 模型可用 + 有 create 权限 + 项目无现有任务）→ 创建任务根节点。
2. 不满足模型条件（project.task 不可用）→ 不创建。
3. 不满足权限条件（无 create 权限）→ 不创建。
4. 项目已存在任务 → 不重复创建。
5. 初始化消息内容与实际执行结果一致。

C1-06 数据异常必须明确：

- 服务端业务校验失败时，事务回滚范围；
- 不得残留不完整 project 记录、孤儿任务根节点或半写消息；
- 部分副作用（如 message_post 在 create 之后失败）的回滚边界需单独验证。

## 5. 依赖文件与指纹范围

product_dependencies（candidate_fingerprint 输入）：

```text
addons/smart_construction_core/handlers/project_initiation_enter.py
addons/smart_construction_core/services/project_creation_service.py
addons/smart_construction_core/models/core/project_core.py
```

authorization_dependencies（业务授权验证输入）：

```text
ir.model.access.csv / sc_record_rules.xml / sc_role_groups.xml
identity_resolver.py / core_extension_policy_maps.py
```

任一依赖文件变化 → candidate_fingerprint / maturity_fingerprint 变化 → 旧证据失效。

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
