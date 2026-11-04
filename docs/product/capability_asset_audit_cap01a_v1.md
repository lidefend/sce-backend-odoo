# CAP-01A · 全量能力资产与发布链审计

状态：只读盘点产物，基线 main `6e674745a`
范围：能力目录、能力身份、Provider、成熟度证据、产品发布/快照晋级写入链
禁止：未修改任何产品运行代码、目录、资格或发布状态

## 1. 能力资产全集清单

现有能力相关载体共 7 类，身份词汇有四套，互不一致：

| 载体 | 数量 | capability_key 风格 | 备注 |
|---|---|---|---|
| `capability_catalog_v1.json` | 42 | `project.initiation.enter` 等 | 手维护目录，`main_action.intent` 全为通用兜底 `ui.contract`，`status` 全 ready，无 maturity_fingerprint |
| `capability_entry_registry_v1.json` | 42 | `entry_key=capability::<catalog_key>` | 与 catalog 1:1，派生 |
| `product_capability_matrix_v2.md` | 63 | 同 catalog 风格 | 比 catalog 多 21 个 |
| `product_menu_source.json` | 131 | `capability_key` 全 None | 产品入口，release_state 全已发布，但能力字段全空 |
| `capability_acceptance_contracts_v1.json` | 42 键 | 同 catalog key | 验收契约，声明 product_dependencies，不授予证据 |
| `sc_capability_group_seed.xml` | 8 | group key（project_management 等） | 能力分组 |
| `project_capability_roadmap_data.xml` | N | `project_organization` 等 | 规划中能力（未发布） |

真实执行载体（与上述身份词汇无关）：具体 intent handler（`project.initiation.enter` 等）、
原生 `ir.actions.act_window`（`action_project_initiation` 等）、模型（`project.project`）。

## 2. 42 vs 63 差异

`product_capability_matrix_v2.md` 比 `capability_catalog_v1.json` 多 21 个能力，均为目录缺失：

```text
construction.diary.open / plan.manage / plan.report
equipment.plan.manage / request.list / settlement.list / usage.list
labor.attendance.list / plan.manage / request.list / settlement.list
project.dashboard.enter / execution.advance / execution.enter / plan_bootstrap.enter
quality.issue.list / recheck.list / rectification.list
safety.issue.list / recheck.list / rectification.list
```

## 3. 能力身份与 Provider 映射矩阵

四类对象现状：

| 对象 | 现状 | 问题 |
|---|---|---|
| Capability Identity | 四套词汇混用 | 无统一稳定身份 |
| Provider Binding | catalog `source_model` + 运行时 action/intent 隐式绑定 | 未显式声明 Provider |
| Capability Qualification | catalog `status=ready` 是手工字段，非证据 | 与 maturity 评估脱节 |
| Capability Release | 无运行时发布状态；仅 build 脚本生成 doc | 无正式发布对象 |

`project.project` 是模型，被 catalog 多处当作 `source_model`，但未被证明是完整原子业务能力；
创建/读取/更新是三个不同业务能力，可引用同一模型 Provider。

## 4. 能力成熟度与证据覆盖报告

- `capability_maturity.py` 已实现 Preview/Standard 两级、依赖指纹、验收标准指纹、receipt/artifact 校验、
  必测用例覆盖、过期/失败/跳过/重复拒绝。
- `capability_maturity_evidence.py` 是独立验证脚本，校验受控 evidence bundle，不发布、不授权。
- 实际覆盖：`capability_catalog_v1.json` 42 个能力 `maturity_fingerprint` 全缺失（0/42）。
- `product_menu_source.json` 131 条 `capability_maturity` 全 None。
- `capability_acceptance_contracts_v1.json` 存在，但当前无对应成熟度 evidence bundle（未发现 artifacts）。

## 5. 发布、晋级、回退写入链审计

发布写入链（现状）：

```text
build_capability_productization_v1.py
  -> _capability_maturity() 字符串启发式（status==ready && has_scene -> productized）
  -> 生成 product_menu_source.json（release_state=released，capability_key/maturity 全 None）

product_menu_source.py（服务）
  -> schema 声明 capability_key/capability_maturity 字段，但数据未填充

capability_maturity.py + capability_maturity_evidence.py
  -> 仅评估/验证，未接入任何发布写入入口
```

结论：`evaluate_maturity()` 与产品发布写入链完全脱节。产品发布直接写 `release_state=released`，
不经过能力资格检查。

## 6. 可绕过能力资格检查的发布入口

1. `build_capability_productization_v1.py` 直接写 `release_state=released`，未调用 `evaluate_maturity`。
2. `_capability_maturity()` 用 `status==ready && has_scene` 启发式，无证据回执。
3. `product_menu_source.json` 的能力字段为空，产品发布与能力身份无绑定。
4. `capability_maturity_evidence.py` 未挂入任何 make/CI 门禁（仅 dev_test 独立 target）。

## 7. 缺口与修复计划（CAP-01B..E 输入）

| 缺口 | 修复阶段 |
|---|---|
| 能力身份四套词汇 | CAP-01B 统一能力身份 + Provider 绑定 |
| 目录缺失 21 个能力 | CAP-01B 补齐目录与真实 intent/action/model 映射 |
| maturity_fingerprint 全缺失 | CAP-01C 为每个能力生成真实资格与可信 receipt |
| 发布写入未强制资格检查 | CAP-01D 所有产品发布/快照晋级入口强制 evaluate_maturity |
| 无逐能力发布/回退审计 | CAP-01D 补发布、回退、停用、退役追溯 |
| 无真实发布/拒绝集成测试 | CAP-01E 发布、拒绝、升级、回退、依赖变化验收 |

不新增：第二套能力 Registry、发布引擎、版本管理。复用 `capability_maturity.py` 与现有目录载体。
