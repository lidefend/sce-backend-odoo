# P4 Isolated Acceptance Gate Portability — 2026-08-05

## 1. 本轮变更

- 目标：让 restricted 门禁在公司 ID 非固定为 `1/2` 的隔离验收租户中复用真实角色与公司证据。
- 完成：
  - 快照收集器支持 profile-only JSON override，并在子进程和所有输出边界移除/脱敏敏感配置。
  - 公司可达性预检支持 profile-only JSON override，保留 baseline 阈值、严格模式与报告路径。
  - 契约闭环结构守卫在 `contract_governance` 拆分后检查真实能力归一化所有者。
  - 新增 22 个定向回归用例，覆盖默认兼容、非法输入 fail-closed、跨 profile 脱敏、字段校验、固定策略保留和负向守卫。
- 未完成：全量前端真实页面审计；该工作属于下一独立批次。

## 2. 影响范围

- Formal Product Layer：P4 运维交付工具。
- Layer Target：隔离验收验证器与结构守卫。
- Module：`scripts/verify`、`docs/ops/verify/README.md`。
- Standard vs User-Specific：通用验收机制；不固化任何客户公司 ID、角色权限或业务数据。
- Why Here：差异来自验收环境身份和源码拆分后的守卫所有权，不属于产品语义。
- Why Not Elsewhere：不应修改 P0/P1/P2 模块、权限、接口、fixture 或数据库来迎合历史 ID。
- Blast Radius：仅 restricted 验收 profile 解析、报告脱敏和闭环结构检查。
- 启动链、contract/schema、default_route、public intent：均不变。

## 3. 环境与证据

- 数据库角色：`isolated_frontend_acceptance_tenant`。
- 租户：`internal_frontend_acceptance`。
- 环境：`codex_frontend_system_audit_20260805`。
- 数据库 / dbfilter：`sc_frontend_acceptance` / `^sc_frontend_acceptance$`。
- Compose namespace：`sc-fe-audit-20260805`；数据库、Redis、Odoo 使用同名独立 volume。
- Backend：`http://127.0.0.1:18094`；`LIST_DB=false`。
- 公司证据：fixture finance 角色对公司 `2`、`3` 的独立快照与可达性检查均 PASS。
- 未修改权限、接口、fixture 或业务数据来满足门禁。

## 4. 验证

- `python3 -m unittest scripts.verify.test_scene_company_snapshot_collect scripts.verify.test_scene_company_access_preflight_guard scripts.verify.test_backend_contract_closure_guard -v`：PASS，22 tests。
- 对上述实现与测试执行 `python3 -m py_compile`：PASS（pycache 位于临时目录）。
- A 线实现复核：PASS。
- B 线独立审计：PASS；跨 profile 密码、原始 override、输出边界和负向结构守卫均通过对抗验证。
- `make verify.restricted ...`：PASS。
  - frontend lint / strict typecheck / production build：PASS。
  - role matrix / company snapshot / company preflight / company matrix / multi-company evidence：PASS。
  - backend contract closure / governance truth：PASS。
- `git diff --check`：PASS。
- `make verify.docs.links`：FAIL（既有 69 个旧绝对路径；本轮修改文档命中 `0`，未在本批次跨范围修复）。

## 5. 产物

- `artifacts/backend/scene_company_snapshot_collect_report.json`
- `artifacts/backend/scene_company_access_preflight_report.json`
- `artifacts/backend/scene_multi_company_evidence_report.json`
- `artifacts/backend/backend_contract_closure_mainline_summary.json`
- `artifacts/backend/delivery_mainline_run_summary.json`

## 6. 风险与回滚

- P0：无。
- P1：profile override 若格式错误会 fail closed；不会回退到 baseline 或降低阈值。
- P2：隔离环境当前无 scene 数据，相关 scene 数量阈值按既有 restricted 策略跳过并保留 WARN；不影响本轮公司可达性证据。
- 回滚：回退本批次提交；不需要数据库回滚或模块升级。

## 7. 下一批次

- 目标：冻结并执行全量前端真实页面审计，覆盖五视口、跨业务域、页面体系、状态、无障碍与 BOSS/PUMA 差异矩阵。
- 前置条件：以本批次提交 SHA 为唯一审计锚点；不部署、不合并；审计、实现、验收职责隔离。
