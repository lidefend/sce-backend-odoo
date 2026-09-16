# P4：可信主线与增量内容验证

## 范围与状态

配置中心 PR #485 已合并，main 为 `0e00c777eb518d3e30f5a7931206bae6e0c636bd`；源候选 `fc7326b563688ff5b7b38228046f8f8578d56533` 的完整 Tree 与合入结果一致，原 Quick 合并时直接复用。未部署、未清理现场，89 入口产品交付未完成。

本批分支 `fix/impact-scoped-validation`，Formal Product Layer=P4，Layer Target=既有本地验证/内容扫描入口，Module=scripts/ci、scripts/verify、make/ci.mk。验证成本归交付工具负责，不调整 P0–P3 产品、数据库、权限或低代码行为。复用现有工作区、Git/Quick receipt、Make 入口；无新运行环境。

## 实际失效层与修复

原本地 Quick 对密钥、个人数据及仓库历史做全量扫描；远端已有 trusted-base，但历史扫描最后仍遍历整个当前树。本批统一自动范围判断：

- 主线以 canonical origin 的 `origin/main` 完整 SHA 识别，必须为候选祖先。
- 复用现有工作区 Quick receipt：schema、producer、head、tree 必须有效，源提交存在且完整 Tree 与主线一致。支持 squash 后不同 SHA、相同 Tree；不改写旧 receipt 冒称新 SHA。
- 主线和当前工作树的扫描器、范围解析器、入口、政策及精确豁免输入必须相同。缺证据、身份不符、非祖先或规则变化时给出理由并全量检查，不能成功跳过。定时审计仍全量执行。
- 密钥/个人数据扫描工作区相对基线的变更、暂存/未暂存及未跟踪文件；历史逐提交枚举字段路径/对象 occurrence，覆盖中途加入后删除、改名及复用旧 blob 到新路径。不是只看最终 diff。
- 历史增量的最终树阶段限制为变化路径；全局仓库身份、根、远端、禁用对象及 Git 完整性检查保留。
- `ci.local.iteration` 输出三个扫描器的模式、精确基线、证据和回退原因。纯扫描测试与实际全量扫描拆开，日常可单独使用 `security.online_capture.unit`、`security.personal_data.unit`、`verify.repository.clean_history.unit`。

边界：本批收口上述三类重复内容扫描，不把最终 Quick 中其余业务/架构门禁宣称为已全部实现增量缓存。没有有效本地对应主线证据时会全量回退；不以任意CI绿色图标代替对应门禁证据。

## 定向验证

L0：以上基线及独立分支，dirty 范围明确。L1：`make ci.local.iteration` 通过。L2：新增17个真实临时Git仓库/CLI测试、原密钥10项、个人数据6项、历史31项通过。覆盖缺失/畸形/错误Tree receipt、非祖先、错误远端、规则删除、精确豁免变更、定时全量、squash同树、旧blob新路径、中间删除敏感内容、未跟踪内容及真实CLI范围选择。

关键效率反例：基线文件未变、候选仅新增一个文件时，密钥/个人数据的工作区读取集合和历史读取集合仅含该文件；history CLI 实际 `read_blob` 集合仅含候选 blob。中间加入后删除的敏感内容仍被两个CLI拒绝。

原日志保留于 `artifacts/config-center-entry/impact-scope-{static,tests,cli-tests}.log`，后续结果在 `artifacts/impact-scoped-validation/`。L3/L4 不运行：没有运行产品输入变化，不升级库、不重跑产品矩阵。扫描器本身发生变化，本批最终扫描不能继承旧扫描器结果；普通业务分支在规则未变后才进入自动增量路径。独立复核/最终门禁结果绑定最终候选，另记已有未跟踪结果区。

独立复核闭环：初审识别自定义 `--policy` 未纳入自动权威集合，以及模式回退后对象集合仍走增量的 S1。现自定义策略显式全量；对象集合只在最终 scan_mode 为 trusted_base_incremental 时缩小。新增一个含两个分支的反例，确认调用完整历史集合、未调用增量集合。17+10+31受影响测试通过（个人数据6项输入未变沿用）。代码变化复核无其余S0–S2。历史guard保持已提交commit/HEAD语义，未新增未提交路径专属规则扫描；最终Quick仍绑定clean HEAD。

## 远端门禁收口

候选 `2a75a655dbdc2de098c6e555813a3289f50f0864` 的本地 Quick 与独立复核通过，PR #486 已创建。远端 professional/public/merge 三项通过；frontend_release_gate 暴露两项既有基线不一致：页头守卫仍要求未含 `!isConfigurationPreview` 的旧表达式；表单1902行超过1900上限。基线 main 与该候选这三个相关文件完全相同，非扫描工具引入。

最小修复：P4页头守卫改为要求当前预览禁写条件并加拒绝反例；P0表单仅删除两行空白（模板及全部非空代码逐行一致），未放宽1900上限。`verify.frontend.product_page_header.unit` 28模型+12守卫、`verify.frontend.style_system.guard`通过。扫描器输入代码未变，定向扫描测试沿用；不重跑浏览器、发布回滚或数据库旅程。新候选刷新受影响生成证据后绑定最终门禁，原失败不改记通过。四层状态保持工具待集成、未部署、89入口未整体交付。
