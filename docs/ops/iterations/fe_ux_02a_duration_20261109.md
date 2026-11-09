# FE-UX-02-A：Duration 统一业务表达

## 批次边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：Contract V2 `float_time` duration 的前端统一业务表达。
- Module：`businessValuePresentation`、ProfessionalBusinessValueControl、
  ListPage 和 Kanban presentation。
- Standard vs User-Specific：平台工程标准。
- Why Here：duration 已由 Contract V2 的 `float_time` widget 选定，必须在
  Form、List、Kanban 共用同一表达。
- Why Not Elsewhere：不修改 Contract V2、后端字段、行业业务规则、ACL、数据或页面宿主。
- Blast Radius：仅影响 duration 的公共表达、三个消费路径及专项测试。

## 开始前只读结论

- 当前 local formatter 位于 `professionalBusinessValueModel.ts`。
- `businessValuePresentation` 未识别 `sc.value.duration`。
- Contract V2 通过 `float_time` widget 选择 `sc.value.duration`。
- 当前正式产品契约搜索未发现实际使用该 componentKey 的字段。
- 精度权威来自 Odoo 17 `formatFloatTime`：
  - false 为空；
  - 以毫秒基准四舍五入到分钟；
  - minute 60 进位到 hour；
  - 负值保留整体符号；
  - 默认不展示秒。

## 验收

- null / undefined / false 为空值。
- 0 为零时长。
- 1、1.5、1.999 和边界舍入符合 Odoo `float_time`。
- Form、List、Kanban 输出一致。
- 不保留第二套 duration formatter。
- 定向单元、Chromium、lint、strict typecheck 和 build 非零通过。

## 执行记录

### 精度与边界裁定

- Contract V2 通过 `float_time` widget 选择 duration，不新增 precision 字段。
- 规则直接采用 Odoo 17 `addons/web/static/src/views/fields/formatters.js`
  的 `formatFloatTime`：
  - `false` 为空；
  - 按毫秒基准四舍五入到分钟；
  - minute 60 进位到下一小时；
  - 负值保留整体符号；
  - 默认不展示秒。
- 中文展示转换为：
  - `0` -> `0 小时`
  - `0.58` -> `35 分钟`
  - `1.5` -> `1 小时 30 分钟`
  - `1.999` -> `2 小时`
  - `-0.5` -> `-30 分钟`

### 实现

- `businessValuePresentation.ts`
  - 新增 `duration` semantic；
  - 新增 `formatBusinessDuration`；
  - `sc.value.duration` 和 `float_time` 进入同一 kind resolution；
  - null / undefined / false / 非法值走声明空值。
- `professionalBusinessValueModel.ts`
  - 删除局部 `formatDuration`，不保留第二套格式化。
- `ProfessionalBusinessValueControl.vue`
  - readonly duration 改用共享表达；
  - false/null/undefined 的输入投影为空，不显示字符串 `false`。
- `ListPage.vue` / `listCellPresentation.ts`
  - list column 透传 componentKey/widget；
  - duration 直接消费共享表达。
- Kanban 已通过 `presentCollectionKanbanCell -> presentDeclaredBusinessValue`
  自动进入同一路径。

### 定向验证

- `business_semantics_consistency_test.ts`
  - 16 个 duration case × Form/List/Kanban；
  - null、undefined、false、空串、0、1、1.5、1.999、0.58、
    59 秒、59.6 秒、负值、非法字符串、NaN、Infinity；
  - PASS。
- `duration_business_value_browser_test.mjs`
  - 真实 `ProfessionalBusinessValueControl` SFC；
  - 8 个代表值 × Form/List/Kanban；
  - editable false 为空字符串、editable 1.5 保持 `1.5` 写值形状；
  - 28 assertions，Chromium `147.0.7727.15`；
  - console errors：0。
- `verify.frontend.business_semantics.unit`：PASS。
- `verify.frontend.professional_business_value.unit`：PASS。
- `verify.frontend.professional_component_registry.unit`：
  162 Python tests + registry guard PASS。
- `verify.frontend.boq_import_preview.unit`：PASS。
- `verify.frontend.dev.incremental.unit`：89 tests PASS。
- `verify.frontend.style_system.guard`：PASS。
- `verify.agent.ledger.unit`：18 tests + guard PASS。
- `verify.frontend.lint.src`：0 errors；仅有既有 warning。
- `verify.frontend.typecheck.strict`：PASS。
- `verify.frontend.build`：PASS。
- `test.inventory` / `test.inventory.summary`：1678 entries current。

### 首次增量入口诊断

首次 `make ci.local.iteration` 在执行任何产品测试前被治理层阻断：

- run.json 漏登记规划器新增的 `agent.ledger`、`boq_import_preview`、
  `dev_incremental`、`style_system` 目标；
- delivery plan 对未提交的 list-surface 输入报告
  `uncommitted suite inputs changed`。

分类：validation_tooling / stage-identity 接线问题，不是产品失败。已补齐 run
登记；list-surface 证据需在 clean committed candidate 上按受管入口复验。

### Clean candidate 增量门禁

在 S1/S2 修复后的 clean 代码/测试候选
`e0a9ea7b1e1d346d085295e9b3f051be28a25e2b` 上执行：

```text
make ci.local.iteration
```

结果：

- 规划 required targets：9
- 实际执行：9
- blocked：0
- not-run：0
- status：PASSED
- receipt：
  `.runtime/frontend-dev-validation/executions/20261109T005657Z-793830-167577381/receipt.json`
- receipt SHA256：
  `20434441be19dd45981eb021325b0f5f7eaa4c6eb2c823cecb165be844049bac`

当前 main 的 delivery evidence manifest 中，`list_surface_structure` 的来源仍不是
本分支 head 的祖先，因此该 runtime suite 明确记为 `verification_pending`。
本批没有正式产品字段消费 `sc.value.duration`，重复执行整个 list-surface 矩阵
不能提供额外 duration discriminator；应在合并证据收口时按受管环境重新绑定，
而不是把历史 suite PASS 冒充当前候选证据。

### R2：Independent review 与 list-surface 证据裁定

初始固定产品/测试候选：`2a3969f5072b4554408148395b45161f3908f129`。

Independent review first returned `REQUEST_CHANGES` S1：Contract V2 collection
column projection dropped `componentKey`, so real List/Kanban did not reach the
shared duration path. The repair now preserves `componentKey` from the actual
`resolveListColumnOptions` producer and adds a producer-to-List/Kanban test.

S1 首次修复候选：`d328a72ed19d0b57b8839a73da750f22d09b4f3e`。

第二轮独立审查确认 S1 已关闭，但指出两个 S2：

- 保留所有 componentKey 会顺带改变 Kanban percentage；
- 记录中的 list-surface fingerprint 归属错误。

S2 修复候选：`e0a9ea7b1e1d346d085295e9b3f051be28a25e2b`。
集合投影只对 `sc.value.duration` 暴露 componentKey；percentage 继续维持
本批之前的普通 float 表达。实际生产者回归增至 14 cases。

修复后定向验证：

- `verify.frontend.contract_shape_projection.unit`：14 cases PASS；
- 真实列投影 `duration_hours` 同时驱动 List/Kanban 的
  `1 小时 30 分钟`；
- business semantics、professional business value Chromium、collection view
  semantics：PASS；
- lint、strict typecheck、production build：PASS；
- clean candidate `ci.local.iteration`：9/9 required targets PASS。

List Surface 输入对账：

- manifest 当前 `input_sha256`：
  `7e3563f0e2b10337eb2f3e7d18efe47b2286b88c3e929d63ec814a47920bd34d`
- 本批修改后的 suite input fingerprint：
  S1 修复前 `c8441fbdf` 对应
  `96e943aa56dd35b91636a26e2688fbd79b9bc8907a9200b4d5ab19b7b4e373cf`。
- S1 修复候选 `d328a72ed` 与其 metadata head `000ed1650` 都对应：
  `7338b5a8cd8adec53f46262b70fb2effc405445659810d4b0c56a346b893cdc3`。
- S2 收窄投影后的候选 `e0a9ea7b1` 对应：
  `692e273dd76a0d78c1f663cd69e6f5327df07ec5b299da73ca229b7fd4e3edac`。
- fingerprint 改变，因此不得把旧 runtime PASS 直接复用于本候选。
- manifest 原绑定 `0ef405468` 经过 squash 后不在本分支祖先链，工具以
  `not an ancestor` fail-closed，身份行为正确。

R2 受影响列表调用链定向验证：

- `verify.frontend.collection_view_semantics.unit`：PASS。
- `verify.frontend.list_surface_search_contract.unit`：PASS。
- `verify.frontend.list_order_field_contract.unit`：PASS。
- `verify.frontend.list_surface_evidence_binding.unit`：PASS。
- `business_semantics` 与 Chromium 已证明新增分支只改变 duration，
  money/status/date/普通值路径保持原结果。

建议裁定：不因本批重新执行完整 list-surface 大矩阵；该矩阵没有
`sc.value.duration` 正式消费者，无法提供新的 duration discriminator。
合并前仍需由独立审查确认“定向调用链覆盖充分”的裁定；在确认前，
runtime suite 保持 `verification_pending`，不写成 PASS。

### 剩余边界

- 当前正式产品契约搜索仍未找到使用 `sc.value.duration` 的字段。
- Editable duration 继续保留原始 decimal-hours 输入和小时 suffix，不改变表单
  写值形状；共享中文表达用于 readonly/List/Kanban 展示。
- `float_time.display_seconds` 未在本批扩展；默认 Odoo 分钟档已覆盖。
- 未启动 FE-UX-02-B。

### 状态

- 批次产品实现与本地定向验证：完成。
- 独立第二审查：最终 APPROVE。
- list-surface 运行证据：verification_pending。
- PR、合并、部署：未执行。

### Independent review 历史

- r1 `REQUEST_CHANGES`：发现 S1，集合投影丢失 duration componentKey。
- r2 `REQUEST_CHANGES`：S1 关闭；发现两个 S2，即 componentKey 全量暴露影响
  Kanban percentage，以及 fingerprint attribution 错误。
- r3 `REQUEST_CHANGES`：S2 关闭；只剩文档 test count 12/14 不一致。
- r4 `APPROVE`：无 S0/S1/S2；审阅 head
  `0766369880e4bb645af69e3e67d5688e789e2312`，最终产品/测试父提交
  `e0a9ea7b1e1d346d085295e9b3f051be28a25e2b`。

Independent review evidence：

- `.runtime/fe-ux-02a/independent-review.md`
  SHA256 `0598f607088da1159a5c036dd844ef109d4b0d20c181184c4832fa4e3a0d2374`
- `.runtime/fe-ux-02a/independent-review-r2.md`
  SHA256 `789604b68cd76c618b1dd7adacd3dd8b749aa5dba401ef4dcd60acd4e5be143a`
- `.runtime/fe-ux-02a/independent-review-r3.md`
  SHA256 `82f321023d65de44c5f12645ffbe111d033e92045fe1b6d2a2f9af8ceb30b6c3`
- `.runtime/fe-ux-02a/independent-review-r4.md`
  SHA256 `d2a01a6720ac61cbc0b39c71dcb3652b701ed267397003f6de4415ec0feceb98`

最终本地代码候选：`e0a9ea7b1`。

唯一剩余阻断：List Surface merge-time runtime evidence 仍是
`verification_pending`；不得改写为 PASS，也不得绕过 `make pr.merge` 的证据门禁。
