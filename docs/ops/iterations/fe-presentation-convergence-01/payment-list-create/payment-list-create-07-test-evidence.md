# PAYMENT-LIST-CREATE-07：测试证据

## 定向结果

`make verify.candidate.view_adapter.unit`：28 项 unittest，通过。入口已接入 `ci.local.quick.run` 唯一依赖声明；没有建立新浏览器车道。源文件 `scripts/ops/test_candidate_view_adapter.py`。

- 实际 plan CLI 对临时 Git 仓库执行精确 blob 读取；修改工作区文件不会改变读取候选。
- 实际 apply CLI 对完整合法请求仍拒绝，原因是没有受支持运行时驱动，不产生写入。
- SHA、镜像、前端摘要、UUID、原始架构摘要、候选 XML 摘要、源/目标碰撞、未知字段/布尔 ID/缺失来源、非目标 XMLID 负向测试。
- XML 多匹配、额外字段/edit 变化、实体声明、被重签的越界计划拒绝。
- 内部事务协议测试：前态漂移、零/多匹配、恢复绑定缺失、见证缺字段时零 ORM 写入；业务/其他视图/队列/资产/arch_prev/表单绑定/缓存超范围时无 commit 并调用 rollback/quarantine。
- ORM 异常、commit 异常不吞掉；commit 结果不明时仍隔离，不能声明已恢复。

内存端口是测试替身，不是 Odoo、不代表数据库恢复成功，不验证真实 ORM 的触发器、提前提交或所有数据覆盖。真实驱动缺失是显式阻断。

## 运行时状态

克隆、视图写入、恢复演练、模块升级、浏览器点击、业务保存：全部 not_run。本次产品候选 #770 未变化，其原有 CI 不重跑。P4 分支自身的检查另记，不借用 #770 成功。

日志：`.runtime/payment07-unit.log`。其他工具检查与候选发布状态由当前 `.agent/runs/PAYMENT-LIST-CREATE-07/run.json` 索引。

`ci.local.iteration` 通过 L1；`ci.delivery.freeze.prepare` 通过。`verify.docs.all` 在链接检查失败：此工作区缺少历史文档引用的 62 个本地运行制品。保留失败，不补造制品，不将其记为文档全量通过；新增文档的相对链接另行核对。

首个冻结候选 Quick 在车道覆盖检查失败：两个 Make 入口缺少可执行引用。随后将真实 Make plan/apply 调用加入既有 CLI 测试，验证离线 plan 成功与 apply 拒绝；不改覆盖守卫或豁免。首次显式 QUICK_SHARDS 参数也被签名入口拒绝，未执行；后续使用默认入口。失败日志保留 `.runtime/payment07-quick.log` 与 `.runtime/payment07-quick-default.log`。
