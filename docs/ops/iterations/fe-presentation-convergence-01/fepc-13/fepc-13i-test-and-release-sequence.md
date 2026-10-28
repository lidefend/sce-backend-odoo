# FEPC-13I 测试、PR与启用顺序

这是实施前拆分建议，不是实施授权。当前仅I-00核查PR可提交；所有未来协议行为测试为not_run。版本标识仍待正式批准，不能直接把设计候选写入运行时。

## 分阶段独立PR

| 顺序 | 独立PR结果 | 合并前判据 | 对实际客户端的边界 |
| --- | --- | --- | --- |
| I1a 声明与编译 | 正式版本化schema支持、同一发布载体关系验证、有效布局绑定与唯一widget解析 | locator缺失/歧义、布局变更、跨记录/字段错配、权限与同级冲突均拒绝；旧定义不变 | 内部能力默认休眠；不得将assembler全局版本直接切到候选新版本，不发布任何启用定义 |
| I1b 安全交付 | 协商、完整旧投影、目标schema校验、最终seal与缓存隔离、未证明patch全量刷新 | 正常/缓存早返回/scene、full/patch边界及真实固定旧decoder矩阵全部通过；非法定义不被降级掩盖 | 旧请求永远合法旧结构；生产/用户入口的启用发布保持关闭。只有独立测试输入可声明新能力，不能对旧Web发新对象 |
| I2 前端消费 | 类型/严格decoder、page identity与presenter、原生文本叶子、可访问性；最终才广告新能力/版本 | readonly/edit/create/preview、复合标题、多occurrence、favorite、键盘/可访问树与旧payload回归 | 单独代码支持不等于启用定义。若分多个前端PR，能力广告必须最后，不能先广告后实现 |
| I3 隔离集成 | 候选服务端+新/旧Web、隔离受管fixture与回滚验收证据 | 新旧协商、缓存、全量刷新、身份/模式/布局切换、sticky及可访问行为实测 | 不写当前Demo；发布范围与环境需要另行批准 |
| 后续启用/部署 | 明确版本、环境、定义来源、受众及回退计划 | I3完成且独立授权 | 才允许在目标环境发布经批准的绑定定义；合并不自动部署 |

I1a与I1b之间必须保持输出协议完全旧态；若无法做到独立禁用，则不得单独合并会导致新输出的半成品，应收敛该最小依赖集合再审查，而不是放宽旧客户端兼容。每个PR只承担对应可独立验收结果，不把I1/I2/I3合成一次大改。

## 必需测试与已知复用入口

- 声明编译/载体：复用form_configuration_compiler、business_config_contract_schema相关测试；入口候选 `verify.frontend.bound_form_configuration.unit`。先核对当前target真实包含范围再补新关系用例，不另建重复车道。
- 缓存/交付：`test_ui_contract_v2_boundaries.py`、`test_load_contract_response_cache.py` 可通过现有 `verify.business_config.formal_list.unit` 验证基础；补本协议用例时必须覆盖所有返回路径，不能只在某一scene fixture通过。
- 真实旧decoder：固定 [核查稿](fepc-13i-implementation-readiness.md) 的完整提交与依赖图；本轮已跑 `verify.frontend.contract_v2_runtime_policy.unit`、`verify.frontend.contract_v2_occurrence_authority.unit`，证明入口真实可执行。未来运行生成的旧投影fixture正例及错误版本/key负例，不能让旧oracle随新客户端一起升级。
- 新decoder/presenter：复用上述前端测试体系与 `verify.frontend.canonical_form_presenter.unit`；对版本/能力/结构三者组合、唯一occurrence、最终readonly来源及未声明旧契约给出判别断言。
- I3浏览器：复用已登记标准页面验收入口与隔离profile，不新增并行验收车道。新数据/收藏/保存测试只使用已授权fixture，必须记录写入与恢复；本次核查无任何此类行为。

目标schema验证必须使用协商后的合法完整payload，不以示例片段或additive模型冒充。需要固定服务端产物哈希、旧decoder提交及fixture哈希，报告非零测试数与覆盖范围。

## 准入矩阵

1. 客户端缺新能力、缺新版本、只支持旧结构：收到完整合法旧payload且保留原文本/控件；不仅删除新key，还必须恢复旧结构和外层版本，lifecycle/envelope不能残留错误新版本。
2. 无共同版本：明确不兼容。非法源关系：在降级之前拒绝，不把非法关系当成无声明。
3. 缓存：能力/版本、用户/公司、record/profile、view/定义/有效布局切换及A→B→A；命中早返回与冷组装结果具有相同交付保证。
4. patch：原有patch自身snapshotId不是base证明；新关系默认全量刷新。只有证明base/layout/binding不变后才能单独授权仅数据增量，并保持页头身份与省略状态原子更新。
5. 回滚：撤回启用定义或停止支持新交付，恢复原生文本；原业务数据与权限不变。刷新/错误期间不能出现两处身份都不可用。
6. I2/I3继承FEPC-13D-R1全部可访问性、编辑/创建、收藏、附加语义、配置预览和固定页头要求，不以服务端协议测试代替。

## 当前已执行与未执行

已执行：源码链追踪、GitHub main与本地身份核对、两个现成Web decoder测试入口；文档/JSON/链接校验与交付门禁记录在本轮run及PR。

未执行：新协议schema/交付/缓存/严格旧投影/可访问/浏览器集成，因为实现尚未授权；没有任何本轮Demo请求。既有测试成功只证明旧基线与测试入口可用。

最终停止点：独立核查PR待GPT复审，之后才授权I1a/I1b的具体范围。09-04继续未修复，F1继续待核实、暂不修复；DATA-01和CFG-01不并行启动。
