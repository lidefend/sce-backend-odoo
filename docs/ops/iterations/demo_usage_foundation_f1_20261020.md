# Demo 用户使用基础数据迭代 · F1 批次记录（2026-10-20）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- 父提交（F1 开工前）：`71b9fb90c856de1a2b4fcf40cbef4ede36e3646c`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（本批切为 `active`）
- Goal：`.agent/goals/DEMO-USAGE-FOUNDATION-20261020.yaml`

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling）
- Layer Target：`docs/demo` + `scripts/verify` + `make/dev_test.mk`（demo 使用基础数据声明与只读审计）
- Module：`smart_construction_demo`（demo 侧），不触碰产品 addons
- Standard vs User-Specific：demo delivery tool，只消费公开契约与动作
- Why Here：manifest 是交付清单，审计是 fail-closed 的声明覆盖检查，不承载产品语义
- Why Not Elsewhere：不改 P0/P1/P2/P3 产品行为、不写数据库、不补业务数据
- Blast Radius：新增 3 个文件 + 1 个 Make 目标；无运行时数据/模型/权限/流程变更

## 3. 本批单一目标

把「用户路径 → 基础数据 requirement」固化为机器可读清单，并提供只读审计入口：
先审计、不补数；发现的产品缺口继续在 `docs/demo/product_gap_registry_v1.md` 回收。

## 4. 产物与文件范围

新增：

- `docs/demo/demo_usage_foundation_manifest_v1.json`
  - 13 个用户动作（登录/我的工作/开项目/选主数据/建基线/合同依据/提交/审批/结算台账/驾驶舱/每日 tick/体验重置）
  - U0–U6 七层（U6 标记 derived-only，禁止 seed）
  - 28 项 requirement，每项含 key / 用户动作 / hard-conditional 前置 / read_entry / scope /
    owner_layer / repair_hint / acceptance_method / gap_ref
  - 5 个 DUF 缺口，每项含 owner_layer / blocking_batches / repair_hint / status
- `scripts/verify/demo_usage_foundation_audit.py`
  - 只读离线审计：manifest 结构校验 + 每项 observed/missing/blocked 分类 + batch_blockers 汇总
  - 不读数据库、不写数据；`data_readback=not_run` 显式声明
- `scripts/verify/test_demo_usage_foundation_audit.py`
  - 17 例离线单测：完整覆盖 / 缺失 / 非法声明（前置、层级、动作、缺口引用）/ 重复键 /
    open gap 阻断 / closed gap 解除 / batch_blockers 交叉暴露

修改：

- `make/dev_test.mk`：接入 `verify.demo.usage_foundation.unit`
- `.agent/runs/DEMO-USAGE-FOUNDATION-20261020/run.json`：status=active，登记新检查与 F1 证据
- `.agent/goals/DEMO-USAGE-FOUNDATION-20261020.yaml`：status=active，F1 完成边界

排除（本批未改、未动）：

- 主产品 worktree `/home/lidefend/workspace/sce-backend-odoo`、`main`、部署
- 数据库、tenant、Compose、端口、卷、凭据
- demo 数据载体、模型、timer、reset 实现（均 F2 及以后）
- `docs/demo/product_gap_registry_v1.md`（本批未发现超出 DUF-01..05 的新缺口）

## 5. 验证结果

| 命令 | 状态 | 层 | 测试数 |
|---|---|---|---|
| `python3 -m json.tool docs/demo/demo_usage_foundation_manifest_v1.json` | passed | L1 | — |
| `make verify.demo.usage_foundation.unit` | passed | L2 | 17 |
| `python3 scripts/verify/demo_usage_foundation_audit.py --manifest docs/demo/demo_usage_foundation_manifest_v1.json` | passed | L2 | — |

审计结论：`coverage_complete=true`；`overall_status=blocked`；
summary `observed=10 missing=0 blocked=2`；`data_readback=not_run`。
blocked 来自开放缺口 DUF-01/DUF-03/DUF-05；batch_blockers 同时暴露
DUF-02（F1/F3/F5）与 DUF-04（F3/F8）两个跨批次验收阻断。

## 6. F1 退出判据核对

- 每个用户动作都有 required-data 键：通过（missing=0）。
- 当前缺口全部有归属和阻断批次：通过（DUF-01..05 均含 owner_layer / blocking_batches / repair_hint）。
- 零测试不算通过：不适用（17 例非零）。
- 未补业务数据、未写产品层：满足。

## 7. 失败分类 / 阻断

无失败。`blocked` 是开放缺口的诚实状态，不是本批执行失败。F1 不声称任何数据就绪。

## 8. 回滚

- 删除 `docs/demo/demo_usage_foundation_manifest_v1.json`、
  `scripts/verify/demo_usage_foundation_audit.py`、
  `scripts/verify/test_demo_usage_foundation_audit.py`；
- 撤销 `make/dev_test.mk`、`run.json`、`goal.yaml` 改动；
- 保留 `docs/demo/product_gap_registry_v1.md` 原缺口登记。

## 9. 下一步精确动作

停止并交所有者。所有者确认后：F2（身份、公司与项目范围校正），开工前重做身份预检并复读 run。
