# 验收证据按套件输入复用收口（2026-10-19）

## 背景

此前验收演进门禁以 HEAD 作为唯一失效键：任何一个后续提交（包括纯文档或 `.agent`
簿记）都会让整包验收证据失效，导致同一份未变化的验证结果被反复重跑。本地 Quick
同样以 head+tree 全等复用，纯簿记提交也会触发整套重跑。

HEAD 只是来源标识，不是运行输入。真正的失效条件是“该套件声明的输入发生变化”。

## 修复

- 验收证据改为按套件输入指纹复用：`suite_input_sha256(registry, suite, head)` 在
  源 head 与评估 head 上一致，且证据文件字节、适配器、计数与时效全部复验通过时，
  才沿用原记录；记录写入 `bound_head`、`input_sha256`、`carried_from`、`carried_at`。
- 输入变化、证据文件缺失、字节被篡改、记录过期或源 head 不是祖先时一律 fail-closed。
- `ACCEPTANCE_EVOLUTION_CARRY_FORWARD=1` 时 `acceptance.evolution.record` 只做
  “输入未变的套件重新锚定”，不再生成新覆盖；不新增独立 Make 目标，避免扩大
  零引用验证面。
- 删除未被生产路径使用的整包簿记指纹分支，策略强制
  `evidence_carry_forward.mode=suite_input_fingerprint`。
- `make/codex.mk` 的簿记候选拒绝改用 `local_quick_evidence.py bookkeeping-delta`，
  与 Quick 复用判定共享同一套簿记路径定义，避免两处口径漂移。
- 新增/更新单测覆盖：套件指纹分层、输入变化拒绝复用、簿记候选复用、根 README 复用、
  运行输入不复用、`bookkeeping-delta` 路径一致性。

## 边界

- 复用只说明“声明输入与源 head 相同”，不产生新的覆盖，也不能替代远端必需检查。
- 本批次不改变部署、数据库、前端运行时行为或任何产品契约。
- 新 head 的远端必需检查仍然是合并前提；旧 head 的远端成功不继承。

## 验收

- `make verify.acceptance.evolution.binding`
- `make verify.branch.governance.consistency`
- `make ci.delivery.freeze.prepare`
- `make ci.local.iteration`
- 提交后按精确 head 运行 `make ci.local.quick`
