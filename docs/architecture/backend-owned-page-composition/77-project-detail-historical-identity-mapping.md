# 77 · Project Detail Historical Identity Mapping（PC-010）

## 结论

PC-010 = NOT_VERIFIED（两个入口一致）

## 已核验

- View 1776 / 944 是数据库中的 `ir.ui.view` 记录，源码中无直接 XML id 对应。
- `view_orchestration_form_section_contract_data.xml` 中的 G12 退役声明针对
  创建入口（action_project_initiation / view_project_create_form），不是
  590/1776 或 652/944。
- 未找到两个入口的历史低代码节点身份、occurrence_index、action/view 绑定与
  迁移前后映射的可追溯快照。

## 判断

没有可靠历史原始记录，不得推测映射关系。PC-010 保持 NOT_VERIFIED，待取得
历史配置快照并建立 before/after 身份对照。
