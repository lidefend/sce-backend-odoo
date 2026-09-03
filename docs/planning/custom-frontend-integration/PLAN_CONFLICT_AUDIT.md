# SCE 前端专题规划冲突审计

> 审计日期：2026-08-06  
> 权威范围：本目录的 `README.md` 与九个非菜单专题 `docs/*.md`  
> 结论：规划层冲突扫描为 0；本结论不等于实现、构建、运行时或发布验收通过。

## 1. 审计口径

根目录 [`README.md`](README.md) 是唯一总控真相源。专题正文只保留与其一致的候选边界；原型源码与 `demo/`、`.workbuddy/` 不构成实施决策，本次未修改。

本轮检查以下可执行冲突：

1. Design System 创建平行 token 真相源，或从页面契约直接接受整套 token、主色和任意 Logo URL。
2. Theme 把 capability 开关或权限放入品牌/主题配置。
3. Chart 新增顶层图表字段，或允许客户端提交自由聚合参数、公式或任意图表 option。
4. Gantt 新增顶层页面类型，而不是使用统一 envelope 中的版本化 capability。
5. Mobile 根据 viewport 下发不同页面契约、权限或业务数据 API。

## 2. 清零结果

| 规则 | 处理结果 | 证据 |
| --- | --- | --- |
| 平行 token / 直接主题字段映射 | 已删除可执行映射，改为 canonical semantic token 与既有包的增量映射 | `design-system/docs/DESIGN_SYSTEM.md` 第五章 |
| 任意品牌资产 | 已删除 URL 示例，限定受控附件/静态资产引用并要求来源校验 | `theme-frontend/docs/TECH_DESIGN.md` 第 7.1 节 |
| 主题承载权限 | 已删除主题内的能力开关示例，明确 capability/permission/action 才是权威来源 | `theme-frontend/docs/TECH_DESIGN.md` 第 7.1 节 |
| 顶层图表字段与自由聚合 | 已替换为 `visualization.chart`、登记 metric/dimension 和受权 dataset ref | `echarts-frontend/docs/TECH_DESIGN.md` 第 5 节 |
| 甘特顶层页面类型 | 已替换为 `planning.gantt` capability，并冻结首批只读 | `gantt-frontend/docs/TECH_DESIGN.md` 第 7 节 |
| 按 viewport 分裂契约/API | 已删除相关建议，明确同一 envelope、权限、动作与业务 API | `mobile-frontend/docs/TECH_DESIGN.md` 第 12 节 |

## 3. 九专题状态

| 专题 | 轨道 | 当前状态 | 下一准入 |
| --- | --- | --- | --- |
| Design System | A | 仅允许审计现有 `@sc/design-tokens`、`@sc/ui` 并增量收口 | 冻结 legacy → canonical 映射和共享 UI 接口 |
| Theme | A | 现有机制增量收口，不新建 Theme Engine | allowlist、品牌资产 carrier、P2/P3 覆盖顺序评审 |
| Mobile | A | 同一 renderer 的响应式收口 | `ui.presentation_hints` Schema 与五视口基线 |
| BOQ | A | 先审计既有导入，再做最小真实闭环 | G2 权限、格式、动作和失败语义证据 |
| ECharts | B | `ADR-PENDING` | 依赖、许可证、CVE、包体、数据口径和回退 ADR |
| Excel | B | `ADR-PENDING`；BOQ 既有导入除外 | 上传、扫描、job、存储、权限和格式 ADR |
| Gantt | B | `ADR-PENDING` | renderer 选型、日历/依赖权威和性能 ADR |
| PDF | B | `ADR-PENDING` | 引擎隔离、字体、模板沙箱、job 和 CSP ADR |
| Editor | B | `ADR-PENDING` | canonical format、服务端净化和附件 ACL ADR |

菜单治理仅作为正式入口、导航契约和最终发布验收的依赖，不纳入本轮九专题实施队列。

## 4. 后续准入

规划冲突清零只完成 G0 的文档条件。后续仍须依次满足：

1. 冻结主仓、服务、运行时与静态产物 SHA，并记录构建和浏览器版本。
2. 环境无关验收在批准环境中可复现，证据绑定同一候选 SHA。
3. Design System 与 capability host/schema 的共享接口冻结并实行单写入者。
4. BOQ 既有导入审计和最小真实闭环通过后，才评审五项新平台能力 ADR。
5. Theme/Mobile 只做轨道 A 收口；任何新依赖或新事实接口重新进入 ADR。

## 5. 复核命令

以下扫描只覆盖权威 Markdown，不读取或修改原型与临时目录：

```bash
printf '%s\n' README.md PLAN_CONFLICT_AUDIT.md {design-system,theme-frontend,echarts-frontend,boq-frontend,excel-frontend,gantt-frontend,pdf-frontend,editor-frontend,mobile-frontend}/docs/*.md
rg -n 'surface_policies\.(theme|primary_color|logo_url)|"features"[[:space:]]*:|"type"[[:space:]]*:[[:space:]]*"chart"|"group_by"[[:space:]]*:|"view_type"[[:space:]]*:[[:space:]]*"gantt"|viewport=mobile' README.md {design-system,theme-frontend,echarts-frontend,boq-frontend,excel-frontend,gantt-frontend,pdf-frontend,editor-frontend,mobile-frontend}/docs/*.md
```

第二条命令预期无输出。审计文本描述规则时避免复用上述可执行代码形态，因此该扫描结果可以直接作为 0 冲突证据。
