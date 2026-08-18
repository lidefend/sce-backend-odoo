# Production Deployment Record — rc12_upgrade_20260801

## 1. 基本信息

| 项目 | 值 |
| --- | --- |
| 部署编号 | `rc12_upgrade_20260801` |
| 部署窗口 | `2026-08-01 Asia/Shanghai` |
| 操作人 | `Codex（用户授权执行）` |
| 审批人 | `用户（会话明确授权）` |
| 生产主机 | `sc-prod` |
| 生产工具目录 | `/opt/sce/deployment-tools/915067ba5d282bfcc03d276d49cd61c5f169a0fd` |
| 生产数据库 | `sc_production`（tenant 身份由生产运行配置解析且不落产品仓库，dbfilter `^sc_production$`） |
| 发布类型 | `incremental package`（不可变镜像升级） |
| 发布包 | `ghcr.io/lidefend/sce-product@sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d` |
| 发布包 sha256 | `5611365c5a69e79575f3a433a2438eb2832ef0e1c8118f5a01a0650e1e37a422` |
| 目标 commit/tag | `3fb17948feacb34c2574668eaba7ddb2ad4bef26` / `v1.0.0-rc.12` |

## 2. 发布范围声明

本次发布范围：

- [x] 发布并同步 RC12 不可变候选镜像。
- [x] 同步 RC12 候选编排清单并提升生产运行身份配置。
- [x] 升级 `smart_core`、`smart_construction_core`。
- [x] 以 RC12 精确镜像身份替换 Odoo 与 Nginx 运行容器。
- [x] 执行两轮相互独立的生产验收。
- [ ] 生产与日常开发服务器全量代码树一致。

变更载体清单：

```text
ghcr.io/lidefend/sce-product@sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d
/opt/sce/candidates/v1.0.0-rc.12
/opt/sce/config/sc_production/runtime.env
/etc/scems/production-promotion.env
```

模块清单：

```text
smart_core
smart_construction_core
```

Migration 清单：

```text
无独立 migration payload；使用 Odoo 标准模块升级入口加载 RC12 中的模块变更。
```

## 3. 发布前状态

生产发布预检通过，数据库、租户、精确 dbfilter、filestore 与候选身份均已解析；
`promotion-readiness.json` 给出 `safe_to_replace=true`。

生产升级前运行身份：

```text
source=2b965443... (RC11)
registry digest=sha256:150098...af14
running image id=sha256:3e1e...2d64
database=sc_production
tenant=resolved from governed production runtime config; cleartext not recorded
dbfilter=^sc_production$
```

日常开发与生产差异登记：

| 差异类型 | 结果 | 说明 |
| --- | --- | --- |
| 发布包文件差异 | `0` | 候选归档 SHA-256、OCI 内容 ID、GHCR digest 及生产加载身份一致 |
| 模块版本差异 | `PASS` | 两个目标模块均完成 RC12 标准升级入口 |
| 全量代码树差异 | `not asserted` | 本次以不可变镜像为发布单元，不声明宿主机工作树全量一致 |
| 数据差异 | `PASS` | 两轮只读生产验收均通过，未引入 demo 数据 |

## 4. 备份

| 类型 | 路径 | 校验 | 结果 |
| --- | --- | --- | --- |
| 数据库 | `/data/backups/sc_production/sc_production-20260731T190202Z-50657a16` | 隔离恢复演练及核心表计数核对 | `PASS` |
| filestore | `/data/backups/sc_production/sc_production-20260731T190202Z-50657a16` | digest `9e324c...7549`，隔离恢复演练 | `PASS` |
| 运行配置 | `/opt/sce/config/sc_production/runtime.env.pre-1_0_0-rc_12-20260731T204500Z` | 提升流程生成的原子回滚副本 | `PASS` |
| promotion 配置 | `/etc/scems/production-promotion.env.pre-1_0_0-rc_12-20260731T204500Z` | 提升流程生成的原子回滚副本 | `PASS` |

备份验证结果：

```text
restore rehearsal id=sc_restore_20260731t202130z_03cb579f
report=/data/backups/sc_production/restore-rehearsals/sc_restore_20260731t202130z_03cb579f.json
RTO=25.343 seconds
ir_attachment=1031
ir_module_module=676
project_project=923
res_users=115
production DB connected=false
production network/volume reused=false
external writes=0
cleanup=PASS
```

## 5. Prod-Sim 验证

RC12 候选先完成隔离候选流水线；生产新备份随后完成网络、数据库和卷均与生产隔离的恢复演练。

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| 生产备份恢复 | `PASS` | `/data/backups/sc_production/restore-rehearsals/sc_restore_20260731t202130z_03cb579f.json` |
| 候选发布包应用 | `PASS` | `artifacts/release/candidates/1.0.0-rc.12/attempts/20260731T163613Z-3257bd9caa264a91a0280f3932803636/release-report.json` |
| 模块升级 | `PASS` | RC12 candidate final-image real-plan gate 与生产模块升级结果 |
| 业务烟测 | `PASS` | candidate acceptance package 与生产两轮验收 |
| 角色矩阵 | `PASS` | candidate acceptance package 与生产两轮验收 |
| 非 demo 污染 | `PASS` | candidate acceptance package 与生产两轮验收 |

prod-sim / restore 运行 ID：

```text
candidate attempt=20260731T163613Z-3257bd9caa264a91a0280f3932803636
restore rehearsal=sc_restore_20260731t202130z_03cb579f
```

## 6. 生产执行摘要

全部生产写操作均通过生产策略允许的 Make target 完成，未直接修改容器、数据库或远端配置。

```text
production.candidate.image.sync: PASS
production.candidate.manifest.sync: PASS
production.deployment.tool.sync: PASS
production.release.config.promote: PASS
release.production.promotion.config.preflight: PASS (safe_to_replace=true)
release.production.db.preflight: PASS
release.production.module.upgrade MODULE=smart_core: PASS
release.production.module.upgrade MODULE=smart_construction_core: PASS
release.production.runtime.up: PASS
release.production.db.preflight (post-switch): PASS
```

服务替换结果：

```text
database and Redis retained running
Odoo and Nginx recreated healthy
configured image=ghcr.io/lidefend/sce-product@sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d
Odoo image ID=sha256:ab646cc224eb08df3605e5aa3dc5ff2dc06064a7b06a1ed8eebfa7569f49edcf
Nginx image ID=sha256:ab646cc224eb08df3605e5aa3dc5ff2dc06064a7b06a1ed8eebfa7569f49edcf
```

## 7. 发布后验证

两轮独立验收证据：

```text
/data/backups/deployments/rc12-20260731T204500Z/acceptance-round-1.json
/data/backups/deployments/rc12-20260731T204500Z/acceptance-round-2.json
acceptance package sha256=c0274b881052c463c9d3183843781a81cc42a08789b029de6374b69131298a5c
```

| 检查项 | 结果 | 摘要 |
| --- | --- | --- |
| `verify.baseline` | `PASS` | 两轮生产验收基线检查通过 |
| `verify.p0` | `PASS` | 两轮 P0 生产门禁通过 |
| `smoke.business_full` | `PASS` | 两轮完整业务烟测通过 |
| `smoke.role_matrix` | `PASS` | 两轮角色矩阵烟测通过 |
| `verify.non_demo_data_contamination` | `PASS` | 两轮非 demo 污染检查通过 |
| `history.attachment.custody.probe.prod` | `PASS` | `history_attachment_custody_ready` |
| 服务健康 | `PASS` | Odoo、Nginx、PostgreSQL、Redis 均 healthy |

Demo 状态：

```text
smart_construction_demo XMLID count=0
smart_construction_demo|uninstalled|
```

运行身份终检：

```text
expected registry digest=sha256:cecdeb03ea68a1d2ddead0cf3f3ffb7a391948ba7de92e3919b752b7635d3a1d
Odoo/Nginx actual image ID=sha256:ab646cc224eb08df3605e5aa3dc5ff2dc06064a7b06a1ed8eebfa7569f49edcf
Odoo/Nginx health=healthy
backup timer=enabled, active
```

## 8. 回滚点

| 回滚对象 | 路径/版本 | 操作说明 |
| --- | --- | --- |
| 数据库 | `/data/backups/sc_production/sc_production-20260731T190202Z-50657a16` | 按生产备份恢复 runbook 从已演练备份恢复 |
| filestore | `/data/backups/sc_production/sc_production-20260731T190202Z-50657a16` | 与数据库按同一备份世代配对恢复 |
| 运行配置 | `/opt/sce/config/sc_production/runtime.env.pre-1_0_0-rc_12-20260731T204500Z` | 由配置提升回滚入口恢复后重建运行容器 |
| promotion 配置 | `/etc/scems/production-promotion.env.pre-1_0_0-rc_12-20260731T204500Z` | 与运行配置配对恢复 |
| 发布包 | RC11 digest `sha256:150098...af14` | 恢复上一不可变镜像身份后走正式 runtime up 入口 |

## 9. 收口结论

- [x] 本次发布包范围已与生产对齐。
- [x] 生产模块版本已达到本次发布目标。
- [x] 生产服务健康检查通过。
- [x] 生产验证矩阵全部通过。
- [x] demo 模块和 demo XMLID 状态符合生产要求。
- [ ] 生产与日常开发服务器全量一致。

生产与日常开发服务器不是全量一致。本次结论仅限于发布包范围和发布后验证结果。

最终发布结论：

```text
RC12 不可变镜像生产升级完成；目标模块升级、精确镜像身份、两轮生产验收、服务健康和备份恢复演练均通过，具备生产运行条件。
```

## 10. 后续事项

| 事项 | 负责人 | 截止时间 | 状态 |
| --- | --- | --- | --- |
| 按既有 systemd timer 持续执行生产备份 | `Ops` | `daily` | `retained: timer enabled and active` |
| 后续升级继续使用不可变候选与双轮生产验收 | `Ops` | `each production release` | `retained: governed release contract` |
