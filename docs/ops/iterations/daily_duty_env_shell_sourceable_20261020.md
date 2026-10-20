# 日常职责环境文件可被 shell source

状态：候选离线验证通过；尚未部署，运行态验收未执行。

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

## 未覆盖/阻断

- 尚未在候选 SHA 上部署日常开发服务器；`daily.runtime.entry.verify`、
  `path_ns_c_acceptance`、平台凭据 verify 与发布面包装入口的实跑证据必须在
  两个职责均绑定该候选后重采。
- `6dd15103` 的既有运行证据不得迁移到本候选。
- 本批不验证浏览器端登录后会话隔离；该项沿用路径命名空间专题的独立门禁。

## 回滚

仅两处文本与诊断改动，回滚即恢复未加引号的模板行和原失败信息。回滚后
`check_env.sh` 会重新在 `source` 阶段失败，因此不得在未回滚代码的情况下
重跑治理升级入口。
