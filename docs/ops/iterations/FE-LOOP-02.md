# FE-LOOP-02 CI 路径归属与验证影响闭环

## 身份与边界

- 基线：`b154eae313cf65428d16325b0dfc3faaa68d919c`
- 分支：`fix/fe-loop-02-ci-path-ownership-20261107`
- Formal Product Layer：P4
- Layer Target：前端质量工具链、Agent 治理、控制面和后端运行时路径归属

本批不修改产品运行时、Renderer、浏览器验收、候选构建或部署。

## 只读审计

| 变更路径 | 当前风险分类 | 当前后端影响 |
| --- | --- | --- |
| `frontend/apps/web/src/**` | STANDARD / frontend | 空 |
| `scripts/verify/frontend_*` | 宽泛 backend STANDARD | 空 |
| `make/frontend.mk` | HIGH_RISK + frontend full | 空 |
| `make/codex.mk` | HIGH_RISK + backend_changed | 空 |
| `.agent/runs/**` | HIGH_RISK unknown | 空 |
| `.agent/context.yaml` / decisions | HIGH_RISK unknown | 空 |
| `scripts/ci/**` | HIGH_RISK + backend_changed | 指定 tool check 或 unknown |
| `.github/workflows/**` | HIGH_RISK | unknown/full |

审计结论：路径归属分散在 `risk_tiering_v1.json`、`backend_impact_plan.py` 的
`NON_RUNTIME/CONTROL_PLANE` 和 workflow 条件中，导致控制面被标记成后端业务变更，
前端质量工具链与前端运行时混淆，代理运行登记没有独立身份。

## 实现与验证

### 唯一路径归属

新增 `config/ci/path_ownership_v1.json` 和 `scripts/ci/ci_path_ownership.py`，作为风险分类器、
后端影响计划和 CI 规划器的共同事实源。类别包括：

- `frontend_runtime`
- `frontend_quality_tooling`
- `frontend_ci_tooling`
- `frontend_delivery_make`
- `frontend_extension_make`
- `codex_control_plane`
- `agent_run_registration`
- `agent_workflow_metadata`
- `agent_governance`
- `backend_runtime`
- `backend_quality_tooling`
- `ci_tooling`
- `security_tooling_control_plane`
- `release_security_control_plane`
- `build_runtime`
- `docs_bookkeeping`

`scripts/verify/frontend_*` 和 `scripts/verify/test_frontend_*` 归入前端质量工具链，
不再归入宽泛后端路径。`scripts/ci/frontend_*` 作为前端 CI 工具同时标记控制面，
但仍不标记为后端业务运行时。

### 责任区分

| 路径 | ownership | frontend | backend | control_plane | 主要验证 |
| --- | --- | --- | --- | --- | --- |
| `make/frontend.mk` | `frontend_delivery_make` | true | false | false | frontend incremental + iteration policy |
| `make/codex.mk` | `codex_control_plane` | false | false | true | iteration policy + publish preflight |
| `.agent/runs/**` | `agent_run_registration` | false | false | true | Agent ledger |
| `.agent/context.yaml` | `agent_governance` | false | false | true | Agent ledger + iteration policy |
| `scripts/ci/**` | `ci_tooling` | false | false | true | CI workflow contract |
| `.github/workflows/**` | `release_security_control_plane` | false | false | true | scheduled gates + security |
| `addons/**` | `backend_runtime` | false | true | false | selected module closure |

风险分类器新增 `control_plane_changed`、`backend_runtime_changed` 和
`ownership_categories_json` 输出；GitHub professional/merge workflows 与 Gitee gate plan 均绑定
`control_plane_changed`。

### 后端影响选择

- 后端影响计划首先读取中央 ownership。
- 仅 `backend_runtime` 非模块路径或 `GLOBAL` runtime/build 输入触发保守全量。
- 纯控制面、前端工具链和 Agent 治理不产生后端模块套件。
- 没有后端运行时影响时，`modules=[]`、`scope_status=NOT_APPLICABLE`，不会因为缺少历史复用证据
  回退到全量模块套件。
- 未知或非法路径继续产生完整模块集合，失败关闭。

### 五场景测试

新增 `scripts/ci/test_ci_path_ownership.py`，固定以下场景：

1. 纯前端：前端标准 lane，无 backend/ORM。
2. 纯后端：仅选择受影响模块闭包。
3. 前后端混合：前端 lane 与后端模块闭包同时保留。
4. 纯 CI 工具链：HIGH_RISK + control plane，backend false、ORM false、模块为空。
5. 发布/安全控制面：HIGH_RISK + control plane，模块为空，仅运行控制面工具检查。
6. 额外兜底：未知路径仍触发 HIGH_RISK、ORM 要求及全量模块选择。

### 验证结果

- `verify.ci.path_ownership.unit`：14 tests PASS。
- CI 相关单元测试：147 tests PASS。
- `verify.ci.workflow.contract`：全部子套件 PASS。
- `verify.frontend.dev.incremental.unit`：68 tests PASS。
- `make ci.local.iteration`：7 个必需目标全部 PASS。
- 执行回执：
  `.runtime/frontend-dev-validation/executions/20261107T122423Z-871563-576496319/receipt.json`

本批未修改产品运行时、浏览器验收、候选构建或部署。
