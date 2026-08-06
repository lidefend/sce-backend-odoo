# Formal Entry Metadata and Orphan Handoff Root Fix — Batch-FEM-RF1

## 1. 本轮变更

- 目标：将正式录入元数据缺口和架构拆分后遗留的三个不可解析 handoff
  UI 入口收敛为可安装、可升级、可幂等验证的 P1 产品修复。
- `smart_construction_core` 从 `17.0.0.81` 升至 `17.0.0.82`。
- 为 `project.project`、`project.funding.actual.event.allocation`、
  `sc.historical.payment.fact`、`sc.tax.certificate.registration` 注册统一的
  `source_created_by/source_created_at` 正式元数据字段，并在原生列表/表单中
  显示；`tender.doc.purchase` 使用其已有的
  `legacy_source_created_by/legacy_source_created_at` 真实历史来源字段。
- 新增版本化迁移：先快照三个 orphan model 对应的 menu/action/view/XMLID 与
  六个 summary/fact relation 行数，再仅移除这些不可解析 UI 元数据。底层 SQL
  view 和 fact relation 不删除、不截断、不改写。
- 正式元数据审计对 active menu 指向 registry 未注册模型实行 fail-closed；普通
  模型扫描仅审计 registry 已注册模型，避免把不可解析 action 当成可用页面。

## 2. 架构与数据边界

- Formal Product Layer：P1 施工行业标准产品。
- Layer Target：L2 原生模型扩展、视图合同、版本化升级迁移和正式表面审计。
- Module：`smart_construction_core`；验证入口位于 `scripts/verify` 与
  `make/dev_test.mk`。
- Standard vs User-Specific：正式录入来源语义和不可解析菜单的 fail-closed
  规则属于行业产品标准；迁移只处理历史交付留下的 UI 元数据，不吸收客户 handoff
  模块或客户业务事实。
- Why Here：行业模块拥有正式模型字段、原生视图、菜单可用性和可重放升级路径。
- Why Not Elsewhere：不得使用前端兜底、`create_uid/create_date`、低代码配置、
  客户模块补装或业务数据修补掩盖注册和 UI 元数据缺口。
- Blast Radius：五类正式录入元数据表面及三个精确 orphan model 的 UI 元数据。
  不影响启动链、public intent、ACL、工作流、业务 relation、附件或生产。

## 3. 隔离升级与行为证明

- 目标数据库角色：新建隔离开发演练库；数据库
  `sc_codex_p82_upgrade_20260806`，精确 DB filter 与独立测试容器配置已确认；
  不含生产数据。
- 从精确基线 SHA `6387c306bbb5a0b42d496f26e4873d7d44ef9688`
  安装 `.81` 后执行当前源码 `.82` 升级，Odoo 正常加载
  `17.0.0.82/post-migration.py` 并退出 0。
- 升级前夹具：目标 action/view/menu 各 3、目标 XMLID 9、同模块 survivor 1；
  六 relation 行数为 `3/4/5/6/7/8`。升级后四类目标均为 0，survivor 仍为
  1，六 relation 行数逐项不变。
- 快照包含三个 orphan model、3 个 menu、3 个 action、3 个 view 的完整可解析
  JSON，以及六 relation 的升级前计数。第二次调用迁移后状态不变且快照字节值不变。
- 真实 Odoo `TransactionCase`：3/3 PASS，覆盖精确删除、其他 XMLID 保留、
  relation 不变、快照、幂等、relation 缺失返回 `None`、active unresolved menu
  失败而 inactive menu 不报错。
- 旧合同编号契约测试
  `TestUserFeedbackBusinessViews.test_contract_list_exposes_single_formal_number`
  真实执行 1/1 PASS；Architecture 2.0 正式树继续只显示一个 `name` 编号，不恢复
  或复制 `legacy_contract_no/legacy_document_no`。

## 4. 验证结果

- `python3 scripts/verify/test_formal_entry_metadata_contract_guard.py`：5/5 PASS，
  含故意删除模型、字段、active-orphan guard 和注入破坏性 SQL 的负向夹具。
- `python3 scripts/verify/formal_entry_metadata_contract_guard.py`：PASS。
- `make verify.formal_product_field_purity`：PASS，legacy alias 违规 0。
- `make verify.formal_surface.transition_field_audit`：PASS。
- `make verify.user_formal_field.module_boundary.audit`：PASS。
- 五个本轮模型的真实 runtime metadata audit：PASS，均为 `ok_visible`。
- `make verify.restricted`：前端 lint、严格类型检查和生产构建 PASS；总门禁因本地
  secondary-company 验收凭证登录 401、profile 成功数 1/2 而预检失败。该环境失败
  不属于本批次代码，未通过写 fixture 或修改产品数据规避；日常环境仍须执行完整正式
  门禁与浏览器验收。
- `git diff --check`、Python 编译和修改 XML 解析：PASS。

## 5. 风险、产物与回滚

- P0/P1 产品风险：隔离行为测试内为 0；日常环境部署前仍由精确 HEAD CI 和配对
  备份保护。
- 快照键：
  `smart_construction_core.17.0.0.82.orphan_handoff_ui_snapshot`。
- 现有日常配对备份：
  `/data/backups/daily_candidate/sc_demo-20260806T012253Z-5c7ebf7e`。
- 回滚：升级前恢复上述数据库/filestore 配对备份，并同步日常运行仓库到升级前精确
  SHA；禁止尝试 Odoo 模块版本降级。迁移未删除任何业务 relation 或附件。
- 下一阶段：精确 HEAD CI/PR 合并后，同步日常 exact bundle，升级 `.82`，复核
  真实 596/619/2826 summary 与 16191/619/7698 fact 行数不变，再执行完整正式
  审计和真实浏览器验收。
