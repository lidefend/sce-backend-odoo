# 本地支付入口运维工具

两入口均限既有 `local.dev` / `sc_dev_demo`。configure 固定公司 1、菜单 339、动作 908、财务用户 47，拒绝检查点漂移。probe 按支付菜单 XMLID 与 `demo_role_finance` 登录名发现实际 ID，并检查该用户允许的各公司；旧结构分支只输出 SQL 结构与候选身份诊断，不等同最终授权结论。不是通用租户修复工具。产品主线部署仍使用已有部署工作树；运维脚本由受管 shell 入口执行。

| 入口 | 行为与车道 | 使用边界 |
|---|---|---|
| `make local.dev.payment_entry.probe` | `local_diagnostic`，按需只读 | READ ONLY 事务、禁止提交、最终回滚。读取发布/场景/企业启用/权限与实际路由；非 sudo 读取记录 ID。不验证支付或撤销 |
| `make local.dev.payment_entry.configure` | `ops_runbook`，显式配置写入工具 | 默认 plan 只读回滚；apply 需要 `BUSINESS_CONFIG_PAYMENT_PHASE=apply` 和脚本定义的精确确认串，并受现有 local.dev 写租约保护。通过正式 Odoo 方法维护发布参数、冻结/发布和企业启用，核验当前有效快照确实发布目标入口及财务非 sudo 正式路由通过后提交，失败回滚。不修改角色、ACL、菜单/动作组、绑定或豁免 |

两入口需要活栈和已有身份，不加入自动 Quick/CI。配置脚本可能产生真实配置提交，不应登记为只读探针；注册本身不授权重放 apply。再次使用 apply 前应核对当前目标与备份/恢复安排，不能以旧回执代替现场回读。

运行范围检查：`make audit.verification.lane_coverage.check`。纯逻辑测试：`python3 -m unittest scripts.verify.test_local_dev_payment_entry_configuration scripts.verify.test_local_dev_payment_entry_probe`。前者检查车道结构，后者检查分类/边界函数，均不能代替完整配置事务或支付业务验收。

车道登记在既有 dispositions 中；冻结身份只增加这两个按需入口，zero-reference 上限相应增加 2。未登记目标容忍数保持 0，其余预算及门禁不变；需经独立审查，不自动扩大基线。
