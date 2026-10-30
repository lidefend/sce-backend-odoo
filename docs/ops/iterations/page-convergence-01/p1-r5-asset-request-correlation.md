# PAGE-CONVERGENCE-01 / P1-R5 · 持久化资产与真实请求关联诊断

结论：2288 与 2290 不是同一页面的“旧/新”两个版本，而是两个不同模型的运行时契约资产。
项目详情请求命中 2288（`project.project`）。2288 的持久化 source token 与当前重算 token
不一致，说明它是一份陈旧内容，且会被当前请求绕过。资产匹配与失效机制本身工作正常。

## 一、运行身份

- 分支：`feature/page-convergence-01`
- HEAD：`d363c01ee0f71cae686da42dbc574bdfbf4d8028`
- 本地受管库：`sc_dev_demo`（项目 `sc-local-dev`；诊断目标，非远程 `sc_demo`）
- 业务账号：pm1（`res.users` id=8）
- 项目记录：`project.project` id=21，action_id=590，menu_id=382
- 目标表单视图：`ir.ui.view` id=1769（`project.project.form.sc.overview`）

## 二、两份资产完整身份

| 维度 | 资产 2288 | 资产 2290 |
| --- | --- | --- |
| contract_kind | runtime_source | runtime_source |
| scene_key（即 cache key） | `ui.contract.v2:27545fba…` | `ui.contract.v2:21df3e45…` |
| role_code | `uid:8:groups:b59e40575e41513d` | 同左 |
| company_id | 1 | 1 |
| source_ref | `ui.contract.v2:project.project` | `ui.contract.v2:project.collaborator` |
| payload.model | `project.project` | `project.collaborator` |
| payload.view_id | 1769 | null |
| status | active | active |
| asset_version（source token） | `031fb909…` | `1079e436…` |
| generated_at | 2026-10-30 07:39:30 | 2026-10-30 07:39:32 |

同一批还生成了 2289（`project.tags`）、2291（`project.responsibility`），它们是项目详情页
渲染时并行的关联视图契约，与 2288 同 role/company、不同 cache key。

## 三、三个问题的答案

### Q1：2288 与 2290 为什么 cache key 不同？

cache key 是 `build_projection_cache_key` 对请求语义身份（namespace、db、uid、role、company、
model、view_types、params）的 sha256。两个资产绑定不同 model（`project.project` vs
`project.collaborator`），身份不同，cache key 必然不同。P1-R4 将二者解读为“旧页头 vs 新页头”
属于误读。

### Q2：15:39 的项目详情请求命中哪个资产？

命中 2288。请求 `/r/project.project/21?action_id=590&menu_id=382`（pm1，company 1）对应
model `project.project`、action 590、view 1769，与 2288 的 source_ref / payload.model /
payload.view_id 完全一致。

### Q3：命中旧资产是匹配规则问题还是失效机制问题？

两者都不是。用当前重算的 source token 查询 2288 返回 miss：

- 2288 持久化 token：`031fb9091abc1029d4cb85de59bcbc3e4b5831ec861e2507bad17562b98f2a4b`
- 当前重算 token（pm1，action 590）：`5f599729541b500d7f884b2c9f755f52e656179c0956bd1bd173ffcebe01216b`
- `get_runtime_source_asset(cache_key=2288.scene_key, source_token=当前 token)` → 未命中

资产仓库按 `(scene_key=cache_key, role_code, company_id, asset_version=source_token)` 精确匹配，
行为正确。

## 四、陈旧内容的真实来源

2288 的 payload 页头仍然包含 `sc-project-title` + `name` + `operation_strategy`（旧结构），
而数据库视图 1769 的 `arch_db` 已更新为新结构（`project_code` + `business_nature`，无
`sc-project-title`，无页头 `name`/`operation_strategy`），`write_date=2026-10-30 07:37:33`。

时间线（均为 UTC）：

| 时间 | 事件 |
| --- | --- |
| 07:35:56 | 提交 `d363c01ee` 删除页头重复节点 |
| 07:37:33 | `make local.dev.upgrade` 更新数据库视图 `arch_db` |
| 07:39:30 | 旧服务进程生成并持久化 2288（仍为旧页头内容） |
| 07:57:32 | 服务进程重启（PID 1 启动时刻） |

07:39 时提供服务的进程是升级前启动的旧进程：`contract_code_fingerprint()` 按进程缓存代码内容
摘要，模块升级在独立进程完成且未重启长驻服务，旧进程继续用升级前的指纹与陈旧 ORM 缓存组装
契约，并把旧内容按其自身（同样陈旧的）token 持久化为 2288。因此 source token 机制无法察觉
“进程外部”发生的代码/数据库变化。

07:57 进程重启后，代码指纹与权威表 write_date 重算，当前 token 变为 `5f599729…`，与 2288 的
`031fb909…` 不一致，后续请求将绕过 2288 并按新视图重建契约。

## 五、边界与下一步

本轮为只读诊断：未删除资产、未改 active 状态、未清 Redis/进程缓存、未重启、未重新升级。

下一步（P1-R6）：用当前已重启的服务进程对 `/r/project.project/21?action_id=590&menu_id=382`
重新组装并浏览器验收三视口，确认页头重复名称/经营方式消失；若仍显示旧内容，再追查
`native_form_projection` 组装链中的视图读取来源，而非资产层。
