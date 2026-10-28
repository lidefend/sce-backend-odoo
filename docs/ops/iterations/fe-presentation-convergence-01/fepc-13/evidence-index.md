# FEPC-13 证据索引

基线 GitHub main：`b918f2a01fbbea01b7665d8c3448ed820050ffae`。任务分支 `audit/fepc-13-title-ownership`。本文件只索引本轮读取的源码和历史证据，不是新的完整 API 响应或浏览器测量。

## 证据分类

| 类别 | 内容 | 可信范围 |
| --- | --- | --- |
| 源码事实 | 页头/原生标题/字段/动作链，见 [职责稿](title-ownership.md) | 绑定本次 main；说明实现路径，不保证当前 Demo 已部署 |
| 历史运行时事实 | FEPC-09 reused-project-facts.json 中 name occurrence 的 native_locator、required/readonly 与历史页面模式 | 原始采集样本；未重新认证或采集；字段定义不替代最终渲染状态 |
| 历史 DOM/截图观察 | FEPC-09 findings 09-04 与 presentation-observations.json，截图 ../fepc-09/01-basic.png | y=137/y=295 仅为当时测量，不作为本轮坐标 |
| 已有测试源码 | canonical_form_presenter_test.ts 的 favorite/title schema 断言 | 证明既有测试意图；本轮未重跑，不能写成新增回归通过 |
| 推断 | 缺少原生 occurrence 与页头身份的明确冗余关系，不能安全选择隐藏集合 | 限已读来源；不是证明全仓/部署配置绝无策略 |
| 未验证 | 当前页面重复标题、查看/编辑/收藏/返回/滚动运行行为、其他表单呈现 | 没有实施与浏览器验收，均 verification_pending |

## 关键限制

没有重新解析目标数据库的完整继承视图链；历史 native_locator 可定位契约 occurrence，但不能据此断言某个仓库 XML 文件是当前最终继承视图的唯一权威。`project_overview_views.xml` 的 sc-project-title 属于另一结构，不当作本样本 h1 的来源。

名称字段、收藏事件、顶部编辑入口均保留原状。阶段 D 的八类验收项只列于职责稿，未执行。组件或文档门禁通过不等于 Demo 全页通过。

## 可复核文件指纹

以下 SHA-256 为基线文件字节摘要；文件均只读，未裁剪或覆盖原始证据。源码位置以文件与函数名为准，行号仅为阅读辅助。

| 文件 | SHA-256 |
| --- | --- |
| [frontend/apps/web/src/app/pageIdentityAdapters.ts](../../../../../frontend/apps/web/src/app/pageIdentityAdapters.ts) | `f86385cf1397f9061e0d8e52046eb95dcdfa3d209d088333d5bb12997f122018` |
| [frontend/apps/web/src/app/pageIdentity.ts](../../../../../frontend/apps/web/src/app/pageIdentity.ts) | `462b93507b796036d6446d417f9fc9bb0cf3a54e98ca16fa6b4b4d3839fa64a8` |
| [frontend/apps/web/src/pages/ContractFormPage.vue](../../../../../frontend/apps/web/src/pages/ContractFormPage.vue) | `0a5a6ec1a55506903e0091e3e08462b9d0b075914264e005d704ac71575ccf68` |
| [frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue](../../../../../frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue) | `50d2443635aa103704152eb38ac0b2ac280d6d5d614d444dd374583a5ecab2a9` |
| [frontend/apps/web/src/components/template/PageHeader.vue](../../../../../frontend/apps/web/src/components/template/PageHeader.vue) | `df9b703c7404a8fae09e9f3993e524ce86a81b40f0df979d177058fdea0ba830` |
| [frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue](../../../../../frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue) | `069312cba0b4a618f31b7842927b433bdf1e2fea63f830ff844f71991de385b8` |
| [frontend/apps/web/src/pages/contractForm/ContractFormNativeCanvas.vue](../../../../../frontend/apps/web/src/pages/contractForm/ContractFormNativeCanvas.vue) | `6f8d900e96d678c778716e7e0d968c1f0cb25c4624b8c421cd4599c3466b5fff` |
| [frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue](../../../../../frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue) | `259fd2ba97cabb135956f763c21e047f1129d0edb1f033f456995a9b3c93a79c` |
| [frontend/apps/web/src/pages/contractForm/canonicalNativeFormBridge.ts](../../../../../frontend/apps/web/src/pages/contractForm/canonicalNativeFormBridge.ts) | `bdf7a1b1dae31662956217c9edf8a95da14bb243eb5c28b68997d9555b12c9fa` |
| [frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts](../../../../../frontend/apps/web/src/pages/contractForm/nativeLayoutUtils.ts) | `5b8160387b1bb4e5d571d815e2550fad121466cbcd6dd65516f96a09199d5db8` |
| [frontend/apps/web/src/app/presentation/contractFormPresenter.ts](../../../../../frontend/apps/web/src/app/presentation/contractFormPresenter.ts) | `c00b886326882c2fd4386d7e9dae29113263cc6d85760b34a7938e3c44257471` |
| [frontend/apps/web/src/app/presentation/canonicalFormFloorplan.ts](../../../../../frontend/apps/web/src/app/presentation/canonicalFormFloorplan.ts) | `e456ddf502a830e83d8bfc75a8b1d2150991a6202cbadaaf04e2ab5178544d90` |
| [frontend/apps/web/src/app/presentation/canonicalFormRenderModel.ts](../../../../../frontend/apps/web/src/app/presentation/canonicalFormRenderModel.ts) | `1d77ac6a314b45b3013ea0e230734c85cd31fd6cb24147a5afed881d34c6726b` |
| [frontend/apps/web/src/pages/contractForm/useRecordActionPresentation.ts](../../../../../frontend/apps/web/src/pages/contractForm/useRecordActionPresentation.ts) | `41b22d1fe760963c8ec58e45c774d25baf591b5a8163c37a227825f239a60d7b` |
| [frontend/apps/web/src/pages/contractForm/contractFormHeaderCanonicalActions.ts](../../../../../frontend/apps/web/src/pages/contractForm/contractFormHeaderCanonicalActions.ts) | `ce71083f8e939ed5b1b286d2324a2336cbfd0453579d6f9addcc1c25881533c5` |
| [frontend/apps/web/src/pages/contractForm/usePrimaryFormActionRuntime.ts](../../../../../frontend/apps/web/src/pages/contractForm/usePrimaryFormActionRuntime.ts) | `53a934602868b759204a3e8f1f8f6cc4aad326c5b3c9fe2ae69f6e2184a4d301` |
| [frontend/apps/web/scripts/canonical_form_presenter_test.ts](../../../../../frontend/apps/web/scripts/canonical_form_presenter_test.ts) | `196c0b6ec7523605980708d08b84d4ac3856c398f39a85964bcd94c02dc30370` |
| [docs/ops/iterations/fe-presentation-convergence-01/fepc-09/findings.md](../fepc-09/findings.md) | `703b1ee5382c0004022781c29f2299caf9650643dcaf70359e4b7445ca0a3b50` |
| [docs/ops/iterations/fe-presentation-convergence-01/fepc-09/minimal-implementation-proposals.md](../fepc-09/minimal-implementation-proposals.md) | `83bfb8e6e1e6c935fe453a9f4c53456b03b70148f1a36fd31a66e0a63d5fa6e4` |
| [docs/ops/iterations/fe-presentation-convergence-01/fepc-09/reused-project-facts.json](../fepc-09/reused-project-facts.json) | `081f3a7fc02b0b2e4b3a8c134d3dd545173c831e539bb8b8ab52a48a812b9491` |
| [docs/ops/iterations/fe-presentation-convergence-01/fepc-09/presentation-observations.json](../fepc-09/presentation-observations.json) | `689a2e2f09ae416d37a6bcebfd8460d77781b790462b86b528dfc1ff18c323b4` |

## 本轮验证与复用边界

- L0：GitHub main API 回读与本地 HEAD 一致；初始工作区干净。
- L1：对以上 21 个证据文件检查存在性和 SHA-256；检查 Markdown 引用可解析。仓库 `ci.local.iteration` 与冻结检查结果写入当前 run。
- L2–L4：not_run；未修改产品实现或测试输入，不重复认证、业务点击、部署和全页验收。
- L5：当前候选 Quick 与 PR CI 结果写入 PR 描述及 `.runtime/fepc13/handoff.json`，不在冻结后制造新代码提交。
- 失败记录保留：首次 run resume 由于尚未创建 record 文件拒绝；创建授权决策记录后重试通过，未绕过门禁。

后续只有取得标题职责/声明依据后，才进入最小实现；本 PR 不授权新的契约字段，也不标记 09-04 已解决。
