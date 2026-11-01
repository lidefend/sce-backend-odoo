# 134 · BNVA-019 Stage 3C-02B-02 · native_onchange_spec 迁移

## 判定

`native_onchange_spec.build_native_onchange_spec` 由 `api_onchange` 在 onchange
意图请求中调用，是独立请求，不共享页面装载请求的 Carrier。

## 处理

不迁移到 Carrier。保持当前用户 `model.get_view()` + `etree.fromstring`。
已核验：使用当前用户 env，不 sudo，权限由 Odoo 决定。

## 结论

独立请求的合法解析，非重复；无需代码改动。

