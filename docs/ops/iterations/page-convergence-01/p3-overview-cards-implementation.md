# PAGE-CONVERGENCE-01 / P3 · 实施记录

## 变更范围

仅两个文件：

1. `addons/smart_construction_core/views/core/project_overview_views.xml`
   - 四卡由 `card/card-body/fw-bold/text-muted` 重组为语义 token：
     `sc-project-card / __title / __metric / __empty / __value-row / __value / __unit / __action`。
   - 合同卡把「权限空态」与「计数区」拆开，保留原 `invisible` 条件与 `groups`，不新增字段。
2. `frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue`
   - 新增上述 token 的 scoped 样式（复用既有 `--sc-space-*`、`--sc-font-*`、`--sc-product-*` token）。
   - 修正 `hasRenderableDescendant`：嵌套容器若携带可见静态文本即视为真实内容，避免合同卡的
     权限空态（纯文本）被误判为空壳而整体隐藏。

## 验证

- `verify.frontend.native_text_presentation.unit`：PASS（21 cases）。
- `verify.frontend.native_form_structure_responsibility.unit`：既有失败（测试断言
  `activePageIndex`，模板已改为 `Number(item.value)`），与本轮无关，记为 pre-existing，不在 P3 修复。
- `make local.dev.upgrade MODULE=smart_construction_core` + `make local.dev.restart`：
  视图升级 77 模块加载、demo authority PASS，服务进程重启加载新代码。
- 四视口浏览器 DOM 验收：见 `p3-overview-cards-evidence.json`，控制台错误 0，无横向溢出。

## 数据边界

- 未修改 `contract-field-fact-diagnosis.md`（结果 B）。
- 未修改 `unified_page_contract_v2_assembler` / 原生视图解析器。
- 未修改 `project_core.py` 的 `_compute_overview_counts`。
- 未修改 ACL / record rule / 角色 / 业务数据。

## 未合并、未部署
