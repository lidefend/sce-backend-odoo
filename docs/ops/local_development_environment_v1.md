# Local Development Environment v1

本地研发固定为三个完全独立的生命周期单元。该约定只服务研发与回归，不改变正式
租户架构，也不允许将任一本地数据库直接提升为生产数据库。

| 用途 | Compose project | Database | HTTP | 数据策略 |
| --- | --- | --- | --- | --- |
| 新功能持续迭代 | `sc-local-dev` | `sc_dev_demo` | `http://127.0.0.1:18081` | 常驻，demo 随当前功能升级 |
| 历史业务样本兼容 | `sc-local-sample` | `sc_dev_sample` | `http://127.0.0.1:18084` | 按需从日常环境恢复，不承诺新功能配置齐全 |
| 干净安装回归 | `sc-local-clean` | `sc_clean` | `http://127.0.0.1:18083` | 无 demo/fixture，可显式销毁重建 |

三套环境使用独立 PostgreSQL、Redis、Odoo filestore/session 卷和精确 dbfilter。
`sc_dev_sample` 的销毁操作受现有 guard 保护；`sc_clean` 的重建还要求确认短语。

`sc_dev_demo` 是新功能开发的唯一常驻本地产品库。代码改变功能事实时，配套 demo 必须同步
升级并由该库验证，不能依赖历史业务记录碰巧满足新前置条件。
首次重建时，Make 会在固定 0600 `.env.dev` 中生成独立随机 demo 用户密码；原文不进入日志。
后续重建复用同一凭据，禁止复用 JWT、bootstrap 或数据库密码代替。
模块增量升级后使用 `local.dev.sync_demo` 幂等同步当前 demo；只有需要从空库重建时才使用带
精确确认的 `local.dev.rebuild_demo`。

`local.dev.sync_demo` 必须在既有领域不可变规则下幂等执行，并在 `local.dev.verify_demo`
未通过时失败关闭。生命周期脚本只能准备身份、凭据、服务和调用既有 demo profile；若失败
源于缺少税种、审批方案或其他产品样本，应登记到对应 P1 demo/fixture 责任层，禁止在 P4
Make、Compose 或恢复脚本中伪造业务数据绕过。

`sc_dev_sample` 是按需兼容检查用的技术样本库，不是 demo fixture 库，也不是发布验收权威。
它可以由日常开发服务器的 paired backup 恢复，保留可供浏览和联调的业务关系；但不保证
自动包含新功能所需的最新字段、配置、审批方案或测试夹具。涉及 schema、视图、安全规则或
业务配置变化时，仍必须先执行目标模块的受控升级，再按专项合同准备测试数据。

## 日常入口

```bash
make local.env.status
make local.dev.up
make local.dev.ps
make local.dev.logs
make local.dev.upgrade MODULE=smart_construction_core
make local.dev.frontend
make local.dev.frontend.watch
make verify.local.dev.frontend.quick.gate
make verify.local.dev.payment_request.native_parity.readonly
make verify.local.dev.payment_request.settlement_component.journey
make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestP1PaymentRequestCapability'
make local.dev.sync_demo
make local.dev.verify_demo
make local.dev.contract_snapshot
CONFIRM_LOCAL_DEV_DEMO_REBUILD=REBUILD_CURRENT_FEATURE_DEMO make local.dev.rebuild_demo
make local.dev.down
make local.dev.snapshot
make local.sample.prepare
make local.sample.up
make local.sample.logs
make local.sample.snapshot
make local.sample.health
make local.sample.down
CONFIRM_LOCAL_DEV_SAMPLE_DISCARD=DISCARD_LOCAL_TECHNICAL_SAMPLE make local.sample.discard
make local.clean.prepare
make local.clean.up
make local.clean.logs
make local.clean.frontend
make local.clean.install LOCAL_CLEAN_MODULES=sc_norm_engine
make local.clean.health
make local.clean.down
```

当持久样本库损坏或明确需要从日常开发服务器刷新时，先用日常环境的 governed paired
backup 取得 `database.dump + filestore.tar.gz + manifest.json + SHA256SUMS`，下载到
`/home/lidefend/workspace/.secure/local-dev-refresh/sc_demo-<timestamp>-<id>/`，然后仅在固定目标卷
不存在时执行：

```bash
CONFIRM_LOCAL_DEV_SAMPLE_RESTORE=RESTORE_VERIFIED_DAILY_SAMPLE \
  make local.sample.restore \
  LOCAL_DEV_SAMPLE_BACKUP_DIR=/home/lidefend/workspace/.secure/local-dev-refresh/sc_demo-<timestamp>-<id>
```

该入口验证来源哈希和 manifest，恢复为 `sc_dev_sample`，重命名 filestore，生成独立本地
database UUID，并在首次启动 Odoo 前禁用本地 cron 与外发邮件服务器。若固定目标卷已存在，
入口失败关闭；必须先创建 `local.sample.snapshot` 并另行归档，禁止就地覆盖。确认归档后，
技术样本只能通过下列固定入口销毁，再重新执行 restore；禁止手工删除容器或卷：

```bash
CONFIRM_LOCAL_DEV_SAMPLE_DISCARD=DISCARD_LOCAL_TECHNICAL_SAMPLE make local.sample.discard
```

只有需要验证全新安装或升级幂等性时才重建干净环境：

```bash
CONFIRM_LOCAL_CLEAN_REBUILD=REBUILD_ISOLATED_REHEARSAL \
  make local.clean.rebuild LOCAL_CLEAN_MODULES=sc_norm_engine
```

`.env.dev`、`.env.local.sample` 与 `.env.local.clean` 都由主工作树作为唯一凭据权威保存。
所有链接工作树必须调用上述 `local.dev.*` / `local.sample.*` / `local.clean.*` 入口，不得在各工作树生成同名凭据文件，也不得手工组合
Compose project、数据库、卷或端口。若 clean 凭据文件缺失但固定卷仍存在，普通 prepare/up
必须失败关闭；只有受控 rebuild 可以生成新凭据并立即重建该隔离演练环境。

链接工作树执行完整 Frontend Quick 时必须使用
`make verify.local.dev.frontend.quick.gate`。该入口仅通过 Git common-dir 解析主工作树的固定
`.env.dev` 权威，拒绝调用者覆盖、软链接、非 `0600` 权限、错误 owner 或错误 `local.dev`
身份；它不会在链接工作树复制、生成或链接凭据文件。普通
`make verify.frontend.quick.gate` 的默认语义保持不变。

所有本地入口会先清除父进程继承的 project、database、dbfilter、volume 与 port 身份，再从
对应的权威 env 文件重新装载。不得通过 shell export 覆盖身份，也不得直接调用嵌套 Make、
Compose 或底层脚本。`down`/`logs` 不隐式创建凭据或资源；`up`/`health`/`test`/`upgrade` 会先
验证其固定生命周期单元已经准备完成。

`local.dev.snapshot` 同时保存 PostgreSQL custom dump 与对应 filestore，并生成 SHA-256
清单。产物位于 `artifacts/local-dev/snapshots/`，不进入 Git。

`local.dev.contract_snapshot` 使用同一固定 `sc-local-dev / sc_dev_demo / ^sc_dev_demo$`
身份调用既有 `contract.export_all`，用于功能迭代后的契约快照刷新。禁止通过通用
`codex.snapshot` 手工覆盖 Compose project、数据库或凭据来替代该入口。

`local.dev.frontend.watch` 是受管的 Vite HMR 入口。它固定复用 `.env.dev` 的
`sc_dev_demo` 与 `ODOO_PORT` 身份，在 `127.0.0.1:5174` 上启动开发服务器，并统一
注入 HMR host/client port、严格端口和缓存目录；`local.dev.frontend` 仍然只负责
静态构建，不替代热更新迭代。

## 研发节奏

1. 在 `sc_dev_demo` 上增量升级目标模块、同步 demo 并做浏览器迭代。
2. 需要验证历史业务关系兼容时，才恢复并启动 `sc_dev_sample`；它不替代 demo 合格证据。
3. 涉及安装、schema、迁移或导入幂等性时，在 `sc_clean` 做干净回归。
4. 本地验收通过后才进入日常开发服务器，后者只承担正式部署前的最终验证。
5. 镜像仅在候选发布阶段构建；本地通过源码挂载与增量前端构建迭代。

## 证据通道硬隔离

日常产品迭代只允许使用本页登记的 `local.dev.*` 入口和
`verify.local.dev.*` targeted tests。它们绑定 `sc-local-dev / sc_dev_demo /
18081`，产物只能作为开发迭代证据，不能称为 release snapshot、发布候选
或最终验收证据，也不能据此执行 `make pr.push`。

只有产品结果已经确定并明确进入最终验收，才能关闭日常写入、冻结 HEAD，
并单独执行：

```bash
CONFIRM_FRONTEND_RELEASE_AUDIT=RUN_FROZEN_FRONTEND_RELEASE_AUDIT \
  make verify.frontend.release.local
```

该入口绑定独立的 `sc_frontend_acceptance` 身份域。若正式审计发现需要修改
产品，必须停止审计、返回 `local.dev.*` 完成新一轮开发；禁止一边修改一边
续写正式发布证据。
