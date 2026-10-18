# 平台运维任务入口修复（2026-10-18）

## 现象

平台管理员登录后点击“运维任务 → 读取”，`GET /platform-admin/api/ops/job/status`
返回 400 `job_id required`，页面显示“读取失败”。

## 根因

`platform.job_status` 在平台职责契约中被声明为一个读取入口，但后端只支持按
`job_id` 查询单个任务；同时前端把手写的表格/JSON 面板当作渲染路径，绕开了官方
`ActionViewShell` 的列表模板。

## 修复

- 契约将 `platform.job_status` 绑定到官方窗口动作
  `smart_core.action_sc_ops_job`，运行期解析为 `/a/<action_id>`，由
  `ActionViewShell` 渲染 `sc.ops.job` 列表。
- `GET /api/ops/job/status` 无 `job_id` 时返回有上限的任务列表；仍保留按
  `job_id` 查询详情，非法 id 明确返回 400。
- 平台面板不再手写运维任务表格或直接读取该 API。

## 验证

- `python3 addons/smart_core/tests/test_platform_admin_duty_contract.py`：22 项通过。
- 前端 `vue-tsc` 与 `vite build` 通过。
- 部署后以平台管理员登录回读 `/platform-admin/api/ops/platform-duty`、登录后
  点击“运维任务”，确认进入官方列表页且无 400。
