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
- 平台职责声明的窗口动作同时注入 `route_authority.admin_actions`
  （`menu_id=0`、`route=/a/<action_id>`），使无原生菜单的动作也能通过 SPA
  路由授权；该注入只对已验证的平台身份生效。
- 补齐验证面：平台职责契约测试登记进前端 PR/发布车道；装配缓存指纹随
  `ui_contract_v2` 变更重钉并升级缓存版本，避免旧装配继续被命中。

## 验证

- `make verify.platform.duty.contract.unit`：31 项通过（Python 25 + Node 6；
  前端测试先用 esbuild 打包，避免 CI Node 版本不支持直接执行 `.ts`）。
- `make verify.agent.ledger.unit`：18 项通过。
- `make audit.verification.lane_coverage.check` 与
  `make verify.unified_page_contract.v2.assembler` 通过。
- 部署后以平台管理员登录回读 `/platform-admin/api/ops/platform-duty`、登录后
  点击“运维任务”，确认进入官方列表页且无 400。
