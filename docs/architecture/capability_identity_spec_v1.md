# Capability Identity Spec v1（CAP-01B · B1）

状态：候选规范，待架构复核
上游：B0 能力本体、ARCH-DECISION-011

## 1. 身份格式

能力稳定身份 `capability_key` 采用三段点分：

```text
<domain>.<object>.<verb>
```

- `domain`：业务域，来自固定的 13 域词汇（见下），不允许新增同义域。
- `object`：业务对象或能力焦点（如 project / plan / ledger / budget）。
- `verb`：业务动作（create / read / update / open / manage / enter / advance / track / compare / report）。

身份独立于 menu_xmlid、页面 scene、模型名和 Provider；这些只能作为映射属性，不能作为身份本身。

## 2. 业务域词汇（13 域，冻结）

`project / contract / cost / finance / material / construction / quality / safety / labor / equipment / analytics / governance / workspace`

同名异义必须并域或更名，不允许 `project_center` 与 `project` 并存表达同一业务域。

13 域是当前建筑施工行业标准域词汇，不是永久封闭枚举。未来新增域（BIM / document /
engineering / ai / supply_chain / human_resources 等）必须经过统一身份治理、命名冲突检查
和兼容性审查，不允许随意创建同义域。

## 3. 身份稳定性规则

1. 身份由“业务目的 + 对象 + 动作”决定，不随 Provider 变化。
2. 换 Provider 且语义兼容：身份不变，升级 Provider 版本并重新验证。
3. 换 Provider 且语义不兼容：新版本或新身份，不覆盖旧身份。
4. 改名必须保留兼容映射（old_key → new_key），发布迁移计划。

## 4. 六类分类操作（B2 使用）

| 操作 | 规则 |
|---|---|
| 保留 keep | 满足五条件，身份稳定，直接保留 |
| 合并 merge | 多个 key 表达同一业务目的，合并为一个身份 + 别名 |
| 拆分 split | 一个 key 混入多个业务目的，拆成多个身份 |
| 更名 rename | 身份不稳定或命名不规范，更名并保留兼容映射 |
| 排除 exclude | 非能力（菜单/页面/模型/字段/入口），排除出能力目录 |
| 暂缓 defer | 是否构成能力待核实，暂不正式登记 |

正式迁移时，每条旧身份必须记录迁移档案：

```text
old_key, canonical_key, disposition, migration_reason, compatibility_alias, affected_consumers
```

旧产品、历史配置和场景引用据此安全迁移，不被静默丢弃或误指向。

## 5. 非能力判定

下列对象一律排除，不作为能力身份：

- 页面导航入口（“打开列表页/看板/表单”无独立可验证结果）
- `menu_*`、`action_*` 载体
- `project.project` 等模型
- 字段、Scene、表单/列表页契约

判据：是否有独立契约 + 可验证执行结果，而非是否有入口或页面。
