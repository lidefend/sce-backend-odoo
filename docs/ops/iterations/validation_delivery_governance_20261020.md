# 验证交付体系治理 2026-10-20

## 范围与身份

基线 `58f39bec868aa3649862bc698d9e42393eaffcfc`；分支 `fix/validation-delivery-governance-20261020`。
Formal Product Layer: P4。Layer Target/Module: scripts/ops、scripts/verify、Make 交付入口。
Standard vs User-Specific: 通用交付机制。Why Here: 负责验证调度与证据可用性，非产品语义。
Why Not Elsewhere: P0-P3 与前端不应决定交付证据有效性。Blast Radius: 只读计划、开发测试回执、冻结预检。
不部署、不改数据库或凭据，不降低远端检查、Quick 或验收证据标准。

## 执行计划与验收

1. 审计实际重复与漏检：复用既有 run/evidence 权威；输出确定性缺口。
2. 落实只读统一计划：包含 dirty 改动、全部必需验收证据与原因、已有定向检查及下一步；不以计划作为通过凭证。
3. 强化检查依赖与失败重试边界，用离线真实 Git fixture 覆盖证据不变、失效、零测试、缺失、篡改和依赖阻断。
4. 接入冻结前提预检；运行 L1 与非零定向 L2，B线独立复核；同步使用规范与真实剩余限制。

验证层：L0 当前身份；L1 ci.local.iteration；L2 治理机制定向测试。L3/L4 跳过：无运行产品/数据库/浏览器变更；L5 待定向门禁通过后按发布范围执行。
回滚：撤销本批 P4 文件；原始证据不覆写、不搬迁；新计划只写 .runtime。
唯一结果索引：对应 .agent/runs run.json；原始日志存 .runtime/validation-delivery-governance。

## 机制发现与变更

- 逐项环境身份缺失：修复旧环境未执行兄弟项被台账头部重新绑定的问题；保留部分失败已完成项，记录权威待办集合。
- 开发检查仅提示禁止重复：begin 现在拒绝未变失败；通过项显式理由重验；DAG 依赖传播输入失效，record 再核验。
- 合并验收基线可被环境变量覆盖：前置只读取实际 PR source/base；Quick 后再次读取身份与证据，保留平台非原子目标窗口说明。
- 昂贵检查先于前提：pr.merge 改为显式 recipe 顺序，make -j 不能提前启动 Quick。日常与冻结入口均输出只读交付计划。

首次组合测试 136 项中 1 项导入错误，归属 P4 入口（不是产品失败）；新增目标补齐 PYTHONPATH=scripts/verify。旧独立分支治理入口的 62+23 项均通过。
补充依赖清单后重新开始记录，早期诊断结果不作为可复用回执。新增真实 Git fixture 覆盖 dirty/untracked 影响。

## 本批复核与结果

阶段身份：HEAD=58f39bec868aa3649862bc698d9e42393eaffcfc，明确 dirty，未冻结/未提交。
L1：make ci.local.iteration 通过，最终原始日志 .runtime/validation-delivery-governance/iteration-final.log。
L2：make verify.validation.delivery.unit，141 tests / OK，原始日志 .runtime/validation-delivery-governance/targeted-final.log；已通过 agent.run.record 登记，后续计划实测输出 reusable，不重复执行。
既有独立分支治理入口诊断 62+23 项通过；最终组合重验仅保留受影响合并类、增量引擎与部分失败类。
B线独立复核：当前 dirty 实现通过；P1 身份误复用与 PR 基线绕过封闭，partial兼容保留。
批次复核以离线真实Git、台账及Make行为为对象，无产品页面或数据库验收要求。证据声明→工具消费→实际拒绝/复用/保持剩余项由定向测试绑定。

批次状态：本批机制改动及定向验收完成。主线状态：未提交、未合并。部署状态：未执行。用户产品验收：不由本批授予。
当前正式验收映射仍将 scripts/ops 变更选入 daily_runtime_entry、path_namespace_identity；计划已提前暴露这两项正式集成待办。本批不修改映射、不降低既有门禁，不将离线回执称为运行证据。
下一步如推进主线：处理现有正式套件选择/证据缺口，准备生成报告，冻结候选后按当前仓库车道完成 Quick、独立冻结复核和远端必需检查。禁止将本次 dirty 复核复述为冻结审查。

## 迭代效率增量（同批续跑）

影响推导：只变更P4治理映射、统一输入归属谓词、推荐器消费及测试分组。五条精确治理路径只需静态治理；其他运行工具及混合修改仍要求原运行验收。全局证据权威和显式suite.inputs保持优先，不能以第一匹配规则排除它们。
原141汇总不含evidence_scope入口的Node身份测试，不能宣称覆盖；拆为治理、evidence_scope、binding、planner四项回执，不新增covers权威。原日志保留；本轮因实际配方/输入变化重验这四组，后续按精确目标独立复用。
L0沿用原HEAD与明确dirty；L1现有入口；L2四组定向；L3/L4无产品/环境输入变化不执行。

冻结准备首次失败归属P4历史索引：PLATFORM-ADMIN-CREDENTIAL-MECHANISM-20261020已completed仍登记active。只删除该active映射，保留原goal/run/日志；定向ledger检查恢复后继续冻结准备，不重跑四组未变测试。

## 效率增量最终结果

四项定向：治理73；evidence_scope Python69 + Node57 + observation16；binding31；planner32，共278项检查通过。原始日志分别 governance-wired.log、evidence_scope-bound.log、binding-efficiency.log、planner-efficiency.log，均在 .runtime/validation-delivery-governance 下。
完整scope入口与组合测试组不再重复包含同一组Python模块。新增治理测试已真实接入正式治理套件，接线测试通过。所有结果在同一run按目标独立登记。
验收映射测试证明：五个精确P4治理文件不再选daily_runtime_entry/path_namespace_identity；部署工具和混合变更保留原运行门禁。此项撤销上文旧阶段“两套运行证据待办”，不是跳过已选门禁。
新增源码输入 business_entry_matrix_model.mjs 后只重验受影响scope组；新增治理接线测试后只重验治理组，binding/planner回执原样复用。L1 ci.local.iteration通过。

最终只读回读：四组回执全部reusable，增量推荐已移除四个已完成目标；仍有前端选择器未映射P4路径，保留人工选择提示，不将其冒称为全仓自动覆盖。冻结准备及生成报告门禁通过。批次开发验收完成；即将冻结本地候选，主线/部署/用户验收未完成，后续Quick/CI回执只存.runtime或PR文本。

## 冻结Quick诊断与责任修复

候选 e7cd95d7f2bbde965a0845e05ef3fbfd58e1818f 的第一次Quick失败，无receipt；原始quick.log保留。失败不是业务验收，而是guard registry分类和可达性两套解析：前者只识别.py字面，后者支持unittest点号模块。修复共用模块调用识别，支持多模块及Class.method；24项测试通过。既有seed按真实引用删除1条过时孤立登记及56条过时file-consumed，未添加豁免。
同层独立检查：test coverage通过；lane coverage报告原acceptance.evolution.verify失去使用登记，正式规范补充独立验收诊断用途，保留功能且不作为PR基线权威。无修改冻结baseline。
此前已通过组中仅governance/binding因Make依赖变化重验；scope/planner继续复用。新候选重新生成报告后重跑最终Quick属于已记录输入恢复，不盲重试旧失败。

覆盖检查仅接受白名单/工作区规范的入口声明，已在白名单登记独立诊断用途；普通说明文档不作为接线证据。lane-measure.json 实测以下七项已有引用，移除过时零引用登记：verify.acceptance.runtime.baseline_rebuild.unit, verify.construction.create_defaults.unit, verify.contract.schema.declaration.sync, verify.frontend.standard_preview.unit, verify.frontend.system_state_recovery.unit, verify.frontend.workspace_composition.unit, verify.local.development_lifecycle.unit。保留原冻结baseline，不增加豁免。治理73、binding31因Make变化重验通过；registry24通过；scope142/planner32输入未变复用。

独立复核否决上条七项删除：registry reason被通用文本索引误判为消费者。七条原登记全部恢复；将registry.yaml归为叙述数据，保留read_anchors结构化入口解析。新增真实Git小仓回归证明reason不能复活dead target且真实anchor保留。不修改baseline。先前lane通过不再作有效结论，按工具输入变化仅重验lane组。

排除registry叙述后额外暴露两项原本仅有reason引用的入口：product_view_structure定向单测与native guidance精确退役重放。按既有配方在执行白名单明确使用场景、前后验证及禁止自动写入边界；本批不执行退役写入、不新增豁免、不改变baseline。

修复收口结果（HEAD=e7cd95d7f2bbde965a0845e05ef3fbfd58e1818f+上述dirty范围）：lane整组73项中71项通过，2项依赖实际登记状态的仓库断言失败；权威声明修正后只重验这2项，通过（lane-invariants-recovered.log），其余71项输入未变沿用lane-narration-unit.log。实际覆盖检查lane-narration-final.log通过。L1 iteration-lane-fixed.log通过。B线复核通过，新增入口仅按需声明，不称已执行/自动接线。此次修复不重跑scope/planner；五组本地回执均reusable。原Quick失败保留，新候选Quick/远端CI/主线仍待完成。

## 已授权GitHub已发布候选同步

所有者本轮明确授权补齐受管同步并处理三处已预览冲突。P4 / scripts.ops同步工具：复用现有Gitee同步机制，仅参数化远端并加入冲突处理回调，原Gitee默认行为不变。GitHub包装绑定PR/分支/源SHA/main及canonical origin；无产品语义或环境写入。active-runs按三方键合并，同键竞争拒绝；两份生成报告仅暂存候选版，同步后由freeze.prepare重生成。其他冲突或同步中远端漂移abort，恢复bundle与原HEAD保留，不推送。
L0=e6bf710+本次dirty；L1 syntax/iteration；L2真实Git同步回归与受影响治理组；L3/L4无数据库或页面输入不执行；L5新候选Quick、独立复核、远端当前基线CI。原Quick对象覆盖因并行main推进失效，已停止回退执行，不冒称取消为通过。

受管同步完成：d24b621e57e6294c3e9a8d4d0492b2ffc1248348 + main 6dd15103ae8f0f892f7e89d915039cff3dd5b997 → b5ade7efac57f7b82ad1d96d206eb0e0f8ca28db，parents精确匹配。三处冲突均在授权集合内。恢复bundle及SHA见.runtime/validation-delivery-governance/github-sync-applied.log；未远端推送。run基线推进到本次已合入main，原基线保留上文和原回执。同步组53、binding31、governance73通过；输入不变scope/planner沿用。main仅改变runtime_ops Make依赖，registry组按声明make/失效并定向重验。生成报告仍待刷新，不称冻结。

同层接线诊断发现registry静态解析器对重复target声明采用覆盖，不能正确累计Make依赖；将新增同步单测直接挂到make/ci.mk原architecture suite声明，消除第二声明，不改注册表/基线。该输入恢复后重验受影响接线检查，未启动Quick。

接线纠正后registry实际审计通过（1502 scripts，全部孤立/未接线状态已登记）；lane coverage在原冻结baseline内通过。六组回执全部reusable：73+142+31+32+24+53=355项，日志沿同一run保留；新增同步组与Make受影响组已重验，未变组不重跑。清理末尾空行后diff check通过。生成清单编号变化来自新增资产和main已合入的probe移动，不手工编辑报告。后续只冻结最终候选一次；本地同步不等于主线集成，部署未执行。

基线漂移反例补验：GitHub实际出现PR.baseRefOid仍为58f39而live main已是6dd151的状态。预检增加独立读取当前main ref并严格比对，防止过期PR基线被误用；新增失配/非法/匹配回归。282b14候选Quick已停止，不签发或复用取消结果。只重验治理组；推荐器及其余组输入未变，继续复用。

新增main-ref调用使既有受控merge测试桩缺少对应API分支，75项中1项失败。已撤销误登记的passed开发回执，保留live-main-unit.log原始失败；停止该次后续冻结链。补齐测试桩后重新执行治理组，不将失败结果冒充通过。

main-ref交叉核验修复最终治理组75项通过（live-main-fixed-unit.log，已按成功命令链登记）；其余五组输入不变，最终六组357项有效。独立增量审查通过，保留平台非原子读取限制。后续发布仍要求当前main身份与必需检查一致。
