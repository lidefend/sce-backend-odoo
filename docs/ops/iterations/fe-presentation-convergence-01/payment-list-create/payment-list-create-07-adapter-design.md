# PAYMENT-LIST-CREATE-07：候选视图适配

## 状态及交付边界

P4，独立基线 main `4853b1b441837aa814049b2b9e31e9bdaa827767`。产品候选 #770 `7bdf888abcde795ff851bf779add219474cf8fd1` 保持不变。本 PR 实现离线准入、候选 XML 提取与事务端口协议；**真实 Odoo 运行时驱动尚未实现，公开 apply 必须拒绝**。阶段 B 部分完成，不能宣称受管环境加载能力已经完整交付。只读评估 06 已证明没有可直接使用的运行时入口，本 PR 不伪造一个。

06 的输入结论：local.contract-snapshot 克隆来源和目标固定，默认整模块升级；RC6 执行器绑定历史候选和多模块升级。沿用它们的身份隔离、不可变制品和来源分离原则，不修改这些入口、不新建凭据或浏览器体系。本次用同一仓库已合并且干净的第二工作区，不增加第三工作区。

## 实现

入口 `make candidate.view.plan CANDIDATE_VIEW_REQUEST=<file>` 读取请求，使用 `git show <full SHA>:<固定路径>` 读取候选 XML，不 checkout、不执行候选代码。要求完整候选 SHA、不可变镜像、前端构建摘要、快照来源/哈希、目标 UUID、XMLID/ID、原始架构及摘要。严格拒绝未知键、错类型、历史身份兜底、源目标冲突和现有 acceptance 数据库。

只有一个目标 occurrence，结构比较只允许根 create 从 false 到 true；edit/delete、子字段及全部其他结构必须保持原样。忽略格式空白不等于忽略字段变化。计划为 offline_plan_only，write_authorized=false；期望运行身份只是申请输入，不能当成实测证明。

`make candidate.view.apply` 执行相同校验后返回 `runtime_driver_not_supported`，退出 2。它不连接 Docker/SSH/Odoo、不读取凭据、不升级或写数据库。机器可读 scope 中 registered_targets 为空；用户输入、verified=true、自填回执或动态 Python 模块名都不能注册驱动。

内部 `execute(plan, driver)` 为未来可信宿主提供事务协议，不是任意驱动加载入口。它在独占锁内重新绑定目标和恢复回执，核对完整前态与唯一视图，调用 ORM 端口，再验证后态与业务/非目标视图/表单绑定不变。超范围、异常或 commit 抛错时回滚并隔离副本；不假设数据库 rollback 可以恢复缓存。单元测试使用明确标记的内存端口，不以其成功证明真实 ORM 行为。

## 副作用与恢复职责

arch_prev、视图元数据、队列/meta、派生资产及缓存状态必须全部进入 state witness，不能只检查 arch。before/after 摘要仅保证被见证的内容一致，不能证明真实驱动枚举完整；因此没有完整且可信的运行时 provider，就没有写入能力。

未来 provider 必须复用现有受管克隆/制品机制验证资源归属、源库隔离、配对快照、恢复回执及精确请求范围；限制事务内提前 commit，锁定相关写入者，保留 Odoo 正常 write 钩子，不使用 no_save_prev 或 SQL 写入规避副作用。提交后再独立读回，提交结果不明时隔离并按已验证的副本清理/恢复流程处理。以上仍是阻断项，不是已实现功能。

## 验收接口

[scope contract](payment-list-create-07-scope-contract.json) 声明身份、唯一视图、允许变化、完整见证和缺失 provider。

离线 plan 输出 request 摘要、候选架构与摘要，不输出“部署成功”。内部协议结果包含候选代码/镜像/前端身份、快照来源、目标 UUID、视图 XMLID/ID、前后摘要和完整状态；browser_acceptance=not_run、business_save=not_authorized。真实运行时恢复结果不能由该协议自行推断。

候选代码、快照来源 SHA、运行进程声明分别记录。所有新目标仍未登记，不借用旧 2068/880/1771 作为未来数据库身份；具体 ID 必须由可信驱动实时解析。来源相同字段不是授权。

## 剩余工作及授权

本次未执行克隆、恢复、视图加载、升级、fixture、部署、保存、HTTP 验收或对现有 acceptance 的连接。阶段 A/C 的离线部分与 D 的证据接口有实现；阶段 B 的运行时集成及真实验收仍阻断。下一步需独立审查运行时 provider、完整状态覆盖及恢复回执的实际可实现性。不得将本 PR 的单元测试通过当作环境变更授权。
