# U-C3 发布台账核对

状态：已核对，主线兼容消费者由 44 更新为 42。

## 核对边界

- 发布基线：`main@3323fb49e41e6bf0851acfde0d3e9df2dafafd8f`（含 PR #484 squash 合入 `640e356d90b556642c84397ce3ac2c75c636184e`；源冻结候选 `48151d07b61c6f42bc74008c6c5762334e8fb5a3`，两者 Tree 均为 `aca2aad24c315a87029ecdc456f1ff90b7167b31`）。
- 核对来源：已合入的
  `docs/ops/iterations/uc3_document_native_lowcode_20260916.md`、#484 发布提交中的
  P1 XML（`views/core/document_admin_document_views.xml`、`data/document_admin_form_productization_contract.xml`、
  `data/policy_document_contract.xml` 及模型级镜像停用 function）与定向契约测试
  （`TestDocumentNativeLowcode`、`TestPolicyDocumentCapability`）。
- 本次只复核合入内容与已有交付记录，不执行 U-C3 Quick，不重跑浏览器验收，也不重造截图。
- 配置中心六包（PR #485）与验证提效（PR #486）不属于兼容消费者扣减口径，本次不扣减；本次核对范围仅限上述三笔合并涉及内容，不据此推断 89 入口无其他遗留问题。

## 两入口结果

| 入口 | action / view | 合入源码核对 | 已记录运行结论 | 台账处理 |
|---|---|---|---|---|
| 证书管理 | 666 / 1703 | 原生条件分组（办理主信息、证照信息、办理、来源追溯、说明/附件，含 `data-sc-anchor`）；配置 191 仅保留标题与 `native_semantic_surface`，无 sections；模型级 `…form_structure_generated` 经 function 写 `active=False` | 迭代记录登记页面通过与用户确认（含空来源章节修复定向自验） | 移除消费者 |
| 制度文件 | 862 / 1703 | 同一原生根表单条件分组（制度文件组、来源追溯）；配置 178 保留 `fact_authority`/`fact_type_authority`、标题与 `fact_type` 只读字段策略，无 sections | 迭代记录登记页面通过与用户确认；另一 action 隔离反例通过 | 移除消费者 |

这次扣减依据是两入口在发布源码中的实际结构退役与模型级镜像停用，以及已合入迭代记录中的页面验收结论；PR 合并状态本身不作为扣减依据。两项均满足后，主线剩余由 44 扣减为 42。

## 证据限制

- U-C3 原始日志与浏览器证据保留于 `artifacts/uc3-document-lowcode/`（未如 UC1 清理而失效），本次不重复执行；不把 CI/PR 状态描述为原始浏览器证据，也不以新截图替代原候选证据。
- 借阅/公司资料存档共用 action 级配置保持 `entry_semantic_surface`，为有意保留的共用反例，不计入本批扣减，也不扩为新增正式入口。
- 制度查看、合法业务草稿编辑、多角色浏览器等未覆盖项按 U-C3 记录原义保留，不因本核对升级为已覆盖。
- action 777 保持原「环境阻断、未通过」状态，本次没有探测或改写。

## 台账字段变更

- `entries` 移除 666/862 两项，`count` 与 `mainlineRemainingCount` 44→42；`localVerifiedCount` 维持 42。
- `uc3LocalMigrationAudit.status` 由 `…integration_pending` 更新为 `mainline_integrated`，`reduction.mainlineRemaining` 同步 42。
- 新增 `uc3PublishedAudit`：绑定 `auditedReleaseHead=3323fb49…`、#484 源/合并/Tree 身份、扣减 44→42、源码核对三项结论、原始证据位置与不重跑声明。
- `nextBatch` 计划字段（selectedGroup/priorityActions 等）仍指向 G01，属 U-C4（G02 发票组）批次记录负责更新的内容，本核对不越权改写。
