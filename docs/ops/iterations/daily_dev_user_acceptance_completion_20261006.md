# Daily Dev User-Perspective Acceptance Completion（日常开发服务器用户视角完整验收，2026-10-06）

Run: `.agent/runs/DAILY-DEV-USER-ACCEPTANCE-COMPLETION/run.json`
Branch: `codex/daily-dev-user-acceptance-completion-20261006`
Baseline: `5ba6398e672da8b46807da3538187be980772b6d` (`main`，PR #588 后)
Runtime repository: `sc-root:/opt/projects/repos/sce-product-odoo`
(`ENV=dev`, `ENV_FILE=.env.dev`, `DB_NAME=sc_demo`)
Owner acceptance entry: `http://1.95.85.92:18081/`（自定义前端），口令 `wutao/123456`

## 1. 目标与责任层

- **Formal Product Layer**：P4（ops delivery / 运行态验收）。
- **Layer Target**：日常开发运行态（sc-root）主线提升 + 用户视角产品交付验收。
- **Module**：`.agent`、`docs/ops/iterations`（本批产品代码预期为 0 变更）。
- **Standard vs User-Specific**：运维交付与验收工具，非行业/客户语义。
- **Why Here**：把权威 `main` 精确 SHA 提升到日常运行态并以真实用户无死角验证，属交付验收层。
- **Why Not Elsewhere**：不改 P0-P3 产品语义，不放宽 ACL/字段权限/断言，不改生产租户。
- **Blast Radius**：sc-root 日常运行仓、其前端静态产物与 dev compose profile、`sc_demo` 只读验收面。

## 2. 状态（四层分列）

- **批次验收**：通过。日常运行态用户视角四象限 91/91、55/55，detail 8/8，
  form-profiles/workbench 明暗皆 PASS；并修复 §3.4 确认的关系打开投影缺陷（P0 `smart_core`，
  提交 `827bffed`），定向 ORM `12 tests / 0 failed`、运行态关系往返复验 `status=pass`
  （`denied_requests=0`、`console_errors=0`）。全程未放宽任何断言或 ACL。
- **主线集成**：完成。PR #589（squash）已合并，`main = dd75f83c`；四个必需检查
  （`public_guard` / `merge_policy_gate` / `professional_quality_gate` / `frontend_release_gate`）
  在精确 HEAD `0794f203` 上全部 success，合并门禁复用同 HEAD 的 `ci.local.quick` receipt
  （`REUSE`，未重复执行套件）。随后 PR #591（squash）以精确 HEAD `6b5230c0` 落地本收口记录，
  `main = b0f0dba5`（该 PR 同时把 run 绑定改到了短命分支，见 §4.3，本批清除）。详见 §3.9、§3.10。
- **版本发布**：未主张。
- **产品交付**：未主张——待所有者对 §4.1 的单项产品策略观察项判断。

## 3. 执行记录

### 3.1 身份与环境（本轮每次运行前重新回读）

- 受管运行态：`http://1.95.85.92:18081/`，`/api/runtime-version` 回读
  `git_sha=5ba6398e672da8b46807da3538187be980772b6d`、`database=sc_demo`、`environment=dev`、
  `product_version=1.0.0-rc.20`；`frontend_build_sha256=""`，身份以 served SHA 绑定。
- 口令：`wutao/123456`（既有隔离验收 fixture 口令，本轮未新增或轮换任何口令）。
- 所有日常运行态验收均走受管入口 `make verify.daily_dev.list_surface.readonly.browser`
  （`SC_ACCEPTANCE_PROFILE=daily`、`target_mode=external`、`operation=readonly`），
  必需显式提供 `ACCEPTANCE_TARGET_SHA`/`ACCEPTANCE_BASE_URL`/`DB_NAME`/`ACCEPTANCE_LOGIN`/
  `ACCEPTANCE_PASSWORD`/`SC_ACCEPTANCE_RUN_ID`/`SC_ACCEPTANCE_DAILY_CREDENTIAL_CONFIRMATION`
  （弱口令确认信封，TTL ≤ 10 分钟，键集固定）。未手拼 compose/端口/凭据，未绕过 DENY。

### 3.2 用户视角四象限视觉覆盖（复用既有干净证据）

串行独占运行（该脚本不可并行：并行会导致登录 500、chromium 崩溃与产物互相覆盖）。
产物：`.runtime/final-acceptance/user-perspective/`。

| 象限 | 文件 | 动作 | 表单 | console/http/request 失败 | 溢出 |
| --- | --- | --- | --- | --- | --- |
| 1440 light | `uavc-1440-light.json` | 91/91 | 55/55 | 0/0/0 | 0 |
| 390 light | `uavc-390-light.json` | 91/91 | 55/55 | 0/0/0 | 0 |
| 1440 dark | `uavc-1440-dark.json` | 91/91 | 55/55 | 0/0/0 | 0 |
| 390 dark | `uavc-390-dark.json` | 91/91 | 55/55 | 0/0/0 | 0 |

- `totalDiscovered=91`（上一轮 90，发布面/入口 +1）。
- 污染证据与纠正：`uavc-1440-dark.netflap.json`、`uavc-390-dark.netflap.json` 为
  `net::ERR_NETWORK_CHANGED` 传输级抖动；`uavc-390-light.frozen-082708.json` 为并发污染。
  三者均非产品缺陷，已按串行重跑覆盖为上面的干净基线，污染副本保留备查。

### 3.3 受管详情车道（复用既有证据）

入口：`make verify.daily_dev.list_surface.readonly.browser`，
`LIST_SURFACE_DAILY_OBSERVATION_SCOPE=detail-only`，绑定 5ba6398e。
产物：`.runtime/final-acceptance/detail-closeout-5ba6398e/`（`light.json`/`dark.json`/实拍）。

- `passed=true`，`record_checks` 8/8（1440+390 各：`declared_entry_route`/`exact_record_contract`/
  `declared_renderer`/`return_to_source` 全 true），console/page/failed/denied 全 0，
  `servedSha=5ba6398e`，`db=sc_demo`。

### 3.4 关系“点击打开 → 返回原记录 → 标签和动作恢复”（本轮新增实测）

新增声明驱动探针 `scripts/verify/record_relation_roundtrip_acceptance.js`：捕获页面自身消费的
`ui.contract.v2` 契约，只对契约声明 `can_read=true` 的关系字段控件做真实点击，再按前端自身发出的
`return_*` 契约校验，回退后断言路径/标题/状态栏/标签/记录动作 before==after，并要求全程无 403、无 console 错误。
产物：`.runtime/final-acceptance/relation-roundtrip/20261006T023437/summary.json`
（源记录 `construction.contract.income/2331`，action 578 / menu 904，14 个声明关系条目）。

- **成功往返（真实点击，不是 handler 诊断）**：`partner_id` → `/f/res.partner/8754?menu_id=598&action_id=786`
  （契约声明 786/598，主体路由授权内）；`goBack` 后 `path/title/statusbar/tabs/actions` 全部恢复，
  `denied_requests=0`、`console_errors=0`。`handler_id`、`tax_id` 同样成功打开。
- **确认失败**：`project_id`（展示“马鞍村库房”）点击后落到
  `/access-denied?reason=NAVIGATION_AUTHORITY_DENIED`。根因已钉住：
  - 契约声明：`project.project` 关系条目 `action_id=334, menu_id=199, can_read=true, can_open=true,
    entry_intent=open, model_write_authority=true`（`pageInfo.model=construction.contract.income` 的
    `layoutContract...fieldDescriptor.relation_entry`）。生产者为
    `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py::_build_relation_entry_map`
    （按 `ir.ui.menu._visible_menu_ids()` 取该模型第一个可见菜单/动作）。
  - 主体授权：`system.init` → `navigation.route_authority` 中 `project.project` 只有
    696/376、1176/969、1178/970、506/379、575/474；**没有 334/199**（`denied_actions` 里也没有）。
  - 前端：`resolveRecordOpenTarget` 因 `model_write_authority=true` 生成 `/f/...`；路由守卫对
    `name='model-form'` 不做 `validateRelationReadRoute`，`findRouteAuthority` 未命中即
    `access-denied`。即 `/r/` 关系读凭证通道对本例不适用，而声明的 `/f/` 授权又不存在。
  - 结论：这是**投影缺陷**（声明了一个主体未被授权的打开入口），不是合法权限边界。若反过来认定
    该条目本就不可打开，也应把 `can_open` 声明收敛为 false，二者必须一致。

### 3.5 创建/编辑与工作台最小证据差额（本轮补齐，明暗各一次）

同一受管入口，`LIST_SURFACE_DAILY_OBSERVATION_SCOPE=workbench-only|form-profiles`：

| 运行 | 产物 | 结果 |
| --- | --- | --- |
| workbench-only light | `.runtime/final-acceptance/workbench-5ba6398e/light.report.json` | PASS（声明主题 + 声明默认落地 `/s/projects.list`，runtime_errors=0） |
| workbench-only dark | `.runtime/final-acceptance/workbench-5ba6398e/dark.report.json` | PASS（同上，dark 解析正确） |
| form-profiles light | `.runtime/final-acceptance/form-profiles-5ba6398e/light.report.json` | PASS（`declared_edit_entry` 1440/390 通过，runtime_errors=0） |
| form-profiles dark | `.runtime/final-acceptance/form-profiles-5ba6398e/dark.report.json` | PASS（同上） |

- 口径说明：`summary.records` 把 `not_applicable` 计为 passed（12/12），实际生效断言只有
  `declared_edit_entry`；`create_*` 为 not_applicable（该列表未声明创建权限），`edit_contract`/
  `edit_renderer` 为 not_applicable（记录契约声明 `readonly` 而非可编辑 profile）。因此这两个 lane
  只能证明“声明被忠实消费”，不能作为创建/编辑写入能力的证明。

### 3.6 本轮工具层修复（只失效依赖它的结果）

`scripts/verify/frontend_list_surface_structure_browser.mjs`：

1. TDZ 缺陷：失败分支引用定义在 `try` 之后的 `LIST_MATRIX_SKIPPED`，掩盖真实错误。
   提升到模块作用域，并让 catch 输出 stderr stack。
2. 等待预算缺陷：daily 外部目标只用固定 8s 等 toolbar，导致
   `no populated runtime list was discovered`；改为 45s（显式路由）/30s（daily）。
3. 同上分支的 `detailOnly` 残留清理。

`scripts/verify/test_frontend_list_surface_search_contract.py`：把“字符串出现即通过”的断言更新为
模块作用域声明，并新增“声明必须先于使用”的顺序断言（锁住 TDZ 修复本身，而不是锁住某段文本）。

新增 `scripts/verify/record_relation_roundtrip_acceptance.js`（声明消费 + 真实行为）。

层内验证：`make ci.local.iteration` PASS（L1，scope 已含 `scripts/verify/`）；
`make verify.frontend.list_surface_search_contract.unit` 22/22 OK + `acceptance_contract_receipt_test` PASS。

### 3.7 其他观察项（未改代码）

- `project.project/581` 的 `user_id` 英文标签 `Project Manager` 来自后端契约本身
  （`field_labels.user_id`、`formStructureContract...fieldLabels.user_id`），前端忠实渲染；
  相邻字段 `manager_id='项目负责人'` 为中文。记为 P0/P1 契约本地化观察项。
- `return_url` 被三重 URL 编码（`encodeURIComponent` 基础上再被路由序列化两次）。当前没有任何前端
  消费者读取 `return_url`（关系读凭证只消费 `return_model/field/record_id/action_id/menu_id`），
  因此不影响本轮结论，记为契约卫生观察项。
- `config/frontend/acceptance_environments_v1.json` 的 `navigation_policy.max_actions=90`，
  而当前发布面实际为 91；本轮 lane 未因该值失败，但口径应在下一次发布面对齐时一并复核。

### 3.8 关系打开投影缺陷修复（P0 平台契约装配，本轮新增）

**责任层**：P0 平台契约投影缺陷（`smart_core` 声明了一个主体未被授权的打开入口），
不是 P1 行业语义，也不是合法权限边界。

- **根因**：`page_assembler._build_relation_entry_map` 用 `ir.ui.menu._visible_menu_ids()` 取关系模型
  第一个可见菜单/动作，与发布导航授权面 `navigation.route_authority` **不同源**；`project.project`
  被声明 `334/199`，而主体授权面中不存在该对 → 前端按 `model_write_authority=true` 生成 `/f/`，
  路由守卫 `findRouteAuthority` 未命中 → `/access-denied?reason=NAVIGATION_AUTHORITY_DENIED`。
- **修复**（提交 `827bffed484dcc1af4db05ec7b0b10a5189e9938`）：
  1. `addons/smart_core/delivery/runtime_route_authority.py` 新增 `iter_published_pairs(authority)`
     （按 bucket 顺序 yield 发布对），`published_pairs` 改为其集合。
  2. `page_assembler._build_relation_entry_map` 改为消费 `build_runtime_route_authority(self.env)`
     **同一授权面**：原生候选对若已在授权面内则保留；否则回退到该模型在授权面内的首个发布入口；
     若该模型在授权面内无任何入口则 **fail-closed**：不声明打开入口
     （`action_id=null`、`menu_id=null`、`can_open=false`、`reason_code="RELATION_ENTRY_NOT_PUBLISHED"`）。
     不覆盖 ACL / 字段权限 / 合法隐藏规则，**无模型特判**。
  3. `_build_relation_entry_for_field` 的 `can_open` 由硬编码 `True` 改为消费 base 声明，
     使 fail-closed 结果真正生效。
- **锁定（层内，非零）**：新增受管 ORM 车道 `make verify.smart_core.relation_entry_publication.orm`
  → `0 failed, 0 error(s) of 12 tests`（日志
  `.runtime/agent-runs/DAILY-DEV-USER-ACCEPTANCE-COMPLETION/relation_entry_publication_orm.log`）；
  `make ci.local.iteration` PASS；`verify.frontend.list_surface_search_contract.unit` 22/22 OK。
- **运行态复验（只跑受影响的定向车道，不重跑矩阵）**：受管入口
  `daily.runtime.candidate.bundle_sync` + `daily.runtime.source_revision.align`（仅 restart，
  本变更无新字段/XML/迁移，Python 方法体变更由容器重启加载）。回读 `/api/runtime-version`
  `git_sha=827bffed484dcc1af4db05ec7b0b10a5189e9938`；部署盘
  `sc-root:/opt/projects/repos/sce-product-odoo` HEAD 同 SHA 且含新符号。
  探针产物 `.runtime/final-acceptance/relation-roundtrip-postfix/20261006T030040/summary.json`：
  - `status=pass`，`declared_entry_count=14`，`denied_requests=0`，`console_errors=0`。
  - `project_id` 现声明**已发布对** `action_id=696/menu_id=376`（原 334/199 未发布→按规则回退），
    真实点击落 `/f/project.project/1245`；回退后 path/title/statusbar/tabs/actions 全部恢复、
    `error_free=true`。
  - `partner_id`(`786/598`)、`handler_id`(`723/438`)、`tax_id`(无菜单对) 仍 `opened`。
- **未放宽断言**：修复只收敛「声明 ↔ 授权面」一致，不新增任何放行；原有失败位置的结论由
  「确认产品缺陷」更新为「已修复并复验」，其余断言不变。

### 3.9 主线合入与日常运行态归一化到 main（本轮新增）

- **PR 合入**：`lidefend/sce-backend-odoo#589`，squash 合入，`main = dd75f83c04e6c47066037755fbbcf0396bd086fc`
  （2026-10-06T03:54:56Z）。四个必需检查在精确 HEAD `0794f2030459cff16d3d69d8550129388e57f2f6` 上全部 success；
  `pr.merge.local_quick_gate` 命中同 HEAD 的 `ci.local.quick` receipt（`REUSE`），未重复跑套件。
  本地 quick 在本轮实际抓到过一项远端未覆盖的阻断（`product.release.version` 认为 `run.json` 重复了产品版本字面量），
  该缺陷已修（提交 `0794f203`）——本地守卫与远端门禁不是冗余关系。
- **运行态归一化**：此前日常运行态处于**分离候选态** `827bffed`（PR 分支头，squash 后不是 main 的祖先）。
  受管入口 `daily.runtime.main.bundle_sync` 走「分离候选 → main」归一化路径
  （`normalized_from_candidate=true`，`old_sha=5ba6398e`、`source_sha=dd75f83c`），随后
  `daily.runtime.source_revision.align` 声明 `SC_SOURCE_REVISION` 并重启；`/api/runtime-version`
  回读 `git_sha=dd75f83c043…`。报告：`.runtime/final-acceptance/daily-deployed/bundle-sync.json`。
- **main 上复验（只跑受影响的定向车道）**：
  `.runtime/final-acceptance/relation-roundtrip-main-dd75f83c/20261006T035750/summary.json`，
  `status=pass`、`declared_entry_count=14`、四个关系条目全部 `opened`、往返
  `path/title/statusbar/tabs/actions` 全恢复、`denied_requests=0`、`console_errors=0`。
- **口径注记**：本主线同步需要 `expected_old_sha` 为远端 `main` 引用而非远端 HEAD；
  若未来把 squash 合入后的分支头直接当作 `expected_old_sha`，预检会以「不是祖先」阻断——
  这是本入口的既有前置条件，已在此记录以免重复排查。

### 3.10 run 索引绑定清理（P4 工具层，本批新增）

- **事实**：PR #591 落地收口记录时，把 `.agent/active-runs.json` 的绑定从
  `codex/daily-dev-user-acceptance-completion-20261006` 改成
  `codex/daily-dev-user-acceptance-closeout-20261006`，随后该分支被 `branch.cleanup` 退役，
  `main` 因此残留一条指向**已删除分支**的悬空绑定（`run.json` 的 `branch` 同值、`status=active`）。
- **影响**：在 `main` 上 `agent_run_context` 解析为 `unregistered`（exit 2），
  `make ci.local.iteration` 无法在 `main` 上得到 `resolved`；绑定还会让未来同名的重开分支静默继承本 run。
- **修复**：本批把 `.agent/active-runs.json` 收敛为 `{"schema_version": 1, "branches": {}}`，
  并把 `.agent/runs/DAILY-DEV-USER-ACCEPTANCE-COMPLETION/run.json` 标记 `status=completed`。
  依据既有先例（`ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT`、PR #586 `48441a3b` 同为 `{}`），
  已退役分支不得在 `main` 留下映射；`main` 上 `ci.local.iteration` 报 `unregistered` 是该车道既有先例。
- **不走捷径**：未改 `agent_run_context` 的解析规则，未放宽 `ci.local.iteration` 的 `resolved` 要求，
  仅让索引回到与「分支已退役」一致的真实状态。
- **顺带修复的记录层缺陷**：`.agent/goals/DAILY-DEV-USER-ACCEPTANCE-COMPLETION.yaml` 第 78 行缩进错误
  （`  - no_relaxation_of_relation_open_authority_or_field_permission` 少两个空格），使整个 goal 记录
  **无法被任何 YAML 解析器读取**（`yaml.safe_load` 直接 ParserError）。已按同级 key 对齐修正，
  并同步 goal 的 `next_exact_step`；`goal.status` 保持 `active`（产品交付仍待所有者判断），
  与 `run.status=completed` 的组合沿用 `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT` 先例。

## 4. 仍未关闭

1. **`项目台账` 的 `/f/` ↔ `readonly` profile 观察项**：列表声明 `model_write_authority=true` 并据此
   打开 `/f/project.project/<id>`，但记录契约给出 `effectiveRenderProfile=readonly`。探针按既有策略记为
   not_applicable（绝不当成编辑通过）；是否为产品策略需所有者确认。这是当前唯一的未决产品策略项。
   **已于 2026-10-09 收口（本项不再是未决）**：定性为「模型级写权限（决定 `/f/` 入口）与记录/状态级
   有效可编辑性」两个不同权威，记录被状态/审批锁住时 `/f/` + `readonly` 是设计内 fail-closed 收窄，非契约矛盾；
   且 served `bfb38367` 上已不可复现（同一记录解析为 `edit`、台账整表无 readonly 行）。证据与判据见
   `docs/ops/iterations/hierarchical_worksheet_usable_ready_20261008.md` §14。
2. 已关闭项：
   - 关系打开投影缺陷：已修复、已合入 main（PR #589 → `dd75f83c`）、已在大运行态复验（§3.8、§3.9）。
   - 测试资产登记：`scripts/verify/record_relation_roundtrip_acceptance.js` 已由
     `scripts/ci/generate_test_inventory.py` 登记为 `T-ASSET-942`（总资产 1462 → 1463）。
3. 已关闭的工具层项：`main` 悬空 run 绑定（PR #591 把绑定指向随后退役的
   `codex/daily-dev-user-acceptance-closeout-20261006`）。本批把 `.agent/active-runs.json` 收敛为
   空索引，并把本 run 标记 `status=completed`；详见 §3.10。此后 `main` 上
   `ci.local.iteration` 报 `unregistered`，与既有先例一致，不是新的缺陷。
4. 四层状态见 §2：批次验收 = 通过，主线集成 = 完成，版本发布 = 未主张，产品交付 = 待所有者判断。

### 3.11 契约 schema 摘要漂移暴露与修复，daily 候选全车道复验（served = e384b832，本轮新增）

- **暴露路径（谁最先看见）**：daily 只读探针 `verify.daily_dev.acceptance.readonly.probe`。
  本轮补齐受管夹具（`daily.dev.acceptance_fixture.ensure` PASS，finance uid 210）后，
  contract 段首次越过口令闸门，随即报 **`contract_schema_digest_not_bound`**：
  运行时契约 `meta.lifecycle.definition.schemaSha256` 与 schema 资产字节不一致。
- **根因**：`d78cb4be`（本分支 P0 声明面提交）改写了契约 schema 资产（+61 行 `formStructureContract.surfaces`）
  但未重派生 `UNIFIED_PAGE_SCHEMA_SHA256`（`204b8f6c…` ← 应为 `28be508e…`）。属**本分支引入**，
  main 上一致。守卫只在 `ci.local.quick`（交付冻结时跑）而不在开发内环，故此前本地未暴露。
- **修复**：走权威派生入口 `make contract.schema.declaration.sync`（不手改常量、不放宽断言），
  并同步 4 个 canonical 示例的溯源摘要；提交 `e384b832`。详见
  `docs/ops/iterations/project_ledger_entry_unification_20261006.md`「契约 schema 摘要漂移」节。
- **daily 复验（受管入口，served=e384b832）**：
  - `daily.runtime.candidate.bundle_sync`（old `ed783035` → `e384b832`）+
    `daily.runtime.source_revision.align`（仅 restart，无 XML/字段/迁移）；`/api/runtime-version`
    回读 `git_sha=e384b832…`、`database=sc_demo`；前端产物按「无前端路径变更」复用 `ed783035` 的 `dist-dev`。
  - `daily.dev.acceptance_contract.resolve`：`expected_sha=e384b832`，唯一目标
    `smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a`
    （`payment.request/36156`、action 780、menu 550）。
  - `verify.daily_dev.acceptance.readonly.probe` **overall PASS**（四段全 PASS，contract 11/11，
    `contract_schema_digest_bound=true`；login nodes=111/actions=89/leaves=89，`forbidden=[]`、`required_miss=[]`）。
  - 详情车道 `detail-only` 1440/390：light 8/8、dark 8/8，`runtime_errors=0`。
  - 关系往返真实点击一次：`status=pass`，4 个声明条目全部 `opened`，往返全恢复，`denied_requests=0`、`console_errors=0`。
  - 创建/编辑 + 工作台：`form-profiles` 12/12 × light/dark；`workbench-only`
    （declared-theme / declared-default-landing / router-workspace-home，1440+390）× light/dark，`runtime_errors=0`。
- **复用口径**：列表范围（108/108、负例 5/5、运行时错误 0）未重跑，输入未变；
  前端车道均在 served `e384b832` 上实测。

#### §4 补充（本轮）
- 新增已关闭项：**契约 schema 摘要漂移**（本分支引入，`e384b832` 修复并在 daily served `e384b832` 全车道复验）。
- 新增证据项：daily 只读探针 contract 段在补齐夹具后首次真正跑通，11/11 检查在前端+后端同候选身份下成立。
- 仍开放项不变：**`项目台账` `/f/` ↔ `readonly` 观察项**（唯一的未决产品策略项，需所有者确认）。
