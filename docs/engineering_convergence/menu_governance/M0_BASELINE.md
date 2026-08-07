# M0：菜单治理基线冻结

## 冻结身份

| 项目 | 值 |
| --- | --- |
| 仓库 | `/home/lidefend/workspace/sce-backend-odoo-menu-governance` |
| 分支 | `feature/product-menu-governance` |
| 产品提交 | `6250dc64eeb67bdd5a5e6686e6ac7c8233e0d4ce` |
| 模块 | `smart_construction_core` |
| 环境 | 本地源码，静态只读 |
| 数据库/角色/公司 | 未使用 |
| 运行时菜单 contract | 未采集 |

初查的“320 个 `<menuitem>` 声明、304 个唯一 ID”是待验证假设。生成器按 `__manifest__.py` 的实际加载顺序解析 205 个 XML 文件，已验证该假设成立；同时识别 `ir.ui.menu` record patch，因此有效静态资产口径与 304 不应混为一谈。

## 证据口径

静态全集定义为 `smart_construction_core/__manifest__.py:data` 中加载的 XML，而不是随意扫描目录后宣称都已安装。目录中存在但未进入 manifest 的 XML 单独列入 JSON 的 `unloaded_xml_files`，不能计入正式加载资产。

每份报告记录：完整 commit SHA、tree SHA、分支、manifest 文件清单、全部来源文件的合并 SHA256、声明历史、统计口径和初查差异解释。

## 运行时采样裁决

本轮没有可证明独占的数据库、账号、端口和证据目录租约，因此不启动服务、不登录、不占用列表专题浏览器资源。所有 `runtime_visible`、`route_reachable` 保持 `null`，覆盖率明确为 0；任何无采样却写入布尔结论的报告都会失败关闭。
