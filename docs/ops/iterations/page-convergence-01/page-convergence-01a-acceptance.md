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

- 有合同只读权限账号场景的合同数量展示（结果 B 冻结，暂不验证真实计数）。
- B3 浏览器真实点击回放（后端 action 已验证，前端点击证据待补）。
- 截图文件名中的记录标识需要改为本地 id=21。

