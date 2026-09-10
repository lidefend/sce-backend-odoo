# 前端官方图标资源采用（2026-09-10）

## 边界

- Formal Product Layer：P0 平台通用前端机制；验证守卫属于 P4。
- Layer Target：`ScIcon`、`@sc/ui/icons` 及现有静态图标消费者。
- Module：frontend。
- 基线：`main@040a7b87536e9d7cfa4e17c766c57be0c7d4576a`。
- 不改契约、权限、路由、业务动作、表单几何、数据库、fixture 或发布链。

## 表达归属

| 表达 | 权威 | 页面职责 |
|---|---|---|
| 业务无关语义名 | `ScIconName` | 只选择已有语义名 |
| 官方图形资源 | `@sc/ui/icons` → `tdesign-icons-vue-next@0.4.9` | 不导入 vendor 路径 |
| 尺寸与颜色 | `ScIcon` props + currentColor | 消费既有尺寸和语义色 |
| 可访问名称 | 外层按钮/控件 | 图标保持 `aria-hidden`，文字或 label 保持权威 |

## 官方能力对照

| 情况 | 处理 | 验证 |
|---|---|---|
| 官方单图标组件可覆盖 | 通过包根级公开 named export 接入 | 49 项映射完整性测试 |
| 页面语义名与 vendor 名不同 | `ScIcon` 集中映射 | TypeScript exhaustiveness |
| 未知 Odoo 图标 dialect | fail-closed，仅保留可访问文字 | presenter 反例测试 |
| 手写 SVG、emoji、字符三角形 | 删除并由 `ScIcon` 替代 | repo guard 零残留 |

采用单图标组件而非默认 SVG sprite，避免运行时加载官方 CDN。生产构建相对基线主入口
gzip 约增加 7.2 KB；构建成功，未外部化依赖。

## 验证状态

- 基线 `make verify.frontend.quick.gate`：PASS。
- `make verify.frontend.official_icon.unit`：PASS，49 个语义映射、4 个反例守卫。
- 严格类型、协作组件、层级工作表、表单 presenter：PASS。
- lint：0 error，32 条既有 warning。
- `make verify.frontend.build`：PASS。
- 生成清单刷新后的最终 `make verify.frontend.quick.gate`：PASS；官方组件清单为 0 gap。
- 浏览器证据工具补充显式 `captureOfficialIconResource`，同时核对可见官方 SVG、语义名和旧 `ScIcon` SVG 残留；对应 9 项 Python 测试 PASS。
- 冻结浏览器候选：`6c003ea4cb4e90f6c1913960ec63dc1932eced66`；完整 tracked、staged、untracked 指纹为 `e6739c01a96f0489ba35be0ba62674722075dcda7e0097633fb9953b12f49a86`（7377 paths）。
- 候选复用受管 `local.dev`：project `sc-local-dev`、database `sc_dev_demo`、API `18081`、candidate frontend `5176`。`local.dev.verify_authority` PASS；没有升级模块、重置 fixture 或写数据库。
- light 1440/390 覆盖首页、我的工作、收入合同层级工作区，共 6 个路由视口。每个样本均有可见 `data-icon-source="tdesign"` 图标，旧 `svg.sc-icon` 数量为 0；可见官方图标数分别为桌面 34/19/90、移动 23/7/13。
- 浏览器摘要 `artifacts/playwright/official-icon-resource-adoption-6c003ea4/summary.json` 为 `pass=true`、`mutationCount=0`、errors/failures empty；启动 `system.init` 成功，层级工作区同时取得正式 `ui.contract.v2` 页面结果。截图人工抽查未发现图标裁切或布局回归，候选服务已停止。

本地实现与受影响范围验证已完成；阶段状态保持 `verification_pending`，等待独立源码/证据复核及 PR 交付授权。这里不声称全系统业务交互、merge-ready 或 release-ready；推送、PR、合并和发布均未执行。
