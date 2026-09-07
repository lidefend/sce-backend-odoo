# 主产品仓库全量审计 — Batch-AUDIT-20260907

## 1. 边界

- Formal Product Layer：P4 ops delivery / verification governance。
- Layer Target：主产品仓库的架构、契约、后端、前端、CI、安全、报告和 agent 协作基线。
- Module：`addons/smart_core`、`addons/smart_construction_core`、`frontend/apps/web`、
  `scripts/verify`、`scripts/ci`、`.agent`。
- Standard vs User-Specific：仓库级治理标准；不包含客户偏好或业务数据基线。
- Why Here：审计证据和下一轮调度属于 P4，必须集中记录，避免前端或业务模块吸收治理语义。
- Why Not Elsewhere：不在 P0/P1 产品代码中修复，不在前端推导契约，不创建运行时/数据库替代路径。
- Blast Radius：仅新增审计与 agent 元数据；无产品模型、intent、契约、启动链、数据库、fixture、端口、卷或远端状态变化。

## 2. 候选身份

- 分支：`audit/full-repository-baseline-20260907`
- 基线：`5a18788534981a2025bc24acecb9bfb1740b0f7c`
- 本批次目标：建立可复现的主产品仓库现状基线，并把下一轮迭代顺序写入 agent 协作 workflow。

## 3. 审计盘点

- 测试资产：1354；review queue 4；unknown runtime 3；long-running 175；manual review 4。
- 模块依赖：13 个 addon、19 条内部边、20 条外部依赖、0 循环、0 缺失内部依赖。
- 复杂度：扫描 4299 个文件；48 个需要 split plan；86 个超过 warning threshold。
- 最高复杂度热点：`unified_page_contract_v2_assembler.py`、`test_ui_contract_v2_boundaries.py`、
  `ui_contract_v2.py`、`page_assembler.py`、`ActionView.vue`。

## 4. 验证结果

### PASS

- `make verify.repository.clean_history`：secret scan 0、personal-data confirmed 0、租户边界通过、
  分支/base policy 通过、GitHub Actions/Gitee guards 通过、reachable scan 无 unreachable/stash/tag 异常。
- `make ci.generated_reports.guard`：7 类生成报告与 contract fingerprint 均 current。
- `make verify.ci.scheduled_gates`：通过，所有 scheduled-gate 测试均通过。

### FAIL（按责任层分流）

1. `make verify.frontend.quick.gate`：`test_zero_gap_report_has_no_stale_next_batch` 失败，
   rendering-detail 报告 gap=7。归因：`baseline_evidence_defect`；现有 landing 文档声称 gap=0，
   需要先统一机器报告与文档基线，禁止在前端补语义。
2. `make verify.backend.architecture.full`：`smart_core_boundary_guard` 失败，
   `addons/smart_core/utils/load_contract_response_cache.py` 含 `smart_construction_core`。
   归因：`product_boundary_defect`（P0/P1 ownership）；下一轮应先完成边界归属审计，再决定迁移或豁免，
   不把行业语义继续留在 `smart_core`。
3. `make verify.guard.registry`：4 个 orphan scripts 未登记：
   `test_backend_business_fact_model_audit.py`、`test_scene_inventory_freeze_guard.py`、
   `test_scene_inventory_test_boundary_guard.py`、`test_scene_r3_action_target_scene_resolution.py`。
   归因：`validation_governance_defect`；需逐个确认 owner、入口和生命周期，不能目录级 seed 豁免。

## 5. 未执行与原因

- 完整浏览器/运行态 acceptance：`not_run`；前端静态 gate 已失败，按规则停止长链。
- 数据库、fixture reset、模块升级、生产/发布快照：`not_run`；本批次是只读审计，不具备产品运行态写入授权。

## 6. 下一轮唯一顺序

1. P4/P0 边界确认：审计 `load_contract_response_cache.py` 的行业依赖，形成迁移/删除/正式豁免决策。
2. P4 报告一致性：修复 rendering-detail 机器报告与 landing 文档的 gap=7/0 漂移，并补非零行为测试。
3. P4 守卫治理：逐个收口 4 个 orphan scripts，补 registry owner、Make 入口和回滚说明。
4. 仅前三项通过后，重跑前端 quick、后端 architecture full，再进入 runtime/contract/browser gates。

## 7. 回滚与产物

- 回滚：回退本批次 agent metadata、审计报告和 workflow 提交；不需要数据库或模块恢复。
- 产物：`docs/engineering_convergence/*` 当前报告、`docs/ops/iterations/repository_full_audit_batch_20260907.md`、
  `.agent/runs/REPO-BASELINE-AUDIT/20260907.yaml`。
