# SCE 前端能力专题总体集成计划

> 状态：架构草案（规划冲突已清零；等待 G0 其余准入门禁）  
> 目标仓库：`/home/lidefend/workspace/sce-backend-odoo`  
> 适用范围：design system、theme、ECharts、BOQ、Excel、Gantt、PDF、Editor、Mobile、产品菜单治理  
> 本目录定位：方案与原型输入，不是可直接复制进主仓库的发布包
> 实施授权：十专题并行实施尚未批准；本轮仅允许文档收敛、现状审计和验收基线建设
> 冲突审计：见 [`PLAN_CONFLICT_AUDIT.md`](PLAN_CONFLICT_AUDIT.md)

## 0. 单一真相源与执行禁令

本文件是本规划目录唯一的总控真相源。各专题 `docs/*.md` 只描述受本文件约束的候选方案；其中标记为 `SUPERSEDED`、`ADR-PENDING` 或“禁止实施”的内容不得用于排期、采购依赖或编码。`.workbuddy/`、`demo/` 和临时构建文件仅为历史证据或原型，不构成架构决策。

在下列条件全部满足前，禁止启动十专题并行开发：

1. 冻结并记录当前前端基础设施验收 SHA；
2. 专题正文与本计划的冲突扫描为 0；
3. 现状、差距和新增工作清单完成评审；
4. 环境无关验收框架可复现；
5. 既有 BOQ 导入能力完成只读审计；
6. BOQ 只读展示与既有导入入口形成最小真实闭环；
7. 其余新平台能力分别完成 ADR 后才可逐项授权。

## 1. 总体结论

本目录的十类能力有产品价值，但不能按十个平行前端工程分别并入主仓库。正确路线是：

1. 复用现有 pnpm workspace、`@sc/design-tokens`、`@sc/ui`、`@sc/schema`、`@sc/sdk` 和 Web 应用。
2. 通用渲染机制归 P0 平台前端；施工业务语义归 P1 `smart_construction_core`；客户品牌与稳定偏好归 P2 客户模块；管理员即时配置归 P3；迁移、验证和发布工具归 P4。
3. 页面结构继续遵循：`Business Truth → Native Expression → Native Parse → Contract Governance → Scene Orchestration → Frontend`。
4. 前端只消费正式场景编排契约，不解析 Odoo XML，不按 `model`、`route`、角色码或中文关键字猜测业务语义。
5. 原型代码先作为设计验证材料审计，禁止整目录复制。每项能力通过契约、权限、依赖和性能准入后再按目标层迁移。

## 2. 当前架构基线

### 2.0 现状—差距—新增工作

| 能力 | 已有事实 | 当前差距 | 本计划新增工作 | 轨道 |
| --- | --- | --- | --- | --- |
| 设计令牌/UI | 已有 `@sc/design-tokens`、`@sc/ui`、硬编码颜色守卫，列表、表单、导航已完成多轮收敛 | 仍需盘点重复 token、组件状态和高级 renderer 接口 | 增量收口，不重建组件库 | A：既有能力接入/收敛 |
| Theme | 已有浅色导航、语义色和现有主题能力 | 品牌来源、覆盖白名单、回退契约需核实 | 约束现有机制；不新造 Theme Engine | A |
| Mobile | 同一 SPA 已覆盖 1440/1280/1024/768/390 等视口，列表和表单已有响应式形态 | 需消除局部溢出和信息优先级漂移 | 在同一 renderer 上继续收口 | A |
| 页面契约 | 已有 `app/contracts`、`app/runtime`、`app/assemblers` 及 schema/sdk 包 | 专项 payload、版本兼容和未知能力降级需统一 | 扩展统一 envelope，不建八个顶层宿主 | A |
| BOQ | 后端已有 `project.boq.import.wizard`、项目导入动作，并在服务端解析 CSV/XLS/XLSX | SPA 对既有导入向导、只读投影和证据尚未形成闭环 | 先审计并接入既有能力 | A |
| Chart/Gantt | 有原型，无获批依赖或权威数据契约 | 指标、维度、日历、依赖算法和性能未决 | ADR 后建设通用 renderer | B：全新平台能力 |
| Excel/PDF | 有原型，尚无获批的通用 job/引擎方案 | 权限、存储、扫描、进程隔离、供应链未决 | ADR 后建设后端服务与薄 UI | B |
| Editor | 有交互原型，无 canonical format 与净化决策 | XSS、附件 ACL、并发、输入法未决 | ADR 后建设受限编辑能力 | B |

轨道 A 优先，目标是利用已经存在的产品能力完成真实闭环；轨道 B 不得以原型中的库或实现路径为既定前提。

### 2.1 运行平面

- SPA：`frontend/apps/web`，Vue 3 + TypeScript + Pinia + Vue Router + Vite。
- Odoo Portal：`/portal/*` 服务端页面。
- SPA API 仅使用 JWT Bearer，禁止 Cookie；Portal 使用 Odoo session cookie。
- `/portal/bridge` 仅承担 JWT 到 Odoo session 的桥接。
- `act_url` 是过渡能力，不能成为新增专题的长期导航主干。

### 2.2 前端分层

| 层 | 现有载体 | 本计划要求 |
| --- | --- | --- |
| Shell | `apps/web/src/layouts` | 只负责壳、导航容器、响应式和通用状态 |
| Routing | `router`、`app/resolvers` | 路由解析，不推断业务身份 |
| Contract | `app/contracts`、`packages/contracts`、`packages/schema` | 所有新能力先定义可版本化 Schema |
| Runtime | `app/runtime`、`packages/action_runtime` | 数据加载、动作执行、取消、重试和错误语义 |
| Assembly | `app/assemblers` | 把场景契约装配成通用渲染模型 |
| Render | `packages/ui`、页面组件 | 纯呈现和交互，不拥有业务事实 |

### 2.3 已知结构性约束

- `ActionView.vue`、`ContractFormPage.vue` 等仍处于拆分期，新专题不得继续扩大超级组件。
- 设计令牌和 UI 包已经存在，禁止创建第二套平行 Token/组件真相源。
- 当前 Web 生产依赖仅有 Vue、Pinia、Vue Router；新增大型依赖必须单独做体积、安全、许可证和维护性评审。
- Workbench 仅用于诊断，不作为产品入口。

## 3. 产品与模块归属

| 专题 | Formal Product Layer | Layer Target | 业务/配置归属 | 禁止事项 |
| --- | --- | --- | --- | --- |
| Design System | P0 | `frontend/packages/design-tokens`、`packages/ui` | 平台通用机制 | 另建平行组件库或 Token 命名体系 |
| Theme | P0 机制 + P2/P3 配置 | theme runtime + contract | P0 支持主题；P2 品牌默认；P3 即时配置 | 将客户品牌硬编码进共享前端 |
| ECharts | P0 渲染适配 + P1 指标契约 | visualization adapter | 指标定义、聚合口径归业务后端 | 前端自行计算财务/项目事实 |
| BOQ | P1 业务契约 + P0 通用树表 | `smart_construction_core` + UI renderer | BOQ 模型、权限和动作归行业模块 | 共享前端按 BOQ 模型名写分支 |
| Excel | P0 导入导出机制 + P1/P2 模板 | 后端专用 intent + UI wizard | 字段权限、模板和校验归后端 | 浏览器绕过权限批量导出/写入 |
| Gantt | P0 时间轴 renderer + P1 任务语义 | UI renderer + construction contract | 依赖关系、关键路径和写动作归后端 | 前端自行决定可写字段和依赖合法性 |
| PDF | P0 报告机制 + P1/P2 模板 | 后端报告服务 + preview UI | 模板归对应产品层 | iframe 直接信任任意 HTML/URL |
| Editor | P0 通用编辑器 + 业务字段策略 | `packages/ui` + contract | 可编辑范围、净化、附件权限归后端 | 仅依赖浏览器净化或存原始危险 HTML |
| Mobile | P0 响应式 renderer | Shell、UI、assemblers | 业务内容仍由同一契约提供 | 建第二套移动业务页面或移动专用事实接口 |
| 产品菜单治理 | P0 导航机制 + P1/P2/P3 菜单内容 | 后端菜单/权限契约 + 现有 Shell | 正式命名与行业归集由产品层负责 | 前端硬编码菜单树、按名称猜权限、重建 XML ID |

## 4. 目标代码布局

```text
frontend/
├── apps/web/src/
│   ├── app/contracts/          # 契约消费与严格模式
│   ├── app/runtime/            # 请求、动作、上传下载、任务状态
│   ├── app/assemblers/         # chart/tree-grid/gantt/report/editor 装配
│   ├── components/             # 应用级薄组件
│   └── layouts/                # AppShell 与响应式壳
├── packages/design-tokens/     # 唯一跨端 Token 真相源
├── packages/ui/                # 通用 Sc* 组件与高级 renderer
├── packages/schema/            # 契约 Schema 与版本兼容
├── packages/sdk/               # API/intent 类型化客户端
└── packages/tools/             # 构建、体积、契约生成与审计工具

addons/smart_core/              # P0 契约、专用 intent、配置治理机制
addons/smart_construction_core/ # P1 BOQ/项目/资金等行业事实与默认契约
sce_customer_<tenant>/          # P2 客户品牌、模板和稳定偏好（仓外私有）
scripts/verify/                 # P4 门禁、迁移和证据生成
```

本目录中的 `*-frontend/src` 只能作为候选实现参考。迁移时逐文件选择并重写 import、类型、Token、API 和测试，不保留独立运行时单例或重复基础组件。

## 5. 统一契约扩展策略

不得建立八个彼此独立的顶层 capability 宿主，也不得用一个无边界的“Contract 2.0”对象持续追加任意字段。新增能力优先扩展现有统一页面 envelope，以受版本控制的专项 payload schema 或数据引用承载差异：

- 统一 envelope 负责页面身份、权限、动作、版本和通用状态；专项 capability 只提供 `key`、`schema_version`、`payload_schema`/`payload_ref` 与降级规则。
- 后端声明 `permissions`、`actions`、`disabled_reason` 和数据来源；前端不推断。
- 契约缺失时显示通用安全空状态并记录 drift，不按模型名补齐。
- 所有写操作通过正式 action/intent，并携带幂等键、ETag/版本或并发策略。
- Editor 正文、BOQ 行数据、图表明细不得写入能力定义；它们属于运行时记录或后端数据投影，只能通过受权数据引用加载。
- Theme、图表、甘特、导入导出等均作为受控 block 注入，不改写 native form/tree 基础结构。
- 响应式信息仅使用受限 `presentation_hints`：后端可声明字段优先级、可折叠性和语义；断点、容器测量与布局算法始终由前端负责。
- 图表只接受后端登记的稳定 metric、dimension 与 dataset ref；禁止前端提交或执行自由业务聚合公式。

建议 capability：

| Key | 版本 | 核心输出 |
| --- | --- | --- |
| `ui.theme` | v1 | mode、semantic token overrides、brand asset refs |
| `visualization.chart` | v1 | dataset ref、series、axes、format、drill actions |
| `construction.boq` | v1 | hierarchy、columns、totals、allowed actions |
| `document.excel` | v1 | export/import policy、template、job limits |
| `planning.gantt` | v1 | task projection、calendar、dependencies、allowed actions |
| `document.pdf` | v1 | template、record scope、preview/download job |
| `content.rich_text` | v1 | format、sanitization policy、attachment policy |
| `ui.presentation_hints` | v1 | field priority、collapse permission、semantic emphasis |

## 6. 十个专题的实施裁决

### 6.1 Design System

- 合并进现有 `@sc/design-tokens` 和 `@sc/ui`，不采用原型中的第二套 `--color-*` 与 `--sc-*` 并存方案。
- 先建立 legacy token → canonical semantic token 映射，再迁移组件。
- 基础组件需补齐键盘、焦点、ARIA、loading/empty/error、RTL 可评估性和移动触控目标。
- 页面模板只能接收 assembler 输出，不直接请求业务 API。

### 6.2 Theme / White Label

- Theme engine 属于 P0；品牌名称、Logo 和默认色不属于 P0。
- 品牌资产使用受控附件/静态资源引用，禁止任意 Base64 和任意外链直接注入。
- 自定义 Token 使用 allowlist、类型和对比度校验；禁止覆盖布局、z-index、安全状态色和可访问性底线。
- localStorage 只能保存个人显示模式；租户品牌真相来自后端契约。
- “功能开关”必须来自后端 capability/permission，主题面板不能自行隐藏后视为授权关闭。

### 6.3 ECharts

- 先做依赖 ADR：版本、许可证、gzip 增量、动态加载、CVE、SSR/浏览器兼容。
- 指标口径、聚合和数据权限由后端输出；前端只做格式化、缩放、筛选和 drill action 派发。
- 图表 renderer 必须支持空数据、部分数据、超时、取消、打印和暗色主题。
- 资金分析是 P1 场景，不进入通用 chart adapter。

### 6.4 BOQ

- BOQ 是 P1 施工行业能力；通用树表、虚拟滚动和内联编辑机制可进入 P0 UI。
- 层级、汇总、计量规则、价格计算、可编辑性和审批均由 `smart_construction_core` 决定。
- 前端提交 patch/action，不在本地形成新的金额事实；服务端返回权威重算结果。
- 大数据验收至少覆盖 1k/10k 行、展开深度、键盘导航、移动只读降级和并发冲突。

### 6.5 Excel

- 取消“≤5000 行默认浏览器导出”的既定结论。数据导出必须由后端基于字段权限和记录规则裁剪。
- 大文件采用异步 job + 状态查询 + 限时下载；禁止把完整文件 Base64 塞入通用 intent JSON。
- 导入固定为上传 → 隔离扫描 → 解析预览 → 字段映射 → 服务端校验 → 原子/分批提交 → 错误报告。
- `replace`、`update` 等危险模式需专用权限、确认摘要、幂等和审计记录。

### 6.6 Gantt

- 先交付只读 renderer，再开放拖拽写入。
- 日历、工期、依赖合法性、关键路径和跨任务权限由后端计算。
- 写入动作必须包含原版本和服务端验证；冲突时回滚 UI 并显示权威结果。
- SVG 方案先以 500 个可见任务为准，超过阈值采用窗口化/分段加载，不承诺无限规模。

### 6.7 PDF

- PDF 是后端报告能力，前端只负责发起、查看 job、预览、下载和打印。
- 生成引擎需单独 ADR；不得假设 WeasyPrint、PyPDF2、字体已存在或可直接进入 Odoo 进程。
- 模板只读取经过投影的上下文，不向模板暴露任意 Odoo record 对象。
- HTML 预览必须同源、受 CSP/沙箱约束；下载校验 MIME、文件名和有效期。
- 正式/草稿/作废水印由后端状态决定，前端不能覆盖。

### 6.8 Editor

- 初期支持受限富文本，而非通用网页编辑器。
- 明确 canonical format（建议受限 HTML 或结构化 JSON 二选一），禁止双真相源。
- 服务端执行 allowlist 净化、链接协议校验、附件权限和内容大小限制；前端净化仅用于即时反馈。
- 粘贴、撤销、输入法、移动端、只读、并发版本和无障碍必须进入验收。

### 6.9 Mobile

- 不引入 Tailwind 作为本专题前提，继续复用现有 CSS/Token 体系。
- 同一场景契约在 assembler 层依据正式 responsive hints 形成桌面表格、平板卡片或移动摘要。
- 移动端不建立第二套路由、权限和数据 API。
- 五个标准视口：1440×900、1280×800、1024×768、768×1024、390×844。
- 移动端必须覆盖安全区、软键盘、触控目标、sticky 工具栏、横向溢出和低网速恢复。

### 6.10 产品菜单治理

- 产品已有大量菜单，本专题先建立能力—权限—菜单—action—路由资产账，再判断真实缺口。
- 正式菜单最大三级：一级业务域、二级流程/子域、三级业务对象/台账/单据/报表。
- 对标 Oracle Primavera Unifier、Autodesk Construction Cloud、Procore 与 BOSS/PUMA 的信息架构原则，不复制名称和权限模型。
- 既有导航组件继续使用；专题只治理契约、命名、归集、角色可见性、图标完整性和迁移兼容。
- 详细计划见 [`menu-governance/docs/TECH_DESIGN.md`](menu-governance/docs/TECH_DESIGN.md)。

## 7. 依赖与实施顺序

```text
Architecture baseline
  └─ Design tokens + UI primitives
      ├─ Theme runtime
      ├─ Responsive/mobile renderer
      └─ Capability host + schema/sdk
          ├─ Chart adapter
          ├─ BOQ tree-grid
          ├─ Gantt renderer
          ├─ Rich-text editor
          ├─ Excel job UI
          └─ PDF job UI
```

禁止十条线同时进入主仓库。批准顺序改为：

| 阶段 | 目标 | 进入条件 | 退出条件 |
| --- | --- | --- | --- |
| G0 | 冻结验收 SHA 与清理文档冲突 | 当前计划 | SHA 可追溯；冲突扫描为 0 |
| G1 | 建立现状/差距清单与环境无关验收 | G0 完成 | 四环境配置化；基线证据可复现 |
| G2 | 审计既有 BOQ 导入能力 | G1 完成 | 权限、格式、动作、失败语义和数据边界有证据 |
| G3 | BOQ 最小真实闭环 | G2 通过 | 只读投影与既有导入入口通过角色/视口验收 |
| G4 | Theme/Mobile 增量收口 | G1 基线稳定 | 无第二套页面、token 或数据契约 |
| G5 | 新能力 ADR | G3 结论可用 | Chart/Gantt/Excel/PDF/Editor 分别批准或否决 |
| G6 | 获批能力的只读/异步实现 | 对应 ADR 通过 | renderer/job 安全降级与预算通过 |
| G7 | 高风险写入与场景发布 | 权限、并发、审计已落地 | 真实角色、历史配置、五视口与回退通过 |

## 8. 工作包与交付物

每个专题必须拆成同样的六个工作包：

1. `ADR`：选型、许可证、依赖、替代方案、回退策略。
2. `Schema`：契约版本、示例、无效样例、兼容策略。
3. `Runtime`：加载、取消、重试、并发、错误和遥测。
4. `Renderer`：纯渲染、键盘、ARIA、响应式和主题。
5. `Backend`：事实、权限、专用 intent、审计和限流。
6. `Acceptance`：单测、契约测试、浏览器矩阵、性能与安全证据。

任何专题缺少 Backend/Contract 决策时，只能停留在 renderer 原型，不得接入真实业务菜单。

## 9. 验收与发布门禁

### 9.1 通用门禁

- 严格 TypeScript、ESLint、生产构建。
- Schema 正反例、版本兼容和未知字段策略。
- 共享前端语义边界、原生视图复用、contract drift 和硬编码颜色守卫。
- 0 控制台错误、0 非预期请求失败、0 页面横向溢出。
- 键盘操作、焦点恢复、ARIA、对比度和 reduced-motion。
- 五视口截图与结构化运行证据绑定同一候选 SHA。

### 9.2 专题门禁

| 专题 | 强制证据 |
| --- | --- |
| Theme | Token allowlist、对比度、品牌资产来源、切换无闪烁 |
| Chart | 数据口径快照、空/错/慢、resize、打印、内存释放 |
| BOQ | 权威汇总、权限、并发冲突、10k 行预算 |
| Excel | 文件类型/大小、公式注入、权限裁剪、幂等、错误回执 |
| Gantt | 依赖环、日历、冲突回滚、500 可见任务性能 |
| PDF | 模板沙箱、字体、分页、签章/水印权威、下载权限 |
| Editor | XSS、协议净化、粘贴、附件 ACL、版本冲突 |
| Mobile | 安全区、软键盘、触控、低网速、横向溢出 |

### 9.3 数值化性能预算

预算同时受“冻结基线的相对回归”和下表绝对上限约束，任一失败即不通过。基准环境固定浏览器完整版本、CPU/内存、网络 profile、视口、数据集、产品 SHA；每场景暖机 3 次、正式 10 次，交互指标至少采样 20 次并报告 p50/p75/p95。

| 场景 | 暂定预算（ADR 可收紧，不得静默放宽） |
| --- | --- |
| Shell/普通业务页 | 首屏路由 gzip 增量 ≤ 30 KiB；高级能力不得进入初始 chunk；LCP p75 ≤ 2.5s（标准测试网络） |
| 通用交互 | 本地 UI 响应 INP p75 ≤ 200ms；打开/关闭专项能力 20 次后 JS heap 净增长 ≤ 20 MiB |
| BOQ 1k 行 | 首次可操作 ≤ 1.5s；排序/展开 p95 ≤ 150ms；无横向意外溢出 |
| BOQ 10k 行 | 首次可操作 ≤ 2.5s；滚动长帧占比 ≤ 5%；峰值 JS heap ≤ 250 MiB |
| Gantt 500 任务 | 首次可操作 ≤ 2.0s；平移/缩放/展开 p95 ≤ 150ms；长帧占比 ≤ 5% |
| Excel/PDF job | UI 发起确认 ≤ 300ms（不含服务端处理）；记录队列、处理时长、大小、失败率，不允许同步阻塞页面 |

未冻结基准设备和数据集前，这些预算用于方案筛除，不能用于宣称正式性能通过。

## 10. 风险与回退

| 风险 | 控制 | 回退 |
| --- | --- | --- |
| 平行设计系统 | 唯一 Token/UI 真相源门禁 | 保留旧组件映射层，逐步迁移 |
| 契约膨胀 | capability 独立版本 | 禁用单 capability，不回退整个页面 |
| 大依赖拖慢首屏 | 动态 import + bundle budget | capability 不加载，显示安全降级 |
| 前端越权计算 | 服务端事实与 action | 切回只读 renderer |
| 文件处理风险 | 专用 job、扫描、限流 | 关闭上传/生成入口，不影响基础页面 |
| 客户配置污染平台 | P2/P3 carrier 与 source authority | 回滚配置版本/客户模块 |

## 11. 首轮可执行任务

1. 记录主仓库分支、完整 SHA、构建摘要、浏览器版本和当前验收证据，冻结前端基础设施基线。
2. 对十份专题正文执行冲突扫描；`SUPERSEDED` 内容不计入候选实施清单。
3. 建立主仓库已有能力清单，将工作拆成轨道 A“既有能力接入/收敛”和轨道 B“新平台能力”。
4. 建立环境无关的验收配置、结构化证据 Schema 和精确 SHA 校验，不访问硬编码服务器或数据库。
5. 只读审计 `project.boq.import.wizard`、`action_open_boq_import` 及 CSV/XLS/XLSX 解析、权限和错误语义。
6. 设计并验收 BOQ 只读投影 + 既有导入入口的最小真实闭环；不得先引入 SheetJS。
7. 根据闭环证据，再逐项提交 Chart、Gantt、Excel、PDF、Editor 的 ADR；Theme/Mobile 仅继续收口当前实现。

## 12. 环境矩阵与证据契约

所有脚本只能读取受版本控制的环境配置或显式环境变量，禁止硬编码服务器、端口、数据库、账号、菜单 ID 或 action ID。密钥不得进入仓库或证据包。

| 环境 | 地址发现 | 认证 | 数据/夹具 | 写入策略 | SHA 证明 |
| --- | --- | --- | --- | --- | --- |
| Local | 配置文件或本地服务发现 | 专用测试身份 | 可重建固定夹具 | 允许夹具范围写入 | Git SHA + runtime endpoint + bundle metadata |
| Test/UAT | 受控环境清单 | 真实测试角色 | 版本化数据集 ID | 允许经批准的模拟写操作，结束后核验清理 | 候选 SHA、服务 SHA、浏览器证据四方一致 |
| Daily Dev | 部署清单发现 | 日常角色账号 | 数据库 UUID/摘要，仅指定夹具可变 | 默认只读；写入需任务授权与备份 | 部署 SHA + runtime SHA + 静态产物 SHA |
| Production | 发布平台发现 | 只读验收角色 | 只记录环境/数据集标识，不复制敏感数据 | 只读探针，禁止测试写入 | 已发布 SHA + 服务响应 + 浏览器产物摘要 |

每条浏览器证据至少包含：环境 ID、数据库或数据集 ID、角色、规范化路由、浏览器 URL、视口与 capture mode、浏览器完整版本、截图摘要、产品/服务/静态产物 SHA、采集时间和工具版本。跨环境不得复用截图或运行报告。

## 13. 分支、Worktree 与集成治理

```text
baseline-freeze
  └─ docs-conflict-cleanup
      └─ acceptance-env
          └─ boq-existing-audit
              └─ boq-minimum-loop
                  ├─ theme-mobile-convergence
                  └─ adr-chart-gantt-excel-pdf-editor
```

- 每条实施分支使用独立 worktree；不得在同一工作区并行切换分支。
- 共享契约、设计令牌、lockfile、Make/CI 入口和生成报告实行单写入者；其他专题通过依赖分支消费。
- 生成报告由对应门禁脚本拥有，禁止人工编辑；集成分支统一刷新一次。
- 主线同步点固定在：基线冻结后、BOQ 审计后、BOQ 最小闭环合入前、每个新能力开始前。
- 集成顺序固定为：验收框架 → BOQ 契约/后端适配 → BOQ renderer/入口 → Theme/Mobile 收口 → 获批 ADR 能力。
- 并行只允许在共享 Schema 和 UI 接口冻结后发生；发现共享文件竞争时立即回到单写入者串行合入。

## 14. 兼容、Feature Flag 与回退

- 统一 envelope 与各 payload schema 独立版本；消费者声明支持范围。未知 capability 或较新版本必须安全降级为可解释空态，不猜测字段。
- 新 block 由后端 feature flag/capability 控制，默认关闭；关闭后必须回到既有 form/tree 页面，不影响基础业务。
- 旧页面契约通过显式 adapter 迁移；adapter 有遥测、截止版本和删除门禁，禁止永久双写。
- 日常库历史配置先做只读迁移预检；未知 token、旧字段和非法资产引用保持原值并告警，不在页面加载时隐式改库。
- BOQ 导入首轮只接入既有服务端能力；出现回归时关闭新入口并恢复旧 action，不回滚业务数据。
- 文件 job、编辑器写入和甘特拖拽分别拥有独立 kill switch。数据库变更必须向后兼容，并准备对应回滚或前滚脚本。

## 15. 完成定义

本计划的“完成”不是九个 demo 可以打开，而是：

- 资产进入主仓库既有层次，没有第二套架构。
- 业务事实、权限、配置和前端渲染的所有权可解释。
- 每个 capability 有正式 Schema、后端事实源、纯 renderer、失败降级和验收证据。
- P0/P1/P2/P3/P4 边界没有通过前端特例被绕过。
- 发布候选通过现有正式门禁及本计划新增的专题门禁。

在上述条件满足前，本目录保持“规划/原型输入”状态，不作为已交付能力声明。

## 16. 团队协作与评审责任

| 角色 | 主要责任 | 必签节点 |
| --- | --- | --- |
| 架构负责人 | 五层边界、依赖 ADR、契约演进 | G0、G2、G5 |
| 后端负责人 | 事实、权限、intent、job、审计 | G2、G5、G6 |
| 前端负责人 | Runtime/Assembler/Renderer 分层 | G1–G7 |
| 产品负责人 | P1/P2 范围、指标口径、模板内容 | 场景契约与 G7 |
| 安全负责人 | XSS、文件、CSP、下载与供应链 | G5、G6 |
| QA/交付 | 角色、数据集、五视口和证据包 | 各阶段退出、G7 |

同一个专题的“实现者”不能单独批准其架构边界和发布证据。P1/P2 内容必须由对应产品负责人确认，不能由前端团队代替确认。

## 17. 规模与排期方法

在 G0 资产审计完成前不承诺固定发布日期。建议按工作量而非日历先估算：

| 工作流 | 初始规模 | 可并行条件 |
| --- | --- | --- |
| G0 资产审计与 ADR | M | 可按专题并行，最终统一评审 |
| G1 Token/UI 基座 | L | 是所有 renderer 的前置，不与重复 UI 开发并行 |
| G2 Capability host/schema | L | 可与 G1 后半段并行 |
| G3 Theme/Mobile | M | 依赖 G1/G2 稳定接口 |
| G4 只读高级 renderer | XL | Chart、BOQ、Gantt、Editor 可分小队并行 |
| G5 Excel/PDF | L | 后端 job、安全 ADR 完成后并行 |
| G6 高风险写入 | XL | 按能力逐一开放，禁止大爆炸上线 |
| G7 场景验收 | L | 发布候选 SHA 和角色数据集冻结后执行 |

每个工作流需先拆成不超过一个迭代周期的可验收切片。任何切片若同时修改业务事实、契约、runtime 和 renderer，应继续拆分，避免无法定位回归责任。

## 18. 决策待办

以下决策未完成前，对应专题不得进入生产实现：

- ECharts 是否引入、固定版本和 bundle 预算。
- Editor canonical format 与服务端净化库。
- Excel 文件处理引擎、异步 job、对象存储和病毒扫描边界。
- PDF 引擎进程隔离、字体许可、模板沙箱和签章边界。
- Gantt 工作日历、依赖类型和关键路径权威算法。
- BOQ 权威金额字段、舍入、币种、层级与并发策略。
- Theme 可覆盖 Token allowlist、品牌资产 carrier 和 P2/P3 覆盖顺序。
- Mobile responsive hints 的正式 Schema 和桌面/移动信息优先级。
