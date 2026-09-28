# Web 全量类型错误收口（2026-09-28）

## 身份与范围

- 用户已确认上一执行器停止写入，本执行器接管现有产品工作树。
- 分支：`fix/web-occurrence-identity-and-failure-atomicity`。
- 交接基线：`c79809757b25f9af779fc4e20e5d28a4a22f029c`，起始 clean；本记录验证身份为该 HEAD 加本批显式 dirty scope，不是冻结发布候选。
- 只读回读的 Gitee main：`28266e9b31e791e380a4a8fa17591228c6a69a9b`。本轮不将未合入的交接分支称为主线。
- Formal Product Layer / Layer Target / Module：P0 通用 Web 类型声明、契约消费及组件适配（`frontend/apps/web/src`、`frontend/packages/schema/src/index.ts`）；P4 仅现有 `package.json` 检查脚本和本记录。
- Standard vs User-Specific：通用机制。Why Here：既有后端字段和组件接口在前端声明/消费处失配。Why Not Elsewhere：不修改行业规则、客户配置或后端契约来适配 TypeScript。
- Blast Radius：列表、表单、关系明细、路由和场景块渲染。启动链、角色真源、default route、public intent、数据库和模块版本不变。
- 不修改交接前的 occurrence、错误归属、失败原子性实现；不放宽 tsconfig，不增加 any、ts-ignore 或双重类型断言。

## 修复结果

基线执行 `scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck`，退出 2，31 项 TS 诊断分布于 14 个源码文件。

| 原错误位置 | 数量 | 修复 |
| --- | ---: | --- |
| HierarchicalWorksheet | 2 | Vue vnode 参数由接口推断，DOM 使用 instanceof 收窄；判别联合显式检查 false |
| BlockRichTextOverview | 2 | 使用 ScButton 的 secondary 变体，由现有适配器映射 outline |
| ProfessionalDetailCollectionControl | 1 | 使用已有 optionalPresentation 控制可选明细，无配置时才走普通 slot |
| FormSection | 1 | 日期范围开始值按字符串传入，与结束值一致，不经过金额格式化 |
| NativeActionOverflowMenu / NativeFormTreeRenderer | 3 | 图标解析结果在局部模板变量中判空、收窄；不传空图标或弱化 ScIcon 接口 |
| X2ManyRelationRenderer | 2 | 标题级别通过数字绑定传入 |
| one2manyRelationQuery | 4 | 元组/对象归一结果声明为 Record<string, unknown>，保留既有 ID/标签校验 |
| ContractFormPage / actionRoutePolicy | 4 | 路由 query 使用既有 LocationQueryRaw / Record 类型，允许移除预览和活动参数 |
| canonicalFormRenderer 消费的共享 FieldDescriptor | 2 | 补齐后端既有 digits、currency_field 可选字段 |
| nativeSectionNavigation | 3 | 非空角色收窄后再加入语义导航 |
| router | 1 | 路由权威对象结构化展开传递，不做不兼容类型断言 |
| SceneContractBlockGridView | 6 | 声明既有 runtime_fetch_hints；场景到页面块映射显式提供 key/block_type，保留合并后的身份和现有空类型降级 |

现有 `typecheck:strict` 脚本改为先执行全量 `vue-tsc --noEmit`，再执行原局部严格配置。现有 Make/CI 调用自动继承完整检查；没有扩大 strict 配置或修改依赖版本。远端离线缓存以 manifests 绑定身份，后续发布须由既有入口验证/准备匹配缓存，不沿用不匹配包。

## 验证结果索引

验证均绑定交接基线 + 本批 dirty scope。现有工具输出在本轮执行记录，不伪造冻结 receipt；未生成契约快照或浏览器证据。

| 层 | 命令 / 结果 | 状态 |
| --- | --- | --- |
| L0 | preflight、`git diff --check` | passed |
| L1 | `make ci.local.iteration`；16 项策略测试，静态扫描通过 | passed；增量建议含旧基线历史范围，不作为本批测试范围 |
| L1 | `scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck` | 修复后 passed，31 → 0 |
| L1 | `make verify.frontend.typecheck.strict` | passed；最后源文件调整后复验，全量 + 局部严格均 0 错误 |
| L1 | `make verify.frontend.lint.src` | passed，0 errors / 40 warnings；已移除日期修复后遗留的未使用 import |
| L2 | `make verify.frontend.boq_line_patch.unit` | passed，真实模型断言（非零） |
| L2 | `make verify.frontend.professional_detail_collection.unit` | passed，6 项矩阵/7 项 domain 场景，10 + 37 项 Python 测试及守卫 |
| L2 | `make verify.frontend.canonical_form_presenter.unit` | passed，177 项 + 10 项分区/导航反例，含日期范围映射 |
| L2 | `make verify.frontend.native_section_navigation.unit` | passed，7 + 3 + 11 + 11 + 7 项场景 |
| L2 | `make verify.frontend.cross_model_action_navigation.unit` | passed，真实跨模型导航断言（非零） |
| L2 | `make verify.frontend.native_form_action_presentation.unit` | passed，16 项测试及守卫 |
| L2 | `make verify.frontend.professional_base_field.unit` | failed：模型测试 54 项矩阵/6 项反例通过，Python 12 项中 1 项基线失败，见下文 |
| L1 | `make verify.frontend.scene_contract.consumption.guard` | passed |
| 构建 | `make verify.frontend.build` | passed；最后源文件调整后复验 5214 modules、21.02s；保留既有大 chunk warning |

### 既有失败隔离

`frontend_professional_base_field_guard` 仍锁定旧的四个 setter/query 函数签名，交接分支已经增加 occurrence 参数。通过其 `validate(read_text=...)` 注入 `git show c7980975:<path>` 的全部原始输入，复现同样 4 条诊断，与当前结果完全相等。本批不修改该守卫及其对应的 form state 实现，也不把该套件记为通过。

该失败归属交接前 P4 守卫与 P0 occurrence 接线同步；它继续阻塞整个交接分支的最终发布门禁。不得为了通过检查撤销 occurrence 保护。

证据复用：最后只删除 FormSection 的未使用 import 并保留场景合并块的 key，补跑类型检查和场景守卫/构建；此前工程量、明细、分区导航、跨模型路由和动作测试的输入未变，携带原通过结果。记录更新不影响产品测试输入。迭代入口的策略/扫描输入未引入新权限、秘密或个人数据；本批 package 脚本仅增强现有检查，不生成发布回执。

## 验证范围和状态边界

- L3 数据库升级/运行时 smoke：not_run；无后端、数据库或模块生命周期变化。
- L4 浏览器/fixture/full release：not_run；本轮仅类型与组件消费收口，未启动产品发布验收；不宣称真实浏览器验收。
- L5 冻结 Quick、独立发布复核、PR/CI、部署：not_run；既有门禁失败未关闭，不为本次类型修复启动整个分支交付周期。
- 代码类型修复已完成；批次产品验收不作全通过声明；主线集成、部署、用户验收均未完成。
- 回滚：仅回退本记录所在的类型修复提交，不回退 `c7980975` 及以前的其他执行器成果。

English: Full-project type diagnostics reduced from 31 to zero without weakening compiler settings. The existing strict script now also checks the full project. An unchanged pre-existing occurrence-signature guard failure remains outside this patch; no merge, deployment, or browser acceptance is claimed.
