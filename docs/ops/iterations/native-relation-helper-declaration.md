# 原生关系值辅助函数声明形态修复

独立于 PR #767、#768，从 main `1e06bcfde151d7669c29825d88c05bf3cd61b455` 提取。产品差异仅为 private identity 箭头函数改成具名函数声明；谓词保持原样，不改变导出、关系值格式或权限。原模块加载边界守卫不变，不添加豁免。

复用 `verify.frontend.collection_view_semantics.unit` 的身份边界回归（17 项新增断言），并执行 `verify.frontend.scene_component_bridge.guard`、原生动作及呈现器既有测试。无 UI 行为变更，不新建浏览器车道或修改隔离/日常数据库。#767 的真实按钮验收仍独立阻断。

仅范围相同的源码和测试从已审查候选提取，未带入阶段要求 handler、路由、探针或业务代码。生成报告仅更新输入摘要。回滚为恢复原 const 声明及其测试；原模块加载守卫会重新拒绝该声明，不涉及数据恢复。最终 Quick、远端门禁和独立评审以精确候选为准，不预先宣称合并资格。

## 授权追加：合并预检历史运行归并（P4）

用户在当前候选独立评审后授权处理本地合并阻断。`integration_cycle.checks_ready` 原先逐条累计 `statusCheckRollup`，将同一 SHA 中旧 CANCELLED/FAILURE 与新 SUCCESS 混算。本次不改工作流或平台保护规则：按 workflowName/check name 分组，以 Actions run ID、同 run 的 job ID 选择最新执行；不按完成时间或数组顺序选取。不同工作流同名检查分别保留；身份缺失、跨仓库歧义、同一执行内容冲突仍阻断。最新失败/取消/超时/等待批准/运行中不借用旧成功；空列表与缺少既有四项合并检查仍阻断。非 Actions 状态不参与历史替换。

独立 P4 提交仅修改既有预检工具及其测试，不改变私有 identity 谓词、模块守卫、产品权限或 FEPC-14 代码。复用 `make verify.integration.cycle.unit`：旧实现运行新增用例出现 9 项失败；修正后 16 项测试通过，包含真实故障归并形态、逆序、重试、旧运行晚结束、不同工作流、歧义、最新失败与缺失检查，以及 HEAD 漂移、Quick 缺失和平台 BLOCKED 不放行。旧 #769 真实 rollup 离线重放通过，不冒充新候选远端门禁。

原始日志：`.runtime/native-helper-preflight-regression-before.log`、`.runtime/native-helper-preflight-targeted.log`。旧候选 56b9e1413db538388350b651b27a6022a3c1a93d 的 Quick、远端及独立审查不自动成为新 HEAD 的结论。当前追加提交需重新冻结、Quick、远端复验与独立复审；未合并、未部署。

## R2：未知完成结果与必需工作流身份

按独立复审仅补强两项 P4 边界。CheckRun 必须显式为 COMPLETED 且 conclusion 是 SUCCESS/SKIPPED/NEUTRAL 才允许通过；缺失、空、未知及新增非成功结论阻断，不回退读取 StatusContext.state。旧实现已有未知结果 pending 分支，本次关闭的是 fallback 与完成状态缺失的空隙，并补足负向证明。

必需集合改为 `(workflowName, check name)`，只有经过有效 Actions 身份解析的 CheckRun 可以满足要求。其他工作流的同名检查和同名 commit status 均不能补位。四项现有工作流/实际 job display name 通过读取对应 YAML 校验；不修改 YAML、GitHub 保护或豁免。run/job ID 最新执行规则、不同工作流分别判断及 HEAD/Quick/平台状态边界不变。

`make verify.integration.cycle.unit`：修正前 19 项测试中 8 个 subtest 失败；修正后 22 项测试通过（包含允许结果白名单、未知/空/新增状态、缺失完成状态、错误工作流/commit status、真实配置绑定及最新执行规则）。`make ci.local.iteration` 通过。原始日志 `.runtime/native-helper-r2-before.log`、`.runtime/native-helper-r2-final-targeted.log`；中间真实 YAML 校验发现 professional_quality_gate 显式 display name，已按实际同名声明修正测试并保留中间失败记录。新候选 Quick 与远端状态另行绑定；本轮不合并、不部署。
