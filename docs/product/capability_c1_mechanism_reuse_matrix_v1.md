# C1 现有机制复用矩阵（CAP-01C C1-02 只读前置）

状态：只读盘点，不开发新脚本、不生成 Receipt、不评估资格

## 1. 五项契约检查 → 现有机制映射

| 契约检查 | 可复用机制 | 输出 | 是否可直接作 v2 Artifact |
|---|---|---|---|
| Identity | `capability_candidate_catalog_check.py --check`、`verify.capability.provider.guard` | provider 注册事实校验（intent/action/model） | 否（需映射为 v2 cases 格式） |
| I/O | 契约 `contract_io` + handler `_ALLOWED_FIELDS`（静态事实） | 静态声明比对 | 否 |
| Dependency | 契约 `product_dependencies` 文件存在性 + `candidate_fingerprint` | 依赖摘要 | 否 |
| Promise | 契约 `contract_promise`（静态声明） | 静态声明比对 | 否 |
| Scope | 契约 `input_fields` ⊆ handler `_ALLOWED_FIELDS`（静态比对） | 静态比对 | 否 |
| 指纹 | `capability_maturity.candidate_fingerprint` / `maturity_fingerprint` | 指纹 | 指纹本身可复用 |
| 资格评估 | `capability_maturity_evidence.verify_bundle` | preview/standard | 是（验证器，非生成器） |

## 2. v2 Artifact / Receipt 格式要求

- Artifact：`{capability_key, fingerprint, check_id, cases: [{id, status}]}`，status ∈ pass/fail/error/skip。
- Receipt：`{check_id, capability_key, fingerprint, artifact_sha256}`。
- Bundle：`{schema: "capability.maturity.evidence.v2", artifacts, capabilities:[{capability_key, dependencies, criteria, receipts}]}`。

现有机制输出均为各自的 JSON 报告，不是 v2 artifact 格式，需一个薄适配层把每项检查结果
映射为 v2 cases，不能手工拼凑或冒充。

## 3. Receipt 生产入口现状

- `verify.capability.maturity` → `capability_maturity_evidence.py`：是**验证器**，不是生成器。
- `scripts/ci/backend_test_receipt.py`：后端测试回执，非能力成熟度回执。
- 未发现现成的 `capability.maturity.evidence.v2` Receipt 自动入库生产链。

## 4. 结论与登记缺口

五项契约检查的计算与验证机制均已存在（provider 校验 + 静态契约 + 指纹 + 验证器），
但缺少“受管执行记录 → v2 Receipt/Artifact 入库”的生成入口。

缺口登记：C1-02 不新建平行引擎，先研究把现有 `verify.capability.provider.guard` /
`capability_candidate_catalog_check.py` / 契约静态校验的输出，经受管通道投影为 v2
Artifact/Receipt；在该通道闭合前，不声称 C1 已取得 preview/standard 资格。
