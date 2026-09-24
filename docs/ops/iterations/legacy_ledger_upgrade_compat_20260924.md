# 旧开发库付款台账升级兼容修复

## 身份与边界

- 基线：61b8d7121b28d1e1f9126e7c03ab01bce57cee62；分支 fix/legacy-ledger-upgrade-compat；当前为未提交候选。
- P1 / smart_construction_core：历史台账身份属于行业财务事实。前置迁移修复升级时序，不从前端或当前业务关联推导历史身份。
- P4：仅补充定向验证入口。原会计 JSON 工作树及其 dirty 改动不纳入。
- 目标开发库 sc_demo 为持久化数据库；保留数据库与 filestore。生产环境不涉及。

## 根因与修复

旧库 17.0.0.132 没有 payment_ledger_allocation 表，也没有台账 normalization_state。
153/154/155 前置迁移以子表缺失为条件整体退出，因此父台账未分类。
ORM 填充 normalized 默认值后，allocation.init 回填缺失身份的历史记录，触发 canonical_identity_complete。

新增 169 前置迁移，在父表存在时独立为 NULL 身份状态标记 legacy_unresolved_identity，
不改金额、公司、币种、合同、既有非空分类，不删除记录或放宽约束。随后复用156迁移隔离资金子项并重算派生汇总，修复156先于父分类的时序遗漏。模块版本递增至 17.0.0.169。

## 验证与现有证据

- make verify.legacy_ledger_preallocation.unit：7 tests PASS。SQLite 实际执行 DML；仅适配 PostgreSQL 表查询、DDL和锁，不能替代 PostgreSQL 升级验证。
- make ci.local.iteration：PASS（L1）；其增量建议基于旧 origin/main，包含历史差异，不扩展本批测试范围。
- git diff --check：PASS。
- 隔离 PostgreSQL 全量恢复升级：进行中，输入为 main + 本批 manifest/169 migration 只读覆盖。
- 服务器原始证据目录：/opt/projects/artifacts/dev-main-redeploy-20260924。
- 已有失败证据：clone-upgrade-r2.log。首次修复验证因只读父挂载内无法创建新子挂载点而未启动Odoo（clone-upgrade-fix169.log）；改用完整模块副本只读挂载，重试日志 clone-upgrade-fix169-r2.log。
- 复用备份：/data/backups/daily_candidate/sc_demo-20260924T073527Z-1de8c1fe。
- 本批不改 Web 内容，复用基线前端构建结果，不重复运行浏览器矩阵。

## 状态

批次验证中；未提交、未推送、未合并；未升级原库、未切换服务、未完成公网联调验收。

- 独立只读复核：169及156重放增量通过，无新S0/S1/S2；实际资金子项状态仍需克隆验收，不把调用顺序单元用例当成数据结果。

## 完整升级暴露的退役契约兼容问题

- clone-upgrade-fix169-r2.log 证明169迁移与原allocation建表回填已越过失败点。
- 后续XML加载失败：旧published契约仅write(active=False)触发replace_and_publish，重新校验已迁出历史字段。
- 精确修复该XML的两处退役声明：active=False,status=draft。沿用现有非发布生命周期，保留payload及版本历史；不降低有效契约发布校验。
- 第二次独立增量复核通过；第7例仅验证声明，运行态以第三轮克隆为准。
- 第三轮日志 clone-upgrade-fix169-r3.log；升级后额外检查台账NULL分类、分摊标准身份完整性与资金子项隔离计数。
