# ACCEPTANCE-READINESS-EVIDENCE-20261107 记录

分支 `fix/acceptance-fixture-readiness-evidence`，基线 `fdd039b4`（main，已合入 #828/#829/#830）。

## 目标

补齐两条此前 NOT_VERIFIED 的浏览器证据：

1. 非草稿项目整段隐藏立项完成度与页头 readiness notice。
2. 可读但无提交权的账号打开草稿，页头一条脱敏 forbidden、正文 0 条。

## 夹具最小变更

- 新增非草稿载体 `fe_project_non_draft`（lifecycle_state=in_progress, sc_approval_state=approved），
  由 pm 管理并关注，与 FE Project A/B/C 分离。
- `fixture_role_project_a_member` 增加 `group_sc_entry_p11`（菜单 382 的只读入口），
  不扩提交能力（`_has_initiation_submit_access` 只认 project_user/manager/super_admin）。

## 探针

- `local_acceptance_project_overview_browser.mjs` 增 `project-non-draft`（notice=0、完成度文本缺失）
  与 `project-forbidden`（notice=1、正文 0、标签含无权限）。
- `frontend_readiness_non_draft_resolver.py` 只读解析非草稿载体 ID。
