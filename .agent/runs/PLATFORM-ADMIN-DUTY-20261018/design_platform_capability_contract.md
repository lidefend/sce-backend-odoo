# 平台首页/能力契约与最小实现清单（Phase 2 设计，未实施）

状态：设计已定稿，等待 C 批释放 `addons/smart_core` 写集后落地。
本文件不描述"概念空壳"：每一项能力都对应一个已存在、已验证的端点或场景。

> 修订（2026-10-18，调度复核）：
> 1. C 批之后 `auth.login` 携带 `db` 参数会被 409 拒绝；实机回读统一走命名空间入口 `/platform-admin/api/v1/intent`，body 不带 `db`。
> 2. 契约投影**不得**输出物理库名；`trusted_instance` 由布尔 + audience + `namespace_id` 等逻辑标识替代，物理库名只在后端校验内部使用。

## A. 契约目标

平台管理员登录后必须拿到**已声明的、非空的**能力集合，且该集合可被后端、前端与测试三方消费：

1. 一个**声明载体**（纯数据，无业务逻辑）：`addons/smart_core/core/platform_duty_contract.py`。
2. 一个**身份投影**：`system.init` 的 `user.platform_duty`（追加字段，不改既有两个布尔）。
3. 一个**只读消费端点**：`GET /api/ops/platform-duty`。
4. 一个**强制边界**：平台控制端点必须同时通过"受信实例 + token 受众 + 当前权限"三重校验。

契约输出禁止项（不得写入前端可见结构）：
- 物理库名（如 `sc_platform_control`）、`db_name`、连接串、主机/端口；
- 任何可用于推断部署拓扑的标识。
允许的逻辑标识：`trusted_instance_verified`（布尔）、`audience`、`namespace_id`（逻辑命名空间标识，缺省 `None`）。

## B. 登录后即可使用的平台能力（已实测）

这 4 项在平台库当前代码下登录即用，契约只需把它们**声明出来并投影**，不需要新写业务逻辑。

| capability key | duty key | 后端来源 | 端点/入口 | 实测 |
| --- | --- | --- | --- | --- |
| `platform.tenant_registry.read` | `platform.tenant_registry` | `res.company` + `sc.entitlement`/`sc.subscription` | `GET /api/ops/tenants` | `200`，`count=1` |
| `platform.maintenance_access.read` | `platform.maintenance_access` | `sc.platform.maintenance.access` | `GET /api/ops/maintenance/access` | `200`，有真实记录 |
| `platform.job_status.read` | `platform.job_status` | `sc.ops.job` | `GET /api/ops/job/status?job_id=` | `404 NOT_FOUND`（端点正常） |
| `platform.release_operator.read` | `platform.release_operator` | release operator read model | `intent: release.operator.surface` | `200`，`release_operator_surface_v1` |
| `platform.workspace.home` | `platform.home` | platform minimum nav contract | 场景 `workspace.home`、默认路由 `/` | 导航根节点 1 个 |

证据：`evidence/08_ops_surface_matrix.txt`、`evidence/04_navigation_probe.txt`。

写类能力（`platform.subscription.write`、`platform.maintenance_access.decide`）端点已存在但本轮**未调用**，契约中标记为 `state="available_unverified"`，不得声称已验收。

注：上表的复现命令使用 `db` 参数，属 C 批之前的采集方式；C 批落地后按第 G 节的命名空间入口复现，不得再带 `db`。

## C. 声明载体结构（`platform_duty_contract.py`）

```python
CONTRACT_VERSION = "1.0.0"
AUDIENCE_PLATFORM_CONTROL = "platform-admin"
AUDIENCE_TENANT = "tenant"
AUDIENCE_NONE = "none"

PLATFORM_DUTIES = (
    {"key": "platform.tenant_registry", "capabilities": ("platform.tenant_registry.read",),
     "route": "/api/ops/tenants", "state": "available"},
    {"key": "platform.maintenance_access", "capabilities": ("platform.maintenance_access.read",),
     "route": "/api/ops/maintenance/access", "state": "available"},
    {"key": "platform.job_status", "capabilities": ("platform.job_status.read",),
     "route": "/api/ops/job/status", "state": "available"},
    {"key": "platform.release_operator", "capabilities": ("platform.release_operator.read",),
     "intent": "release.operator.surface", "state": "available"},
    {"key": "platform.subscription", "capabilities": ("platform.subscription.write",),
     "route": "/api/ops/subscription/set", "state": "available_unverified"},
)

TENANT_DUTIES = (
    {"key": "tenant.config.catalogue", "capabilities": ("tenant.config.catalogue.read",)},
    {"key": "tenant.config.usage", "capabilities": ("tenant.config.usage.read",)},
    {"key": "tenant.config.health", "capabilities": ("tenant.config.health.read",)},
)
```

投影函数（fail-closed，未声明/不匹配一律空集，不抛默认值）。**不输出物理库名**：

```python
def build_platform_duty_surface(
    *,
    is_platform_control_admin: bool,
    is_tenant_config_admin: bool,
    namespace_id: str | None = None,
) -> dict:
    if is_platform_control_admin:
        audience, duties = AUDIENCE_PLATFORM_CONTROL, PLATFORM_DUTIES + TENANT_DUTIES
    elif is_tenant_config_admin:
        audience, duties = AUDIENCE_TENANT, TENANT_DUTIES
    else:
        audience, duties = AUDIENCE_NONE, ()
    return {
        "audience": audience,
        "duty_keys": sorted(d["key"] for d in duties),
        "capabilities": sorted({c for d in duties for c in d["capabilities"]}),
        "contract_version": CONTRACT_VERSION,
        "source": "platform_duty_contract",
        # 逻辑标识，禁止物理库名：受信实例判定只在这里折算成布尔，
        # 库名本身留在后端 platform_control_scope() 内部。
        "trusted_instance_verified": bool(is_platform_control_admin),
        "namespace_id": str(namespace_id) if namespace_id else None,
    }
```

不变量（测试必须覆盖）：
- 平台 admin：`capabilities` **非空**且全部来自 `PLATFORM_DUTIES`/`TENANT_DUTIES` 声明。
- 租户 admin：`capabilities` 不含任何 `platform.*` key。
- 普通用户：`duty_keys=[]`、`capabilities=[]`、`audience="none"`。
- 声明 key 唯一且稳定排序；未声明 key 不得出现在输出。
- 投影 JSON 中不得出现 `sc_platform_control`、`db_name`、`trusted_instance`（物理库名字段）；测试用负向断言锁定。

## D. 三重校验落地

```
platform control API
  ├─ 受信实例：is_declared_platform_control_database(env.cr.dbname)      # 已有 :84
  ├─ token 受众：identity_audience == "platform-admin"                  # C 批 :105 接缝
  └─ 当前权限：组校验（smart_core.group_smart_core_admin）               # 已有 :262
  三者全真 → 授予 platform duty；任一失败 → 403，且不返回任何 duty
```

技术恢复管理员（`base.group_system`）**不自动获得平台 duty**：两库实测均为 `true`，因此只能作为"恢复通道"，必须带审计与实例范围，不得进入平台能力集合。这一条写入契约注释与测试（负向用例）。

物理库名只出现在后端校验 `is_declared_platform_control_database(env.cr.dbname)`（`platform_admin.py:84`）内部；对外只暴露 `trusted_instance_verified` 布尔。

## E. 最小实现清单（C 提交后执行，5 个文件 + 1 个测试）

| # | 文件 | 动作 | 规模 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | `addons/smart_core/core/platform_duty_contract.py` | 新增 | ~90 行 | 纯声明 + `build_platform_duty_surface`；不 import odoo |
| 2 | `addons/smart_core/core/system_init_identity_payload.py` | 修改 | +8 行 | 先算两个布尔与 `namespace_id`，再追加 `platform_duty` 字段；不改其他字段 |
| 3 | `addons/smart_core/controllers/platform_duty_controller.py` | 新增 | ~45 行 | `GET /api/ops/platform-duty`；复用 `_platform_env()` 语义；403/401 分支 |
| 4 | `addons/smart_core/controllers/__init__.py` | 修改 | +1 行 | `from . import platform_duty_controller` |
| 5 | `addons/smart_core/tests/test_platform_admin_duty_contract.py` | 新增 | ~140 行 | 7–8 个用例，见 F |

明确不做（本批）：
- 不改 `security/platform_admin.py`（C 批写集）；不改 `handlers/login.py`、`intent_dispatcher.py`、namespace 文件。
- 不改前端烧录逻辑与产品代码；不引入 namespace 解析；不改 nginx。
- 不写 `sc.capability` 种子（平台库无该模型，声明以代码为准）。

## F. 定向测试清单（非零通过）

1. `test_contract_declares_unique_sorted_keys` — key 唯一、排序稳定、版本非空。
2. `test_platform_admin_surface_is_non_empty` — `is_platform_control_admin=True` → 能力非空且全部已声明。
3. `test_tenant_admin_has_no_platform_capability` — Demo admin → 无 `platform.*`。
4. `test_plain_user_surface_is_empty` — 两项 false → 全空、audience=`none`。
5. `test_undeclared_capability_is_rejected` — 注入未声明 key → 输出不含它（fail-closed）。
6. `test_break_glass_admin_does_not_get_platform_duty` — 技术恢复管理员布尔不参与 duty 判定。
7. `test_identity_payload_projects_platform_duty` — `SystemInitIdentityPayload.build` 输出 `platform_duty`，平台 admin 非空、Demo admin `platform.*` 为空。
8. `test_controller_route_is_declared` — 静态断言 `platform_duty_controller.py` 含 `/api/ops/platform-duty` 路由且调用 control 谓词。
9. `test_surface_exposes_no_physical_database_name` — 序列化结果不含 `sc_platform_control`、`db_name`、`trusted_instance`；只允许 `trusted_instance_verified` 布尔与 `namespace_id` 逻辑标识。

## G. 验收命令（落地后执行）

```
python3 -m py_compile addons/smart_core/core/platform_duty_contract.py \
  addons/smart_core/controllers/platform_duty_controller.py
python3 addons/smart_core/tests/test_platform_admin_duty_contract.py
python3 addons/smart_core/tests/test_platform_admin_boundary.py    # C 提交后应恢复全绿
python3 addons/smart_core/tests/test_admin_predicate_split.py       # C 提交后应恢复全绿
make verify                                                        # 精确 HEAD 上退出码 0
```

实机回读（需部署到 `sce-product-odoo` 挂载并重启平台容器后）：

```
# 命名空间入口登录：body 不带 db（C 批后带 db 会 409）
POST /platform-admin/api/v1/intent  {"intent":"auth.login","params":{"login":"admin","password":"123456"}}
POST /platform-admin/api/v1/intent  {"intent":"system.init","params":{"scene":"web"}}
  → user.platform_duty.capabilities 非空；无 db_name / 无物理库名字段
GET  /api/ops/platform-duty         → 200，返回同一份声明
GET  /api/ops/tenants               → 200（现有能力仍可用）
```

验收时同时断言：
- 带 `db` 的旧写法返回 409（证明命名空间入口已生效）；
- `platform_duty` 结构中不含 `sc_platform_control`、`db_name`、`trusted_instance` 物理字段。
