# 414 · BNVA-04 Clean Browser Session Binding

## 源码一致性（五方）

| 维度 | 值 |
| --- | --- |
| Git HEAD | 11635b8fec38a4269bd2b75f0b0fe25990bf0fe2 |
| 产品提交 | b7e2383a156163794a93596372fb4d7dcd435855 |
| Odoo 源挂载 | /home/lidefend/workspace/sce-backend-odoo-pc01（实时 bind，内容=HEAD） |
| 前端构建 | frontend/apps/web/dist-clean（前端源码未随本批变更） |
| DB 模块版本 | smart_construction_core 17.0.0.172 installed |

## SHA 口径澄清

运行版本接口 `/t/clean/api/runtime-version` 返回 `source_revision=7a5a84ae`，这是 clean env 文件中
遗留的旧 `SC_SOURCE_REVISION`（`local.clean.prepare` 不刷新该值），不代表实际运行源码。实际源挂载
为 pc01 工作树（HEAD=11635b8fe），且 DB 已加载本批契约与视图修正（ORM 实测），因此运行时行为
以 HEAD 为准，`7a5a84ae` 仅是不一致的簿记标签。

## 浏览器会话身份

- Namespace：clean（ns_c6fed472e939，经 `/t/clean/` 前缀路由）。
- Database：sc_clean（dbfilter=^sc_clean$）。
- User：fixture_role_finance（独立 clean 会话，未复用 acceptance Cookie）。
- Backend revision：HEAD 11635b8fe（簿记标签 7a5a84ae 已澄清）。
- Frontend revision：与后端同源（前端源码未变更）。
