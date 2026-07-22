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

## 成对备份与校验

将 `scripts/release/production_colocated_backup.py` 和 `deploy/production-backup/` 模板安装到受控运维路径后，使用独立授权执行：

```bash
python3 /opt/ops/production_colocated_backup.py backup
python3 /opt/ops/production_colocated_backup.py validate --backup-dir <immutable-backup-directory>
```

脚本固定拒绝 `sc_prod` 等其他生产目标，为每次执行创建新的时间戳目录，不覆盖或删除旧备份，并验证数据库身份、非空文件、dump 目录和 SHA-256。备份必须同时包含 `sc_production` 数据库与其 filestore。

## 隔离恢复演练

恢复容器不得与正式 PostgreSQL/Odoo 容器相同；目标库必须使用 `r10e_restore_*` 且预先不存在：

```bash
RESTORE_DB_CONTAINER=<isolated-postgres> \
RESTORE_ODOO_CONTAINER=<isolated-odoo> \
RESTORE_TARGET_DB=r10e_restore_<run_id> \
python3 /opt/ops/production_colocated_backup.py restore-drill \
  --backup-dir <immutable-backup-directory>
```

演练比较业务表与 `smart_core` 平台表计数，并比较源/恢复 filestore 内容摘要。恢复目标已存在、容器未隔离或摘要不一致时立即停止，不得覆盖。

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
