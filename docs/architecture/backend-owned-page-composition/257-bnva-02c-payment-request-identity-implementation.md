# 257 · BNVA-02C-02B-02 · payment.request Identity 实施

## 变更

`payment_request_form_productization_contract.xml` 的
`payment_request_receive_productized_form_v1` 增加：

```python
'identity_fields': ['name'],
```

依据：`payment_request.py:128` `name = fields.Char(string="申请单号")`，`name`
是对象标识（申请单号），非显示标题。仅补充 `name`，不自动补 type /
business_category_id / date_request。

## 验证

- XML 解析通过；contract_json 可 eval。
- 结构完整性校验：不再报 IDENTITY_MISSING / IDENTITY_NOT_IN_SECTION。
- 剩余 SECTION_KEY_MISSING（7 段缺稳定 key）属下一轮确认，不在本轮授权范围。

