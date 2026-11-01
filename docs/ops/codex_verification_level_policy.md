# Codex 验证层级策略（避免反复重跑全量 Quick）

> 目的：按任务类型选择最低充分验证，不再每提交一次就跑 `make ci.local.quick`。
> 本策略是 AGENTS.md「Layered Validation Efficiency」的操作化补充，优先级低于 AGENTS.md。

## 任务类型 → 最低充分验证

| 任务类型 | 最低充分验证 | 是否跑完整 Quick |
| --- | --- | --- |
| 只读审计 / 设计文档 | `git diff --check` + 文档自检（无代码改动） | 否 |
| 纯测试新增（不改产品代码） | `py_compile` + 定向单测 | 否 |
| 死代码 / 未用导入删除 | `py_compile` + 定向单测 + `verify.unified_page_contract.v2.assembler` | 否（阶段末一次） |
| 内核行为改动（handler/assembler/parser） | `py_compile` + 定向单测 + assembler/runtime guard + 五个页面 smoke | 阶段末一次 |
| 请求级缓存 / 权限 / 生命周期改动 | 上述 + 权限对照测试 + 隔离单测 | 阶段末一次 |
| 阶段收口（一个 Stage 完成） | 一次精确 HEAD Quick | 此时跑一次 |
| 集成 / 合并前 | 一次精确 HEAD Quick + relation roundtrip + 必要 list surface | 此时跑一次 |

## 轻量验证清单（取代逐提交 Quick）

```bash
# L1 语法/静态
python3 -m py_compile <changed files>
git diff --check

# L2 定向单测（按变更选择，非零测试）
# 通过 candidate 容器 bootstrap 运行对应 test 模块

# L2 assembler/runtime guard
make verify.unified_page_contract.v2.assembler
make verify.unified_page_contract.v2.runtime

# L3 五页面 smoke（仅当改动影响契约/结构）
# 通过 odoo shell 对五个样本调用 handler，断言 authority/slots/manager_id 不变
```

## 触发完整 Quick 的两个唯一时机

1. 一个 Stage 收口（本地阶段交付）。
2. 用户批准集成前的最终验证。

其余提交一律用轻量清单，不再逐提交跑 Quick。

