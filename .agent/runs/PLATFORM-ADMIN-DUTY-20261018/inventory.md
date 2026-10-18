# PLATFORM-ADMIN-DUTY-20261018 只读盘点（Phase 1）

- 执行器：`Aquinas`（lane=demo）；调度者 `codex-main-dispatcher-20261018C`
- 授权：`owner-standing-auth-20261018`（active，sha256 `c13e3fa6ab0f1857ed34d746dc2bacc563835668b60b5f0b487f9d1b1b47e83c`）
- 仓库：`/home/lidefend/workspace/sce-backend-odoo`，分支 `codex/daily-platform-demo-20261018`
- 盘点基线 HEAD：`d52ce8a0b81c7ddbc6644bd04d66b56440fe8cc2`（证据内 `00_worktree_state.txt`）
- 运行容器代码：`sce-product-odoo` HEAD `fb1815519`（B 批代码；不含 C 批与本任务的设想改动）
- 写入声明：本轮**只写** `.agent/runs/PLATFORM-ADMIN-DUTY-20261018/`；**未修改任何 addons 产品代码**；C 批写集未触碰。

## 0. 结论

1. 平台库 `sc_platform_control` 的 `admin`：`is_platform_control_admin=true`、`is_tenant_config_admin=true`，但 **`capability_count=0`**、`has_sc_capability_model=false`、`/api/ops/platform-duty` **404**。平台管理员有"权限"，没有"能力面"。
2. Demo 库 `sc_demo` 的 `admin`：`is_platform_control_admin=false`、`is_tenant_config_admin=true`，`capability_count=5`。同名同组，但平台控制权限被"声明实例"阻断——边界目前只有这一处是强制的。
3. Demo 公司名实际为 **`demo演示公司`**，与目标 `Demo演示公司` 相差首字母大小写（`d` → `D`），不是同名字符串。
4. 平台侧确实有 4 项登录后即可使用的只读能力（实测 200/NOT_FOUND 语义正确），但它们**不是声明出来的能力**，只靠 URL 前缀与一个布尔谓词隐式存在。
5. 三类管理员语义中，`is_break_glass_technical_admin` 仍是纯组判定（`base.group_system`），在两库都为真——技术恢复身份没有实例/受众约束。

## 1. 平台库事实（sc_platform_control）

| 事实 | 值 | 证据 |
| --- | --- | --- |
| `admin` login | 200，`token_len=876`，`entry_kind=explicit`，uid=2 | `evidence/07_login_company.txt` |
| `is_platform_control_admin` | `true`（`group_ok=true`、`instance_ok=true`、`audience_ok=true`） | `evidence/06_admin_class_matrix.txt` |
| `is_tenant_config_admin` | `true` | 同上 |
| `platform_instance_scope` | `is_platform_control_instance=true` | 同上 |
| `has_sc_capability_model` | **false** | `evidence/01_platform_capability_shell.txt` |
| `capability_count` | **0**（`capability_keys=[]`、`capability_groups=[]`） | 同上、`evidence/03_live_surface_probe.txt` |
| 已安装模块 | 12 个，仅 `base`/`web`/`smart_core` 等平台底座，无行业/产品模块 | `evidence/01_platform_capability_shell.txt` |
| `system.init` | `capabilities=[]`、`scenes=4`、`navigation.nav` 1 个根节点（platform minimum surface） | `evidence/03`、`evidence/04_navigation_probe.txt` |
| `GET /api/ops/platform-duty` | **404**（声明式能力面端点不存在） | `evidence/05_platform_duty_endpoint.txt` |

### 1.1 平台 admin 登录后即刻可用的能力（实测，只读）

| 动作 | 端点 | 实测 | 证据 |
| --- | --- | --- | --- |
| 租户注册表读取 | `GET /api/ops/tenants` | `200`，`count=1`（`My Company`，`plan_code=default`） | `evidence/08_ops_surface_matrix.txt` |
| 维护访问列表 | `GET /api/ops/maintenance/access` | `200`，返回真实记录（如 `access_id=5`） | 同上 |
| 运维任务状态 | `GET /api/ops/job/status?job_id=1` | `404 NOT_FOUND "job not found"`（端点工作正常，无任务数据） | 同上 |
| 发布运营面 | `POST /api/v1/intent` `release.operator.surface` | `200`，`contract_version=release_operator_surface_v1` | 同上 |
| 平台首页场景 | `workspace.home`（platform minimum surface） | 导航根节点 1 个、默认路由 `/` | `evidence/04_navigation_probe.txt` |

未实测：`POST /api/ops/subscription/set`（写操作，只读盘点不调用）、`/api/ops/maintenance/access/request|approve|reject|revoke|expire`（写操作）。

### 1.2 能力面为空的代码路径

1. `addons/smart_core/core/capability_provider.py:111` `load_capabilities_for_user`：先找扩展钩子 `smart_core_list_capabilities_for_user`（仅行业 addon 提供，平台库未安装）；再取 `env["sc.capability"]`（`:134`），模型不存在时 `:136 return []`。
2. `addons/smart_core/handlers/system_init.py:1737,1745,1769`：能力取回 → 归一化 → 装入 `data.capabilities`，空入空出。
3. `addons/smart_core/delivery/delivery_engine.py:265,269,324`：delivery 能力由产品策略驱动，平台无产品策略 → 空。
4. `addons/smart_core/core/platform_minimum_nav_contract.py:62` + `core/system_init_scene_runtime_surface_builder.py:259`：**导航有兜底（minimum surface），能力没有兜底**。
5. `addons/smart_core/core/system_init_identity_payload.py`：只输出 `is_platform_admin` / `is_tenant_config_admin` 两个布尔，无职责/能力投影。

## 2. Demo 库事实（sc_demo）

| 事实 | 值 | 证据 |
| --- | --- | --- |
| `admin`/`123456` 登录 | 200，`token_len=1620`，`entry_kind=explicit`，uid=2 | `evidence/07_login_company.txt` |
| 公司名（实际） | **`demo演示公司`** | 同上、`evidence/06_admin_class_matrix.txt` |
| 公司名（目标） | `Demo演示公司` | 任务要求 |
| 精确差异 | 仅首字符大小写：`d` vs `D`；其余 5 个字符一致；长度 7 相同 | 同上 |
| `is_platform_control_admin` | `false`（`instance_ok=false`，`group_ok=true`） | `evidence/06_admin_class_matrix.txt` |
| `is_tenant_config_admin` | `true` | 同上 |
| `has_sc_capability_model` | `true` | `evidence/02_demo_capability_shell.txt` |
| `capability_count` | **5**：`project.list.open`、`project.board.open`、`project.task.list`、`workspace.today.focus`、`workspace.project.watch` | 同上 |
| 能力分组 | `project_management(3)`、`others(2)` | 同上 |
| `system.init` | `capabilities=5`、`scenes=93` | `evidence/03_live_surface_probe.txt` |

说明：公司名差异是**数据事实**，来源为 demo 模块种子；本轮只记录，不修改（种子修正属 demo 数据 lane）。

## 3. 三类管理员语义与边界

### 3.1 三类语义

| 类别 | 谓词（`addons/smart_core/security/platform_admin.py`） | 判定 | 平台库 admin | Demo admin |
| --- | --- | --- | --- | --- |
| 平台控制管理员 | `user_is_platform_control_admin` `:179` | 组 + 声明平台实例 + audience | `true` | `false` |
| 租户配置管理员 | `user_is_tenant_config_admin` `:219` | 当前库组校验 | `true` | `true` |
| 技术恢复管理员 | `user_is_break_glass_technical_admin` `:296` | **仅组** `base.group_system` | `true` | `true` |

另有 `user_is_security_admin` `:290`（独立安全组）两库均为 `false`；`user_is_platform_admin` `:232` 已是 `platform_control` 的显式别名，不再表示"组即平台"。

### 3.2 平台 API 应有的三重校验（现状 vs 目标）

| 校验项 | 现状 | 目标 |
| --- | --- | --- |
| 受信实例 | `platform_control_scope.instance_ok` 已强制（`platform_ops_controller.py:75`） | 保持，并在声明载体中显式声明 `trusted_instance=sc_platform_control` |
| token 身份域/受众 | C 批新增 `_current_identity_audience()`（`:105`），未提交 | 平台 API 必须校验 audience=`platform-admin`；租户 token 不得换取平台身份 |
| 当前权限 | 组校验 `CAPABILITY_DISCOVERY_ADMIN_GROUPS` | 组校验保留，但只作为三重条件之一，不单独构成平台身份 |

### 3.3 仍属模块内约定的位置

- `addons/smart_core/security/platform_admin.py:274` `can_discover_platform_capabilities`、`:284` `can_manage_system_configuration`：**仅组判定**。
- `addons/smart_core/handlers/app_shell.py:262,277,251,524,631`：用上述组判定决定 `PLATFORM_ADMIN_SCENE_APP_IDS`（`:57`）与 `ADMIN_APP_DEFS`（`:59`，`release_management`/`company_access`）可见性 → Demo admin 与平台 admin 同组，判据相同。
- `addons/smart_core/delivery/menu_service.py:1742`、`app_config_engine/services/dispatchers/nav_dispatcher.py:115,166,205,556`：同样用组判定控制"发现已安装能力"。
- 硬编码身份：`model/ui_tenant_extension_field.py:192,202,877`（`has_group("base.group_system")`）、`security/tenant_payload_operator.py:306`（`user.id == SUPERUSER_ID`）。

## 4. 与 C 批的重叠（写集状态）

C 批当前未提交文件（`evidence/00_worktree_state.txt` 基线快照）：

```
M addons/smart_core/__manifest__.py
M addons/smart_core/controllers/intent_dispatcher.py
M addons/smart_core/core/context.py
M addons/smart_core/handlers/login.py
M addons/smart_core/models/__init__.py
M addons/smart_core/security/auth.py
M addons/smart_core/security/credential_service.py
M addons/smart_core/security/ir.model.access.csv
M addons/smart_core/security/platform_admin.py
M config/nginx/templates/default.conf.template
?? addons/smart_core/data/sc_platform_namespace_seed.xml
?? addons/smart_core/models/platform_namespace.py
?? addons/smart_core/security/namespace_errors.py
?? addons/smart_core/security/namespace_resolver.py
```

重叠性质：
- **文件级不重叠**：本任务计划写入的 5 个文件均不在上述集合。
- **语义级重叠**：`core/system_init_identity_payload.py` 依赖 `security/platform_admin.py` 的谓词，而 C 正在改该模块 audience 逻辑 → 必须等 C 提交后重读最终版本。
- **邻近冲突**：`controllers/__init__.py` 需加 1 行 import，紧邻 C 改的 `controllers/intent_dispatcher.py`。
- **测试基线**：C 提交前 `test_platform_admin_boundary` 7/15 失败、`test_admin_predicate_split` 2/10 失败，不能作为本任务回归基线。

## 5. 未决与风险

- C 写集未释放；并行 lane 仍在产生脏文件（本轮已观察到 `frontend/apps/web/src/**`、`addons/smart_core/tests/test_auth_token_boundaries.py` 等新脏文件）。
- 容器运行 `sce-product-odoo` 代码，不等于本仓库工作树；新声明文件需显式部署步骤才能实机验证。
- 平台库无 `sc.capability` 模型，声明能力面只能来自代码声明文件，不能依赖 ORM 种子。
- 前端未消费 `platform_duty`；字段落地前前端只能依赖两个布尔。
