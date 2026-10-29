# PAYMENT-LIST-CREATE-EVIDENCE-03 — 隔离候选验收能力设计

状态：阶段 A（profile、合同 schema、守卫、配建契约与定向测试）；未创建环境、未写业务。

## 目标

为 #770 候选建立不依赖共享 `sc_frontend_acceptance` / `sc-fe-r2-p1-01` 的候选验收路径，
使 `list_surface_structure` 与 `relation_roundtrip` 能在同一候选身份上运行，并把证据绑定
完整候选 SHA、数据库 UUID、前端构建指纹与后端契约回执。

## 候选 profile 合同

`config/frontend/acceptance_environments_v1.json` 新增 `candidate` profile：

- `target_mode=external`：永不自动管理服务，永不回退共享 carrier。
- `base_url_required` / `database_required` / `expected_sha_required` /
  `target_identity_required` 全部为真：身份缺失即失败。
- `allowed_operations=["readonly"]`：仅允许只读证据采集。
- `resource_contract` 声明独立 `sc-fe-candidate-770`、独立三卷、独立三端口与候选库
  `sc_frontend_acceptance_candidate`。
- `isolation_guard.never_target` 显式排除共享资源。

工具矩阵为 `list-surface-structure` 与 `relation-roundtrip` 增加 `candidate` profile。

## 守卫与配建入口

`scripts/ops/candidate_acceptance_profile.py`：

- 解析并校验 candidate profile 的隔离不变量（外部模式、只读、强制身份、资源不与
  `sc-fe-r2-p1-01` / `sc_frontend_acceptance` / `sc_fe_r2_p1_01_*` 重叠）。
- `provision_plan`：只输出资源合同与所需输入，不创建任何资源。
- `provision_apply`：要求精确确认与已登记资源回执；在阶段 C 授权前拒绝任何实际配建。

## 制品与回执 schema

- `config/frontend/acceptance_fixture_manifest_v1.schema.json`：验收夹具配对制品
  （模块/版本、来源 UUID、数据库与附件摘要、配对稳定、恢复期望表计数）。
- `config/frontend/candidate_contract_receipt_v1.schema.json`：后端契约回执
  （候选 SHA、数据库 UUID、服务身份、action/view、有效 create/edit/delete、
  表单绑定与默认上下文）。

## 阶段边界

- A：本设计 + profile + 守卫 + schema + 定向测试（本次）。
- B：独立 Draft PR，等待复审。
- C：复审通过并单独取得资源创建授权后，才实现实际 carrier 配建、夹具安装与前端构建绑定。
- D：身份/隔离/契约回执通过后，才运行 E2.3 两项浏览器验收。

## 未实现部分（待阶段 C）

- 实际资源创建与 carrier 配建（当前 `provision_apply` 明确拒绝）。
- 验收夹具配对制品生成与隔离库 fixture 安装。
- 前端构建身份绑定与后端契约真实读取回执生成。
