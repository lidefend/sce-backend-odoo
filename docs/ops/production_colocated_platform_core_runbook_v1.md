# 生产平台内核单库共置发布 Runbook v1

英文版本：[production_colocated_platform_core_runbook_v1.en.md](production_colocated_platform_core_runbook_v1.en.md)

## 范围与停机点

本 runbook 只适用于 `PRODUCTION_BUSINESS_DB=sc_production` 且 `PRODUCTION_PLATFORM_DB=sc_production`。正式执行必须另获生产变更授权，并先生成新的、非覆盖式数据库+filestore 成对备份。本 R10E 任务只在隔离克隆验证，不授权运行以下正式写操作。

禁止创建生产 `sc_platform_core`、复制开发平台数据、直接插入快照、隐式跨库读取、切流或自动进入 R11。

## 发布前只读预检

1. 固定候选镜像 digest、Git SHA、数据库 `sc_production` 和正式 filestore volume。
2. 设置部署模板中的 `TARGET_DB=sc_production` 与 `PLATFORM_RELEASE_DB=sc_production`；不得使用缺省值。
3. 运行 `release.production.db.preflight`。该检查要求环境配置与 `ir.config_parameter.smart_core.platform_release_db` 同时显式等于当前数据库。
4. 只读确认 `smart_core` 已安装、产品策略存在、正式库当前活动快照数量和业务/平台数据基线。
5. 确认 Nginx 锁库仍为 `sc_production`，客户端数据库输入矩阵不能改变 registry。

## 受控安装、三联备份与校验

生产端不得直接 `scp/install/systemctl`。从双远端一致、工作树干净的批准
`main` 先执行只读预检，再在独立授权下原子安装：

```bash
ENV=prod PRODUCTION_COMPOSE_PROJECT=sc_production TARGET_DB=sc_production \
BACKUP_TOOL_SOURCE_SHA=<approved-main-sha> EXPECTED_LIVE_MAIN_SHA=<same-sha> \
BACKUP_ENCRYPTION_STATUS=<verified-policy> BACKUP_RETENTION_DAYS=<days> \
make production.backup.install.preflight

ENV=prod PROD_DANGER=1 PRODUCTION_COMPOSE_PROJECT=sc_production \
TARGET_DB=sc_production BACKUP_TOOL_SOURCE_SHA=<approved-main-sha> \
EXPECTED_LIVE_MAIN_SHA=<same-sha> \
BACKUP_ENCRYPTION_STATUS=<verified-policy> BACKUP_RETENTION_DAYS=<days> \
CONFIRM_BACKUP_TOOL_INSTALL=YES_INSTALL_GOVERNED_BACKUP_TOOL \
make production.backup.install

ENV=prod PROD_DANGER=1 \
CONFIRM_PRODUCTION_BACKUP=YES_CREATE_SC_PRODUCTION_TRIPLE_BACKUP \
make production.backup.run
```

安装器保存旧文件、摘要、权限和 timer 状态；unit 离线验证失败时恢复旧状态，
且成功安装后也保持 timer 暂停，直至手动备份和恢复演练均通过。每个 backup
set 原子包含 `sc_production` 数据库、对应 filestore 和脱敏部署元数据。独立锁
拒绝并发执行，完成目录不可覆盖，临时或失败目录不能作为恢复点。

## 隔离恢复演练

恢复入口自行建立固定范围的内部网络、数据库 volume、filestore volume 和
容器命名空间；它不加入生产 network，不挂载生产 volume，不连接生产
PostgreSQL，并通过无外网、零 cron 的 Odoo `--stop-after-init` 验证启动：

```bash
ENV=prod PROD_DANGER=1 \
BACKUP_DIR=/data/backups/sc_production/<backup-set-id> \
RESTORE_ID=sc_restore_<utc>_<random> \
RESTORE_REPORT=/data/backups/sc_production/restore-rehearsals/<restore-id>.json \
RESTORE_ODOO_IMAGE=<immutable-odoo-digest-ref> \
RESTORE_POSTGRES_IMAGE=<immutable-postgres-digest-ref> \
CONFIRM_RESTORE_REHEARSAL=YES_RUN_ISOLATED_RESTORE_REHEARSAL \
make production.restore.rehearsal
```

演练比较关键表计数、附件抽样和 filestore 内容摘要，并记录 RTO 与
`external_write_side_effects=0`。失败报告保留且不自动重试。资源清理由单独的
精确确认入口按报告中的固定资源清单执行。只有安装、三联备份和恢复演练全部
通过后，才允许 `production.backup.timer.restore` 恢复安装前已启用的等价调度；
安装前未启用时必须另行决定调度。

## 共置参数初始化

仅在备份成功后，通过受控 Odoo 配置模型写入；禁止 SQL 手工修改：

```bash
SC_COLOCATED_PLATFORM_CONFIG_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION \
PLATFORM_RELEASE_DB=sc_production TARGET_DB=sc_production \
make release.production.platform.configure
```

重复执行必须返回 `changed=false`。已有其他数据库值时失败关闭。

## 活动发布快照初始化

仅使用当前库中受版本控制的活动 `sc.product.policy` 和现有 `EditionReleaseSnapshotService`：

```bash
SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY=I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION \
PLATFORM_RELEASE_DB=sc_production TARGET_DB=sc_production \
PLATFORM_RELEASE_PRODUCT_KEY=<approved-product-key> \
PLATFORM_RELEASE_VERSION=<approved-version> \
make release.production.platform.snapshot.initialize
```

相同产品、版本和策略指纹重复执行不得创建新快照。错误数据库、缺少策略、预检阻塞或参数冲突均停止。

## 验收与回滚点

- 运行 `production_menu_release_gate_guard.py`、完整 103 项 HttpCase、45 请求数据库安全矩阵和 `make ci`。
- 确认只有 `sc_production` 连接、无 `sc_platform_core`/随机库连接、无 HTTP 500。
- 确认活动快照、策略、登录路由、附件和业务计数与批准证据一致。
- 回滚点是参数/快照写入前的不可变成对备份和旧镜像 digest。若验证失败，停止候选，不切流；正式恢复必须使用单独授权和已演练的恢复路径。
