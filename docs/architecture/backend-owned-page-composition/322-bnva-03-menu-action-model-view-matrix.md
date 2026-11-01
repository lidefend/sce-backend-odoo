# 322 · BNVA-03 Menu/Action/Model/View Matrix

## 关联完整性

- 悬空菜单 action：0。
- 无菜单 action：233（待分类）。

## 专项

| 对象 | External ID | Model | 视图 |
| --- | --- | --- | --- |
| Action 709 | action_sc_payment_execution（付款执行） | sc.payment.execution | 模型默认，无显式绑定 |
| Action 908 | action_sc_payment_execution_actual_outflow（实付登记） | sc.payment.execution | tree 1657 / form 1658 |
| Action 590 | action_sc_project_list（项目台账） | project.project | tree 1507 / form 1776 / kanban 1421 |
| Action 652 | action_sc_project_manage（项目管理） | project.project | view_id 1422，无显式 act_window.view |
| action_project_initiation | 项目发起 | project.project | 分节契约数据绑定于此 |

## 配置绑定

- `project_project_overview_form_structure_v1` → action 590（form）。
- `project_project_form_structure_v1` → action 795 / view 1511。
- action 652 无 productized 配置。
