# CAPABILITY-EXPLORER-05 主线集成验收报告

状态：`BLOCKED_PENDING_DIFFERENCE_RECONCILIATION`

报告日期：2026-11-15

目标仓库：`lidefend/sce-backend-odoo`

验收基线：`main@f35d981b2a37d6268e31592edeef460c9580240c`

## 1. 结论

PR #889 已合入当前 main，合并树与 PR 最终候选树一致。Explorer 的
List、搜索、分页、Detail、Diagnose、`catalog_token` 过期拒绝和管理员权限拒绝均在
当前 main 的真实 HTTP/浏览器观察通过。Explorer 读取前后，目标业务、场景、发布与旧能力表
的逐表内容摘要不变。该观察不改变严格隔离验收状态。

隔离 `sc_clean` 的模块升级没有通过，原因是该演练库处于不一致状态：
`smart_construction_core=17.0.0.172` 已标记 installed，但
`sc_product_scenario_entry` 不存在，导致 `17.0.0.180` pre-migrate 的无条件
`ALTER TABLE` 失败。该项保持 `BLOCKED`，不能用后续 `sc_dev_demo` 升级结果替代。

本报告同时记录一次执行范围偏离：为消除合并前运行进程缓存，本轮升级并重启了持久
`sc_dev_demo`。该动作不属于“只在隔离环境完成升级”的严格验收，也不能被描述为全只读。
其 API 结果保留为主线上运行行为的观察证据，但本轮严格隔离验收状态仍为 `BLOCKED`。
所有者已通过 `CAP05-D01` 裁定保留当前持久开发状态、暂不恢复；`CAP05-B02` 继续保持
BLOCKED，等待恢复点差异核对，任何恢复仍需重新取得明确授权。

## 2. 主线身份与远端证据

| 项目 | 观测值 | 状态 |
|---|---|---|
| 本地工作树 | `/home/lidefend/workspace/sce-backend-odoo` | PASS |
| 验收基线 | `f35d981b2a37d6268e31592edeef460c9580240c` | PASS |
| 远端 `origin/main` | `f35d981b2a37d6268e31592edeef460c9580240c` | PASS |
| PR #889 状态 | `MERGED` | PASS |
| PR 最终候选 | `088f00e6f3b15d4167f2c21c555542eed0c69b79` | PASS |
| PR 合并提交 | `f35d981b2a37d6268e31592edeef460c9580240c` | PASS |
| 候选树 | `1efc48e0cb44e55031b563df22066bccfb6ff694` | PASS |
| 合并树 | `1efc48e0cb44e55031b563df22066bccfb6ff694` | PASS |
| 差异 | `git diff 088f00e6 f35d981b` 为空 | PASS |

PR 最终候选上的四项必需检查均为 `success`：

| 必需检查 | Workflow run / Job | 状态 |
|---|---|---|
| `public_guard` | `43714494715 / 132813028300` | SUCCESS |
| `merge_policy_gate` | `43714494734 / 132816404986` | SUCCESS |
| `professional_quality_gate` | `43714494881 / 132816367285` | SUCCESS |
| `frontend_release_gate` | `43714494737 / 132812966488` | SUCCESS |

生成证据：

- Quick receipt
  `.git/codex/evidence/ci.local.quick/088f00e6f3b15d4167f2c21c555542eed0c69b79.json`
  SHA256 `923376f38c30e7cde0863a86da37e23613a759e8346e4e3567fdeca940eca97c`，
  head 为 PR 最终候选，tree 为同一合并树。
- `managed_orm` artifact `14162051492` 绑定
  `head=088f00e6f3b15d4167f2c21c555542eed0c69b79`，归档摘要
  `sha256:7f7d9f28c6dc1df838d5d3df25aee2ba4418c62f9cd0ecb3a802915d5f0f4da1`。
- 后端计划 artifact `14162355366` 绑定同一 PR head；4 个 backend shard、
  coverage 和 professional quality 汇总均成功。

## 3. 隔离与你给运行环境

### 3.1 `sc_clean` 隔离库

前置身份：

- project `sc-local-clean`
- database `sc_clean`
- dbfilter `^sc_clean$`
- isolated rehearsal，无 demo/fixture

第一次健康检查失败为 `environment_defect`：Nginx 仍挂载另一工作树的
`frontend/apps/web/dist-clean`，返回 404。通过 `make local.clean.frontend` 与
`make local.clean.up` 重建后，健康检查通过。

随后执行：

```text
make local.clean.upgrade MODULE=smart_core
```

结果：`BLOCKED / FAILED`

只读回读发现：

```text
smart_construction_core|installed|17.0.0.172
smart_core|installed|17.0.1.1.19
sc_product_scenario_entry|to_regclass=null
```

升级尝试在依赖模块 `smart_construction_core` 的 `17.0.0.180` pre-migrate 阶段失败：

```text
ALTER TABLE sc_product_scenario_entry
DROP CONSTRAINT IF EXISTS sc_product_scenario_entry_menu_uniq

ERROR: relation "sc_product_scenario_entry" does not exist
```

分类：`environment_defect`。该干净演练库本身不一致；由于没有获得销毁重建
`sc_clean` 的授权，本轮不执行重建，也不把该升级标记为通过。后续若要证明通用升级路径，
应在明确授权的隔离恢复点或新建演练库上验证，并单独判断迁移脚本是否应对缺失表 fail-closed。

### 3.2 `sc_dev_demo` 当前主线运行态

为排除合并前进程缓存，执行了受管 `local.dev.upgrade`、重启和入口身份校验：

- `smart_construction_core` 升级到 `17.0.0.182`。
- 77 个模块加载完成，demo authority 通过。
- `local.dev.entry_identity.verify` 通过
  `alias=demo / namespace=ns_000000000002 / database=sc_dev_demo`。
- Odoo 进程重启后完成真实浏览器与 HTTP 验收。

该结果证明当前 main 可升级和运行，但不是隔离升级的替代证据。
升级后、重启前的一次浏览器结果因运行进程仍可能持有旧 registry，已明确排除，不进入
本报告的证据结论；下文只使用重启并完成入口身份校验后的结果。

### 3.3 范围偏离与恢复风险

`sc_dev_demo` 升级是持久环境写入，已明确登记为 `CAP05-B02 / scope_deviation`：

- 它不是隔离验收环境，不计入隔离升级 PASS。
- 它没有改变 ORM、ACL、Record Rule、Scene、Candidate、Qualification 或 Release 源码，
  但模块升级会按设计刷新持久开发库的模块元数据和 XML 声明。
- 受管入口没有在本轮执行数据库/filestore 恢复。
- 可用升级前恢复点：
  `artifacts/local-dev/snapshots/20261115T082948Z/`，来源
  `source_sha=d176e2fd67fec87257114b207cec655ec8fa6e9d`，manifest SHA256
  `bf9db35d4715f656521f9e5964fcdfdb905b3b7820958f5648d561769d08d316`。
- 本批没有为 `local.dev` 建立受管 restore Make 入口，因此不能把该恢复点描述为已完成回退。
  恢复需所有者单独授权、验证 dump/filestore 配对摘要并制定受管恢复方案。

所有者裁定 `CAP05-D01`：**暂不恢复，也不把当前持久状态认定为严格验收通过。**
下一项独立只读工作应比较 2026-11-15T08:29:48Z 恢复点与当前数据库/filestore，识别模块升级、
快照后业务新增和回滚数据损失。任何恢复仍需新的明确授权。

## 4. Explorer 验收

### 4.1 静态与契约测试

| 检查 | 结果 |
|---|---|
| `verify.platform.capability_explorer.unit` | PASS，19 + 6 + 2 tests |
| `verify.frontend.platform_capability_explorer.unit` | PASS，27 + 4 + 13 + 3 + 21 cases |
| `verify.odoo_native_capability_explorer.unit` | PASS，10 tests |

### 4.2 真实浏览器

环境：candidate 静态载体 `http://127.0.0.1:5176/t/demo`，API 代理到
`local.dev/sc_dev_demo`，`admin`，`zh-CN`，桌面 1440px 与移动 390px。
该 candidate 从 R1 exact HEAD 构建，验证结束后已受管关闭。

- 29/29 assertions PASS。
- List：17 条，unbound 17。
- 搜索“项目”：服务端过滤到 1 条。
- Center filter：`unclassified` 返回 2/2。
- Detail：Menu/Action、模块、模型、View、ACL、Record Rules、Preview/Standard
  资格分栏均渲染。
- Diagnose：真实请求成功；迟到诊断竞态探针不能覆盖当前选定入口。
- `CATALOG_STALE`：唯一预期 409 被精确消费；无其它 HTTP 失败。
- Console/Page errors：0。
- 移动端无水平页面溢出。
- 普通用户 `wutao` 被路由拒绝，路由访问期间 Explorer List 请求数为 0；
  直接 Handler 请求返回精确 HTTP 403 `PERMISSION_DENIED`。

浏览器复验记录：

- 首次在共享 `18081` 和 candidate `5176` 上，均在 stale-token 恢复等待处超时；
  此时已生成列表与详情截图，但完整 harness 未完成，不记 PASS。
- 独立诊断在同一 candidate 上观察到 `409 CATALOG_STALE -> List 200` 的真实恢复链路。
- 基于该恢复事实，在候选前端未变化的情况下重试一次并取得 29/29 PASS。
- 原始失败、诊断和通过日志均保留在本目录的 `evidence/`。

证据：

- `docs/audit/capability-explorer-05/evidence/browser-report.json`
  SHA256 `7de13fb3349e9314f31995371f4606bd8a2bb4531e699c52c8aa0c39ffc72af0`
- `docs/audit/capability-explorer-05/evidence/browser-pass.log`
  SHA256 `03315aa66fcbbde8b9705090d3e1cea4343fd63d2dc98a16e018920a5ca1ec7e`
- 首次超时日志 SHA256
  `02e46d849172da53363cece32930e4a1d319e04adc6fa40bc6f0aa34529440eb`
- `409 -> 200` 恢复诊断日志 SHA256
  `33624cdecb4d2076bca9fe88ffe074815a9a04b46217d0953be8acf0cb43f1d0`

### 4.3 真实 HTTP API

使用同一 `admin/zh-CN` 会话直接调用 `/t/demo/api/v1/intent`：

| 检查 | 结果 |
|---|---|
| `catalog_token` | `sha256:37490e5695e1a632a4786716867e7d1f5f4b482346cde16d4a787fa19cdfec7b` |
| 第 1 页 | `offset=0, limit=5, next_offset=5, has_more=true` |
| 第 2 页 | `offset=5, limit=5, next_offset=10, has_more=true` |
| 分页重叠 | 0 |
| List/Detail/Diagnose | 200 / 200 / 200 |
| Diagnose | `native_valid=true, draft_selectable=true, scene_assignable=true` |
| Stale token | 409 `CATALOG_STALE` |

证据：HTTP 日志 SHA256
`4a396c1896bd687277435e0b44810d328ca76aa854f4d446b54b6178b7cfa37c`。

## 5. 只读性与业务状态

在最终 HTTP 验收前后，对以下表计算行数与全行内容摘要：

`sc_capability`, `sc_capability_audit_log`, `sc_capability_group`,
`sc_edition_release_snapshot`, `sc_product_policy`, `sc_product_scenario`,
`sc_product_scenario_entry`, `sc_release_action`

前后摘要完全一致，SHA256 均为
`42fe2ee148633555a997d62ba820315097c9fe81e7c0f709d7a032ad3e759c57`。

结论：Explorer 的 List、Detail、Diagnose、搜索、分页和 stale-token 拒绝没有创建或修改
业务记录、场景绑定、发布状态、候选或企业启用状态。模块升级本身当然会更新模块元数据和
XML 声明，这与 Explorer 请求的零业务写入是两个不同事实。

## 6. 状态与未决项

### PASS

- PR #889 合并身份、树一致性和四项必需 CI。
- 当前 main 的 Explorer 单元、契约，以及持久开发环境上的真实 HTTP/浏览器观察。
- 后端权限拒绝与前端路由拒绝。
- API 分页、搜索、Detail、Diagnose、stale token。
- Explorer 请求前后业务/发布表不变。
- 历史 282 个复合身份与当前 282 个原生事实 1:1 对账。

### BLOCKED

- `CAP05-B01`：隔离 `sc_clean` 从已标记 `17.0.0.172` 但缺少
  `sc_product_scenario_entry` 的状态升级失败。未获授权重建该库。
- `CAP05-B02`：持久 `sc_dev_demo` 被升级和重启，属于范围偏离；严格隔离验收不可关闭。
  所有者已裁定暂不恢复并保持 OPEN；需另行完成差异核对，任何恢复都需重新授权。

### NOT_VERIFIED

- 其他租户、生产库和平台控制实例的同类 API 验收。
- 超过 50 条的 Explorer 前端翻页交互；API 两页不重叠已验证，17 条运行库未触发
  浏览器第二页。
- 隔离干净库升级后的 API 验收；被 `CAP05-B01` 短路。
- Preview/Standard 产品资格：当前证据仍为 0 项 evidence-backed qualification。

## 7. 下一阶段准入建议

| 方向 | 准入建议 |
|---|---|
| 原生能力发现 | 准入。继续以 Odoo 安装模块、Menu、Action、Model、View、ACL、Rule 为事实源。 |
| 能力身份 | 准入但必须固定复合身份 `(menu_xmlid, action_xmlid)`；不能只用 Action XMLID。 |
| 能力资格 | 不准入声明“已合格”。现有 evidence-backed Preview/Standard 均为 0，须由后端独立证据裁决。 |
| 能力发布 | 与能力资格分离；274 个 released 入口不能再被解释为 274 个已合格能力。 |
| 场景引用 | 只有后端确认已发布且满足场景准入的能力可引用；当前 75 个有场景权威绑定，207 个仅中心分类。 |
| 企业启用 | 保持独立租户级决策，不从产品发布或日志推断。 |
| Explorer | 准入为只读管理与诊断面；不得增加发布、资格推断或企业启用写操作。 |

部署状态：未部署。用户验收状态：未执行。PR 合并不等于部署或产品交付。
批次状态：`BLOCKED`。持久库暂不恢复；严格隔离验收和整体能力治理仍未完成。

## 8. 候选验证与复审入口

- `make agent.run.resume`：resolved，无越界路径。
- `make ci.local.iteration`：PASS；增量选择执行
  `verify.agent.ledger.unit` 18 tests，并完成相关 L1 守卫。
- `git diff --check`：由增量门禁执行，PASS。
- 当前 run 状态：`blocked`；本报告的候选可独立入主线，但不构成整体验收完成。
- 原始日志：`docs/audit/capability-explorer-05/evidence/ci-local-iteration.log`。
- exact-HEAD 定向日志：
  `native-unit.log`、`explorer-unit.log`、`frontend-unit.log`、`agent-ledger.log`。
