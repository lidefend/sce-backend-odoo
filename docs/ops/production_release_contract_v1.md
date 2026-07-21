# 生产发布契约 v1

本文定义镜像构建和数据库生命周期控制，不构成部署授权。

## 不可变镜像输入

生产 Dockerfile 保留可读版本 tag，并以不可变 `sha256` digest 固定基础镜像。生产 Compose 同样按 digest 固定 PostgreSQL 与 Redis。构建必须使用 `EXPECTED_RELEASE_SHA` 指定的提交，最终 OCI revision label 必须与之相等。

更新基础镜像时，必须读取官方 registry manifest，选择目标平台（当前为 `linux/amd64`）的 digest，直接向 registry 验证 `repository:tag@sha256:digest`，再更新引用并执行 `make verify.production.release_contract` 和隔离镜像验收。不得仅依赖浮动 tag 或本地缓存推断 digest。Odoo 或 PostgreSQL 大版本变更必须另立兼容性任务。

## 数据库身份与存储

正式名称固定为：

- `sc_migration_rehearsal`：迁移演练库，绝非生产库。
- `sc_production`：新正式生产库。
- `sc_prod`：只读封存的旧练手库，永远不能作为初始化或升级目标。

每个目标库使用独立的 PostgreSQL、Redis、filestore、session、tmp 和 log 卷，名称为 `sce-<database>-<purpose>`。演练库与正式库不得共享 filestore。没有匹配 filestore 快照的数据库备份不是完整恢复点。

## 运行与管理入口分离

普通容器启动在确认显式目标库存在且已安装 `base` 前只执行只读检查。数据库缺失、不可达或未初始化时立即停止。普通启动永不创建数据库、安装/升级模块、恢复数据或加载 demo/fixture。

数据库生命周期命令严格独立：

```sh
# Safe templates only; secrets remain outside the repository.
TARGET_DB=sc_migration_rehearsal SC_ENVIRONMENT=migration_rehearsal \
EXPECTED_RELEASE_SHA=<40-char-commit> make release.production.db.preflight

TARGET_DB=sc_migration_rehearsal SC_ENVIRONMENT=migration_rehearsal \
EXPECTED_RELEASE_SHA=<40-char-commit> make release.production.db.init

TARGET_DB=sc_migration_rehearsal SC_ENVIRONMENT=migration_rehearsal \
EXPECTED_RELEASE_SHA=<40-char-commit> TARGET_MODULE=smart_construction_core \
make release.production.module.upgrade
```

还必须显式提供精确卷变量和候选镜像。`sc_production` 初始化或升级另需一次性确认 `SC_PRODUCTION_CHANGE_APPROVED=I_ACKNOWLEDGE_SC_PRODUCTION_CHANGE`，且镜像 revision 必须等于 `EXPECTED_RELEASE_SHA`。该确认值不得写入 Compose 或版本库。

生产配置设置 `list_db = False`、精确 `dbfilter` 和 `SC_ALLOW_DEMO_DATA=0`。即使调用方尝试启用 demo，`sc_production` 也拒绝 demo/fixture 模块。初始化始终使用 `--without-demo=all`。

## 发布与回滚边界

正式初始化或模块升级前，必须冻结写入并建立已校验的数据库/filestore 成对备份，验证 manifest 与 checksum，并完成另行授权的恢复演练。模块升级写入 schema 或元数据后，仅切回旧镜像不是完整回滚；必须按已批准方案恢复成对数据库和 filestore 恢复点。

本契约不授权部署、服务器变更、建库、数据迁移、附件封存或 Nginx/TLS 变更。
