# Frontend acceptance fixture 命名空间重建设计

日期：2026-09-09

状态：设计完成，未实现、未执行；任何数据库或 filestore 清理仍需独立授权。

## 1. 目标与边界

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：受管 frontend acceptance fixture 生命周期。
- Module：未来的 Make 入口、`frontend_acceptance_operation_entry.sh` 操作和 `smart_construction_acceptance_fixture` 精确清理器。
- Standard vs User-Specific：平台内部验收治理，不是 P1 行业事实、P2 客户数据或 P3 配置。
- Why Here：人工 fixture 应由其生成器和命名空间控制生命周期；旧 fixture 不应迫使产品增加历史迁移。
- Why Not Elsewhere：不得放宽 P1 的付款与资金基线约束，不得让前端或现有 fixture upsert 猜测历史事实，也不得手工组装数据库命令。
- Blast Radius：仅允许作用于注册 profile `sc-fe-r2-p1-01`、数据库 `sc_frontend_acceptance`、dbfilter `^sc_frontend_acceptance$` 及其绑定 filestore/session；不得触达 `local.dev`、`local.sample`、`local.clean`、UAT、客户租户或生产。

本设计不创建新数据库、Compose project、端口、volume、credential file、fixture 体系或临时测试入口。

## 2. 默认策略

默认执行命名空间重建，而不是整库重建：

1. 通过既有受管 preflight 核对 project、database、dbfilter、volumes、credential authority、filestore 与当前写入租约。
2. 从 `ir.model.data` 中解析 `smart_construction_acceptance_fixture` 拥有的 XMLID，并由版本化清理清单补充浏览器产生但没有 XMLID 的、带稳定 fixture 来源关系的记录。
3. 在删除前计算反向引用闭包；任何非 fixture 记录引用目标时 fail closed，输出模型、记录 ID 和引用字段，不自动扩大删除范围。
4. 按子记录到父记录的确定性顺序清理数据库记录及其 fixture-owned attachments；共享用户、公司、产品字典、非 fixture 附件和审计事实不得按名称或通配符删除。
5. 运行当前候选的模块安装/升级，再运行当前版本 fixture 生成器；生成器负责产生完整一致的当前状态，不修订旧人工基线来模拟历史兼容。
6. 验证 XMLID 唯一性、记录计数、外键、附件/filestore 一致性、角色/公司绑定和 fixture 二次执行稳定性；零测试、跳过或残留引用均为失败。
7. 生成绑定 exact HEAD、完整候选指纹、清理清单哈希和运行身份的外部证据；只有成功后才能生成 release snapshot 和运行浏览器验收。

整库重建只在另一次明确授权中允许，并必须先证明该 database、filestore、sessions 和全部记录均为可丢弃的隔离验收资产。模块卸载不等于 fixture 清理，也不得作为替代方案。

## 3. 接口草案

未来实现应沿用现有命名，不直接执行以下草案：

```text
make acceptance.frontend.fixture.namespace.audit
make acceptance.frontend.fixture.namespace.rebuild \
  APPLY=1 \
  EXPECTED_HEAD=<40-char-sha> \
  EXPECTED_DATABASE=sc_frontend_acceptance \
  CONFIRM=REBUILD_FRONTEND_ACCEPTANCE_FIXTURE_NAMESPACE
```

`audit` 必须只读；`rebuild` 必须拒绝缺少完整 SHA、错误 profile、并发写入者、非空未知引用、服务身份漂移或未确认 destructive phrase。底层数据库、Compose 和凭据只能由受管操作入口解析。

## 4. 当前运行态处置

现有 `sc_frontend_acceptance` 已执行撤出前端候选的 `smart_construction_core` `.163/.164`，不能通过降 manifest 或逆向 SQL 恢复。当前页面候选恢复为 `17.0.0.162`，因此在命名空间重建能力完成并获授权前：

- 不运行 `db.frontend.acceptance.ensure`、fixture reset、release snapshot 或正式浏览器 gate；
- 不把旧 snapshot、旧数据库 PASS 或 `.164` 环境结果绑定到当前候选；
- 保留此前报告和外部 artifact 作为历史执行证据，不作为当前验收结果。

## 5. 独立 P1 兼容候选

`.163/.164` 是否交付应由独立 P1 任务决定。最低证据必须包含明确支持的源版本矩阵，以及授权脱敏历史副本或从该版本正式 schema/载荷构造的升级样本。当前 ORM 人工构造测试只能证明迁移算法，不足以声明客户历史升级通过。

## 6. 回滚

本文件仅为设计，没有运行时回滚。未来实现必须在清理前生成数据库与 filestore 同一身份的可恢复备份，并证明失败时能够整体恢复；禁止仅恢复数据库或仅恢复附件目录。
