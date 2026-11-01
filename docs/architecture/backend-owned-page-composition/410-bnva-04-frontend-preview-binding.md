# 410 · BNVA-04 Frontend Preview Binding

## 前端源码

本批产品改动均为后端（addons/smart_construction_core 的 XML/契约/视图）与文档，未改动
`frontend/apps/web/src`。因此 clean 前端产物 `dist-clean` 无需重建，仍与候选前端版本一致。

## 运行身份

- Namespace：clean（ns_c6fed472e939）。
- Database：sc_clean；dbfilter=^sc_clean$。
- 后端：http://127.0.0.1:8072/web/health → `{"status":"pass"}`。
- 前端：http://127.0.0.1:18083/ → 正常返回 `企业应用平台` index.html。

## 结论

前后端均绑定 sc_clean 同一次运行；API 请求数据库身份由入口命名空间在运行时解析。
