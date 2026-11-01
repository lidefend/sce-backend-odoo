# 391 · BNVA-04 Two-Page Productization Regression

## 一致性

- 两页共用同一机制：`composition_mode=native_semantic_surface` 稀疏注解，结构权威交给原生 arch。
- 两页业务身份独立：质量问题（`workflow_authority=sc.quality.issue`，标题「质量问题办理」）
  与 外经证登记（`tax_certificate_registration_productized_form_v1`，标题「外经证登记」）
  不共享字段结构、不合并通用模板。
- 两页均未新增 Identity / Section / FieldOwnership body，均未复制原生 arch。

## 差异

- sc.quality.issue 的 action 原本未显式绑定 form，产品化补了 `ir.actions.act_window.view` 绑定。
- sc.tax.certificate.registration 的 action 已显式绑定 tree+form+search，无需补绑定。

## 运行时回归

| 项目 | 结果 |
| --- | --- |
| List / Form 一致性 | NOT_RUN（无运行时 fixture） |
| 关系字段（project_id / handler_id / attachment_ids 等） | 静态声明齐备，运行时 NOT_RUN |
| 保存及重新进入 | NOT_RUN |
| 角色权限表现 | ACL/Record Rules 未改动，运行时 NOT_RUN |
| 页面导航 | 菜单/动作已存在，运行时 NOT_RUN |

无真实运行时条件，按口径如实标记 NOT_RUN；已具备运行时后按 BNVA-04-06 验收清单补齐。
