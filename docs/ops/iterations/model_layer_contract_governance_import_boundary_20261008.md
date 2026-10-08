# P1 模型层对 P0 契约治理的导入边界修复（2026-10-08）

## 1. 背景与责任层声明

`verify.boundary.import_guard` 在主线上因 `model_ui_dependency_guard` 失败：

```
[model_ui_dependency_guard] FAIL
addons/smart_construction_core/models/support/workflow_contract_service.py: forbidden model-layer UI dependency import: odoo.addons.smart_core.utils.contract_governance
```

- `Formal Product Layer`: **P1**（建筑行业标准产品）。
- `Layer Target`: `smart_construction_core`（模型层 + 服务层）。
- `Standard vs User-Specific`: 行业标准产品的分层规则——P1 模型层不得依赖 P0 契约治理机制，P0 消费点在 P1 服务层。
- `Why Here`: 守卫只约束 `smart_construction_core/models/**`，违规点就在该模型层；本模块已在
  `services/contract_governance_overrides.py` 消费 P0 契约治理，且已有 `models → services` 先例
  （`models/support/product_policy_sync.py` → `services/locked_menu_policy_contract`）。
- `Why Not Elsewhere`: 不放宽守卫前缀或断言；不改用 `contract_governance_registry` 钻前缀边界；不新增 P0 env seam；
  不改前端；不加模型特判；不动 ACL/字段权限/隐藏规则。
- `Blast Radius`: 仅 `workflow_contract_service._external_profile_by_model` 的注册表读取路径 +
  新增一个服务层访问器 + `services/__init__.py` 注册行；行为不变。

## 2. 根因

`2d164a1f`（PR #525）把行业工作流服务对「外部（P0 注册表）工作流投影档案」的读取直接写成模型层的
`from odoo.addons.smart_core.utils.contract_governance import workflow_contract_profiles`，
违反了自 clean baseline（`401bcb3b`）起即存在的 `model_ui_dependency_guard` 规则。该守卫不在
必需 CI 车道（也不在 `ci.local.quick`），故长期未被暴露。

## 3. 修复

将 P0 注册表读取迁到服务层，模型层只调用本地服务访问器：

- 新增 `addons/smart_construction_core/services/workflow_contract_profile_registry.py`：
  唯一 seam，`external_workflow_contract_profiles()` 返回 P0 注册表发布的档案。
- `addons/smart_construction_core/services/__init__.py` 注册该模块。
- `addons/smart_construction_core/models/support/workflow_contract_service.py`：移除对
  `smart_core.utils.contract_governance` 的直接导入，改由服务层访问器读取。

未放宽任何守卫、断言、ACL、字段权限或负例。

## 4. 验证

### 4.1 层级与命令

- **L1**：`make ci.local.iteration` → **PASS**（`change_state=dirty coverage=L1_only`）。
- **L2 定向（离线，非零）**：
  - `make verify.boundary.import_guard` → **PASS**（`Ran 2 tests` + boundary/schema/model 三守卫）。
    修复前 `[model_ui_dependency_guard] FAIL`，修复后 `PASS`。
  - `make verify.model.ui_dependency.guard` → **PASS**（扫描 `addons/smart_construction_core/models/**` 163 个 py 文件，0 违规）。
  - `make verify.native_view.workflow_action_coverage` → **PASS**（`Ran 8 tests` + `Ran 54 tests`）。
  - `python3 -m py_compile`（模型层、服务层访问器、`services/__init__.py`）→ OK。
- 回执（advisory，非交付门禁）：`.runtime/agent-runs/MODEL-LAYER-CONTRACT-GOVERNANCE-IMPORT-BOUNDARY/`
  的 `model_ui_dependency_guard.json` / `boundary_import_guard.json` / `workflow_contract_profile_loader.json`。

### 4.2 行为锁基线对照（重要）

行为锁用受管入口 `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestWorkflowContractBackend'`
（本地 `sc_dev_demo` profile）：

| 运行 | 结果 | 失败集合 |
| --- | --- | --- |
| 含本次改动 | `1 failed, 8 error(s) of 31 tests` | 9 个（见下） |
| 基线 `dba12da5`（`git stash` 本次 addons 改动） | `1 failed, 8 error(s) of 31 tests` | **完全相同**的 9 个 |

两次的失败测试名与数量逐条一致，失败原因是本地 demo 数据漂移（`P0_STATE_ILLEGAL_TRANSITION`、
`费用与扣款单据必须关联已归属公司的有效项目`、`test_the_shared_approval_family_declares_only_reachable_states`
期望 10 个模型却为空等），**与本次「导入位置搬迁」无关**。

因此本次改动的行为结论为：

- **不引入任何回归**（改动前后失败集合逐条相同）；
- `verify.workflow_contract.backend` 的行为用例在本地 `sc_dev_demo` 上本就非全绿，
  属既有环境/夹具漂移，且不在必需 CI 车道；**不在本批修复**，不可据此宣称该车道通过。

## 5. 边界

本条只主张**批次验收**；主线集成、版本发布、产品交付另行报告。

## 6. 收口

- 精确候选 `f833b860ddeafdd7ca1502e8220c7d135125f941`（tree `5682c8e52292d6c7370849ee9c626d07d925c929`）
  的 `make ci.local.quick` 回执已签发（`.git/codex/evidence/ci.local.quick/f833b860….json`）。
- PR #616（head `f833b860…`，base `dba12da5…`）四项必需检查在精确 head 全 success，
  `make pr.merge` 复用同一 exact-head 回执（`REUSE`）后按受保护 PR 合并为
  `5c028d03fe6069340515886b498740d348291755`。
- 本 run/goal 标记 `completed`，`.agent/active-runs.json` 不再保留指向已合并
  `fix/model-layer-contract-governance-import-boundary-20261008` 分支的索引项。已合并分支的删除属于
  独立 `branch.retire.historical` 车道。
- 同一候选内发现的迭代效率缺陷（记账类候选重复支付全量 Quick）另立专题，见
  `docs/ops/iterations/merge_lane_bookkeeping_candidate_guard_20261008.md`。
