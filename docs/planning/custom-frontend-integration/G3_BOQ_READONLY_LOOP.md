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
