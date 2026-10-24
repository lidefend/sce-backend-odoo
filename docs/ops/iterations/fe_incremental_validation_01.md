# FE-INCREMENTAL-VALIDATION-01

目标：精确候选之间的 RUN / REUSE / BLOCK 决策及实际工作量对照。

- 分支：`fix/fe-incremental-validation-01`；起点：`1ddade160d7759ebb2fcda03c162d42593461e45`，该提交仍仅在本地。
- Formal Product Layer：P4；Layer Target / Module：既有 CI 影响分析、测试登记与 evidence_scope 引擎。
- Standard vs User-Specific：通用验证机制。测试定义与覆盖范围由现有入口决定，不新增平行注册体系。
- Why Here / Why Not Elsewhere：问题在测试选择及证据消费，不涉及 P0–P3 业务规则。
- Blast Radius：先只读取证与依赖映射；证据明确后实施最小适配；保留 PR #722 的远端门禁与资格。
- 排除：产品逻辑、放宽断言、推送、合并、部署、重跑有效的 14 模块全量测试。
- 集成基线：PR 对 main 的完整变更；增量基线：对已验证候选的变化；两者独立记录。
- 当前阶段：Stage 0/1；不预记复用成功，不将估算时间写成实测节省。
- 回滚：本批仅工具与记录变更，可独立撤销，无服务/数据库变更。

证据根目录：`.runtime/fe-incremental-validation-01/`。

## Stage 0：事实与原始证据

PR #722 仍 OPEN/CLEAN，四项必需检查成功。此前 `pr.merge.prepare` 成功回执保留在主工作树 `.runtime/fe-ux-entry-continuity-remote-integration-01/prepare-final.log`，本轮未重复执行。

| 身份 | 上一候选 | 当前 PR 候选 |
| --- | --- | --- |
| SHA | `459e4f133056fadbefd46451ae9190a9f91e314d` | `88b4c1609eb2802f95a0b367a44efffd985db173` |
| tree | `432176db49dfd73cbe59a9bb9c8c28f17503f54a` | `7be4386a1d38cd65194c0d825be612721c9172d3` |
| workflow run | 40094246011 / attempt 1 | 40094940241 / attempt 1 |

两次集成基线均为 `96c860d0fb041c556b687afaad6dc689528785e5`，从原始运行日志的 BASE_SHA/IMPACT_BASE 核对；不把 API 中可能随 PR 更新的嵌套 head/base 字段当作历史事实。运行顶层 head_sha、job 成功及日志测试结果交叉核对。

`1ddade160d7759ebb2fcda03c162d42593461e45` 的父提交是当前 PR head，tree 为 `324baf4a8acb7c2e2e6632058765d63cf4ecdeea`。8 文件差异仅含行号语义比较、本地预检接线及该批上下文；没有远端增量决策器。仍未推送。

原始证据包括两次 run/jobs JSON、完整日志、artifact 列表、PR 快照和 SHA256 文件清单。两次专业 workflow artifact 数量均为 0。`previous-baseline.json` / `current-baseline.json` 将每个模块的日志行号、真实测试数及时间段绑定原始文件摘要。

## Stage 1：实际依赖与复用资格

`dependency-map.json` 从既有 backend_impact_plan 的 manifest/import 图和实际执行入口生成，覆盖 14 个模块及 433 个潜在测试源码文件；实际执行的带标签测试及 Python 测试共 673 项。该文件是分析产物，不是新的测试注册表。

| 目标类别 | 现有执行入口 | 已确认的依赖 | 复用限制 |
| --- | --- | --- | --- |
| 13 个 ORM 模块 | `make test MODULE=<module>` → scripts/test/test.sh | 模块安装依赖、测试标签、Make/脚本、Odoo 与 DB、docs/config 挂载、测试依赖包、安装产生的角色权限 | 缺少已执行容器完整环境指纹，不能仅按模块源码复用 |
| 场景 Python 测试 | workflow 内 unittest discover | 场景源码、动态 importlib 加载、smart_scene/行业能力、PyYAML、场景 YAML 与 delivery JSON | 模块 import 图不能覆盖全部动态文件读取；宿主测试工具身份未形成输入回执 |
| professional 质量检查 | 既有标准后端 Make 组合与单独 ORM 检查 | 全仓源/生成物、契约、发布声明、语法工具及 ORM 上下文 | 不能由“后端模块 0 影响”推断整个 job 可复用 |
| frontend_release_gate | pnpm lint/typecheck/test/build | 前端源码与 lockfile、Make 单测、台账、Node/pnpm、生成物 | 本次台账修正属于该入口实际输入，原失败不得复用 |
| public_guard | 仓库历史/公开范围/工作流扫描 | 当前差异、历史范围、扫描定义与权限策略 | 新 SHA 仍须当前范围裁决 |
| merge_policy_gate | 当前候选检查聚合 | 实时 head/base、当前权威检查与状态 | 始终重新聚合，不复用旧 ready 状态 |

已证实两个缺口：

1. `backend_impact_plan.NON_RUNTIME` 包含 `docs/**`，但 `test_action_only_scene_semantic_supply.py` 直接读取 `docs/product/delivery/v1` 的三份 JSON。离线反例 `dependency-counterexample.json` 表明修改该依赖仍返回空模块列表。现有“0 模块”仅可用于初筛，不足以作为 REUSE 证明。没有修改测试文件或规则。
2. `scripts/test/test.sh` 在每次一次性容器启动时在线安装 `config/requirements-test.txt`；其中 `odoo-test-helper`、`jsonschema` 未锁版本。PostgreSQL/Redis 使用可变标签，历史记录没有实际镜像 RepoDigest 或安装后的完整包身份。已记录的 Docker/Compose 版本、固定 Odoo base digest 和 runner image 版本不足以填补这些缺项。

因此当前 14 个目标的严格复用资格均为 BLOCK；原有必需全量执行仍是无可靠证明时的保守回退，不被本分析关闭。`input_fingerprint` 明确为 null，另列测试源码摘要，避免将部分摘要冒充完整有效输入身份。本轮没有触发回退执行。

## 远端缓存核查

通过 Actions cache API 全分页取得 43 项缓存：41 项前端 BuildKit 层、1 项 pnpm、1 项 Chromium。PR #722 命中缓存 ID `9445555605`，key 尾部 `ac55df1b…`，大小 195804303 字节，ref 为 `refs/pull/722/merge`。

- 上一次 4 分片使用 frontend 层前缀回退，后一次 4 分片精确命中。缓存路径仅为 runner.temp/backend-frontend-buildkit，由 frontend builder 的 cache-to 导出。
- 前端构建步骤观测由 41/49/42/46 秒变为 13/17/17/17 秒。这是既有缓存命中后的历史观察，不是本专项实测提效。
- Odoo 构建与数据库启动仍各需 66–97 秒（当前 4 分片）；该 workflow 没有持久化相应构建缓存或测试结果回执。isolated builder 在 cleanup 删除。
- professional 的 pip 缓存路径为宿主 `~/.cache/pip`，且恢复发生在 ORM 执行之后；实际 pip 安装在一次性容器内。两次日志均有 Path Validation Error（路径不存在，未保存），当前 API 无 pip 缓存项。
- 构建 cache、依赖包 cache 均不能替代测试成功与环境输入回执。仓库的 Gitee frontend-reuse 机制也未被这些 GitHub workflow 调用，不能跨环境套用。
- 核查了缓存元数据、命中日志及保存/消费路径；没有下载或执行缓存归档，没有清理远端缓存。

## 定量基准与当前完成边界

| 指标 | 上一候选实测 | 当前 PR 候选实测 |
| --- | ---: | ---: |
| 模块执行数 | 14 | 14 |
| 实际测试数 | 673 | 673 |
| 4 分片墙钟跨度 | 487 秒 | 636 秒 |
| 4 分片 runner 时间合计 | 1536 秒 | 1713 秒 |
| 模块执行阶段累计 | 871.704 秒 | 1155.056 秒 |

这些是 GitHub 原始记录，并非新策略的对照实测。当前新策略尚未执行：REUSE 0、证明不足 BLOCK 14、新触发模块执行 0、可认领实测节省 0 秒。不能把没有重跑解释为已经证明节省。

Stage 0/1 取证完成，但复用依据尚未闭合；Stage 2–4 未开始，不宣布专项验收完成。当前不新增一个只能把 14 个模块再次全跑的控制器。下一最小步骤：在既有 CI 执行/回执路径补齐完整环境与有效输入身份，修正已证实的依赖映射缺口；再由既有 evidence_scope 引擎做候选间决策。历史缺失身份不能通过今天的缓存标签或今天重新 pull 镜像补造。下一次本来就需要执行的受管 CI 应顺带记录，避免为补回执专门重跑旧全量。

本轮仅只读取证、离线依赖分析与记录更新；未修改验证规则、断言、产品代码或 PR，未推送、合并、部署。
