# 本地 `sc_dev_demo` 写租约（2026-10-20）

## 1. 问题

产品执行器和 demo 执行器共享固定 `sc-local-dev / sc_dev_demo`。`local.dev.upgrade` 原先没有
仓库级互斥，两个执行器可能同时改写同一数据库；这次只是执行时间刚好错开。

## 2. 机制

- 固定锁：`/tmp/sc-local-dev-sc_dev_demo.write.lock`。
- `flock` 独占租约；持有期间写 owner JSON（operation/pid/worktree/branch/head/started_at）。
- 默认等待 1800 秒；超时输出 `LOCAL_DEV_WRITE_LEASE_BUSY` 和当前持有者。
- `local.dev.upgrade`、`local.dev.sync_demo`、`local.dev.rebuild_demo` 自动串行化。
- 对应 `.run` 内部目标要求 `SC_LOCAL_DEV_WRITE_LEASE_TOKEN`，直接调用失败关闭。
- 其他写目标在迁移前通过 `scripts/dev/local_dev_write_lease.sh` 通用包装串行执行。

## 3. 验证

```bash
make verify.local.dev.write_lease.unit
```

结果：5 tests PASS；覆盖第二写者 75 失败、等待后获取、`--require` 拒绝直调、
租约内命令通过、生产 lock override 拒绝。

只读状态：

```bash
make local.dev.write_lease.status
```

## 4. 边界

- 不创建新数据库、Compose project、卷、端口或凭据。
- 不改变 `local.dev` 生命周期身份；锁只表达写入互斥。
- 不改产品代码；属于 P4 本地环境机制。
- 未自动串行化的写目标仍必须显式套通用租约，后续批次再迁移。

## 5. 回滚

回退本批 commit；锁文件位于 `/tmp`，不需要数据恢复。
