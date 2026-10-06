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

- **批次验收**：本批（P4 验收工具 + 记录）通过；日常运行态用户视角四象限 91/91、55/55，
  detail 8/8，form-profiles/workbench 明暗皆 PASS。同时确认 1 项用户可见产品失败
  （关系打开 `project_id` → 无权访问，根因见 §3.4），未因该失败放宽任何断言。
- **主线集成**：`main = 5ba6398e`（PR #588 已合并），必需检查全绿；本批不改产品代码。
- **版本发布**：未主张。
- **产品交付**：未主张——待 §4 的关系打开投影缺陷收敛后再判断。

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

## 4. 仍未关闭

1. **关系打开投影缺陷（产品修复，需所有者决策定层）**：`project.project` 关系条目声明
   334/199，主体授权中不存在该入口，真实点击落到无权访问。修复位置在 P0 平台契约装配
   （`_build_relation_entry_map` 应消费与 `navigation.route_authority` 同源的授权面，或把
   `can_open` 收敛为 false），属后端模块变更，需按实际变更决定是否升级模块并在日常运行态复验。
   本轮按“只修确认失败、不擅自跨层改产品语义”的口径未动手。
2. **`项目台账` 的 `/f/` ↔ `readonly` profile 观察项**：列表声明 `model_write_authority=true` 并据此
   打开 `/f/project.project/<id>`，但记录契约给出 `effectiveRenderProfile=readonly`。探针按既有策略记为
   not_applicable（绝不当成编辑通过）；是否为产品策略需所有者确认。
3. **测试资产登记**：新脚本尚未进入 `docs/engineering_convergence/test_inventory.csv`
   （由 `scripts/ci/generate_test_inventory.py` 生成，属交付冻结准备步骤）。
4. 本批产品代码 0 变更（仅 P4 验收工具与记录），所以**未主张版本发布与产品交付完成**；
   四层状态见 §2。
