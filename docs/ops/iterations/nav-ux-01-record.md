# NAV-UX-01 场景化中心导航交付收口

## 目的

把场景化导航从“6 域 hand JSON 投影 + 新旧导航二选一”收敛为“原生菜单树中心 + 数据库维护业务场景 + 统一前端消费”的一条交付链，并恢复搜索、展开记忆、当前位置定位与权威空态/错误态。

## 批次范围

- 后端：`sc.product.scenario` / `sc.product.scenario.entry` 模型、视图、权限、种子导入、policy 同步 create-only。
- 投影：`scenario_surface_projection.project_authorized_nav_with_env`，中心取原生 `ir.ui.menu` 父级链，场景取数据库模型。
- 前端：`AppShell` 单一场景导航消费，`ProductScenarioNavigation` 中心→场景→入口 + 搜索/展开/定位，`session` 展开持久化。

## 验证状态

- 静态：py_compile / manifest / XML / CSV / vue-tsc / eslint 通过。
- 定向：`verify.nav01.native_authority.unit`、`verify.frontend.workspace_scenario_lifecycle.unit` 通过。
- 运行时：隔离候选环境 `sc_frontend_acceptance_candidate` 完成。`list_surface_structure` PASS（rows=18），`relation_roundtrip` PASS（13 entries，error_free）。PR #810 Draft。

## 执行复盘（事故记录，避免再犯）

### 根因：偏离既定受管车道

仓库本来就有现成的 `candidate` 验收车道：`SC_ACCEPTANCE_RUNTIME_PROFILE=candidate` → `sc-fe-candidate-770` 环境 + `sc_frontend_acceptance_candidate` 库，并已接好 fixture / contract_receipt / 两个浏览器套件 / evolution.record / preflight / pr.push / pr.create。我没有走这条车道，而是自建 `sc-navux-verify` 环境和 `navux_branch` profile，再把它逐处塞进七八个硬编码 profile 守卫，导致每补一处就换 SHA、重生成制品、重建容器，形成死循环。

### 次因一：没先取真实异常就猜

`record_relation_roundtrip_acceptance.js` 的顶层 `catch` 只打印 `locations`，吞掉了 message/code/cause。我连猜了好几层（fixture 作用域、host 预览、production build、tool matrix），直到补了脱敏诊断才拿到确切原因 `relation-roundtrip is forbidden for profile navux_branch`。

### 次因二：SHA 自引用循环

每个 profile/脚本修复都是 tracked 文件 → 必须提交 → HEAD 变 → 制品按新 SHA 重生成 → 后端重建 → 套件按新 SHA 重跑。书签类（`.agent/run.json`）改动也单独提交，再次触发该循环。正确做法是把书签类改动并入产品提交，或在动手前一次性把 run 的 scope/blockers 更新到位。

### 次因三：临时环境踩了标准预览的宿主进程假设

`standard-*` 操作要求宿主级 `release_static_server.mjs` 预览（含 `/proc/<pid>/environ` 身份校验），而我用 docker nginx 提供前端，两者不兼容，白跑了好几轮。

### 正确的既定顺序（下次直接照做）

1. `make db.frontend.acceptance.ensure SC_ACCEPTANCE_RUNTIME_PROFILE=candidate`
2. `make acceptance.frontend.fixture SC_ACCEPTANCE_RUNTIME_PROFILE=candidate SC_ACCEPTANCE_FIXTURE_SCOPE=candidate SC_ENVIRONMENT=acceptance SC_ALLOW_DEMO_DATA=1 SC_ACCEPTANCE_FIXTURE_PASSWORD=...`
3. `make acceptance.runtime.contract_receipt SC_ACCEPTANCE_RUNTIME_PROFILE=candidate`
4. `make verify.frontend.list_surface_structure.browser SC_ACCEPTANCE_RUNTIME_PROFILE=candidate`
5. `make verify.frontend.relation_roundtrip.browser SC_ACCEPTANCE_RUNTIME_PROFILE=candidate SC_ACCEPTANCE_RELATION_LOGIN=fixture_role_config_admin`
6. `make acceptance.evolution.record ACCEPTANCE_EVOLUTION_STAGE=merge ACCEPTANCE_EVOLUTION_SUITES="list_surface_structure=<路径> relation_roundtrip=<路径>"`
7. `make pr.publish.preflight EXPECTED_HEAD=<完整 SHA>`
8. `make pr.push EXPECTED_HEAD=<完整 SHA>` → `make pr.create PR_DRAFT=1 ...`

### 铁律

- 优先复用已有 profile 和受管 make 入口，不新造平行环境/平行 profile。
- 遇到被吞掉的异常，先补脱敏诊断拿到真实 message，再修，不猜。
- 书签/台账改动与产品提交合并，避免单独提交触发 SHA 循环。
- 前端浏览器验收必须用宿主标准预览（`frontend_standard_preview.py build/up` + `release_static_server.mjs`），不用 docker nginx 顶替。
