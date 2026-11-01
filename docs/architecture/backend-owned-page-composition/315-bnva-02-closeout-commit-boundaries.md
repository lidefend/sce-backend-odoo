# 315 · BNVA-02 Closeout Commit Boundaries

## 建议四个独立单元

| 单元 | 内容 | 数量 | 验证门禁 |
| --- | --- | --- | --- |
| A · P0 发布门禁修复 | ui_business_config_contract.py、backend_contract_boundaries.py、test_backend_contract_boundaries.py、test_view_orchestrator.py | 4 | py_compile、37 项边界/结构测试、62 项 orchestrator 测试、fresh rebuild PASS |
| B · P4 local.clean 工具 | make/dev.mk、docker-compose.yml、nginx 模板、clean runtime entry、6 个脚本 | 10 | demo 默认行为不变、clean 仅绑 sc_clean、platform 不变、bash -n / py_compile |
| C · P4 验收证据（286–306） | 17 份报告 | 17 | 报告内容与运行时证据一致，保留 NOT_RUN |
| D · 内核收口 + run record（307–313） | 7 份矩阵 + run.json | 8 | run.json valid、七维状态可复核 |

如按“至少三个单元”收口，可将 C+D 合并为一个文档/治理单元。

## 关键约束

- 不将环境秘密、`.env.local.clean`、artifacts 或临时角色纳入提交。
- 共享 nginx 模板/docker-compose 的改动只做参数化，默认值仍为 demo。
