# 历史分支资产退役准备（2026-09-11）

## 当前结论

状态为 `RETIREMENT_DELIVERY_IN_PR`。本批完成受管入口、12 项精确 manifest、恢复 bundle、历史证据归档及两个独立技术任务的价值路由；exact-manifest 退役已获授权，但必须等待 PR #462 的 exact-head 独立审查、必需 CI、合并和 main 同步完成，**当前尚未删除任何本地或远端引用**。

- 基线：`main@3c5b048075181e15c046fd172031413c9d6952bb`
- 工作分支：`audit/historical-branch-asset-retirement-v1`
- 退役入口提交：`e16cbcbe45ccbb4ec2b5513b53ba5adbd511d879`
- 历史证据归档提交：`2207f6bfa3e82368c7de0b5f3242c5b20f0035a3`
- Formal Product Layer：P4；Layer Target：受管历史 Git 引用退役与证据保存；Module：`scripts/ops`、Make、`docs/ops`。
- 排除：P0/P1 产品恢复、数据库、fixture、迁移、发布、收入合同页面和旧业务流程。

## 12 项退役清单与预演

权威清单：`docs/ops/manifests/historical_branch_retirement_20260911.json`；SHA-256：
`cac22ce59dbabf3ce9eb77dcf356d7dc55b8c545473f2562f73d854e7bb754a7`。

| 本地引用 | 本地 SHA | 远端状态 / SHA | 预演 |
| --- | --- | --- | --- |
| `feature/native-view-action-semantics-closure-v1` | `8db4e92a9648a1271751faa06b3b4bf9b5b20bf4` | present `9de00a9b28e5d4da68badeabd7c32fcedd49486b` | eligible |
| `fix/scene-entry-runtime-blocks` | `85711cb7336aff30ebb84fbf862de7e475fde24b` | present `a1906e3bf3a69ea0c0637489528561b60f522a97` | eligible |
| `fix/canonical-navigation-container-promotion` | `85711cb7336aff30ebb84fbf862de7e475fde24b` | present `85711cb7336aff30ebb84fbf862de7e475fde24b` | eligible |
| `fix/p4-governed-branch-sync-bootstrap-v1` | `e71146ed1518436e1191ef5e69b85b27adc00932` | present same SHA | eligible |
| `audit/form-structure-baseline-evidence-v1` | `59bcba6febacdca3bfd18e3445ca18922b8183ec` | absent | eligible |
| `feature/p0-official-design-system-alignment-v1` | `a3891a86b17500d037d02996f146043e8f6d0548` | absent | eligible |
| `feature/p0-overlay-lifecycle-convergence-v1` | `78bc9494fd5a7b6d7db5805ca17fb0fa7a0a2afa` | absent | eligible |
| `fix/p0-native-inline-text-presentation-semantics-v1` | `47d6d053c8bb4e6cf08e7cb5182f14d302121eff` | absent | eligible |
| `feature/demo-mainline-alignment-clean` | `c8a8ef29a3fa50628b76a98fbf6fdc86aa4894c8` | absent | eligible |
| `fix/p4-candidate-label-dispatch-idempotency-v1` | `9ebb6d81d843eb7e83f5aef536195de11210074b` | present same SHA | eligible |
| `fix/superseded-pr-retirement-v1` | `307c7ed1d2f83c6fa8d31b193b07127c1b146aed` | absent | eligible |
| `audit/project-profile-mainline-closure-v1` | `9008b81514bb8d00efa2d58352a344b145f5a132` | present same SHA | eligible |

真实仓库 dry-run 为 12 eligible、0 skipped。入口默认 dry-run；apply 必须同时匹配 manifest SHA-256、确认短语和后续明确授权。SHA 漂移、工作树占用、开放 PR 或关联工作证据不可用均跳过，远端不存在不会被推断为同名删除。

## 恢复包

- 路径：`/home/lidefend/workspace/sce-backend-odoo-historical-recovery/historical-branch-retirement-cac22ce59dbabf3c.bundle`
- bundle SHA-256：`d58b5e56ae423e6607efaa404663cd8676cc8275bd09fd97b5c331447d313a9c`
- `git bundle verify`：PASS，complete history。
- advertised heads：18（12 个本地身份，外加 6 个明确存在的远端身份）。
- 每个恢复头位于 `refs/codex/historical-retirement/cac22ce59dbabf3c/{local|remote}/<full-branch-name>`；逐项恢复命令见 `docs/ops/historical_branch_retirement_runbook.md`。

最终修复提交 `70b5054ee154dd2f482e4d6cc35d6d8696ddf43b` 的 11 个非零临时仓库测试 PASS：原 8 项覆盖默认预演、SHA 漂移、开放 PR/工作树占用、远端缺失、未授权 apply、关联工作证据不可用、恢复包不完整和远端部分失败；新增 3 项覆盖报告目标不可写时零删除、执行中结果落盘失败后停止后续删除，以及全部跳过时不创建空 bundle 并输出 `not_executed`。正常退役测试同时核对最终原子报告为 `completed`。真实仓库没有用于测试删除行为。

apply 现在要求显式报告路径：首个删除动作前实际创建、写入、flush 并 `fsync` 同目录临时文件；bundle 验证后先原子落盘准备态，并在每个引用删除前落盘 `in_progress` 写前记录。结果记录失败会立即停止后续引用，最后一份 durable report 保持明确的未完成状态。

上下文 lint/verify、docs inventory、temp guard、contract sync 均通过。`verify.docs.links` 在标准 `ENV=dev` 基线（允许既有最多 200 项）下以 81 项通过；同一工作树在未声明环境且阈值为 0 时如实失败 81 项。本批没有新增这批绝对路径/旧相对路径坏链，也没有降低或修改链接规则。

## 四个保留分支与三个任务

| 分支 | 处置 | 承接状态 |
| --- | --- | --- |
| `audit/frontend-mainline-landing-closure-v1@18f5ce3781834a7486c3b17f4ff76ceaffb56382` | 保留 | #455 有效事实已进入统一归档；归档合入主线后进入下一份退役清单 |
| `audit/frontend-expression-mainline-acceptance-v1@a87ebe893376aad5464c0aa3cf469dc9b787e374` | 保留 | #456—#459 有效事实已进入同一归档；归档合入主线后进入下一份退役清单 |
| `feature/payment-execution-canonical-workflow-validation-v1@3f86732124b23096b847a044a2c89d1ec1283151` | 保留 | 当前通用 P0 缺口已由诊断确认；等待独立 P0 批次提取最小 resolver/反例测试，不恢复付款或 demo 内容 |
| `feature/demo-mainline-alignment@113ad564a05df3c367b5ffa4ef9412230df6026b` | 保留 | 控制器 checkpoint 恢复已登记独立 P4 待办；尚未实施，旧 demo/browser 内容不提取 |

统一历史证据文件：`docs/ops/iterations/frontend_expression_historical_evidence_archive_20260911.md`。它实时核对了 #455—#459 的 PR/合并/四项 CI；历史浏览器 artifacts 当前缺失，因此候选样本与哈希明确保留为源报告事实，没有冒充重跑。

## Workflow authority 诊断

当前 `workflowContract.ts` 的可执行诊断得到：合法唯一布尔行保持 enabled；重复执行身份仍 enabled；载体含畸形行时畸形行被过滤且匹配动作仍 enabled；`enabled: "yes"` 被当作 enabled。故通用 fail-closed 缺口确认存在，但本 P4 分支未修改产品代码。

合法唯一性边界定为：一个可执行动作按 exact method、exact action key 与声明 alias 的匹配并集必须恰好命中一行；多行即使值相同也属于歧义。畸形载体只应阻断它声称管理或已知的流程动作，不能禁用真正无关的非流程动作。后续独立 P0 任务只提取这一通用机制和非零反例测试，不引入付款模型特例。

## Controller checkpoint 恢复待办

当前 `scripts/ops/codex_agent_controller.py` 在 `FAILED_RECOVERABLE` 重启路径仍调用 `initial_prompt`。旧提交可复用的仅是 `checkpoint_context_prompt`、`restart_from_checkpoint_prompt`、`fallback_recovery_result` 设计；新任务必须绑定 checkpoint 身份和已完成写入边界，证据缺失时失败关闭，禁止重复执行已完成写操作。本轮仅登记，不实施。

## 下一步与授权边界

下一步仅是：完成 PR #462 的 exact-head 独立审查与必需 CI，合并并同步 main；随后以已授权 manifest SHA-256 `cac22ce59dbabf3ce9eb77dcf356d7dc55b8c545473f2562f73d854e7bb754a7` 重新核验身份、开放 PR、工作树和恢复 bundle，再执行清单。漂移项逐项跳过，不扩大到四个保留分支或任何未列引用。
