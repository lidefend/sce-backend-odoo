# Local Development Environment v1

本地研发固定为两个完全独立的生命周期单元。该约定只服务研发与回归，不改变正式
租户架构，也不允许将任一本地数据库直接提升为生产数据库。

| 用途 | Compose project | Database | HTTP | 数据策略 |
| --- | --- | --- | --- | --- |
| 持续产品迭代 | `sc-backend-odoo-dev` | `sc_demo` | `http://127.0.0.1:18081` | 保留真实关系数据，只做增量升级 |
| 干净安装回归 | `sc-local-clean` | `sc_clean` | `http://127.0.0.1:18083` | 无 demo/fixture，可显式销毁重建 |

两套环境使用独立 PostgreSQL、Redis、Odoo filestore/session 卷和精确 dbfilter。
`sc_demo` 的销毁操作受现有 guard 保护；`sc_clean` 的重建还要求确认短语。

## 日常入口

```bash
make local.env.status
make local.dev.snapshot
make local.clean.prepare
make local.clean.up
make local.clean.frontend
make local.clean.install LOCAL_CLEAN_MODULES=sc_norm_engine
make local.clean.health
```

只有需要验证全新安装或升级幂等性时才重建干净环境：

```bash
CONFIRM_LOCAL_CLEAN_REBUILD=REBUILD_SC_CLEAN \
  make local.clean.rebuild LOCAL_CLEAN_MODULES=sc_norm_engine
```

`local.dev.snapshot` 同时保存 PostgreSQL custom dump 与对应 filestore，并生成 SHA-256
清单。产物位于 `artifacts/local-dev/snapshots/`，不进入 Git。

## 研发节奏

1. 在 `sc_demo` 上增量升级目标模块并做浏览器迭代，不为纯后端或纯前端改动运行无关 CI。
2. 涉及安装、schema、迁移或导入幂等性时，在 `sc_clean` 做干净回归。
3. 本地验收通过后才进入日常开发服务器，后者只承担正式部署前的最终验证。
4. 镜像仅在候选发布阶段构建；本地通过源码挂载与增量前端构建迭代。
