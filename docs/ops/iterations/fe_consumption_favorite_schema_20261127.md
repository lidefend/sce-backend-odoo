# FC-01 收藏 schema 身份消费切片

本切片从 PR #1019 的完整堆叠基线
`125aff3841486b22b1b284c748be5a58841274d5` 出发，只在独立工作树中处理一个
可区分产品缺口：收藏 schema 装饰仍以 `is_favorite` 字段名作为第二权威。

目标是让收藏持久化、canonical schema 装饰和 record-form schema 扁平化共同只消费
后端声明的 `boolean_favorite` widget 身份；同名普通 checkbox 必须保留为普通字段。
本切片不修改后端，不宣称浏览器、远端 CI、主线发布或产品交付完成。

## 本地验证

- `make ci.local.iteration`：13 个受影响目标、7 个测试目标、110 项测试、5 项静态检查，
  `unmapped_paths=0`、`not_run=0`、`blocked=0`，退出 0；
- `verify.frontend.contract_basis.unit`：15 项测试通过，台账 37 个绑定、0 个未闭合缺陷；
- `make verify.frontend.build ENV=dev ENV_FILE=/home/lidefend/workspace/sce-backend-odoo/.env.dev`：
  生产静态构建退出 0，构建指纹
  `2450d2b8b5c473f3cec5cab55a2c9043dcbaf50e1d4952e66de4cf3024feef6d`。

上述结果绑定堆叠基线 `125aff3841486b22b1b284c748be5a58841274d5` 上的待提交内容，
不是 clean 精确 HEAD 或浏览器行为证明。下一步是提交该切片并对新完整 HEAD 重跑精准门禁。

## clean 精确 HEAD 验证

切片提交为 `d1c69ef9edf5476dcc57603ab148f7d187267776` 后，在干净工作树重跑：

- `make ci.local.iteration`：执行 6 个目标、复用 8 个、非零测试 21 项、静态检查 4 项，
  `unmapped=0`、`not_run=0`、`blocked=0`；
- `make verify.frontend.build ENV=dev ENV_FILE=/home/lidefend/workspace/sce-backend-odoo/.env.dev`：
  构建退出 0，构建指纹
  `bbc1ec33f23cd800a9b3d7809f45eec42a2bf79249aef7c9a68142ad3d94562b`。

远端 PR #1019 当前源 HEAD 已由另一写者推进到
`40afa747ec1deaaf3027898bcba48081ff0ba4b0`。因此本切片需要先形成以该完整 HEAD
为父的堆叠提交，再由 PR #1019 的单一写者发布；本独立工作树不改动原源工作树。

该转接已在独立工作树完成：把 `d1c69ef9e` 的精确补丁应用到
`40afa747ec1deaaf3027898bcba48081ff0ba4b0`，唯一冲突是自动生成的 component-driver
清单，已由受管生成入口重新生成，而非手工二选一。转接提交仍须对新的完整 HEAD 重跑
本地精准门禁和构建。

转接后的 clean 精确 HEAD 为 `3d0e669d795485dee631789c0c9d278b2f67ce1e`：

- `make ci.local.iteration`：14 个受影响目标、8 个测试目标、128 项测试、5 项静态检查，
  `unmapped=0`、`not_run=0`、`blocked=0`；
- 前端构建通过，构建信息记录同一 source revision，构建指纹
  `4d1827fbca4079b648627969783fd77d3c4786cafb2682b3d9a54eec1e3aad9f`；
- 契约台账与当前同栈 assignee 变更合并后保持 38 个绑定、0 个未闭合缺陷。

证据记录写入后会形成新的纯记录 HEAD；发布前以该完整 HEAD 重跑定向静态/测试门禁。
