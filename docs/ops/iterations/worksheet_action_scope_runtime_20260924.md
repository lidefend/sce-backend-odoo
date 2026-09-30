# 工作表动作范围与大列表渲染修复

## 身份与边界

- 基线 39a90e6da4f25c6942fdddb7aa07032dd02da7cc，复用 fix/dev-form-contract-upgrade 工作树；本记录随代码提交，非冻结发布候选。
- Formal Product Layer: P0。Layer Target / Module: smart_core 页面契约装配、共享工作表数据源、ScTable 官方组件适配。
- 通用动作查询范围及渲染性能由平台拥有；不在 P2 客户模块、P3 运行时偏好中补偿，不改变业务数据、权限或行业规则。
- 中等风险：所有 hierarchical_worksheet 契约与显式启用 virtualScroll 的表格。其余表格保持原渲染模式，横向宽度继续使用 tableContentWidth。
- L1 + L2 定向验证后部署已有开发服务做受影响 L4 浏览器复验；无数据库 schema/模块数据变化，跳过 L3 模块升级。完整 CI/主线集成未执行，不跑本地 Quick。

## 根因和修复

1. 工作表独立查询仅消费 sheet_domain，遗漏 action domain 和有效上下文。普通列表查询范围正确，工作表却请求全模型可读记录。
2. 后端将动作 domain 与默认 sheet_domain、每个可切换 tab domain 分别按 Odoo 隐式 AND 合成，保留 tab 对局部工作表筛选的替换语义；不将单据模型 domain 套到其他模型的 hierarchy 上。
3. sheet.context 携带装配时有效上下文，数据源透传给已有 listRecords，不推导公司/业务范围。
4. ScTable 增加显式可选 virtualScroll/height，调用锁定 TDesign 1.20.5 官方虚拟滚动；删除无效 scroll.x 的 any 断言，横向滚动仍由 tableContentWidth 承担。
5. 工作表启用官方动态行高虚拟滚动，数据未截断。保留原有全量分组/搜索语义；本批不宣称实现服务端分页，超大数据集全量传输仍是后续性能边界。

## 验证

- make ci.local.iteration PASS（L1_only，非交付回执）。
- make verify.frontend.hierarchical_worksheet.unit PASS：后端 21 项，交互 15 项，domain-tab 断言全部通过。增强的后端回归覆盖 OR 动作域与局部域合成、tab 保留动作域、上下文深拷贝及异模型 hierarchy 不继承 sheet 域。
- make verify.frontend.primitive_adapter.unit PASS：46 组件、9 事件例、31 个 Python 用例。
- make verify.frontend.typecheck.strict PASS。
- make verify.frontend.component_driver_takeover.unit：7 项通过，初次因源码摘要变化报告 stale；刷新既有清单后 PASS，仅 inputDigest 变化。
- 早期定向命令复用旧依赖目录仅作诊断；最终命令已改为与候选 lockfile/package manifests 一致的现有依赖，重新通过。未修改依赖源工作树。
- 开发服务器 make verify.frontend.build ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo FRONTEND_DIST_DIR=frontend/apps/web/dist-worksheet-candidate PASS，34.68 秒；构建在服务器完成，无本地重型 CI。
- git diff --check PASS。

## 开发环境验证

- 在既有开发服务发布限定四个运行文件，逐文件核验原 HEAD 内容摘要；静态资源先拷贝、index 最后原子替换，旧资源保留以兼容已打开页面。
- 重启既有 Odoo 容器，保留其全部持久卷和客户模块挂载；不重建数据库、不调整权限、不写业务记录。
- 浏览器收入结算：工作表请求保留动作域及公司/语言/业务上下文，结果 73 条；旧错误请求为全模型 3416 条。
- 浏览器支出结算：正确动作域，结果 3343 条，首屏实际 tbody 11 行；滚动后仍仅 32 行而非完整挂载。页面可响应。
- 无匹配词搜索显示 0 条，通过“清除搜索”恢复 3343 条。搜索结果中的末条记录可检索，结果 1 条；通过“打开记录”进入详情，无服务端错误，返回原列表。
- 浏览器工具对超宽整行的 click/dblclick 报定位错误，改用页面可见“打开记录”入口完成验证；不将工具定位错误记为业务失败，也不宣称双击场景通过。
- 原始服务器证据沿用 /opt/projects/artifacts/dev-main-redeploy-20260924：worksheet-update-20260924.json、worksheet-build.log。

## 状态和剩余边界

- 本批指定读取路径修复并在开发服务复验通过；本地提交、未推送、未合并。
- 开发服务为 main 加本批限定覆盖，不是新的主线发布版本。
- 不将本批读取证据扩展为全部公司、角色、创建/保存/审批通过。客户配置迁移及历史附件覆盖沿用私有客户批次记录，不复制客户资产到公共仓库。
- 官方虚拟滚动只优化 DOM；全量加载、长文本导致的高行、用户手工清空输入后的提交等后续交互场景未在本批全部验收。

## 合并两份修复（2026-09-24 追加）

同一问题出现过两份独立实现：本记录对应 `20e2956d`（已发布到开发服务），以及
`e0df4111`（本地 `fix/settlement-worksheet-action-scope`）。逐项核对后只保留一份，不并行维护两套：

| 维度 | `20e2956d`（已部署） | `e0df4111`（本地） | 取舍 |
|---|---|---|---|
| `sheet.domain` 动作域 | `action_domain + sheet_domain`（Odoo 隐式 AND） | 声明了 `sheet_domain` 就替换，否则等于 `action_domain` | 取 `20e2956d` 形式；两者**不是普遍等价**，条件见下节 |
| domain tab | `action_domain + tab_domain` | 未改动 | **取未改动**：`20e2956d` 使 BOQ「编制中版本」由 3 行变 0 行 |
| `sheet.context` | 新增 `deepcopy(effective_context)` + 数据源透传 | 无 | 保留 `20e2956d` |
| 虚拟滚动 | ScTable `virtualScroll`/`height`，移除失效的 `scroll.x` | 无 | 保留 `20e2956d` |
| 守卫测试 | 平台单测 +11（含把 tab 回归固化为期望的一条） | 平台单测 +85、P1 三例投影断言 | 合并：保留 P1 三例，修正 tab 期望 |

合并后的候选以已发布提交为基线，仅追加两个提交：`272b05be`（tab 作用域纠正）、
`54b8fcd4`（P1 投影断言）。已发布历史未改写，`20e2956d` 保持原样。

### 等价条件与范围反例（2026-09-24 追加，纠正上一版措辞）

上一版把两种写法记为"等价"，这不成立。准确的适用条件是：

> `action_domain + sheet_domain` 与"声明了 `sheet_domain` 就替换"结果相同的**充要条件是
> 被合成的域已经蕴含动作域**。一旦被合成的域刻意走出动作域，两种写法必然分叉。

两个方向各有一个实测例子：满足蕴含条件的「已发布版本」tab，以及刻意走出动作域的「编制中版本」tab，
行数对比见下节证据表。

### tab 与动作域冲突的证据

受管 dev（`sc_dev_demo`）实测 `project.boq.line`：动作域 `[('version_id.state','=','published')]`，
全模型 40 行、动作域 37 行；`sheet_domain` 与动作域合成为 37 行。**这只是本样本两版行数相同，
不构成“两版等价”**：等价与否由上一节的蕴含条件决定（对**所有合法数据**成立才算等价），单一样本
结果相同既不能证明等价、也不能排除分叉。

| 已发布 tab | 声明域（未改动） | `action_domain + tab_domain`（`20e2956d`） |
|---|---|---|
| 「已发布版本」 | 37 行 | 37 行 |
| 「编制中版本」 | **3 行** | **0 行** |

前端 `applyWorksheetDomainTab` 是**替换** `sheet.domain`（key 无效时返回原对象），
所以 tab 是完整备选作用域而非默认查询的补充；把动作域拼进 tab 只会窄化那些刻意走出动作域的 tab。
tab 是否有权走出动作域属产品问题，本批只恢复已发布行为，不代替产品裁决。

### 范围没有随页签切换丢失（反例）

按工作表动作逐一核对"必须保留的范围"来自哪一层（受管 dev 实测）：

| 工作表动作 | 动作域 | 公司/项目范围来源 |
|---|---|---|
| 534 工程量清单（`project.boq.line`） | `[('version_id.state','=','published')]` | `project.boq.line` **无** `ir.rule`；`project.boq.version` 有 462/463（463 为 `[(1,'=',1)]`） |
| 781/782 收入/支出结算（`sc.settlement.order`） | `[('business_category_id.code','=','settlement.income'|'expense'), ('contract_source_kind','!=','general_contract')]` | `ir.rule` 400/401/402：`company_id in company_ids` + 项目可读规则；422 为 `[(1,'=',1)]` |
| 837 付款执行（`sc.payment.execution`） | `[('source_kind','=', 'actual_outflow')]` | `ir.rule` 261–264：`company_id in company_ids`（+ 项目可读规则） |

结论分两条，不合并成一句：

1. **结算与付款执行**：公司隔离与项目可读范围由 `ir.rule` 承担，规则对**每一次查询**生效，与当前
   `sheet.domain` 是默认域还是某个 tab 域无关，因此切换页签不会丢失公司/项目范围。
   实测动作域本身也不含公司或项目条件——把动作域拼进 tab 从来没有提供过这两类范围。
   **本条的证据等级须写明**：上表记录的是**规则定义**（组配置与域文本）加机制语义，**不是**
   在受管库上对该角色做过的“两公司 + 授权/未授权项目”实际读取实测。看到规则定义不等于已经证明
   特定角色不可越权——还需要规则组合与实际读取结果。本批**未**为 `sc.settlement.order` /
   `sc.payment.execution` 补做该实测，列为剩余缺口（`project.boq.line` 的实测见
   `boq_line_record_rule_scope_20260924.md`）。
2. **工程量清单**：`project.boq.line` 上不存在承载公司范围的 `ir.rule`，因此**默认查询与任何 tab 都没有
   公司范围可丢**：这不构成"页签切换导致丢失"的证据，而是另一个独立缺口——清单行的工作表查询本身
   没有规则层的公司边界。该缺口不在本批修复范围，登记为待核验项，不以动作域拼接掩盖。

据此明确本批边界：**动作默认筛选是业务默认范围，权限边界是 `ir.rule`，两者不互相替代。** 本批不主张
tab 必须重述动作域，也不以"拼接动作域"充当权限控制；页签若要收窄范围，应在 tab 声明或规则层表达。

### 投影断言

`test_payment_settlement_component_profile.py` 断言三个已发布 worksheet 投影的
`sheet.domain` 以动作域为前缀。只回退该合成时三例全部失败（`[] != [动作域]`），已确认非永真。
