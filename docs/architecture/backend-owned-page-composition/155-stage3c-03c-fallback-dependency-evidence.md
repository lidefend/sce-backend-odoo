# 155 · BNVA-019 Stage 3C-03C-02A · fallback 依赖证据

## 证据分层

| 类型 | 结果 |
| --- | --- |
| SOURCE_STATIC | 调用链唯一：catch-all 仅 `_page_composition_contract` 一处；primary_facts 仅启发式 DEFAULT |
| TEST_EXECUTION | 离线单测 + assembler/runtime guard 通过（迁移后） |
| RUNTIME_OBSERVATION | 上述页面 default_fallback=0、catch_all=0 |

## 判定

已知样本无真实 fallback 依赖。旧 catch-all 仅在原生投影抛异常且回退到
DEFAULT 时才可能执行，实际观测为 0。

