# 验证交付机制与使用规范

本规范遵循 AGENTS.md 的阶段边界。交付工具归属 P4；不承载产品语义，不授权环境写入。

## 一份任务索引，三个既有证据职责

- `.agent/runs/<id>/run.json`：本批范围、定向检查、依赖关系、原始日志位置及下一步。`agent_run_context.py` 管理开发回执；不是交付通过凭证。
- `evidence_scope.py`：声明单元的 affected/reusable/blocked 唯一判定引擎。每项结果绑定实际输入与环境身份；浏览器或其他执行器只提供实际执行结果。
- `acceptance_evolution_binding_guard.py`：变更到正式验收套件的映射、证据格式、时效、输入指纹和完整性。正式证据仍通过 `acceptance.evolution.record` 登记。

`validation_delivery_plan.py` 只汇总以上权威，不另建缓存或证据台账，不执行测试或登录，不读取密码。计划写入 `.runtime/validation-delivery/plan.json`；该文件不是通过证据。

## 日常入口与顺序

1. `make agent.run.resume`：解析当前分支，检查任务范围。
2. `make ci.local.iteration`：L1，并自动输出交付影响计划。也可独立执行 `make ci.delivery.plan`；它包含已提交、暂存、未暂存、未跟踪路径及重命名两端。
3. 查看计划：全部缺失/失效的运行证据会一起列出，附登记的执行入口；在调用运行检查前，核对其受管环境、凭据注入、授权与恢复前提。计划不会声称这些外部前提已经验证。
4. 按风险执行非零 L2；需要时再进入受管 L3/L4。通过的未变输入直接复用；已知失败先修复责任输入或更新权威环境回读，不能无变化重试。
5. `make ci.delivery.freeze.prepare` 在生成报告前再次输出影响计划。dirty 阶段不要求伪造冻结证据；缺失的正式证据是明确待办，不能称为收口完成。
6. 清洁候选、审查、正式验收登记、Quick 与远端检查按所选车道执行。普通 Gitee 发布仍遵循 AGENTS 最新分工；本批未改变其授权与必需 CI。

## 开发检查依赖

run 中的每项检查可以声明 `depends_on: ["another_check_id"]`。引用必须存在且无环。

`make agent.run.begin AGENT_CHECK=<id>` 拒绝未通过/失效的前置项；记录时重新检查前置输入。
上游输入变化会使下游失效，即使下游本身文件没有变化。互不依赖的检查可继续执行，不要求整个批次重跑。

未变失败不能重新 begin；修改原因字符串不构成恢复。已通过且可复用的检查默认拒绝重复开始。
确有所有者要求或新验证目的时，可通过环境 `AGENT_REVERIFY_REASON=<具体原因>` 重新验证已通过项，原因会进入回执；此选项不能放行失败项。

这些限制约束受管 begin/record 入口，不声称能阻止直接手工执行任意测试命令。检查依赖必须完整登记；未声明的依赖不能由工具推断。

## 中断与增量

允许保存本次真正执行的部分结果，保留成功项与失败项。引擎重新计算并记录 `authoritative_affected` 和 `not_executed`，未执行项仍待办。
环境变更后，每项单独核对身份；更新台账头部不能把未执行旧项变成新环境通过。
旧台账首次追加时保留旧项原环境身份。全量收口仍要求无未覆盖项，部分落账不等于完整通过。

## GitHub 合并门禁

`make pr.merge PR=<n> EXPECTED_HEAD=<full_sha>` 的顺序为：

1. 读取真实开放、同仓、目标 main 的 PR source/base，核对本地精确 HEAD 与 clean 状态。
2. 直接以实际 source/base 计算全部必需套件并验证证据。`BASE_SHA`、`HEAD_SHA` 或调用者选择的基线不能缩减合并范围。缺本地目标提交时拒绝，先通过现有允许的同步入口恢复。
3. 前提通过后，才复用有效 Quick 或执行原有 Quick 后备路径。Make recipe 保证 `-j` 也不能并发越过前提。
4. Quick 后重新读取 source/base 并验证证据，漂移或证据改变即拒绝；随后沿用受保护 PR 合并及 head 绑定。

合并入口不再暗中记录证据；新证据先显式执行 `acceptance.evolution.record`。所有原始记录、哈希、套件适配器和时效检查保持。
此流程仍不是 source/base 原子锁：GitHub head 绑定和目标保护继续生效，最后回读与平台实际合并之间仍存在目标变化窗口，不能宣称原子自动合并。

## 验证体系自身的回归

定向检查分组登记，避免组合目标与子目标重复执行：

- `verify.validation.delivery.unit`：开发回执/DAG、PR 身份与顺序、部分失败适配；已接入 `verify.contract.architecture.suite`。
- `verify.frontend.business_entry.evidence_scope.unit`：增量引擎、实际调用适配器和 Node 身份测试，独立记录、独立复用。
- `verify.acceptance.evolution.binding`：精确变更分类、输入指纹、证据适配器与复用边界。
- `verify.frontend.dev.incremental.unit`：推荐器消费相同的 DAG 状态，前置阻断项不进入执行建议。

不要仅凭汇总目标名称声明覆盖某个子目标；必须包含该目标的完整配方，包括 Node 等非 Python 检查。

## 精确选择与失效范围

`offline-delivery-governance` 仅列五个确切治理文件，归入静态治理；运行脚本、真实验收探针及混合修改继续选择运行验收。
指纹和 dirty 预检使用同一 `suite_owns_path`：全局证据权威与显式依赖优先，普通路径遵循首次匹配。后续宽泛规则不得重新吸收已归属的治理文件。
这不豁免证据权威变更：registry、guard、Make/CI 等全局输入仍会使已有正式证据失效；本次没有把旧算法指纹改写为新算法通过。


最终报告分别列批次、主线、部署、用户验收状态。计划成功、测试通过、代码干净均不单独代表主线集成或产品交付完成。

## 独立验收清单核验

已有正式证据完成 `make acceptance.evolution.record` 登记后，可用
`make acceptance.evolution.verify` 单独检查当前验收清单，定位格式、哈希、时效与缺项问题。
这是保留的验收诊断入口；调用者必须确认其评估基线，不能以它替代读取真实 PR 身份的合并预检。
