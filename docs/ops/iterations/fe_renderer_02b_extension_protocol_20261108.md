# FE-RENDERER-02B：Renderer 扩展协议与生命周期

## 批次边界

- Formal Product Layer：P0 平台内核产品。
- Layer Target：Renderer extension protocol、Contract V2 版本兼容和宿主能力边界。
- Module：component registry generator、professional Renderer resolver、FormSection host。
- Standard vs User-Specific：平台工程标准。
- Baseline：`ed066f7bf1ae4a5a567dfad85ef7f7c745c6ae59`。

## 目标

在 FE-RENDERER-02A 的 platform/industry 分离基础上，把 `rendererVersion`、
Contract V2 支持区间、真实宿主能力、安装和卸载生命周期纳入同一协议。

## 明确排除

不修改 Contract V2 Schema，不迁移第二个行业 Renderer，不修改付款业务语义、
金额/日期/状态表达或 `@sc/ui`，不修改 PR #834，不部署。

## 实现结论

- `component.yaml` 为每个字段组件投影 `renderer_version`、`contract_version`
  有界区间和 `requiredCapabilities`；平台默认 Renderer 版本为 `1.0.0`，
  当前支持 Contract V2 `>=2.0.0 <2.3.0`。
- 能力及 provider 由 `capability_providers` 单一声明。本批真实能力为
  `form.relation.one2many`，提供者为 `FormSection.relationAdapter`。
- 平台字段组件当前禁止声明宿主能力；执行器尚无平台分支的等价消费点，
  因此生成器和守卫拒绝声明，避免形成新的 declared-but-unconsumed。
- 付款结算行业 Renderer 声明需要 `form.relation.one2many`；FormSection
  仅在页面版本兼容且 relation adapter 存在时提供该能力。
- 行业注册仍为原子提交；新增原子注销。非法注销在修改任何状态前失败。
- `main.ts` 启动时安装行业 Renderer，Vite runtime dispose 时注销。
- FormSection 输出 page Contract V2 版本、Renderer 版本和支持契约区间标记，
  使运行时绑定可审计。

## 测试覆盖

- Vue 单测覆盖合法版本、非法 semver、非法区间、版本上下界、能力缺失、
  未知 provider、重复注册、身份不匹配和原子注销。
- 实际 FormSection SSR 覆盖“行业 Renderer 已注册但宿主能力缺失”显示
  fail-closed，以及能力提供后正常渲染行业组件。
- 生成器覆盖 capability/provider 投影、平台能力拒绝、未知能力拒绝和 carrier
  一致性。

## 当前状态

实现与 L1/L2 已完成。

- `make ci.local.iteration`：PASS，14 个必需 target，`notRunTargets=[]`，
  `unmappedPathCount=0`。
- Receipt：`.runtime/frontend-dev-validation/executions/20261107T170846Z-2296061-428503222/receipt.json`。
- Semantic registry：44 个 Python 测试及四项 carrier 一致性检查 PASS。
- Professional component registry：Node 版本/能力/生命周期断言与 162 个守卫测试 PASS。
- Professional detail collection：真实 FormSection SSR 149 checks PASS，其中包含
  行业 Renderer 已注册但能力缺失时 fail-closed、能力提供后正常渲染。
- Lint 0 error；strict typecheck PASS；component inventory required=33 missing=0。
- 生成器刷新、真实浏览器和远端门禁尚待执行。
