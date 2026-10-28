# 测试接入前置检查

基线：`1e06bcfde151d7669c29825d88c05bf3cd61b455`。P4 标准工程机制，独立于 FEPC-14 产品 PR #767；不修改产品、权限、数据库或运行环境。

## 改动与边界

既有 `make ci.local.iteration` 在 diff 检查后、增量测试规划前执行以下只读检查，任一失败即停止：

| 检查 | 拦截的问题 | 修正位置 |
| --- | --- | --- |
| `local_quick_evidence.py preflight` | Make 分散追加或多目标声明 Quick 依赖，分片执行却只读取规范行，导致测试漏执行 | 将依赖登记在 `make/ci.mk` 唯一的 `ci.local.quick.run:` 行 |
| `audit.verification.lane_coverage.check` | 新测试入口或守卫未接入有效车道 | 复用已有测试目标并接入车道；不放宽冻结基线 |
| handler split guard | 新 import 与独立测试桩注册表不同步，加载器返回空 intent 集合 | 明确报告缺失模块及类，补齐测试注册并验证 intent |
| page boundary guard `--check-only` | 新页面未登记，或声明消费缺少对应检查 | 登记真实契约消费边界，不取消页面约束 |

预检不执行完整 Quick、不产生成功收据、不改写页面边界报告。原后置 Quick、架构套件及远端门禁保留。预检通过仅证明上述接入条件，不能代替非零定向测试、真实浏览器验收或发布准入。

Quick 依赖检查覆盖仓库 `Makefile` 与 `make/**/*.mk` 中的显式目标声明；不声称是通用 GNU Make 解析器。继续要求规范依赖为单行、字面目标、无重复；分片本身调用同一校验，不仅依赖开发者记得先跑预检。

## 回归证据

- `make ci.local.iteration`：通过，四项前置检查实际执行，报告 `coverage=L1_only receipt=none`。
- `make verify.baseline.iteration.execution.policy`：19 项用例通过；其中 4 项前置命令 × 6 类变异（缺失、注释、忽略退出码、`|| true`、重复、后移）必须拒绝；handler 未注册模块/相对导入/未注册类有显式诊断；页面检查失败仍不写报告。
- `make verify.branch.governance.consistency`：Quick 收据/分片 66 项、分支治理 23 项通过。包括跨文件、多目标、双冒号声明拒绝，合法 PHONY/注释/recipe 不误判；预检不写收据，拒绝非预检参数。
- `make verify.quick.evidence.unit`：14 项增量收据回归通过。
- `make audit.verification.lane_coverage.test`：73 项通过，复用现有孤立入口和登记失效负向测试。
- 原始日志：`.runtime/integration-iteration-final.log`、`.runtime/integration-quick-manifest-tests-final.log`、`.runtime/integration-targeted.log`。这些是本地证据；最终 HEAD 的 Quick 与远端检查以 PR 和收据为准，本文不预先声明通过。

预期负向用例会输出拒绝信息；应以对应测试进程退出码及非零用例数判断结果，不能仅搜索日志中的 FAIL 字面。没有为使测试通过而自动补桩、自动忽略新增页面或降低覆盖基线。

## 交付与回滚

独立 Draft PR，等待审查；不合并、不部署。回滚仅撤销前置接线、诊断和测试；既有完整门禁仍保留。FEPC-14 的非草稿真实按钮点击限制不因本机制通过而解除。

## 主线同步复验

独立基线修复 PR #769 已合并为 4853b1b441837aa814049b2b9e31e9bdaa827767。本分支通过受管 published GitHub 同步入口追加 main，保留恢复 bundle，仅自动合并 active-runs 索引；未改动预检业务。原 153abbe97ccd455b54cf85638e7b5adcdd1da012 的失败/成功不视为新候选结论。新候选需重新 Quick 和远端门禁，保持 Draft，不合并、不部署。#767 的真实按钮阻断不由本工具 PR 关闭。

## DEV-FOLLOWUP-01：附件测试依赖边界

候选 a0b1c50fa1a016eacfac9985dbe3be68d5127a8a 的远端 frontend_release_gate（run 40754172541）失败于 `unexpected attachment stub NativeWeightedRelationDisplay.vue`。这是测试加载器边界遗漏，不是附件权限或产品组件缺陷：X2ManyRelationRenderer 已导入该通用加权关系组件，后者消费声明并通过 readRecord 读取关系名称；同一测试工具的 native-layout 已编译它的真实 SFC。附件分支却把它错误归入 presentation stub 校验。

修复仅在既有测试加载器中将精确源码路径路由至真实 SFC 编译，不新增 stub、不放宽旧 stub 清单、不修改产品或传输边界。4 项边界断言验证真实依赖、原有合法桩、同名异目录和未知组件；另外断言构建确实编译了该 SFC，防止登记存在但执行仍被替换。

实际执行 `make ci.local.iteration verify.frontend.professional_relation_field.unit` 通过：附件挂载 38 项断言、边界 5 项、关系模型 18 场景/17 反例、列来源 3 项、选项限制 6 项、Python 10+40 项。原有附件读取/拒绝/下载/卸载行为断言全部保留。日志 `.runtime/integration-attachment-final-targeted.log`。L3/L4 不适用：只修改离线测试加载器，无产品与数据库行为变化。最终 Quick 和远端结果须绑定后续冻结 HEAD；旧失败记录保留。

#767 本地同步已完成但未发布；其真实非草稿按钮验收继续 blocked。本次不改变样本或权限，不将工具测试替代产品验收。
