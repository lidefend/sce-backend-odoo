# PR 草稿：统一系统页面体验并冻结独立审查基线

## 摘要

以页面体系为交付单位，统一系统外壳、工作事项、付款集合与详情、层级工作区、配置工作台和异常恢复；冻结付款样板，并补齐独立审查所需的真实依赖、页面边界、候选身份和回退证据。

## 范围

- P0：共享外壳、页面模式、工作区、列表/详情表达和通用错误/浮层机制。
- P3：配置工作台的对象、草稿、发布及请求状态表达。
- P4：非零单元/静态门禁、受管候选浏览器载体、生成清单、证据、阶段报告及非执行性的 acceptance 命名空间重建设计。
- 不含：P1 历史迁移、fixture 生命周期改造、新增审批/支付能力、业务数据写入、多角色授权、独立移动端、性能重构、远程发布。

## 验证

- `make verify.frontend.quick.gate`
- `make verify.business_config.unit`
- `make verify.frontend.hierarchical_worksheet.unit`
- `make verify.frontend.overlay_lifecycle.unit`
- `make verify.frontend.page_identity`
- `make verify.frontend.theme_profile.unit`
- `make local.dev.test MODULE=smart_core TEST_TAGS=runtime_view_contract`
- `make local.dev.test MODULE=smart_core TEST_TAGS=business_config_change_set`
- 1088/390 明色与 1440/320 暗色受管候选浏览器矩阵
- `CONFIRM_FRONTEND_RELEASE_AUDIT=RUN_FROZEN_FRONTEND_RELEASE_AUDIT make verify.frontend.release.local`

当前 release gate 为 `not_run`：必须先由独立 P4 批次重建与源码版本一致的 acceptance 命名空间，并修正错误的详情验收目标；草稿不预写 PASS。

## 证据与回退

- 独立审查交付包：`docs/ops/iterations/frontend_system_page_baseline_delivery_20260909.md`
- 全量范围：`docs/ops/iterations/frontend_system_page_baseline_scope_manifest_20260909.csv`
- artifact 哈希：`docs/ops/iterations/frontend_system_page_baseline_evidence_manifest_20260909.csv`
- 回退按 manifest 的 formal layer、逐路径 commit 和验证列执行；混合 P0/P3 提交不作整提交单层回退。

## 已知限制

仅管理员真实会话与既有 demo 数据；配置写操作、其他角色、认证、独立移动端、性能和远程交付另行处理。
