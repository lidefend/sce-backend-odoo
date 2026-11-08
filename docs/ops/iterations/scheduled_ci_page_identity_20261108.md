# SCHEDULED-CI-PAGE-IDENTITY-01：定时 CI 页面身份导航声明同步

## 批次边界

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：scheduled frontend page-identity audit declaration。
- Module：`config/frontend/authoritative_navigation.json` 与 frontend release evidence。
- Baseline：`88558bce9df0009749546f457b3a8a4a844cfb35`。

## 失败证据

- schedule run `42419449670` 在 main `5d184f483` 上执行 page-identity audit。
- 运行时真实导航为 63 个叶子，旧 `browser_leaf_keys` 为 33。
- 四个 schedule 失败 run 的依赖链为：
  `frontend_release_gate failure -> professional_quality_gate managed ORM consumer
  -> merge_policy_gate -> release_candidate_gate`。

## 根因

- PR #794 将多角色切换为 `discover_installed_capabilities`，真实可见导航扩展到财务、
  PM、owner 等角色的安装能力面。
- `authoritative_navigation.json` 的 full/browser 声明仍是旧快照。
- `frontend_release_evidence.py` 使用 full `leaf_keys` 汇总，而 navigation report
  使用 `browser_leaf_keys`，两个消费面口径不一致。

## 修复原则

- 不修改后端角色策略、菜单持组、ACL 或 Record Rule。
- full `leaf_keys` 只扩展，不删除历史已声明身份。
- browser audit surface 精确登记当前真实可见身份。
- navigation audit 继续拒绝 missing、unexpected、duplicate、invalid。
- release evidence 与 navigation report 统一使用 `browser_leaf_keys` 计数面。

## 状态

- 声明同步：PASS。
  - finance：28 个 browser audit 身份，full 59。
  - owner：13 个 browser audit 身份，full 16。
  - PM：19 个 browser audit 身份，full 37。
  - project member：3 个 browser audit 身份，full 10。
  - browser audit 合计：63；schedule 实测 63。
- 导航守卫：PASS。
  - role surface exposure：16 tests。
  - release navigation policy：18 tests，released identities 122。
  - navigation audit：31 tests；missing/unexpected/duplicate/invalid 仍 fail-closed。
- Release evidence：PASS，12 tests；汇总口径改为 browser audit surface，返回 63。
- Planner：PASS，80 tests；导航声明、导航审计、release evidence 及测试均映射到非候选
  `navigation_policy.unit` / `evidence_bundle.unit`。
- `ci.local.iteration`：PASS，5/5 targets 实际执行，无 blocked/not-run/unmapped。

Receipt：
`.runtime/frontend-dev-validation/executions/20261108T003125Z-265768-222379487/receipt.json`

## 未覆盖

- 本地已用 schedule run `42419449670` 的 63 个真实导航身份完成精确对账。
- 仍需在推送后派发 exact-head candidate full lane，确认 GitHub hosted runtime 端到端通过。
