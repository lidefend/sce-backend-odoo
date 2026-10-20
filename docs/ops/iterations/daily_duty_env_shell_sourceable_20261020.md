# 日常职责环境文件可被 shell source

状态：已合并并在日常开发服务器部署验证通过。

任务：`DAILY-DUTY-ENV-SHELL-SOURCEABLE-20261020`

基线：`fix/daily-duty-env-shell-sourceable-20261020` /
`6dd15103ae8f0f892f7e89d915039cff3dd5b997`

## 判定

发布面包装入口 `daily.runtime.published_face.converge` 在
`6dd15103` 上失败，根因不在发布面本身，而在**同一个职责环境文件被两个
解析器读取**：

- Docker Compose 以 `--env-file` 读取 `daily_runtime_duty_stack.env`；
- 治理入口 `scripts/common/check_env.sh` 用 `set -a; source` 读取同一个渲染产物。

`SC_DECLARED_NAMESPACE_ALIASES` 渲染值是正则 `demo|platform`。不加引号时，
Compose 得到正确字符串，但 shell 把 `|` 当成管道，在 source 阶段执行
`platform`，升级因 `platform: command not found` 中止。手工直接执行
`release.daily_product_navigation.converge` 不经过 `source`，所以此前手工
收敛通过而包装入口失败，形成了“包装入口坏了、内层其实能跑”的错觉。

属于 P4 运维交付机制缺陷，不涉及平台或租户身份语义、品牌、业务数据或前端构建。

本批同时修复第二个可诊断性缺陷：包装入口失败时只输出 reason 码和
`module_upgrade_tail`，内层 `converge_tail` 未透出，导致真实错误需要回到主机
手工重放才能看到。

## 改动清单

- `config/ops/daily_runtime_duty_stack.env`
  - `SC_DECLARED_NAMESPACE_ALIASES` 模板改为双引号包裹，Compose 取值不变，
    shell source 后仍得到完整正则。
- `scripts/verify/daily_runtime_entry_guard.py`
  - 同步模板期望行。
- `scripts/verify/nginx_proxy_db_authority_guard.py`
  - 同步模板期望行；正则本身与 nginx 消费方式不变。
- `scripts/ops/test_daily_runtime_database_duty.py`
  - 新增回归测试：渲染环境文件必须可被 bash `source`，且
    `SC_DECLARED_NAMESPACE_ALIASES` 读回完整 `demo|platform`。
- `scripts/ops/daily_runtime_published_face_converge.py`
  - 失败信息附带内层 `converge_tail`（截断 1500 字符），不再只给 reason 码。
- `docs/ops/iterations/daily_duty_env_shell_sourceable_20261020.md`
  - 本记录。

## 验证

| 命令 | 结果 |
|---|---|
| `python3 -m unittest scripts.ops.test_daily_runtime_database_duty scripts.ops.test_daily_runtime_published_face_converge` | 193 tests PASS |
| `make verify.daily.runtime.database.duty` | 30 + 163 tests PASS |
| `python3 scripts/verify/daily_runtime_entry_guard.py` | PASS |
| `python3 scripts/verify/nginx_proxy_db_authority_guard.py` | PASS |

## 运行态验证（合并后 main）

部署身份 `b9a060c622c3943dafcb0f7d332fd9e87b22b781`，两职责均回读该 SHA：

- demo：`sc_demo` / `ns_000000000002`，受众 `tenant`。
- platform_control：`sc_platform_control` / `ns_000000000001`，受众 `platform-admin`。

| 入口 | 结果 |
|---|---|
| `make daily.runtime.database.duty.refresh`（demo、platform_control） | PASS；平台管理员凭据 `authenticated=true`、`writes=0` |
| 渲染后环境文件 `bash source` 回读 | `SC_DECLARED_NAMESPACE_ALIASES="demo|platform"` → `demo|platform` |
| `make daily.runtime.published_face.converge`（修复前失败的那个包装入口） | PASS；standard 91 页、preview 129 页，`guard_status=PASS` |
| `make daily.runtime.entry.verify` | PASS，66 项 0 失败 |
| `scripts/ops/path_ns_c_acceptance.py` | PASS，23 项 0 失败 |

关键判据：包装入口 PASS 覆盖了 `check_env.sh` 的 `source` 环节，因此“环境文件可被 shell
读取”不再是推断，而是被真实升级路径消费后仍成立。

## 未覆盖/阻断

- 浏览器端登录后会话隔离沿用路径命名空间专题的独立门禁，本批未重跑。
- 本批不改变平台或租户身份语义，也不覆盖角色与权限体系。

## 回滚

仅两处文本与诊断改动，回滚即恢复未加引号的模板行和原失败信息。回滚后
`check_env.sh` 会重新在 `source` 阶段失败，因此不得在未回滚代码的情况下重跑治理升级
入口；若需紧急恢复，可先手工为渲染产物加引号，再回滚代码。
