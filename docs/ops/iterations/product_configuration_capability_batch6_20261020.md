# 产品配置能力 · Batch 6 执行记录（2026-10-20）

## 0. 身份

- Worktree：`/home/lidefend/workspace/sce-backend-odoo`
- Branch：`feature/product-configuration-capability-20261020`
- Base（main）：`82dbd9134288576ede315370179858c5ba70ce87`
- 批次起点 HEAD：`1d36703b8c07367cb4cd874d3c75b572373e6d56`
- 阶段身份：HEAD + 显式 dirty 范围（日常开发，未冻结）
- 运行环境：`sc-local-dev` / `sc_dev_demo` / `/t/demo` / `127.0.0.1:18081`

## 1. 决策边界

- Formal Product Layer：P1（项目、合同、付款对象语义）+ P0（workspace_home 通用契约投影）+ P0 前端契约消费。
- Layer Target：`smart_construction_core` 的 system.init 事实贡献、`smart_core` 的 `workspace_home` 契约、前端 `WorkspaceHome`。
- Module：`smart_construction_core` / `smart_core` / `smart_construction_scene` / frontend / docs / .agent。
- 目标（唯一）：完成业务全功能账号的真实浏览器验收，并让首屏“我的项目与业务对象”消费真实业务记录。
- 标准 vs 用户特定：项目/合同/付款是建筑行业标准产品语义，归 P1；`my_objects` 的通用形状归 P0。
- Why Here：真实对象查询必须有 ORM 与记录规则权威，不能让前端按菜单、角色名或名称推导。
- Why Not Elsewhere：不在前端过滤 `scene_groups` 冒充项目对象，不在低代码配置层写业务查询。
- Blast Radius：`workspace_home` 新增 `my_objects` 字段与数据源；首屏对象区块改为 `/r/<model>/<id>` 记录路由。既有 `scene_groups`、`group_overview`、`risk`、`today_actions` 消费保持不变。

## 2. 本批实现

1. **P1 真实对象行**：`build_home_object_rows` 从 `project.project`、`construction.contract`、
   `payment.request` 读取可访问记录，输出项目、合同、资金三类行；每行带 `model`、`record_id`
   与 `/r/...` 记录路由，金额由后端按记录币种格式化。
2. **P0 契约投影**：`workspace_home` 新增 `my_objects`、`ds_my_objects`、布局 section 与
   文案声明；只接受带有效 `model`、正数 `record_id`、`/r/` 路由和标题的声明行。
3. **前端消费**：`WorkspaceHome` 的“我的项目与业务对象”改为消费
   `session.workspaceHomeObjectRows`；每行输出 `data-object-kind/model/record-id/route`，
   不再使用 `scene_groups` 作为对象来源。
4. **浏览器验收**：新增 `product_configuration_capability_browser.mjs`，覆盖登录、
   六区块、八张配置卡、参数目录、我的能力、真实对象记录打开、console/pageerror 与失败请求。

## 3. 验证结果

| 层 | 命令 | 状态 | 结果 |
|---|---|---|---|
| L1 | `scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck` | passed | vue-tsc 无错误 |
| L1 | `make verify.product_configuration.capability` | passed | 16 例；audiences=4 cards=8 categories=6 capabilities=25 |
| L1 | `make verify.frontend.product_capability_catalog.unit` | passed | 18 例 |
| L1 | `make verify.frontend.contract_basis.unit` | passed | 15 例；bindings=13 open_defects=0 |
| L1 | `make verify.frontend.contract_basis.enforce` | passed | bindings=13 exemptions=5 logic_sites=3 open_defects=0 |
| L1 | `make verify.frontend.dev.incremental.unit` | passed | 32 例 |
| L3 | `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make local.dev.upgrade MODULE=smart_construction_core` | passed | schema/ACL 应用；`local.dev.demo.authority` PASS |
| L3 | `make verify.product.home_objects.contract` | passed | 2 例；demo 库产出非空记录行 |
| L3 | `make local.dev.entry_identity.verify` | passed | `alias=demo namespace=ns_000000000002 database=sc_dev_demo` |
| L4 | `DB_NAME=sc_dev_demo E2E_LOGIN=wutao E2E_PASSWORD=<existing-demo-credential> make verify.frontend.product_configuration_capability.browser` | passed | 31 断言 |

浏览器断言结果：6 个首屏区块；8 张配置卡；6 类参数目录、13 个参数；我的能力 19 项；
历史访问空态明确；`my_objects` 真实对象行为项目/合同/资金，首条记录成功打开
`/t/demo/r/project.project/125`；console error=0、pageerror=0、失败请求=0。
截图与报告：`artifacts/playwright/product-configuration-capability/`。

## 4. 过程中发现并处理的问题

1. **验收工具路径错误**：脚本引用了不存在的 `scripts/playwright_runtime.mjs`，改为仓库既有
   `scripts/verify/playwright_runtime.mjs`。
2. **凭据口径错误**：`wutao` 在本库的既有验收口令不是 `scdevpass`；使用仓库既有验收口令后
   登录通过。401 属凭据口径，不是产品登录链缺陷。
3. **运行时旧代码**：Odoo 进程启动早于 Batch 2 的后端 intent，导致 `/api/v1/intent` 404；
   通过受管 `local.dev.upgrade` + `local.dev.restart` 加载新代码，未手工拼装容器或数据库。
4. **“我的项目与业务对象”语义缺口**：原实现使用 `scene_groups`，实际渲染“能力矩阵/项目工作”
   等场景入口，不是项目/合同/资金。已按 P1/P0 分层补齐真实记录行，并加入浏览器断言。
5. **演示数据残留**：真实对象中仍出现“成本并发隔离测试项目”测试记录。该问题属于 demo 数据
   迭代线，本批只保证产品消费真实记录，不在 P0/P1 代码中按名称过滤。

## 5. 未执行

- 主线集成：`not_run`（不合并 main）。
- 部署：`not_run`。
- 用户交付验收：`not_run`。
- 演示数据清理/重灌：不属于本批产品线范围，登记为 demo 线后续项。

## 6. 风险与回滚

- 风险：`workspace_home` 新增字段属于向后兼容扩展；前端只消费 `my_objects`，旧字段仍保留。
- 回滚：`git revert` 本批提交即可恢复到 Batch 5 首屏；无部署、无 main 变更、无数据库破坏性写入。
- 运行数据库：本批只执行受管模块升级/重启和定向测试；没有创建、复制或删除数据库、卷或租户。
