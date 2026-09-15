# Draft PR：投标中标事实确认与合同承接解耦

## Summary

本 PR 将“确认中标事实”与“生成收入合同”拆开：用户从正式投标入口明确选择中标开标记录，登记资料依据和税口径，系统冻结中标金额、币种、确认人及时间；确认动作不再静默选择报价/清单金额，也不创建合同。

同时修复两项通用契约消费问题：关系 occurrence 的原生 domain 不再被模型级空值覆盖，普通 client reload 不再制造缺少 menu 的导航目标。没有投标模型或字段名前端特判。

## User-visible improvements

- 投标表单保留基本资料、中标事实确认、清单明细、协作和审计的完整结构；中标确认字段集中、有独立导航，清单保持全宽。
- 仅能选择当前投标中结果为中标的开标记录；资料引用必填，税口径可明确为未知。
- 确认后只读展示正式中标金额、币种、确认人和时间，并明确“合同尚未生成”。
- 历史缺快照记录显示“来源待核实”，不自动回填。
- 来源记录后续变化不能静默改写已确认快照；重复请求不改变确认时间，也不创建合同。
- 系统快照字段不能通过普通创建或确认前写入伪造，只能由确认动作在完成业务校验后生成。

## Architecture Impact

Layer Target：P1 中标事实模型、P0 通用契约消费、P4 受管验证。

Affected Modules：`smart_construction_core`、`smart_core`、`frontend/apps/web`、`scripts/verify`。

- P1 `smart_construction_core`：中标事实模型约束、正式入口原生章节、动作与契约声明。
- P0 frontend/smart_core：通用关系 domain 保真、父记录 id 求值、安全字面量解析及 reload 入口保持。
- P4：仅 `sc-local-dev/sc_dev_demo` 的批次 fixture、浏览器旅程、清理和门禁说明。
- 不改合同计价、审批、权限、数据库架构政策、低代码载体或业务外壳。

## Verification

- 最终补修 `cb7c10681ae4334b1df66ae19f5cd6624c928631` 封闭 context / `ir.default` 默认值注入；全部 13 个 P1 方法通过，独立 B 线确认 S1 关闭。
- 新批次 `award-20260915j` 在上述同 HEAD 产品及工具上通过确认、回读、重复请求、刷新只读和精确清理，证据为 `artifacts/p4-tender-award/award-20260915j-cb7c1068/journey-summary.json`。
- 此次纯 Python 补修经受管 restart 加载；前端候选载体按新 SHA 重建。以下旧批次证据仅按受测文件影响分析复用，最终 Quick / CI 以最终冻结 HEAD 为准。

- `make ci.local.iteration`：16 tests，PASS。
- `make verify.local.dev.tender_award.unit`：7 个方法，PASS。
- 同步 `main@12f6256c…` 后，canonical form 162 cases、create journey、native section navigation、professional detail collection 与 collection view semantics 五组受影响前端 L2 均非零通过。
- P1 中标事实：选择并实际执行 11 个定向方法（Odoo 统计 13 项，含框架阶段），覆盖快照、归属、税口径、资料、历史、防重、不可变、创建/确认前快照字段注入拒绝与正式契约；0 failed、0 errors。
- P0 关系 domain：6-profile matrix、7 个 domain cases；对应 Python/guard 非零 PASS。
- P0 reload：navigation entry target 12 个纯测试 PASS。
- `smart_core` 受管增量升级、local.dev authority/restart：PASS。
- 产品样板：`tender-award-fact-2e5a0419-structure-recovery/summary.json`，桌面/移动，零写入，`pass=true`。
- 真实闭环：独立复核缺陷修复后的 exact-head 批次 `award-20260915i`，1200/1000/900，确认、权威回读、重复请求防重、刷新只读、未创建合同、精确清理均 PASS。
- 冻结前执行 `make ci.delivery.freeze.prepare`；最终 clean HEAD 只运行一次 `make ci.local.quick`，随后绑定同一 HEAD/Tree/完整指纹独立复核。

## Evidence

- 迭代报告：[tender_award_fact_confirmation_20260915.md](tender_award_fact_confirmation_20260915.md)
- 只读样板：`artifacts/playwright/tender-award-fact-2e5a0419-structure-recovery/summary.json`
- 最终受管闭环：`artifacts/p4-tender-award/award-20260915i-e98d29a1/browser/summary.json`
- 确认后权威回读：`artifacts/p4-tender-award/award-20260915i-e98d29a1/fixture-post-inspect.json`
- 清理及最终状态：`fixture-cleanup.json`、`fixture-final-inspect.json`（同目录）

## Boundaries

- 本 PR 不提供合同生成动作，不构造虚假合同明细，不向合同计算字段直接赋值。
- 不强制投标报价、清单合计、中标金额或未来合同金额相等。
- 不推断未知税口径，不批量回填历史数据。
- 浏览器写入仅使用受管开发 fixture；未执行生产写入、合同、审批、付款或开票旅程。

## Risk and rollback

这是业务动作与共享契约双层改动，风险由非零 P1/P0 定向测试及受管真实闭环控制。回滚按 P4 → P0 → P1 逆序；不能只撤共享 relation domain 后继续交付中标入口。

## Delivery status

源候选 `c5ee2944…` 已通过受管 extended 入口同步为 `f7286c9c…`；只刷新失效的生成证据并形成最终冻结 HEAD。候选具备受管远端交付授权；部署、发布与数据库操作仍不在范围内。
