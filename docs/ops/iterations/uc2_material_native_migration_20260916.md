# U-C2：材料入库／出库原生结构迁移

状态：入库代表面已完成源码迁移并通过 L1、定向 L2 和受管增量升级；已确认受影响页面的只读浏览器样板不依赖全量 demo 对账，尚未完成 L4 浏览器证据和消费者扣减。

## 边界与基线

- 基线：`main@28b7695dc9f1cebbbe9bd5d715e951c6dec8a4da`。
- 分支：`feature/uc2-material-native-v1`；唯一写入工作树为
  `sce-backend-odoo-material-handling-v1-uc2-material-native-v1`。两个既有历史工作树保持原状。
- Formal Product Layer：P1；Layer Target / Module：`smart_construction_core` 材料标准原生视图和分类字段语义。
- Standard vs User-Specific：建筑材料业务标准。
- Why Here：材料表单的章节、字段顺序、明细列和操作按钮由 P1 原生 XML 拥有。
- Why Not Elsewhere：不在 P0 前端推导材料语义，不把稳定标准留在 P3 兼容编排，也不通过 P4 脚本修改库存事实。
- Blast Radius：本批只迁移材料入库。库存、计价、保存、审批、权限、出库和退库业务规则不变。

## 46 项台账中的实际范围

| 台账消费者 | 正式入口 | 台账身份 | 原生表单 | 本批处理 |
|---|---|---|---|---|
| 材料入库 | `menu_sc_material_inbound` → `action_sc_material_inbound_handling` | action 546 / menu 494 | `view_sc_material_inbound_form`，view 1428 | 代表面迁移 |
| 材料出库 | `menu_sc_material_outbound` → `action_sc_material_outbound` | action 547 / menu 495 | `view_sc_material_outbound_form`，view 1431 | 后续同类批次 |

`menu_sc_material_return` 通过 `action_sc_material_return` 打开同一
`sc.material.outbound` / `view_sc_material_outbound_form`，仅以
`outbound_type=return` 和 `material.return` 分类区分。它没有独立出现在 46 项台账中，不能作为第三个消费者重复扣减。`sc.material.supplier.return` 使用独立原生模型和
`view_sc_material_supplier_return_form`，同样不在本台账范围内。

## 入库代表面

- 原生表单直接声明入库主信息、项目与供应商、入库明细、说明与附件、来源追溯。
- 明细保留材料档案、规格、单位、数量、单价、金额、来源验收行和备注；表尾保留数量汇总、税率、金额、含税金额与币种。
- 状态栏和提交、确认入库、退回草稿、取消、带入验收明细保持原方法和原权限组。
- 来源验收单、来源调拨单、库存入库单、历史来源标识、录入人／时间以及付款、结算状态均由原生视图承接。
- 四个旧结构拥有者按精确 XMLID 停用：基础章节、生成字段顺序、P1 业务事实排序和 action 级产品化结构。新增 action 级配置只声明 `native_semantic_surface`。
- `material.inbound` 分类模板移除 `sections`，继续保留 required、readonly、visible profile 和字段角色，不修改模型方法或业务状态流转。

## 验证结果索引

| 层 | 命令 | 结果 | 测试数／事实 | 下一步 |
|---|---|---|---|---|
| L0 | `make codex.preflight` | passed | 基线完整指纹 `520b4856b3c958b612bcc1d3223653862c6c34f4238d6531fcff77585d84df44` | L1 |
| L1 | `make ci.local.iteration` | passed | 16 tests；P4 归档工具另有 16 tests | L2 |
| L2 | `make local.dev.test ...` 四个入库精确方法 | passed | 4 个非零测试方法 | L3 |
| L3 | `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make local.dev.upgrade MODULE=smart_construction_core` | passed | `sc-local-dev` / `sc_dev_demo` / `^sc_dev_demo$` / `sc_local_dev_odoo_data` | 只读候选运行态 |
| L4 错误前置诊断 | `make local.dev.sync_demo` | failed | 该入口调用 `demo.load.full`，会写入并对账全量演示数据；既有已审批结算样本发票金额期望 280000、实际 0 | 单列 demo settlement fixture 问题，不作为只读样板门禁 |
| L4 只读前置 | `local.dev.candidate.frontend.up/health/visual-smoke` 调用链审计 | passed | 保留允许分支、干净精确 HEAD、源码挂载、数据库/dbfilter/filestore、有效账号和目标路由身份检查；不调用 demo reset | action 546 创建态与已有查看态 |
| L4 浏览器 | 未运行 | not_run | 尚无截图和浏览器扣减依据 | 保持台账 46 |

曾运行一次过宽的 `TestUserFeedbackBusinessViews`，71 个方法中出现 13 failed / 16 errors；入库新增契约测试通过，新增静态断言的作用域错误已修复。其余失败属于既有发票、费用归属、历史模型和列表基线，不作为本批测试入口，也未通过重复宽测掩盖。

## 计数规则

UC1 发布台账保持 46。入库虽已在实际模块升级后无兼容结构依赖，但尚缺冻结候选的受影响浏览器效果，因此本批不把 46 改为 45。出库／退库共享表单只有在其实际契约与浏览器效果均通过后才处理对应的单个出库消费者。

## 清理前证据归档

新增 `make workspace.evidence.archive`，使用精确候选 HEAD 清单归档摘要、身份绑定、关键截图和独立复核报告到工作树外既有
`.codex-evidence/workspace-archives`。入口复制后逐文件重读并校验 SHA256；
摘要、身份和复核文档必须含精确候选 HEAD，身份必须为 JSON，截图必须具备有效图片内容签名。
`make workspace.worktree.cleanup` 的 apply 模式会重读本批 manifest，并要求路径、HEAD、角色清单和哈希均与外部 verified receipt 匹配。16 个定向单元测试已证明 receipt 缺失、HEAD 不匹配、归档文件缺失及哈希不符时均拒绝清理；任意文本冒充截图或未绑定 HEAD 的文档同样被拒绝。反例只使用临时仓库，没有清理历史工作树。U-C2 工作树当前不清理；待浏览器与独立复核完成后才生成四类实际证据并执行归档。

候选浏览器启动前发现全局 pidfile 指向已删除 UC1 工作树的残留静态服务。P4 候选载体仅在记录工作树已不存在，且进程属主、cwd、命令、静态目录、端口、代理和候选 HEAD 全部匹配时允许受管 `down` 清理该孤儿进程；记录工作树仍存在时继续拒绝跨工作树停止。16 个候选载体定向单元测试通过；未操作两个历史工作树。

链接工作树首次候选构建还发现 nginx 预先创建了 root 属主的空 `dist-dev`。候选载体只移除精确路径下“不可写且为空”的目录后再交给正式构建；不可写的非空目录或符号链接继续拒绝，避免覆盖未知产物。候选载体定向单元测试因此增至 17 个。

首次 action 546 页面探测在浏览器脚本等待旧 `data-floorplan-region=relation` 时超时，前后业务指纹一致但不记通过。材料样板入口已改为读取原生 `container_tree_authority`：核对 view 1428 / action 546、零兼容依赖、入库三个原生页签、`line_ids` 明细、来源追溯字段以及创建/只读操作能力；仍保留业务指纹前后对照和零写请求检查。该恢复只修改 P4 验收选择器，不修改业务视图或数据。

恢复后的第二次探测正确读取到来源 `S80-MA-001`，但因错误要求五个来源字段全部可见而失败；原生只读渲染会隐藏空值字段，实际样本显示两个有值来源事实。门禁改为契约必须完整包含五个来源字段，已有样本至少显示一个实际来源事实，并保留实际可见数量；这次失败不记通过。

第三次探测确认新建态唯一页头状态栏、保存能力及契约内 `action_load_acceptance_lines` 均存在，但旧断言把页头状态字段计作正文重复，并要求需先保存记录的 object button 在空白新建态可见。门禁改为正文不得重复状态、页头恰有一个状态栏；“带入验收明细”必须保留在原生契约，空白新建态按 `requires_record` 隐藏不判失败。该次同样不记通过。

action 777 保持原“环境阻断、未通过”状态，本批没有探测或改写。
