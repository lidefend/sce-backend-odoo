# Demo 隔离租户栈运行手册 v1

> 2026-09-05 · R3「demo 物理隔离迁移」收口产物。演示环境从 dev 栈（`sc_dev_demo` @ 18081）
> 迁移到物理隔离租户栈 `sc-demo-lifecycle`，演示数据、前端产物与 dev 栈完全解耦。

## 1. 栈身份与拓扑

| 项 | 值 |
| --- | --- |
| compose project | `sc-demo-lifecycle`（`COMPOSE_PROJECT_NAME`） |
| 入口 | nginx `http://127.0.0.1:18085` |
| odoo 直连 | `http://127.0.0.1:18086`（dbfilter `^sc_demo$`） |
| 数据库 | `sc_demo`（独立 volume `sc_demo_lifecycle_db_data`） |
| redis / odoo 数据 | `sc_demo_lifecycle_redis_data` / `sc_demo_lifecycle_odoo_data` |
| 前端产物 | `frontend/apps/web/dist-demo`（独立构建，见 §3） |
| env 文件 | `.env.demo`（gitignored，600 权限） |
| 演示用户 | `pm1` / `mat1` / `fin1` / `cost1` / `ct1` 等（密码统一为 `SC_DEMO_USER_PASSWORD`） |

## 2. 隔离不变量（`scripts/demo/tenant_lifecycle.sh` 硬校验）

以下任一不满足，`demo.tenant.reset` / `demo.tenant.verify` 直接拒绝执行（exit 40-46）：

- `ISOLATED_DEMO_TENANT=1` 且 `SC_DEMO_TENANT_LIFECYCLE=1`
- `ODOO_DBFILTER` 必须精确等于 `^sc_demo$`
- `COMPOSE_PROJECT_NAME` 必须匹配 `sc-demo-*`
- `DB_DATA` / `REDIS_DATA` / `ODOO_DATA` 必须匹配 `sc_demo_*`
- `SC_CUSTOMER_ADDONS_ROOT` 必须为空（隔离栈禁止挂客户插件）
- 全局 `SC_DEMO_DATA` scope guard（`scripts/common/demo_data_guard.sh`）

## 3. 前端产物（dist-demo）

demo 栈前端**独立于 dev 栈的 dist-dev**：

- 构建命令：`make demo.frontend.build`（等价于
  `ENV=demo DB_NAME=sc_demo FRONTEND_DIST_DIR=frontend/apps/web/dist-demo bash scripts/dev/frontend_static_build.sh`）
- 产物烧录 `VITE_ODOO_DB=sc_demo`（`VITE_ODOO_DB_LOCKED` 默认 1 → 前端 db 钉死 `sc_demo`，
  与隔离栈 dbfilter 一致）。**不能复用 dist-dev**——其烧录 `sc_dev_demo`，登录会被
  dbfilter 拒绝（AccessError）。
- `.env.demo` 的 `FRONTEND_DIST_DIR=./frontend/apps/web/dist-demo` 驱动 nginx HTML root 挂载。
- 重建产物后需重建 nginx 容器生效（仅 nginx，不动 db/odoo）：

  ```bash
  docker compose --env-file .env.demo up -d --no-deps nginx
  ```

- `runtime-config.js` 机制保留（`window.__SC_RUNTIME_CONFIG__` 可在部署时覆盖
  `odooDb` / `odooDbLocked`），当前 demo 构建未启用覆盖，靠构建期烧录。

## 4. 生命周期操作

```bash
# 栈启动（首次/整体重建）
docker compose --env-file .env.demo up -d

# 演示租户重置（数据全量重播种；CODEX_MODE=gate 必须 export）
export CODEX_MODE=gate
ENV=demo ENV_FILE=.env.demo make demo.tenant.reset

# 演示租户健康校验（模块状态 + demo_xmlids + odoo ready 探测）
ENV=demo ENV_FILE=.env.demo make demo.tenant.verify
# 期望输出：[demo.tenant] PASS db=sc_demo demo_xmlids=406 customer_modules=0 pending=0
```

已验证参考值：`demo_xmlids=406`，customer 模块 0，pending 模块 0。

## 5. 演示体验 E2E 验证（迁移验收口径）

对 `http://127.0.0.1:18085` 的 API 级验收（无需浏览器）：

1. `login` intent（`X-Anonymous-Intent: true`）→ token + session db == `sc_demo`
2. `system.init`（`scene_ready_mode=full`）→ `role_surface.role_label`
   （pm1 → 「项目经理」，cost1 → 「成本管理」，PR #429 生效）
3. `project.dashboard.block.fetch`（`project_id` + `block_key`）→ 运行时块
   `progress` / `risks` / `next_actions` / `boq`：
   - 健康 = `ok=true` + `block_type` 存在 + `visibility.allowed=true` + `error.code` 为空
   - `state` ∈ {`ready`, `empty`}：`empty` 是合法空数据态（块自带
     `empty_message` 文案），不是降级
4. `project.dashboard.enter` intent 被接受（status 200）

已知数据条件：demo 种子无清单导入批次（`project_boq_import_batch` 0 行），boq 预览块
渲染为空态；需要演示导入预览时经清单导入向导产生批次即可。

## 6. 与 dev 栈的关系

| | dev 栈（sc-local-dev） | demo 隔离栈（sc-demo-lifecycle） |
| --- | --- | --- |
| 用途 | 日常开发调试 | 演示 / demo 租户生命周期验证 |
| 数据库 | `sc_dev_demo` | `sc_demo` |
| 前端产物 | `frontend/apps/web/dist-dev` | `frontend/apps/web/dist-demo` |
| 入口 | 18081 | 18085 |

两栈互不影响：dev 重建 dist-dev / 重置 sc_dev_demo 不触碰演示栈任何状态；反之亦然。
