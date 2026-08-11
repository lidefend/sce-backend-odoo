# 产品发布探针数据库路由收口（2026-08-11）

## 问题

隔离环境采用多数据库入口。登录、`system.init`、产品等级切换和性能采样虽然携带 token
或在 JSON 中声明数据库，却没有像正式前端一样持续发送 `X-Odoo-DB`。认证前无法选库
时会返回 500，认证后请求会返回 401；旧门禁因此产生假失败或以 warning 跳过运行验证。

## 修复

- 通用登录与 bootstrap 探针在认证前发送 `X-Odoo-DB`。
- bundle 安装、UI 表面稳定性、产品等级覆盖和性能采样在认证后继续携带同一数据库路由。
- 四类探针均新增单元测试，断言数据库头不能在调用链中丢失。
- 未放宽性能预算、产品等级规则、表面形状规则或错误判定。

## 隔离验收

- `verify.bundle.installation.ready`：PASS。
- `verify.ui.surface.stability.ready`：PASS。
- `verify.product.tier.coverage`：PASS，并完成参数恢复。
- `verify.platform.performance.smoke`：PASS，所有样本为 HTTP 200 且 `ok=true`。
- `verify.product.release.ready`：PASS。
- 执行数据库：`sc_product_center`；未访问日常开发或生产环境。

运行生成的时间戳和机器性能报告没有纳入提交，避免用一次隔离机采样覆盖已冻结的正式发布
证据；本提交只固化探针契约、测试和可复现门禁入口。
