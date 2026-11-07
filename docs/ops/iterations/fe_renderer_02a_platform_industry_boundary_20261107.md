# FE-RENDERER-02A：平台与行业 Renderer 边界收敛

## 批次边界

- Formal Product Layer：P0 平台内核产品。
- Layer Target：前端契约呈现、FormSection 字段调度与行业 Renderer 扩展注册。
- Module：Contract V2 presentation、semantic/component registry、industry renderer manifest。
- Standard vs User-Specific：平台工程标准，不属于客户或单一行业业务规则。
- Baseline：`1fc108f6c166124ae226bc982da90f281e65f8a4`。
- 独立候选参考：PR #834 `ac7a858fd394563347baa805055cf546727a91f2`，只读，不修改、不 rebase、不 cherry-pick。

## 目标

移除正式主线中平台对付款结算行业组件的直接依赖。平台 carrier 只保留 platform 类别，
行业 componentKey 由独立 manifest 注册，FormSection 只通过统一 Resolver 消费。

## 明确排除

不实现 `rendererVersion`、`contractVersion` 协议扩展或真实 capabilities；不新增行业 Renderer；
不修改 Contract V2 Schema、金额/日期/状态表达或 `@sc/ui`；不修改 PR #834；不部署、不合并。

## 结果索引

- L1/L2：`make ci.local.iteration`，结果以当前 run 的逐 target 回执为准。
- 注册表与生成器：`make verify.semantic.registry.lint`。
- Renderer 行为：`make verify.frontend.professional_component_registry.unit`。
- 详情集合回归：`make verify.frontend.professional_detail_collection.unit`。
- Lint / strict typecheck：由 FE-LOOP-01 增量执行入口自动纳入。
- L3/L4：在全部 L1/L2 通过后执行受管真实浏览器验收与独立 PR 门禁；结果另行回填。

## 实现结论

- 前端平台 carrier `semantic_registry.generated.ts` 只包含 platform 类别，现有 25 个平台字段组件。
- 行业 Renderer 由独立 `industry_renderer_manifest.generated.ts` 承载，当前 1 个行业组件。
- `FormSection` 已移除 `PaymentSettlementDetailCollectionControl` 的直接 import 和固定分支，改为统一 Resolver 的 `componentKey + fieldType + renderer identity` 解析。
- 行业扩展通过 `registerIndustryRendererExtensions` 整批校验后原子提交；重复 key/semantic/renderer、缺失 component、空字段类型、平台保留 renderer 均拒绝。
- `main.ts` 在 `bootstrapApp()` 和 `app.mount()` 之前调用 `registerIndustryRenderers()`。
- `rendererVersion`、真实 capabilities 与安装/卸载生命周期仍未实现，未把空能力数组宣传为已交付能力。

## L1/L2 结果

`make ci.local.iteration` 实际执行 14 个必需 target，全部退出 0：

- `ci.local.iteration`：PASS，`executedTargetCount=14`，`notRunTargets=[]`，`unmappedPathCount=0`。
- Receipt：`.runtime/frontend-dev-validation/executions/20261107T140333Z-1391760-859607509/receipt.json`。
- Semantic registry lint：PASS；generator `--check` 对 Python carrier、平台 carrier、行业 manifest 和 domain carrier 四项均一致。
- Professional component registry：Node 行为断言和 154 个 Python 守卫/负例通过。
- Professional detail collection：模型、真实 FormSection SSR、付款结算引入契约和 46 个 Python 守卫用例通过。
- Canonical form presenter、Contract V2 occurrence authority、primitive adapter、page pattern、product pattern、style system、lint、strict typecheck、agent ledger/resume、增量规划器均通过。
- Component driver inventory 已刷新；required=33、missing=0、raw=0。
- Lint 仅有 4 个既有 warning，无 error；strict typecheck 无诊断。

## 未计入通过

- 直接诊断 `make verify.frontend.industry_agnostic.guard` 仍报告 68 个既有全域行业知识 finding，不属于本批 P0 Renderer 边界的通过证据；更广泛的前端行业知识收敛仍留在后续 FE-RENDERER 批次。
- 真实浏览器、当前 HEAD 的远端五项门禁和 PR 审查尚未执行。
