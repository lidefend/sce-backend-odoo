# 416 · BNVA-04 Tax Certificate DOM Consumption

## 结果

sc.tax.certificate.registration 浏览器 DOM 消费 PASS（列表态）。

## 实测证据

- 导航：`/t/clean/a/711?menu_id=539`，无拒权。
- V2 Contract：pageId=sc.tax.certificate.registration.tree，model=sc.tax.certificate.registration，
  viewType=list，renderMode=governed，contractVersion=2.2.0。
- Vue Renderer：ActionView 渲染，`data-collection-state=empty`。
- 树列字段（contract.containerTree）：
  name, company_id, project_id, taxpayer_name, taxpayer_identifier, tax_report_management_no,
  cross_region_business_address, validity_start_date, validity_end_date, prepaid_tax_date,
  tax_payment_certificate_no, handler_id, state（共 13 个，全部有效）。
- source_created_by / source_created_at：0 个（04-06B 修正已在 DOM/契约层生效）。
- 控制台 / pageerror / API 错误：NONE。

## 未覆盖

- 表单 DOM：无业务记录，新建表单未执行（避免创建记录），FORM DOM 标记 NOT_RUN。
- Search DOM：action 绑定 search view，未单独打开搜索面。

## 结论

税务凭证页从 Odoo 原生 View → V2 Contract → Vue Renderer 的列表消费链路已实证；FORM/Search 留待
有记录或允许新建表单后补验。
