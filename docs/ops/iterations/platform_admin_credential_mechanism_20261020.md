# 平台管理员凭据机制（平台控制职责）

Run: `.agent/runs/PLATFORM-ADMIN-CREDENTIAL-MECHANISM-20261020/run.json`
日期: 2026-10-20
范围: 日常开发服务器 `platform_control` 职责；不涉及用户模块、生产与前端构建。

## 1. 所有者裁决

- 平台管理员默认口令为简单口令，由所有者后续自行维护。
- 口令错误时重置，不使用复杂的一次性口令。
- 该口令属于平台控制职责的受管凭据，不属于 Demo、租户数据或前端配置。

## 2. 机制

| 对象 | 归属 | 说明 |
| --- | --- | --- |
| 登录名 | `platform_control` duty 的 `admin_credential.login` | 唯一权威声明 |
| 凭据键 | `admin_credential.password_env` | 受管环境键，禁止与自动生成的 duty 密钥重名 |
| 凭据值 | 目标 duty 的 0600 环境文件 | 只存在于受管主机，不提交、不打印、不作为 argv |
| 认证执行 | 目标库原生 `res.users` | 平台库不代验租户密码，也不代发租户身份 |
| 校验/收敛 | `scripts/ops/daily_runtime_platform_admin_credential.py` | `verify` 只读；`ensure` 失配才写；`seed` 只记录所有者提供的值 |

三条硬约束：

1. 只有 `data_purpose=platform_control` 的 duty 可以声明 `admin_credential`，其它 duty 声明即校验失败。
2. 凭据值缺失时渲染 fail-closed，不生成随机口令，也不回落到任何默认账户。
3. 凭据键在 duty 环境整体重渲染时必须保留；`duty_credentials()` 重写文件时不得丢弃所有者维护的键。

## 3. 入口

```bash
# 记录所有者提供的值（从 stdin，非 argv）
SC_PLATFORM_ADMIN_PASSWORD=... make daily.runtime.platform.admin.credential.seed

# 只读校验：登录名唯一、账户启用、声明口令可认证
make daily.runtime.platform.admin.credential.verify

# 受控收敛：仅在声明口令不再认证时写入，并回读确认
SC_CONFIRM_PLATFORM_ADMIN_CREDENTIAL=ENSURE_DECLARED_PLATFORM_ADMIN_CREDENTIAL \
  make daily.runtime.platform.admin.credential.ensure
```

`daily.runtime.database.duty.refresh` 选中 `platform_control` 后自动执行同一收敛逻辑，避免重建后再次手跑 ORM。

口令轮换：先用 `seed` 更新受管文件；`seed` 遇到不同旧值必须带
`SC_CONFIRM_PLATFORM_ADMIN_CREDENTIAL_SEED=REPLACE_DECLARED_PLATFORM_ADMIN_CREDENTIAL`。
声明值是权威：只改 UI 密码而不更新受管文件，下一次收敛会按声明恢复。

## 4. 验证

- `make verify.platform.admin.credential.unit`：声明语法、回执断言、argv 安全、seed 幂等与模式检查。
- `make verify.daily.runtime.database.duty`：声明整体校验与 stack surface 守卫。
- 服务器：`verify` → `ensure` → 再 `verify`，两次都是 `unchanged`/`writes=0`；平台职责刷新后再次 `verify` 仍为 `unchanged`，证明整环境重渲染保留了声明凭据。
- 主线身份：PR #699 源 `4d2d852e…`，必需 CI 全绿，合并 `49e4f0fa…`；日常开发服务器两职责均服务 `49e4f0fa…`。
- `daily.runtime.entry.verify`：66/66 PASS；`path_ns_c_acceptance.py`：23/23 PASS（均绑定 main 精确 SHA）。
- 浏览器：15/15 PASS，覆盖 `/platform-admin` 登录与平台面板可见、平台与 Demo 同名 `admin` 双标签页的库/命名空间/受众隔离、双向 token 重放拒绝、Demo 退出不影响平台会话、会话过期回到 `/platform-admin/login?reason=session_expired` 且重登返回原平台页。

部署顺序按 fail-closed 设计执行：同步代码 → `seed` 声明值 → `verify` → `ensure` → 平台职责 `refresh` → `source_revision.align`。批次内修正了凭据键名没有传入容器导致的 `KeyError`：容器现在通过 `SC_PLATFORM_ADMIN_CREDENTIAL_PASSWORD_KEY` 获知声明键名，值仍只按该键传递，不进入 argv。

## 5. 未覆盖与风险

- 浏览器登录复核需在部署后单独执行，不以单测代替。
- 平台管理员在 UI 内改密后，必须同步更新受管文件，否则刷新会按声明恢复。
- 该机制不改变平台/租户身份边界，也不把平台库变成租户认证代理。
- 仓库内 `scripts/ops/path_ns_c_s4_browser_probe.mjs` 仍把 Demo 口令硬编码给两个入口；本轮浏览器证据使用按入口分别取口令的一次性探针。该脚本应随下一次 ops 批次改为消费 `SC_PATH_NS_TENANT_PASSWORD` / `SC_PATH_NS_PLATFORM_PASSWORD`，并在改动后重跑运行期证据。
