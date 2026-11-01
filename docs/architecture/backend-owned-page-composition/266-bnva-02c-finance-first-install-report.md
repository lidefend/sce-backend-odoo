# 266 · BNVA-02C-02D · 财务页面首次安装报告

## 静态已验证

- 产品 XML 种子中 `smart_core.lowcode` 预置配置数量 = 0，即首装不依赖任何预置
  用户低代码配置（`rg -c smart_core.lowcode addons/smart_construction_core/data/*.xml` 为空）。
- 三个财务配置 source 均为 `smart_construction_core.product_release`，status=published。

## 未执行（not_run）

真实全新隔离库安装（drop/install 正式模块 + 登录 + 页面操作）未执行；需
`local.clean` 可处置库 + 模块安装 + fixture 角色。不得用已有开发库历史配置替代。

