# U-C1：合同／结算退出兼容结构路径

状态：合同组实施中；结算组待合同浏览器复核。结果索引为本专题 `artifacts/uc1/RESULT.json`，不以准备状态登记通过。

## 基线与责任

- 基线：main `0f8b5ee6ac1dba8237d99294921af8d5f3280597`，Tree `b810985b2d944d64bccb4394ecb797dcf76f3d80`。
- 分支：`feature/uc1-contract-settlement-native-v1`。新专题通过 `workspace.worktree.create` 从精确基线创建；两个旧专题保持原干净提交 9572436a／a8fe1c15，不参与本批写入与运行。
- Formal Product Layer：P1；Layer Target / Module：`smart_construction_core` 标准分类策略与原生合同／结算视图。P4 仅测试及交付记录。
- Standard vs User-Specific：行业标准。Why Here：原生 XML 拥有业务组织，分类仅增强语义。Why Not Elsewhere：不引入 P0 或前端模型判断，不改 P2/P3 客户偏好。
- Blast Radius：合同 609/view1569、610/view1570；随后结算 781、782/view1764。分类共享的补充合同模板保持不变；列表工作表、金额计算、税额、保存、审批和权限排除。

## 合同组结构退役

| 来源 | 迁移前 | 迁移后 |
|---|---|---|
| 分类 8/10，seed 与 Python 模板 | `sections` 决定标题、顺序、字段归属 | 移除输出 `sections`；原字段策略保留，并显式承接旧章节对来源／履约摘要的创建态排除 |
| 收入合同配置 | 字段 `sequence` 排序 | 同一产品配置仅声明 `native_semantic_surface`；精确解除该 XMLID 的 noupdate，升级可重放 |
| 支出合同生成配置 | 38 个字段排序声明 | 沿用受管 XML 退役入口停用精确记录；新语义配置声明 native，不携带结构 |
| 原生视图 | 已有六个业务章节、全宽明细、从属历史付款区 | 复用原生声明；正文和导航消费最终 `containerTree` |

一级业务章节为：身份与基本资料、合同范围、合同明细与金额、说明与附件、履约信息、来源与系统追溯。历史付款承接保持从属区及原权限限制。其实际可见性由原生和字段策略共同约束。

字段帮助、标签、既有显隐／必填／只读 profiles、附件策略、动作说明、domain、ledger 元数据保留。旧配置没有独立的帮助或动作语义，不能把停用纯排序配置解释为删除业务能力。补充合同分类保留兼容章节，本批不减其消费者。

## 验证与环境

- L0：完整 tracked / untracked 指纹写入结果索引。运行绑定 sc-local-dev、sc_dev_demo、精确 filter `^sc_dev_demo$`、filestore `sc_local_dev_odoo_data`；内部开发租户、company 1，非生产／历史 UAT。
- L1：`make ci.local.iteration`；L2：既有 `verify.form_structure_authority_unification.unit` 和 `local.dev.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestContractHandlingPagePolicy`。
- 模块测试使用实际产品 XML 在回滚事务中载入声明；不依赖手改开发库。首次旧库配置未升级的失败单列保留。
- L3：受管 `local.dev.up`、`local.dev.upgrade MODULE=smart_construction_core`，核验配置实际退役；不重建数据库、不重置已有业务记录。
- L4：合同组 1088/390；创建入口、真实记录只读与可用编辑态；零保存／审批。对照来源、明细、字段状态、章节导航及请求 trace。
- 无 P0 改动，因此不重跑已迁移页面矩阵；未改列表、计算、审批、权限，排除其完整旅程。已有新建 fixture 不复制，不执行无关保存旅程。
- L5：四入口收敛后再生成预检、冻结、独立复核及一次 Quick。上一批成功 Quick 和浏览器证据不重跑。

## 计数和退出

起点保持 53→50。合同组未有实际运行通过之前不减数；四入口全部满足 native、compatibilityDependencies 为空且实际页面通过后才登记 50→46。管理员／公司1／创建态的统计与其他状态覆盖分列。

结算组继续使用同一专题，先处理共享 view1764 的方向与条件列，不改金额或权限。action 777 继续为“环境阻断、未通过”；不探测、不停启历史容器。

回滚必须成对恢复分类输出与编排声明，并通过同一受管模块升级；不能仅恢复一侧形成双重结构所有权。
