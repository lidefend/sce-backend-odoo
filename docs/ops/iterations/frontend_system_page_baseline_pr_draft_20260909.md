# PR 草稿：统一系统页面体验并冻结独立审查基线

## 摘要

以页面体系为交付单位，统一系统外壳、工作事项、付款集合与详情、层级工作区、配置工作台和异常恢复；冻结付款样板，并补齐独立审查所需的真实依赖、页面边界、候选身份和回退证据。

## 范围

- P0：共享外壳、页面模式、工作区、列表/详情表达和通用错误/浮层机制。
- P1：对既有 acceptance 历史付款台账做当前约束兼容迁移；缺失身份只隔离，不推导或伪造。
- P3：配置工作台的对象、草稿、发布及请求状态表达。
- P4：非零单元/静态门禁、受管候选浏览器载体、fixture 通过正式资金基线修订生命周期保持幂等、生成清单、证据与阶段报告。
- 不含：新增审批/支付能力、新增业务写入口或未经治理的数据写入、多角色授权、独立移动端、性能重构、远程发布。已授权的 acceptance migration、fixture reset 与 release snapshot 写入单独登记。

## 验证

- `make verify.frontend.quick.gate`
- `make verify.business_config.unit`
- `make verify.frontend.hierarchical_worksheet.unit`
- `make verify.frontend.overlay_lifecycle.unit`
- `make verify.frontend.page_identity`
- `make verify.frontend.theme_profile.unit`
- `make local.dev.test MODULE=smart_core TEST_TAGS=runtime_view_contract`
- `make local.dev.test MODULE=smart_core TEST_TAGS=business_config_change_set`
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=p1_contract_payment_allocation`
- `make local.dev.test MODULE=smart_construction_acceptance_fixture TEST_TAGS=acceptance_fixture_gate`
- `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make acceptance.module.upgrade MODULE=smart_construction_core`
- `make acceptance.frontend.fixture`
- `make acceptance.frontend.release_snapshot`
- 1088/390 明色与 1440/320 暗色受管候选浏览器矩阵
- `CONFIRM_FRONTEND_RELEASE_AUDIT=RUN_FROZEN_FRONTEND_RELEASE_AUDIT make verify.frontend.release.local`

最终 release 命令结果以交付时同一 HEAD 的本地输出为准，不在草稿中预写 PASS。

## 证据与回退

- 独立审查交付包：`docs/ops/iterations/frontend_system_page_baseline_delivery_20260909.md`
- 全量范围：`docs/ops/iterations/frontend_system_page_baseline_scope_manifest_20260909.csv`
- artifact 哈希：`docs/ops/iterations/frontend_system_page_baseline_evidence_manifest_20260909.csv`
- 回退按 manifest 的 formal layer、逐路径 commit 和验证列执行；混合 P0/P3 提交不作整提交单层回退。

## 已知限制

仅管理员真实会话与既有 demo 数据；配置写操作、其他角色、认证、独立移动端、性能和远程交付另行处理。
