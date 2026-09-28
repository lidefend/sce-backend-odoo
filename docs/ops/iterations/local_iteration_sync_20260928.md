# 本地同步及未合并迭代收口（2026-09-28）

Formal Product Layer: P4. Layer Target: governed local Git synchronization and audit handoff.
Module: scripts/ops/gitee_published_branch_sync.py, make/codex.mk, existing iteration records.
Standard vs User-Specific: repository delivery mechanism. Why here: local refs and safe candidate
synchronization are delivery tooling; no P0–P3 product behavior belongs in this change.
Blast Radius: local main ref and explicitly selected candidate only; no push, database, runtime
or deployment changes from synchronization. Current base: `22ee5391b0dd543af1c75f7aff4e1d63d1c1650b`.

## 保全与分类

当前工作树从精确 Gitee main 新建 `fix/local-iteration-sync-20260928`，原分支均保留。
另一个登记工作树 upgrade-compat 为 clean detached `28266e9b`，未写入。

| 分支/来源 | 本轮处置 |
| --- | --- |
| PR #30 源分支 `1c89d604` | 与 squash main 文件树完全一致，非遗漏，不重复合并 |
| `audit/r7r9-registry-reconcile-20260928@1048f298` | 权威 registry.yaml 已与 main 一致；不引入旧导出报告 |
| `fix/settlement-worksheet-action-scope@e8e73d9d` | 代码目标被主线 `20e2956d`/`272b05be` 更完整替代；旧代码会丢动作域 AND 条件/context/model_field，不搬运 |
| `fix/gitee-unpublished-branch-sync@45350e9d` | 重放其 6 文件有界工具增量；保留主线后续 Make/文档新增内容 |
| `audit/formal-entry-gap-intake@28d2e05e` | 恢复 3 历史交接件，给现有缺口记录追加导航；不声称产品已实现 |
| `feature/gitee-orm-restricted-channel@00bcf7c8` | 15 文件真实残差保留原分支；身份和环境前提阻断，不能直接合入 |
| 其余历史本地分支 | head 为当前 main 祖先，无责任残差；不删除引用 |

## 同步机制

未发布候选使用既有同步模块的 `--allow-absent` 模式：成功读取远端证明同名分支不存在，
绑定 clean HEAD/main，追加 main 而不重写历史；恢复 bundle、冲突 abort 保持。
本地主线使用 `main.sync.gitee`，要求精确旧 main、新 main、当前合规分支/HEAD，拒绝 dirty、
非快进及其他 worktree 占用 main；CAS 快进本地 main，保持当前专题工作树与远端不变。
不改 GitHub origin 或原 main.sync；不伪造远端跟踪配置。
拒绝 symbolic main 并使用 --no-deref；CAS 防 ref 漂移，worktree 占用检查仍依赖仓库单写入者约束，
不宣称可防任意并发 checkout。preview 的 writes=0 指不写目标分支，fetch 会更新本地 Git 元数据。

## 验证与证据

风险：P4 有界本地 ref 写入。L0 身份及历史差异检查先行；L1 iteration，L2 现有同步单元
24 项通过，覆盖预演/成功、dirty、漂移、占用、分叉、符号引用、确认与冲突恢复。L3/L4 业务环境、浏览器、ORM
不运行：没有产品或运行时输入变化。发布仍需 clean 候选、独立审查、公开范围检查和最新远端四项。
原始执行结果在仓外单一 result-index，不能继承 PR #30 的远端成功。

## ORM 后续的真实阻断

旧实现的 orm_request 和 verify --sha 绑定 base_sha，不能证明 PR head；旧 executor 还会覆盖
PR #30 的前端复用、pnpm 隔离和 .git 只读修复。orm_gate 尚需计划及平台接线。
历史环境记载容器运行时停用及资源不足，不代表今天已恢复；本轮未启动服务或创建数据库。
需独立 P4 批次先澄清/修复目标身份和接线，再验证受管环境前提、成功/拒绝回传与清理，
不得用“安装脚本存在”宣称通道可用。

回退：专题增量可回退；本地 main 的旧 SHA 及工具回读存入仓外证据，旧历史仍是新 main 祖先。
批次、主线集成、部署和产品验收分别记录；本轮不代表 89 入口交付。
