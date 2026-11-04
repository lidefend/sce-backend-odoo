# CAP-01C 成熟度资格 · 只读基线（三个样板差距矩阵）

状态：只读盘点，不生成资格、不修改正式目录

## 1. 三个样板现状

| 样板 | 能力 | 验收契约 | 现有测试 | 测试覆盖层级 | evidence bundle | 结论 |
|---|---|---|---|---|---|---|
| C1 | project.initiation.create | 无 | `test_project_initiation_native_lowcode.py` | 视图/表单结构对齐（接口/声明级），未覆盖完整业务写入结果 | 无 | 先补契约，再补业务结果测试 |
| C2 | construction.plan.manage | 无 | 仅 `test_role_surface_project_member.py` 间接 | 无专门计划能力测试 | 无 | 先补契约 + 依赖能力资格 |
| C3 | project.list.open | 有 | `test_capability_registry_service.py` + `ListPage.vue` | 部分（查询契约 + 角色表面） | 无 | 契约已声明，缺 evidence bundle |

## 2. 成熟度指纹计算（对齐 capability_maturity.py，不另造）

```text
candidate_fingerprint = sha256({capability_key, dependencies})
maturity_fingerprint  = sha256({candidate_fingerprint, criteria})
```

- `dependencies`：能力依赖文件摘要（roles/users 不作为输入）。
- `criteria`：preview / standard 两级必测用例；standard 必须包含 preview 全部用例。
- 指纹必须由 evaluator 计算，不能人工填写。

## 3. 证据链要求（capability_maturity_evidence.py）

- 每个能力必须有 `capability_acceptance_contracts_v1.json` 契约。
- evidence bundle（schema `capability.maturity.evidence.v2`）绑定：
  `capability_key` + `dependencies`（与契约 product_dependencies 一致）+
  `criteria`（与契约 product_criteria 一致）+ `receipts` + `artifacts`。
- receipt 绑定 capability + 依赖指纹 → artifact 执行用例（pass/fail/error/skip）。
- 过期、失败、跳过、重复证据一律拒绝。

## 4. Preview / Standard 差距

| 样板 | Preview 缺口 | Standard 缺口 |
|---|---|---|
| C1 project.initiation.create | 无契约 + 无业务写入结果测试 + 无 receipt | 同上 + 无 standard 全量用例 |
| C2 construction.plan.manage | 无契约 + 无组合契约 + 依赖能力未定资格 | 同上 + 依赖版本/兼容性/组合行为证据 |
| C3 project.list.open | 契约已有，但无 evidence bundle / receipt | 同上 + 无 standard 全量用例 |

## 5. Receipt 可追溯性

当前仓库未发现任何 `capability.maturity.evidence.v2` bundle，即三个样板均无真实
Receipt。Receipt 必须能独立追溯到真实执行记录（执行对象、版本、时间、验证范围），
不能人工填写。

## 6. CAP-01C 实施前提（按序）

1. 为 C1/C2 补 `capability_acceptance_contracts_v1.json` 契约（仅声明，不授予证据）。
2. 为三个样板确定真实业务结果测试（而非页面/接口测试）。
3. 生成受信 evidence bundle（真实 receipt + artifact）。
4. 用 `capability_maturity_evidence.py` 验证，输出 preview/standard 资格。

不允许为了凑齐三个样板而人为授予资格；达不到标准就保持未达标或退出候选。
