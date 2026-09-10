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
- 最终 Quick、受管 runtime/browser、独立复核、PR/CI：尚未运行。

阶段状态为 `verification_pending`，不等同于 merge-ready 或 release-ready。
