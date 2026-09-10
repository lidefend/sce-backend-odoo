# 前端官方图标资源采用（2026-09-10）

## 边界

- Formal Product Layer：P0 平台通用前端机制；验证守卫属于 P4。
- Layer Target：`ScIcon`、`@sc/ui/icons` 及现有静态图标消费者。
- Module：frontend。
- 基线：`main@040a7b87536e9d7cfa4e17c766c57be0c7d4576a`。
- 不改契约、权限、路由、业务动作、表单几何或发布语义。为完成既有交付门禁，分支内另含
  可独立审查的 P4 fixture 与验证入口修正，不将其计作前端产品能力。

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
- 独立源码与证据复核绑定产品头 `bc86a5f34e1d1a4133eab8b1961e561471131636`，结论为
  APPROVE，未发现 S0/S1/S2 问题。后续提交仅处理 P4 交付验证工具与 fixture 对齐，不再修改
  官方图标产品实现。

## P4 交付支持与剩余风险

- 分支另含四类 P4 修正：付款专项 fixture 目标、execution fixture 的公司归属、对话框安全取消
  按钮的真实 autofocus 断言，以及受管 release runtime identity 入口和请求/响应诊断。
- 在 `b214aba61e9b48b5e6bf510188c451ac013cb163` 上，release audit 的静态与导航检查、性能探针、
  J10 对话框焦点检查通过。
- J11 多公司“我的工作”检查仍未通过：实际请求 `company_id=9`，响应 `query_scope` 也为 `[9]`，
  但返回事项为空。证据排除了旧响应污染，问题归为既有 P1 多公司 My Work 服务后续，不属于
  官方图标实现，也不会通过删除断言或放宽门禁掩盖。
- 因此本地结论是“官方图标产品范围及独立复核完成，完整 release audit 存在独立阻断”；不声称
  merge-ready 或 release-ready。

本地实现、受影响范围验证和独立复核已完成；阶段进入 draft PR 交付。推送与创建草稿已获授权，
必需 CI 以远端 exact-head 实际结果为准，不预填通过。这里不声称全系统业务交互、merge-ready
或 release-ready；Ready、合并和发布均未授权。
