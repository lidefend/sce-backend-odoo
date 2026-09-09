# Frontend acceptance 基线恢复设计与预演

日期：2026-09-09

状态：恢复路径已选定，受管 audit/dry-run 已实现并通过；尚未执行任何删除、覆盖、fixture 或 release gate。

## 1. 边界

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：受管 frontend acceptance 完整生命周期恢复。
- Module：`make acceptance.runtime.baseline_recovery.audit`、`make acceptance.runtime.baseline_rebuild` 及既有 acceptance profile/operation entry。
- Standard vs User-Specific：平台内部验收治理，不是 P1 行业事实、P2 客户数据或 P3 配置。
- Why Here：当前源码为 `smart_construction_core 17.0.0.162`，持久化 acceptance 数据库已执行 `17.0.0.163/.164`；fixture 清理和普通模块升级都不能降级 schema。
- Why Not Elsewhere：不恢复撤出的 P1 迁移，不用前端或 fixture upsert 掩盖版本差异，不为本轮建设通用命名空间清理框架。
- Blast Radius：只允许 profile `local` 的 project `sc-fe-r2-p1-01`、数据库 `sc_frontend_acceptance`、dbfilter `^sc_frontend_acceptance$`，以及三个精确卷 `sc_fe_r2_p1_01_db`、`sc_fe_r2_p1_01_redis`、`sc_fe_r2_p1_01_odoo`。

## 2. 只读盘点结论

受管 `make acceptance.runtime.preflight` 和新 audit 入口确认：

| 项目 | 结果 |
| --- | --- |
| 数据库角色 | `platform_internal_acceptance`，fixture allowed，customer business data forbidden |
| 当前模块版本 | `smart_construction_core=17.0.0.164` |
| 数据库 | 319315303 bytes；17 users；552 attachments；78 fixture XMLIDs |
| filestore | 125147442 bytes；421 files |
| session | Redis 0 keys |
| `.162` 完整备份 | 仓库、已登记 off-repo artifact 目录及恢复目录均未发现 |
| 现有 restore 入口 | 仅重新挂载现有三个卷，不能恢复数据库版本 |

该环境由版本化 profile 明确限定为内部、合成 fixture acceptance，不允许客户业务数据；release checklist 也把它登记为 disposable P4 环境。虽然历史文档称其“persistent”，其含义是跨日复用，不是客户历史保存义务。数据库、filestore 和 session 必须作为同一个生命周期单元处理。

## 3. 唯一推荐路径

选择受管整环境重建，而不是命名空间清理或逆向迁移：

1. 校验 exact HEAD、clean worktree、profile、数据库/filter、三个卷和 credential authority。
2. 要求受管 frontend 与独立 backend carrier 已关闭，并持有 acceptance lifecycle lock。
3. 停止 Odoo 写入，生成当前 `.164` 数据库 dump、完整 Odoo volume archive 和 Redis volume archive。
4. 写入固定 off-repo recovery root，生成 SHA-256，使用 `pg_restore --list` 验证数据库备份可读。
5. 仅在精确 confirmation 下删除三个固定卷，并以同名 profile 重建空基础设施。
6. 破坏开始后任一步失败，脚本自动从同一 recovery bundle 恢复数据库、filestore 和 session；不把部分成功计为 PASS。
7. 重建成功后才执行既有 `db.frontend.acceptance.ensure`、fixture、snapshot 和 release gate。当前脚本不复制这些已有能力。

命名空间清理仍是数据库政策要求的长期 fixture 生命周期能力，但它不能解决 `.164 → .162`，因此不作为本轮恢复前置。

## 4. 已完成预演

当前 HEAD `92a50e59d7e712a0ab67a066d17a686c1dc8b43f` 上执行：

```bash
make verify.acceptance.runtime.baseline_rebuild.unit
make acceptance.runtime.baseline_recovery.audit
make acceptance.runtime.baseline_rebuild \
  EXPECTED_HEAD=92a50e59d7e712a0ab67a066d17a686c1dc8b43f
```

29 个非零单元/身份测试及 source guard PASS，audit 和 dry-run 均 PASS。dry-run 输出了精确 project、database/filter、三个卷、恢复包根目录和后续步骤；没有创建恢复包、停止 carrier 或写数据库。

最终提交后必须以新 exact HEAD 重新预演，旧 HEAD 不能授权实际执行。

## 5. 待单独确认的破坏性执行

以下只是未来执行序列，不是本报告的执行授权：

```bash
make frontend.acceptance.down
make backend.acceptance.down

CONFIRM_ACCEPTANCE_BASELINE_REBUILD=REBUILD_DISPOSABLE_FRONTEND_ACCEPTANCE \
  make acceptance.runtime.baseline_rebuild \
    APPLY=1 \
    EXPECTED_HEAD=<最终干净候选的完整 40 位 SHA>
```

执行前必须再次确认 `sc_frontend_acceptance`、三个精确卷及其全部内容可丢弃。成功结果必须给出 recovery bundle 的不可变路径；随后从最早失效门禁开始运行 current-source install/upgrade、fixture、snapshot 和正式 release gate。

## 6. P1 与回退

`.163/.164` 继续作为独立 P1 历史兼容候选冻结；本恢复方案不评价或删除其 Git 历史。

代码回退可移除新增 Make/operation/script/test。静态 inventory 可由原生成器重建。实际环境重建一旦开始，回退 authority 是执行前生成并校验的数据库+Odoo volume+Redis volume 成对恢复包，不是逆向 SQL 或删迁移文件。
