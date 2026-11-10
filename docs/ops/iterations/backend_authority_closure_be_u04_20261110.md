# BE-U04 Scene Publication Authority

状态：本地批次验收完成；主线集成、部署和既有版本重发布未执行。候选分支
`codex/be-u04-scene-publication-authority-20261110`，基线为
BE-U03 候选 `53e949fa0a8dc1c1504ca0bab52bd770b8bbd401`。

## 目标

场景发布冻结产品定义，不冻结发布者当时的用户授权投影：

- 发布会包含所有 active 且 visible 的 tile；
- 冻结 payload 不包含 `allowed`、`user_visible`、`state`、`reason_code` 等用户结果；
- 已发布版本运行时按当前用户重新计算能力访问；
- 产品发布状态与企业启用继续独立，撤销后下一请求生效。

## 层与范围

- `Formal Product Layer`：P1 施工行业标准。
- `Layer Target`：`sc.scene`/`sc.scene.version` 发布构建与运行时投影。
- `Module`：`smart_construction_core`。
- `Why Here`：场景版本模型拥有“冻结了什么”的权威。
- `Why Not Elsewhere`：前端、产品策略或企业启用数据都不能恢复未进入快照的 tile。

## 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.backend.authority_closure.unit` | PASS，7 tests；G04 发布/运行投影锚点一致 |
| `make verify.frontend.dev.incremental.unit` | PASS，108 tests；场景发布路径有专属 ORM 目标 |
| `make verify.scene.publication_authority.orm` | PASS，2 tests；受限发布者仍冻结两个定义，运行时只返回可访问 tile |
| `make ci.local.iteration` | PASS，affected targets=5；一次性 `sc_test` ORM 重验 2/2 |

首次 ORM 失败为 `validation_tool_defect`：测试用户只有 `base.group_user`，缺少现存 `sc.scene`
读 ACL，尚未进入发布逻辑。测试主体改用既有 `group_sc_internal_user` 后重跑 2/2。原始失败日志保留。

覆盖限制：本批不重写历史 `sc.scene.version`；旧版本若已被发布者可见性裁剪，仍须识别后重新发布。
产品发布资格、企业启用和历史版本完整性未在本批重新验收。

提交钩子刷新了测试覆盖 registry、复杂度预算和拆分队列；差异只描述新增测试与文件规模，
不改变产品断言，已纳入本批范围。

## 回退

回退 BE-U04 提交即可。既有版本记录、schema、ACL 与部署产物不变。
