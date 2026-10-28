# Demo 定稿重建收口（2026-10-28）

状态：demo 已按定稿 seed 重建，发布面与锁定契约一致，91 个正式发布导航叶子视觉走查全绿。
数据缺口作为后续迭代优先级，不属于本轮阻断。

## 重建身份

- 部署源码：`3f46dd7eba9f351386fee446151ee9eb545d56a4`
- demo duty：`sc_demo`，数据库 UUID `c7ffe700-ce02-11f1-9a86-a213133df790`
- 受管重建入口：`daily.runtime.database.duty.recreate`（先落恢复点，再 drop 业务行并重放定稿 seed 链）
- 重建结果：`status=PASS`，`phase=recreate`，`duties=[demo passed]`

## 定稿发布面

重建会重置发布面，随后经 `daily.runtime.published_face.converge` 刷新到锁定契约：

- 正式发布（released）：91
- 预览（preview）：40
- 有效总数（effective）：131
- `exact_match=true`，与锁定契约一致

`demo_full` 运行时可见 91 个正式发布叶子，40 个预览叶子不默认展示，这是契约的正确状态。

## 视觉走查结果

converge 后在定稿数据上重跑只读视觉走查：

| 角色 | 页数 | 错误 | 渲染失败 |
| --- | --- | --- | --- |
| demo_full | 91 | 0 | 0 |
| demo_role_owner | 4 | 0 | 0 |
| demo_role_executive | 1 | 0 | 0 |
| demo_role_project_user | 4 | 0 | 0 |
| demo_role_project_manager | 4 | 0 | 0 |
| demo_role_project_a_member | 4 | 0 | 0 |

合计 108 页、0 页面错误、0 加载失败。

## 收口结论

demo 数据库恢复到定稿权威状态，发布面与锁定契约一致，正式发布导航全绿。
23 组数据缺口（质量验收、材料退货、薪资发放等）不在定稿 seed 范围内，按缺口清单自身的
定义属“后续迭代优先级”，作为独立迭代项继续排队，不构成本轮交付阻断。

完整 90 项矩阵、130 个新建点击、业务写入链仍作为最终交付验收的独立步骤，在后续轮次执行。
