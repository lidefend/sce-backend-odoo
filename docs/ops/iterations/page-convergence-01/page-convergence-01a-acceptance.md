# PAGE-CONVERGENCE-01A · 验收记录

## 运行身份

- 分支：`feature/page-convergence-01`
- 候选 HEAD：`55712a688`（升级前快照 source_sha）
- 本地受管库：`sc_dev_demo`（项目 `sc-local-dev`）
- 快照：`artifacts/local-dev/snapshots/20261030T070532Z/`

## 已验证通过

| 项 | 证据 |
| --- | --- |
| 升级前快照 | 数据库+filestore 配对，双 SHA256，`pg_restore --list` 可读（22679 条） |
| 受管升级 | `make local.dev.upgrade MODULE=smart_construction_core`，77 模块加载，demo 权威通过 |
| B3 只读 action | 返回 `ir.actions.act_window`，模型 `sc.project.stage.requirement.item`，tree，按 lifecycle_state 过滤，create/edit/delete 禁用 |
| B3 无向导 | `sc.project.stage.requirement.wizard` 记录数 0 |
| 六组布局 | 页面出现「项目身份/业务主体与项目属性/联系信息与合同关联/项目安排日期/计划开竣工日期/责任信息」 |
| 四卡过渡态 | 页面出现「数据暂不可用」，无伪造 0 |
| 四视口无横向溢出 | 1440/1024/768/390 均 scrollWidth==clientWidth |

## 待补齐

- TASK-01 合同数量正向场景：`NOT_VERIFIABLE_WITH_EXISTING_AUTHORIZED_IDENTITIES`（本地
  `pm1/ct1/sc_contract_read` 的 `sc_project_contract_entry_available` 均为 false；后端
  `sc_overview_contract_count=4` 计算正常）。环境覆盖限制，非产品缺陷。
- B3 前端点击：已真实点击，目标模型/阶段过滤/禁用/返回均正确，无向导；但只读 item 树
  未完整渲染（前端路由到 `/f/.../new` 并返回 400）；随后将只读 tree 动作改为 `target=current`，
  真实点击后进入列表路由 `/a/822`（view_id=1936，domain/context 保留，create/edit/delete=false），
  400 消失，返回详情正常，无临时向导。B3 前端点击判定为 PASS。
- 截图已重命名 `project-10` → `project-21`，SHA256 前后一致。

