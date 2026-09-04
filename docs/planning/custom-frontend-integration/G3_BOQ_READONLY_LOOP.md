# G3：BOQ 最小真实闭环 —— 阶段进展（G3.1）

> 状态：G3.1 已交付（本 PR）；G3.2 前端只读投影、G3.3 真实角色/数据/视口验收待续。
> 基线：main `ea600d6e`（PR #405，G2 审计收口）。

## G3.1 交付物

### 1. BOQ 只读域契约（`contracts/domain/boq.yaml` v1）

- 实体 `ProjectBoqImportBatch`，**全字段 readonly**，只读投影语义显式声明。
- `preview_payload` 字段挂接结构化快照 `sc.boq.import.preview.v1`，标注
  「前端只读消费，不得反解或回写」。
- **safe_degradation 节**：批次不存在 / 无权限（同语义防枚举侧信道）/
  快照缺失（空快照空态渲染）三种降级路径均写入契约，消费方不得白屏。
- 已登记 `contracts/registry.yaml`（domain: boq, version: 1）；结构指纹随
  `generate_contract_structure_fingerprint.py --write` 重算。

### 2. 只读 intent：`project.boq.import.preview.fetch`

- 文件：`addons/smart_construction_core/handlers/boq_import_preview_fetch.py`
- 事实源：`project.boq.import.batch.preview_payload`（G2 审计锁定的唯一权威快照）。
- 入参：`batch_id`（指定批次）或 `project_id`（按 `id desc` 取最新批次）。
- 访问判定：`search` 语义（ir.model.access + 记录规则参与），**无权限与
  不存在同响应**，避免批次枚举侧信道；不做 browse 直读。
- 降级：MISSING_PARAMS / BATCH_NOT_FOUND 均为结构化 `ok=false`，不抛异常；
  `preview_payload` 非对象时以空快照返回。
- `MACHINE_ACCESS = "read"`，`ACL_MODE = "record_rule"`。
- 桩式单测 7 例（`test_boq_import_preview_fetch_handler.py`），不含数据库依赖。

### 3. R-G2-01 收口：计量单位白名单

- 风险回顾（G2 审计）：导入向导对文件中任意未知单位静默 `sudo` 创建全局
  `uom.uom` 主数据，低质量/恶意文件可无限膨胀全局单位表（中危）。
- 修复（`wizard/boq_uom_policy.py` + 向导接入）：
  - `UOM_AUTO_CREATE_WHITELIST`：建筑清单常用计量单位（经
    `UOM_ALIAS_MAP` 归一后的规范名），纯常量模块、零 Odoo 依赖。
  - 白名单外单位：**不创建全局主数据**，降级为业务兜底单位「项」；
    降级名单经 context 收集器传出，在**预检警告**与**批次日志**中
    显式列示（不静默）。
  - 白名单扩展属于产品决策，须随 `domain/boq.yaml` 契约评审进行。
- 单测 4 例（`test_boq_uom_policy.py`）：标准单位命中、垃圾名拒绝、
  frozenset 冻结、模块零运行时依赖。

## 与总控计划的对齐

| 计划条目 | 本 PR 落点 |
| --- | --- |
| G3.1 统一 envelope 中定义 BOQ 只读数据引用与安全降级 | domain/boq.yaml safe_degradation 节 + handler 降级实现 |
| 轨道 A：既有能力收敛、不新增浏览器解析器 | 只读投影直接消费既有 preview_payload，未引入任何前端解析 |
| 大依赖须 ADR | 零新增依赖 |
| R-G2-01（G3 前置） | 白名单 + 显式降级列示，已收口 |

## 后续（G3.2 / G3.3）

- G3.2：前端只读投影组件（按契约准入迁移原型目录中的预览面板，
  非整目录复制），消费 `project.boq.import.preview.fetch`；
  导入入口沿用既有向导（digest 绑定 + `[SC_GUARD:*]` 错误透传）。
- G3.3：真实角色（cost_manager/cost_user）、1k/10k 行数据、五视口验收，
  证据按 G1 `acceptance_evidence_contract_v1.schema.json` 归档。

---

# G3.2：前端只读投影 —— 阶段进展

> 状态：G3.2 已交付（本 PR）；基线 main `cf7f60fb`（PR #406，G3.1 后端侧）。
> 原则：按契约准入迁移原型（`boq-frontend/src/` 共 9 文件 2092 行）中的
> 预览投影，**非整目录复制**；导入入口沿用既有向导，不在前端另起写路径。

## G3.2 交付物

### 1. API 封装（`frontend/apps/web/src/api/boqImportPreview.ts`）

- 走统一 intent 入口 `intentRequest`（对齐 `myWork.ts` 模式），intent 为
  `project.boq.import.preview.fetch`（G3.1 已合入 main）。
- 类型对齐后端 `_serialize_batch` 全字段 + `sc.boq.import.preview.v1`
  快照结构（row/item/summary/heading/skipped/warning/amount/
  source_diagnostics/analysis 等）。
- **降级不抛异常**：业务层降级（MISSING_PARAMS / BATCH_NOT_FOUND）
  为结构化 `ok=false`，经 envelope data 透传给 presentation Model 投影；
  传输层异常照常抛出。封装内**禁用通用 data op**（list/read/create/
  write/unlink），守卫强制。
- 入参对齐 handler：`batchId`（指定批次）或 `projectId`（取最新批次）。

### 2. presentation Model（`frontend/apps/web/src/app/presentation/boqImportPreview.ts`）

- 纯函数投影 `projectBoqImportPreview(raw) → BoqImportPreviewViewModel`，
  零网络/会话依赖（守卫强制），可被 esbuild 单测直接覆盖。
- **四态视图状态机**（对齐契约 safe_degradation 节）：
  - `ready`：快照齐备，投影统计卡（总行数/明细项/跳过/警告/金额/
    综合单价分析）与解析诊断行；
  - `missing_payload`：ok=true 但空快照 → 空态渲染（不白屏）；
  - `error`：ok=false → 结构化错误透传（errorCode/message/
    suggestedAction）；
  - `degraded_shape`：ok=true 但 batch 序列化形状异常 → 防御性降级。
- 数值容错：字符串计数归一、非法日期原样透传、金额千分位
  （`formatBoqPreviewAmount`，null/NaN → `—`）。
- 跳过/警告 > 0 的统计卡标记 warning emphasis。
- `BOQ_IMPORT_PREVIEW_VIEW_READONLY = true`：Model 不产生任何写 intent。

### 3. 只读面板组件（`frontend/apps/web/src/components/boq/BoqImportPreviewPanel.vue`）

- 消费 ViewModel，按状态三段渲染：错误态卡 / 空态卡 / 就绪态
  （标题 + 批次元信息 + 统计卡网格 + 解析诊断列表）。
- 证据属性：`data-boq-import-preview` / `:data-view-state` /
  `data-readonly="true"` / `data-preview-error` / `data-preview-empty` /
  `data-preview-stats` 等。
- **只读边界（守卫强制）**：组件内禁止 `@click`、`api.data`、
  `call_method`、`action_import` 等任何写操作入口。
- 从原型 `ScBoqImportWizard.vue`（490 行）中仅准入预览统计展示语义；
  树视图/行内编辑/导入操作不迁移（属 G3.3+ 范畴）。

### 4. 单测与守卫

- **esbuild 单测**（`frontend/apps/web/scripts/boq_import_preview_model_test.ts`）：
  node:assert 全断言，覆盖四态投影、BATCH_NOT_FOUND/MISSING_PARAMS
  错误透传、空快照空态、形状异常防御、null/畸形 raw 防御、金额格式化、
  字符串计数容错、诊断空行过滤、统计 emphasis —— 全绿。
- **静态守卫**（`scripts/verify/frontend_boq_import_preview_guard.py` +
  unittest 7 例 `test_frontend_boq_import_preview_guard.py`）：
  - API 必须走专用 intent，禁止通用 data op 旁路；
  - Model 必须含四态常量 + 只读标记，必须保持纯函数（禁 fetch/
    intentRequest/useSessionStore）；
  - 组件必须结构化渲染错误态/空态/防御态，禁止写操作；
  - 单测必须覆盖四态与金额格式化；
  - frontend.mk 必须注册单测目标。
- **Makefile 注册**（`make/frontend.mk`）：新增
  `verify.frontend.boq_import_preview.unit`（esbuild bundle → node →
  unittest → guard），并接入 `verify.frontend.quick.gate` /
  `verify.frontend.pr.unit` / `verify.frontend.release.unit` 聚合链。

## 与总控计划的对齐

| 计划条目 | 本 PR 落点 |
| --- | --- |
| G3.2 前端只读投影组件（契约准入迁移，非整目录复制） | API/Model/组件三件套，仅迁移预览投影语义 |
| 消费 project.boq.import.preview.fetch | API 封装直连 intent，无旁路 |
| 导入入口沿用既有向导（digest 绑定 + [SC_GUARD:*]） | 组件与 Model 零写路径，守卫强制只读 |
| 消费方不得白屏 | 四态状态机 + 结构化错误/空态渲染 + 单测覆盖 |

## 后续（G3.3）

- 真实角色（cost_manager/cost_user）、1k/10k 行数据、五视口验收，
  证据按 G1 `acceptance_evidence_contract_v1.schema.json` 归档。
- 组件挂接真实路由/页面（当前为可复用只读面板，等待 G3.3 验收场景
  落位后接线）。


---

## G3.3-A 组件挂接（进行中，2026-09-04）

### 目标

把 G3.2 的只读面板从「可复用组件」升级为「项目驾驶舱契约内的正式 block」，
按既有 dashboard block builder 模式挂接（不新建平行渲染通道）。

### 交付物

- **后端块投影**（`project_dashboard_builders/project_boq_preview_builder.py`）：
  `ProjectBoqPreviewBuilder`，block_key=`block.project.boq_preview`、
  block_type=`boq_import_preview`。块本身不携带业务事实，只声明受权数据引用
  （`fetch_intent=project.boq.import.preview.fetch` + `fetch_params.project_id`）
  与批次存在性状态（ready/empty），事实源仍由 G3.1 intent 权威输出。
- **注册链**：BUILDERS + `RUNTIME_BLOCK_MAP["boq_preview"]` + service zones
  `boq` + scene content `zone_blocks` 增补（secondary 区，成本控制之后）。
- **前端块包装**（`components/page/blocks/BlockBoqImportPreview.vue`）：
  接收 block/dataset 契约 props，经 `resolveBoqBlockProjectId` 解析项目上下文
  （dataset 投影优先，路由 query `project_id` 兜底），调用专用 intent 拉取快照，
  投影后复用 `BoqImportPreviewPanel` 渲染；只读（守卫强制无写入口）。
- **block 注册**：`pageBlockRegistry.ts` 登记 `boq_import_preview` 类型。
- **Model 扩展**：`resolveBoqBlockProjectId` 纯函数（可单测的上下文解析）。

### 测试与守卫

- 后端桩单测 `test_project_boq_preview_builder.py`：7 例全绿
  （块身份/无项目空态/有批次 ready/无批次空态仍带项目引用/可见性/
  forbidden 降级/域限定到 project_id）。
- 前端 Model 单测：+13 例 `resolveBoqBlockProjectId` 断言
  （优先级/兜底/非法值防御/浮点截断/非对象 dataset 防御）。
- 守卫 `frontend_boq_import_preview_guard.py` 扩展：wrapper 必须复用
  panel + 专用 intent + 上下文解析，且无写操作；registry 必须登记
  `boq_import_preview`；unittest 9 例（新增 wrapper 写操作反例、
  registry 缺登记反例）。
- `component-driver-takeover-inventory` 已刷新收录 BlockBoqImportPreview。

### 边界说明

- 块 envelope 的 `state=empty`（无批次）由前端包装渲染为空态文案，
  不触发 intent 之外的任何数据通道。
- 五视口/真实角色验收（G3.3-B）仍待环境，证据按 G1
  `acceptance_evidence_contract_v1.schema.json` 归档。

---

## G3.3-B 真实角色/数据/视口验收（harness 已就绪，待环境执行）

### 目标

按规划 README §12 浏览器证据契约 v1，对项目驾驶舱的 BOQ 只读投影
做**真实角色 × 真实数据 × 真实视口**三重矩阵验收，证明 G3.3-A
`BlockBoqImportPreview` 在桌面、平板、移动三档视口下都能稳定渲染，
且两个成本角色看到的页面与受权数据一致；任何视口出现横向溢出、
契约响应缺 BOQ preview block、console/page error 即视为 G3.3-B 不通过。

### 矩阵规格

| 维度 | 取值 | 来源 |
| --- | --- | --- |
| 角色 | `cost_manager`（`sc_fx_cost_manager`）/ `cost_user`（`sc_fx_cost_user`） | G3.1 既有 demo fixture；与既有成本管理场景登录态一致 |
| 视口 | `1440×900`（桌面大）/ `1280×800`（桌面中）/ `1024×768`（桌面小）/ `768×1024`（平板竖）/ `390×844`（手机） | README §12 + G1 既有 collection-view 视口列表 |
| 数据集 | `boq_1k`（小型项目，约 1k 行 BOQ 行）/ `boq_10k`（大型项目，约 10k 行） | 既有 `project.boq.import.wizard` 落地的批次 |
| 笛卡尔积 | 2 × 5 × 2 = 20 cell | 全部必须各自独立截图、独立契约探针 |
| 路由 | `/s/project.management?project_id=<dataset_project_id>` | G3.3-A 挂接的场景 |

### 交付物

- **harness** `scripts/verify/boq_dual_role_five_viewport_browser_acceptance.mjs`：
  - 20 cell 顺序执行；每 cell 新建 `browser.newContext` 隔离 cookie/localStorage；
  - 每 cell 登录对应角色 → 跳到 `project.management` → 等待
    `[data-block-key="block.project.boq_preview"]` 出现 → 截图；
  - 监听 `pageerror` / `console.error`（剔除 favicon、ResizeObserver 噪音）
    / 4xx-5xx 响应 / `ui.contract.v2` POST；
  - 校验 `ui.contract.v2` 响应中含 `boq_import_preview` block；
  - 校验无横向溢出（`documentElement.scrollWidth ≤ viewport.width + 2`）。
- **证据守卫**
  `scripts/verify/boq_dual_role_five_viewport_evidence_guard.py`：
  - 校验 `artifacts/boq-dual-role-five-viewport/evidence.json` 满足
    `config/frontend/acceptance_evidence_contract_v1.schema.json`；
  - 11 个必填浏览器证据字段每 cell 都齐；
  - `cross_env_reuse_forbidden`：20 cell 的 `screenshot_digest` 必须两两不同；
  - 20 cell 必须覆盖 2 × 5 × 2 笛卡尔积；
  - `environment_assets` 含 3 个受控环境资产 + harness 本体的 sha256；
  - `baseline_sha` 可追溯到 `origin/main` 历史。
- **守卫单测**
  `scripts/verify/test_boq_dual_role_five_viewport_evidence_guard.py`：
  27 例全绿（结构/矩阵规格/cell 校验/可复现性/集成）。
- **Make 目标** `make verify.boq.dual_role.five_viewport.evidence`：
  跑守卫 + 单测；不依赖 dev 环境（无 `evidence.json` 时友好提示）。
- **测试资产登记** `docs/engineering_convergence/test_inventory.csv`：
  自动 `T-ASSET-170`（harness，e2e/release_candidate/keep_release_only）、
  `T-ASSET-171`（evidence guard）、
  `T-ASSET-1055`（单测）。

### 证据包结构

```jsonc
{
  "schema": "frontend_acceptance_evidence_contract.v1",
  "baseline": { "baseline_sha": "<40-char>", "baseline_sha_source": "...", "capability_inventory_path": "..." },
  "environment_assets": {
    "profiles_present": ["daily", "local", "production", "test"],
    "assets": [ { "path": "...", "sha256": "..." }, ... 4 项 ]
  },
  "toolchain": { "node": "v22.x", "playwright": "playwright-runtime.mjs" },
  "collected_at": "2026-XX-XXTHH:MM:SSZ",
  "browser_evidence_contract": {
    "required_fields": [11 项],
    "cross_env_reuse_forbidden": true
  },
  "matrix_spec": { "roles": [...], "viewports": [...], "datasets": [...], "cell_count": 20 },
  "cells": [
    {
      "environment_id": "local",
      "dataset_id": "boq_1k",
      "role": "cost_manager",
      "normalized_route": "/s/project.management?project_id=...,
      "browser_url": "http://...",
      "viewport": "1440x900",
      "capture_mode": "readonly",
      "browser_full_version": "Chromium 138.x",
      "screenshot_digest": "<64-char>",
      "product_service_static_shas": { "frontend_sha": "...", "backend_sha": "...", "contract_schema_sha": "..." },
      "collected_at_and_tool_version": "2026-...|boq-dual-role-five-viewport-browser-acceptance.mjs@0.1.0"
    },
    ... 19 more
  ]
}
```

### 环境前置（执行 harness 时）

- dev nginx + Odoo（`http://127.0.0.1:18083`）；
- `sc_clean` 数据库存在；
- `sc_fx_cost_manager` / `sc_fx_cost_user` 两个 fixture 用户已初始化；
- 1k 行与 10k 行 BOQ 导入批次已通过 G3.1
  `project.boq.import.wizard` 落地，`BOQ_1K_PROJECT_ID` /
  `BOQ_10K_PROJECT_ID` 环境变量已 export；
- `playwright` chromium 已下载（既有 `playwright_runtime.mjs` 复用）。

### 执行入口（待环境）

```bash
export E2E_PASSWORD='<fixture password>'
export BOQ_1K_PROJECT_ID=<id>
export BOQ_10K_PROJECT_ID=<id>
export FRONTEND_URL=http://127.0.0.1:18083
export FRONTEND_SHA=<40-char>  # 可选，写入 product_service_static_shas
export BACKEND_SHA=<40-char>
export CONTRACT_SCHEMA_SHA=<40-char>
node scripts/verify/boq_dual_role_five_viewport_browser_acceptance.mjs
# 验收：
make verify.boq.dual_role.five_viewport.evidence
```

### 边界说明

- 20 cell 互不复用截图（`screenshot_digest` 两两不同）；
- harness 不会触发任何写意图；`capture_mode=readonly` 是 schema 强约束；
- 任何 cell 出现 `pageerror` / `http 4xx-5xx` / `console.error` / 缺
  `boq_import_preview` 契约 block / 横向溢出 → 整包标 FAIL，CI 拒绝。

