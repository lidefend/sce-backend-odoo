# 252 · BNVA-02C-02B-01 · Identity-only 伴生配置关联核实

对象：`business_config_contract_project_overview_form_structure_v1`
（model=project.project，identity_fields=[name, project_code, user_id, manager_id,
owner_id]）。

它是 `project_project_form_structure_v1`（native_semantic_surface，无 identity）的
伴生 Identity 声明。建议：**关联到现有产品配置**（02B-02 实施时把 identity 并入
project 的产品默认结构，并核实二者 action/view 作用域是否同一入口），不独立保留、
不删除。

