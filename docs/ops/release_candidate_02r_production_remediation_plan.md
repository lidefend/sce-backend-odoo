# RELEASE-CANDIDATE-02R 生产整改方案

英文版：[release_candidate_02r_production_remediation_plan.en.md](release_candidate_02r_production_remediation_plan.en.md)

## 边界

本方案只固化下一次生产操作的顺序和门禁，不授权或执行生产连接、Git
修改、容器变更、数据库写入、备份写入或部署。旧 `rc.1` 及其 archive、
manifest、scan 和 checksum 继续只读保留，不得覆盖、删除、retag 或提升为生产制品。

唯一正式目标为：

```text
PRODUCTION_COMPOSE_PROJECT=sc_production
PRODUCTION_DATABASE=sc_production
LEGACY_TARGET=sc_prod (forbidden)
```

## 授权前必须形成的精确执行包

操作员须先提交以下只读结果，由发布负责人明确批准后才能生成本次发布窗口备份：

1. `sc_production` PostgreSQL 实例、数据库和唯一对应 filestore 的解析结果。
2. 当前 Odoo/Nginx 容器、健康状态、不可变镜像 digest，以及其 release manifest；
   manifest 缺失时须给出可验证的替代身份记录，不能用 tag 推断 digest。
3. 上一可运行版本的 Odoo/Nginx digest 集合、manifest 和精确回滚 Compose 输入。
4. 数据库实际大小、filestore 实际大小、备份目录可用空间。最低空间预算为
   `数据库逻辑备份估算 + filestore 归档估算 + 25% 校验/临时余量`，并须保留现有备份。
5. 新恢复点名称，格式
   `sc_production-release-<UTC YYYYMMDDTHHMMSSZ>-<source SHA 前12位>`；禁止复用已有目录。
6. 将要执行的完整命令清单（凭据仅使用引用，不输出内容）、预计写入路径、
   预计持续时间和停止条件。

`.incomplete-*` 目录和 2026-07-22 历史备份均不得作为本次发布窗口恢复点。

## 经单独生产授权后的执行顺序

1. 再次确认唯一目标为 `sc_production`，且所有 `sc_prod` 输入被门禁拒绝。
2. 在不切换版本的前提下诊断 Odoo/Nginx unhealthy 根因；记录日志时间窗、
   容器 digest、配置引用和只读健康探针结果。
3. 冻结一个恢复点时间窗，并在该窗口内生成成对资产：
   `database.dump`、`filestore.tar.gz`、配置引用快照、当前镜像 digest 和当前
   release manifest（或经批准的可验证替代记录）。
4. 对数据库与 filestore 文件计算 SHA-256，记录开始/结束时间、数据库身份、
   filestore 归属和文件大小；时间窗或归属不一致立即 BLOCKED。
5. 在隔离命名空间执行恢复演练。恢复命令必须指向新建的非生产数据库和隔离
   filestore，禁止覆盖 `sc_production`。
6. 验证恢复库可打开、关键表存在、filestore 引用可读、checksum 相等，并保留
   恢复命令和销毁隔离目标的受控步骤。
7. 只有健康根因已收敛、成对备份有效、恢复演练通过、上一版本回滚 digest/manifest
   可用后，才可请求候选部署授权。

## 后续发布顺序

本 PR 合并后锁定新的 `main` SHA，构建 `v1.0.0-rc.2`，执行完整扫描、manifest v2
生成及 artifact identity gate。生产整改和备份须绑定该 `rc.2` 发布窗口；通过前不得
创建 Git release tag、切换生产 Compose 或设置 `SC_PRODUCTION_CHANGE_APPROVED`。
