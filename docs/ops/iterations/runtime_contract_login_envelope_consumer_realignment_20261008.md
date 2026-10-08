# 运行态契约族登录封套消费面对齐（2026-10-08）

## 1. 目的与边界

把运行态契约族（`verify.contract.surface_mapping_guard`、`verify.scene.catalog.runtime_alignment.guard`、
`verify.scene_capability.contract.guard`、`verify.contract.ordering.smoke`、`verify.contract.mode.smoke`、
`verify.contract.view_type_semantic.smoke`、`verify.contract.assembler.semantic.smoke` 及其能力下限级联）
在受管 `local.dev` 档案下重新取证，并给出真实结论。

- Formal Product Layer：P4（受管验证工具族与其门禁）。
- Layer Target：`scripts/verify/`、`scripts/e2e/`、`scripts/audit/`、`scripts/ops/`、`scripts/release/` 的
  登录封套消费面；新增一个 fail-closed 守卫目标。
- Standard vs User-Specific：ops delivery tool（P4）。
- Why Here：登录生产者本身正确，其声明形状为 `data.session.token`；缺陷在消费该声明形状的 P4 验证工具层。
- Why Not Elsewhere：不改登录契约、不加/删生产者兼容别名、不放宽任何断言/ACL/字段权限/负例、
  不改 Odoo 模块、不改前端。
- Blast Radius：仅验证工具族的 token 读取路径；服务端、契约 schema、权限、动作零改动。

## 2. 根因（已确证）

`addons/smart_core/handlers/login.py:323` 在洁净产品基线起就把 token 发布在 **`data.session.token`**；
只有 `contract_mode in {"compat","debug"}` 时才额外补顶层 `data.token`，且该兼容面已声明
`compat_deprecated: true` / `compat_sunset_phase: "next_iteration"`（`login.py:372-376`）。
`data.session.token` 由 `git blame` 定位到 `401bcb3b`（2026-07-20，洁净产品基线）。

而 `scripts/` 下大量验证/冒烟脚本仍只读 `data.token`，因此在**凭据完全正确**时依然报
`missing token` / `login failed`。已用只读探测取证：

- `http://localhost:8070/api/v1/intent`（库 `sc_dev_demo`）上
  `admin/admin`、`wutao/scdevpass`、`demo_pm/scdevpass`、`sc_fx_*/prod_like` 均返回 200，
  token 位于 `data.session.token`；
- 在这些凭据下重跑 `make verify.contract.surface_mapping_guard` 仍报
  `RuntimeError: missing token`（`scripts/verify/surface_mapping_guard.py:31`），证明与凭据无关。

结论修正：原 `saved_search_capability_unit_recovery_20261008.md` §4.C 把这批失败整体归因为
「运行环境前置未满足」，对其中 `data.token` 只读消费者而言**不成立**——它们是 P4 工具层的
**陈旧声明消费者缺陷**，不是环境前置。诚实标注：该 §4.C 结论在此更正。

附带事实：这族目标**没有任何 GitHub 计划 CI 车道调用**（`grep` 计划工作流无命中），
所以该漂移长期未被守门发现；这是守门缺口，本身不构成本批修复对象。

另一个独立前置：`session.bootstrap` 在本库报
`bootstrap user not found: svc_project_ro`。`.env.dev` 声明了 `SC_BOOTSTRAP_LOGIN=svc_project_ro` /
`SC_BOOTSTRAP_SECRET`，但该服务身份未在 `sc_dev_demo` 中开通；须走既有受管入口开通后复验。

## 3. 修法与证据

本批共四类根因，各自独立责任层，一次性收口。

### 3.A P4 消费面：登录封套 `data.token` 陈旧读取（原目标）

- 修法：全部 `scripts/**` 登录消费者统一改用共享读取器
  `scripts/verify/python_http_smoke_utils.py:extract_login_token`（读 `data.session.token`，
  按声明保留 `data.token` 兼容面的读取顺序）。共迁移 71 处（首轮 65 + 守卫暴露的 6 处遗留：
  `role_surface_smoke.py`、`e2e_scene_smoke.py`、`e2e_contract_smoke.py`、`role_nav_diff.py`、
  `verify_colocated_platform_matrix.py`、`production_user_password_reset.py`）。
- 清理迁移残留死局部（`data`/`session`），AST 扫描归零；改动文件 `py_compile` 全部通过。
- 新增 fail-closed 守卫 `scripts/verify/login_envelope_consumption_guard.py`
  （AST 追踪 login 派生名与别名链，命中「login 信号绑定的 token 读」即红，`session` 面豁免，
  不可解析即 fail-closed，仅豁免共享读取器自身），单测
  `scripts/verify/test_login_envelope_consumption_guard.py` 9 项（含先证明未注入基线正常、
  再证明注入被检出的负例）。注册 `verify.login_envelope.consumption.guard`，
  并挂入 `ci.local.quick.run` 前置，补上「该族无任何计划 CI 车道」的守门缺口。

### 3.B P0 生产者：`ui.contract` 交付数据的 surface 元信息丢失（本批新暴露）

- 缺陷：`addons/smart_core/handlers/ui_contract.py:_shape_delivery_data` 已解析并用于
  `meta.contract_surface` 的 surface，在 fallback 分支被丢弃——
  `apply_contract_governance(data, contract_mode, inject_contract_mode=False)` 未传
  `contract_surface`，于是默认值 `user` 覆盖了交付数据。表现为请求
  `contract_surface=hud` 时 `meta.contract_surface='hud'` 但 `data.contract_surface='user'`
  （`data.source_mode='governance_pipeline'` 也证明最后一次治理调用来自该 fallback）。
- 权威依据：`docs/contract/contract_surface_spec_v1.md` §2「所有生产 contract 必须包含
  `contract_surface`」、§4.1「统一通过 `apply_contract_governance` 输出 surface 元信息」、
  §5.3 `verify.contract.surface_mapping_guard`「验证 mapping 结构完整与 surface 对齐」。
  故守卫断言正确，缺陷在生产侧的元信息丢失。
- 修法（通用、无模型特判、不动 ACL/字段权限/隐藏规则）：fallback 透传已解析的
  `contract_surface`；`user` 面行为不变，`hud/native` 按声明面标注。
- 证据：
  - 离线单测 `addons/smart_core/tests/test_ui_contract_delivery_surface_alignment.py`
    （2 项，经 `verify.ui_contract.delivery_surface.unit` 注册）；负例已证：还原缺陷写法时
    hud/native 用例失败且 `user` 控制用例仍通过，说明该对照能检出「硬编码 user」。
  - 运行态 `verify.contract.surface_mapping_guard`：修复前 FAIL（`hud: data.contract_surface
    must be hud`）→ 修复后 PASS。
  - 独立回读（`http://localhost:8070`，库 `sc_dev_demo`，`op=model project.project form`）：
    `user → data/meta 均 'user'`；`hud → data/meta 均 'hud'`；`native` 仍按声明对前端返回 410
    （`native ui.contract op is disabled for frontend delivery`）。

### 3.C P4 校验工具：角色矩阵口令未消费受管声明（级联失败真因）

- 缺陷：`scripts/verify/scene_capability_contract_guard.py` 用
  `os.getenv("E2E_ROLE_MATRIX_DEFAULT_PASSWORD") or "demo"`，未消费受管档案声明的
  `SC_DEMO_USER_PASSWORD`（`.env.dev`，`local.dev.demo_credentials.prepare` 固定为
  `scdevpass`）。因此在受管 local.dev 上 `demo_pm/demo_finance/demo_role_executive` 三个
  legacy 登录全部失败，样本里被计为 **capability_count 0**，才出现
  `role_capability_floor.guard: demo_role_executive: capability_count 0 < min 4`
  这一步下文级联。
- 修法：口令解析补上受管声明 seam（`E2E_ROLE_MATRIX_DEFAULT_PASSWORD` →
  `SC_DEMO_USER_PASSWORD` → `demo`），与既有 `scene_ready_strict_gap_full_audit.py` 的写法一致；
  不改角色、不改基线阈值、不放宽下限。
- 证据：修复后 `demo_role_executive` 实数 **63**（原报 0），
  `verify.role.capability_floor.guard` PASS、`verify.business.capability_baseline.report` PASS。

### 3.D 诚实更正（前轮结论）

前轮 `saved_search_capability_unit_recovery_20261008.md` §4.C 把这族失败整体归因为
「运行环境前置未满足」。除 3.A 之外，3.C 又给出第二个反例：失败来自 P4 校验工具的
**陈旧口令假设**，同样不是环境前置。该 §4.C 结论在此再次更正：环境中确实存在**独立**的
DENY 项（见 §5），但不能用它解释本族失败。

### 3.E 级联聚合的前置补齐（非缺陷）

`verify.backend.architecture.full.report` 的 4 个子证据报告在本档案下**从未生成**
（`capability_core_health`、`load_view_access_contract`、`scene_capability_matrix`、
`scene_contract_semantic_v2`），属聚合前置缺失而非产品失败；按各自受管入口补齐后
聚合 PASS。`verify.contract.evidence.guard` 的剩余失败同样是**生成证据前置**（见 §6）。

## 4. 本批运行态结果（受管 local.dev：`sc-local-dev` / `sc_dev_demo` / 8070）

命令统一为 `ENV=dev VERIFY_CACHE=0 make <target>`（`run.json` 记录 10 项 receipt）。

| 目标 | 结果 | 说明 |
|---|---|---|
| verify.login_envelope.consumption.guard | PASS | 9 单测 + 全库 AST 守卫 0 违规 |
| verify.ui_contract.delivery_surface.unit | PASS | 2 测（含缺陷还原负例对照） |
| verify.contract.surface_mapping_guard | PASS | 修复前 FAIL，本批 P0 修复解除 |
| verify.scene.capability.contract.guard | PASS | 口令 seam 修复后 11 角色样本 |
| verify.role.capability_floor.guard | PASS | 4 必需角色全部达标 |
| verify.role.capability_floor.prod_like | PASS | 7/7 fixture |
| verify.scene.catalog.runtime_alignment.guard | PASS | catalog=5 runtime=96 |
| verify.contract.ordering.smoke | PASS | scenes=96 capabilities=5 |
| verify.contract.mode.smoke | PASS | 8 单测 |
| verify.contract.view_type_semantic.smoke | PASS | 6 视图类型覆盖 |
| verify.contract.assembler.semantic.smoke | PASS | — |
| verify.business.capability_baseline.report | PASS | 3 检查全通过 |
| verify.backend.architecture.full.report | PASS | 前置 4 子报告补齐后 14 检查全通过 |
| verify.contract.governance.brief | PASS | — |
| verify.contract.evidence.guard | FAIL | 生成证据前置缺失，见 §6 |

## 5. 环境审计结论（仍保留的 DENY，不外推）

- **保留**：环境 DENY 仅针对「重建/快照车道」的阻断结论，必须绑定实际入口依赖与独立复核依据；
  本批未触碰该车道，也不存在「环境全部通过」的结论。
- **不做放宽**：审计门禁、ACL、字段权限、负例断言、`rendering_detail_state` 排除项一律未改。
- **本批实际改动面**：P4 验证工具（消费面 + 守卫 + 口令 seam）、P0 契约生产者的 surface 元信息
  标注。两者都不修改业务模型、契约 schema、权限或前端渲染。
- **凭据**：本批只消费既有受管声明（`.env.dev` / `SC_DEMO_USER_PASSWORD`），未新增或轮换任何凭据；
  固定口令沿用既有的隔离 fixture，不改动通用登录默认。

## 6. 剩余失败（诚实列出）

1. `verify.contract.evidence.guard`：`grouped_governance_brief` /
   `grouped_governance_policy_matrix` / `grouped_governance_trend_consistency` /
   `boundary_import_report` 指向的**生成证据报告不存在**（"report_json must point to a readable
   report"）。这是生成证据前置（`ci.generated_evidence.*` / freeze prepare）未跑，不是运行时契约
   缺陷；按批次规则在冻结候选阶段统一生成后再复验。
2. 本批未覆盖（属其它责任层，需独立单元）：`rendering_detail_state` 等既有权衡项仍引用既有证据与裁决，
   不在本批重复证明。

## 7. 后续（本批尚未完成的部分）

- L1 `make ci.local.iteration`、L2 定向非零测试、冻结 clean HEAD、完整指纹、一次
  `make ci.local.quick`、独立复核与 PR 发布。整体分支目标**未标记完成**。

## 8. 合并结果与 run 收口（2026-10-08 同日）

- 精确候选冻结 HEAD：**`a9ce7528db6464702395be3d7108f35abdab19db`**（clean，`tree=2f87e7d4`）。
- clean HEAD 上一次 `make ci.local.quick` → **PASS**（620s），回执
  `.git/codex/evidence/ci.local.quick/a9ce7528…json`；`make pr.push`（受管入口，`authoritative_remote=origin`）推送成功。
- PR #614 四项必需检查对**该精确 head**重新通过：`public_guard` / `merge_policy_gate` /
  `professional_quality_gate` / `frontend_release_gate`；辅助检查
  `classify` / `public_guard_classify` / `professional_authorization` /
  `python310_runtime_compatibility` / `release_candidate_gate` 均 pass。
- `make pr.merge PR=614 EXPECTED_HEAD=a9ce7528…`：
  `[pr.merge.local_quick_gate] REUSE: exact-head ci.local.quick evidence verified` → 受保护 PR 合并成功（squash）。
- 合并提交：**`d04b9fa1925391d98b10549c29b95b8c9f047350`**（"Merge PR #614"），`origin/main` 由
  `6c30c919` 前进到 `d04b9fa1`；已回读确认候选 head 为 main 祖先。

**收口（本轮）**：run 与 goal 标记 `completed`；`.agent/active-runs.json` 回到空终态，任何索引项都不再指向
已合并的 `fix/runtime-contract-login-envelope-consumer-realignment-20261008`；main 上
`make agent.run.resume` 将报 `unregistered`（沿用 `ACTIVE-RUN-INDEX-CLOSEOUT` / `-DANGLING-CLOSEOUT` 先例）。
已合并分支的删除属独立的 `branch.retire.historical` 车道，不在本批内。

**边界**：本条只主张**批次验收 + 主线集成**；**版本发布**与**产品交付**未主张。
