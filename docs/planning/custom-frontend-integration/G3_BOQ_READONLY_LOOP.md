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
