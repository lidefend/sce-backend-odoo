# FE-EXPRESSION-02A/B 20261122

## 输入结论

R09 在当前验收运行身份上已经将问题从推测转为可复现事实。本批只处理：

1. `route.authority.validate` 的 503 被错误显示为“无权访问”。
2. 列表导出失败没有保留后端原因与可重试反馈。
3. 付款申请 390 手机页头的状态/操作区被挤压。
4. 项目台账同时存在两个 H1。

02C 的业务值统一表达和 02D 的项目经理收入合同配置缺口只做诊断，
本批不实现。

## 层与范围声明

- `Formal Product Layer`: P0 generic frontend runtime
- `Layer Target`: route error presentation, collection feedback and shared responsive heading hierarchy
- `Module`: `frontend/apps/web`
- `Standard vs User-Specific`: platform generic
- `Why Here`: HTTP error meaning, transient feedback and responsive layout belong to the generic frontend
- `Why Not Elsewhere`: no contract field, permission result, state machine, industry default or customer preference is changed
- `Blast Radius`: route guard failure branches, list export operation, shared ProductPageHeader, embedded Scene heading ownership

## 必须守住的边界

- 403 remains fail-closed and continues to route to access-denied.
- A transport/5xx failure is not shown as a permission denial.
- Export failure keeps `reason_code`, message, trace ID and retry path.
- Mobile layout preserves identity, status and actions; important business information is not hidden.
- Exactly one visible H1 remains authoritative.
- No backend, database, fixture, customer module or Renderer Registry change.

## 当前状态

`active`。02A/02B 源码与聚焦行为锁已通过，生产构建、增量入口、真实浏览器视口
和最终精确 HEAD 验证尚未完成。

## 首轮实现

- Route authority 失败分为 authentication、forbidden、not-found、conflict、
  service、network；只有明确 401/403/404/409 才进入对应业务错误页，5xx/network
  不再显示成无权访问。
- Intent envelope 的数字错误码不再被丢弃；真实 403 仍 fail-closed。
- 导出失败保留后端 message、reason code 和 trace ID；请求未完成时阻止重复提交。
- 标准列表只由 CollectionBatchActionBar 展示一次反馈，并提供 live region。
- ProductPageHeader 在 600px 以下把标题、状态、操作排为全宽三行。
- 嵌入 ActionView 或 ContractForm 的 Scene 不再输出竞争性隐藏 H1。

聚焦结果：

- route authority：传输/权限分类通过。
- record form return：22 个案例通过。
- selection feedback：失败原因/trace 保留，重复提交被阻止。
- ProductPageHeader：77 个 Python 测试、28 个模型案例和 adapter contract 通过。
- 标题所有权：21 个案例通过。
- incremental planner：208 个测试通过。
- lint：0 error；strict typecheck 通过；contract-basis open defects=0。
- 首次增量入口将原先零引用的 `verify.frontend.record_form_return.unit` 变成真实
  引用，验证覆盖工具按治理入口移除 stale disposition；没有放宽 coverage 基线。
- `ci.local.iteration` 最终执行 22 个真实受影响目标，`unmappedPathCount=0`；
  receipt SHA256 =
  `8b1b8566d27b40156b00d8f36d36db25c7020934bf693a192b963d3610c2c466`。
- acceptance 生产构建通过；dist artifact SHA256 =
  `643f1f26ce665d05b05f6cf7a2ea509f1a62fe72d32dcd48e0f62b905be774dc`。
- 初步浏览器矩阵 10/10 PASS：四个样板的 1440/390 页面均只有 1 个 H1 且无横向
  溢出；付款申请 390 的状态和操作区按全宽上下排列；项目台账不再出现重复 H1。
- 导出 500 暴露后端 message、`EXPORT_SERVICE_UNAVAILABLE` 与 trace，且仅发出
  一次请求；route authority 503 进入 `/route-error`，显示“服务暂时不可用”与
  trace，不再显示“无权访问”。
- 浏览器仅有两条预期 Console resource error，分别来自注入的 500 和 503；
  page errors 为 0；浏览器加载的 72 个资源均存在于当前 dist-release。

最终 code HEAD `b9d5db978` 已完成精确构建与浏览器回归：

- build-info source = `b9d5db978`，tree = `636644e0b`；
- acceptance runtime source revision = `b9d5db978`；
- runtime frontend build SHA256 =
  `177560323d737f3a1b590b765657c65dc0bfceeebe7f65724c8e3c44060376d8`；
- 浏览器 10/10 PASS，0 failure，0 page error，72/72 加载资源存在；
- 两条 Console error 仅为注入的 500/503 资源错误；
- browser report SHA256 =
  `ec28b526a5fa76b1903af37e90a35b333599d1b000d19fcd76e7b9e11cc0ef8a`；
- `ci.local.iteration` 11 个受影响目标通过，receipt SHA256 =
  `56e160073165681ca9b489444c5ce5e84abec3d87e2c4113cb87c557a309e83f`。

P2 收尾：RouteErrorView 只保留一个 H1 主标题；没有 `from` 时重试按钮禁用；
嵌入 SceneContractBlockGridView 在 loading/error 阶段保留隐藏语义 H1，ready 后由
PageRenderer 接管。

## 02C / 02D 诊断

- `.runtime/FE-EXPRESSION-02/01-business-value-diagnosis.md`
- `.runtime/FE-EXPRESSION-02/02d-pm-income-contract-diagnosis.md`

本轮没有实现 One2many/附件表达改造，也没有修改项目经理收入合同配置。
