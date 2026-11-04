# Capability Discovery Architecture v1（CAP-01B 补充）

状态：只读设计，待架构复核；不开发 Discovery Engine，不改正式目录

## 1. 六环节能力生命周期

```text
发现 Discovery → 识别 Identification → 契约化 Contracting → 验证 Qualification → 发布 Release → 交付 Delivery
```

前五个环节管理能力资产，最后一个环节由产品场景组织能力交付。

## 2. 关键边界：四件事分离

| 环节 | 产出 | 是否自动 |
|---|---|---|
| Discovery 发现 | 技术事实（模型/字段/方法/视图/Action/Groups/Intent/服务接口） | 自动扫描 |
| Identification 识别 | 能力身份候选（符合 B0 五条件） | 自动提取候选 + 人工确认 |
| Contracting 契约化 | 输入输出、Provider、依赖、错误语义、验证要求 | 人工/受管 |
| Qualification / Release | Preview/Standard 资格、正式发布 | 证据驱动，禁止自动 |

发现结果 ≠ 能力登记 ≠ 能力发布。这是避免自动扫描制造大量伪能力的关键。

## 3. 三个来源适配层

| 来源 | 发现依据 | 典型发现结果 |
|---|---|---|
| Odoo 模块 | Manifest、ORM、Fields、Methods、Views、Actions、Groups、Intent | Odoo 能力候选 |
| API / 微服务 | OpenAPI、服务描述、事件定义、调用契约 | API / Service 能力候选 |
| AI / 专业软件 | 模型服务描述、工具定义、输入输出 Schema | AI / Domain Provider 能力候选 |

Odoo 是第一个完整落地的适配器；其他来源只遵循统一 Discovery 输出规范，不单独开发完整系统。

## 4. 六项治理要求

1. 自动扫描：识别新增、修改、删除的模块和技术载体。
2. 候选识别：从技术事实提取可能业务能力，但不自动认定。
3. 身份去重：识别已有能力、别名、同义能力和潜在拆分。
4. 依赖发现：识别对模型、服务、其他能力和外部系统的依赖。
5. 变化检测：模块升级后识别 Provider 或契约变化。
6. 人工确认与追溯：保留来源、扫描版本、发现证据和身份裁定记录。

## 5. 现有可复用资产（不新建 Registry）

| 资产 | 用途 | 复用方式 |
|---|---|---|
| Odoo 原生 `ir.model` / `ir.model.fields` | 模型与字段技术事实 | 直接查询，不复制 |
| Odoo 原生 `ir.actions.act_window` | Action 技术事实 | 直接查询，不复制 |
| Intent handler 注册（`registered_handlers` + `INTENT_TYPE`） | Intent 事实 | 直接读，不复制 |
| `ir.module.module`（state=installed） | 模块安装/升级状态 | 直接读 |
| `extension_loader.py` / `hooks.py` | 模块生命周期钩子 | 挂接发现钩子 |
| `scene_registry.py` / `scene_registry_content.py` | 已有场景身份 | 去重引用 |
| `backend_impact_plan.py` | 文件依赖扫描模式 | 变化检测模式复用 |
| `capability_candidate_catalog_check.py` | 候选目录校验 | 识别结果校验 |

禁止新建第二套 Model Registry / Action Registry。

## 6. 从技术事实形成能力候选

发现到的模型/字段/Action/Intent 只是技术事实，必须经过 B0 五条件过滤：

```text
技术事实（model/field/action/intent）
  -> 提取候选业务动词（create/read/update/manage/enter/advance/track/compare/report）
  -> 逐项套用五条件（目的/身份/契约/可验证/生命周期）
  -> 去重（别名、同义、拆分）
  -> 产出 capability_candidate（qualification=unreleased）
```

示例：安装 CRM 后扫描到 `crm.lead` 模型、线索创建/更新 Action、阶段流转方法、报表接口，
但只有“创建商机 / 查询商机 / 推进商机阶段 / 分析销售漏斗”等通过五条件的才成为候选，
模型、字段、Action 本身不自动登记。

## 7. 变化检测

模块升级触发：扫描 diff（新增/修改/删除的模型、字段、Action、Intent），
对照已有候选身份，标记 Provider/契约变化；变化命中已发布能力时，触发依赖重新验证
（对齐 DECISION-S2-06），不静默升级。

## 8. 非 Odoo Provider 接入协议

统一 Discovery 输出规范：`{ source, technical_facts[], candidate_hints[], evidence }`。
非 Odoo 来源（OpenAPI / AI 工具定义 / 专业软件）按同一规范输出候选事实，
进入同一识别、去重、契约化、资格、发布流程，不单独开发完整系统。
