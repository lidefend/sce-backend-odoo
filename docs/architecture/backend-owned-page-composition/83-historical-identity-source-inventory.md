# 83 · Historical Identity Source Inventory（PC-010）

## 结论

历史身份原始来源：NOT_VERIFIED

## 已确认来源

1. Git 历史（可信原始来源之一）：
   - `303ebd630 fix(project): deduplicate identity projection and restore status field rendering`
   - `8bd832066 fix(project): disambiguate project identity responsibility labels`
   - `9734b5c6a feat(product): prepare first preview with unified authority and native contracts (#712)`
2. 当前候选数据库中的 `ir.ui.view` 记录（View 1776 / 944）可提供当前节点身份，
   但不是历史快照。

## 缺口

- 未找到 1776/944 的历史配置快照、低代码节点路径、occurrence_index 与
  action/view 关联的历史记录。
- 源码中的 G12 退役声明针对创建入口，不适用于这两个入口。

## 判断

不得用字段名、当前节点顺序或相似 XML 结构推断历史身份。before/after 映射
缺失，PC-010 保持 NOT_VERIFIED。
