# 付款申请黄金页面 Batch-B：动作权威与阻断态收敛

## 边界

- Formal Product Layer：P0 平台通用契约归一化与前端产品表达。
- Layer Target：`smart_core` 动作归一化、付款详情 Floorplan 宿主、只读浏览器证据。
- Standard vs User-Specific：通用渲染机制；未加入付款申请模型、角色、中文标签分支。
- Why Here：后端 runtime business action 已提供最终业务可用性，Contract V2 必须把该权威结果投影到同一后端按钮方法的 Native occurrence。
- Why Not Elsewhere：不能由 Floorplan、TDesign 或付款页面重新推断权限和状态，也不能放宽领域动作校验。
- Blast Radius：所有具备 Native occurrence 与 runtime business action 双来源的 object 按钮；通过通用单元测试、付款申请阻断态和第二模型浏览器复用验证 containment。

## 产品结果

- Native modifier 只决定 occurrence 可见性，不再把“可见”解释为“业务可执行”。
- 同一按钮类型与后端方法的 runtime business action 统一供应业务可用性、授权结果和确认安全信息。
- 被阻断的付款申请不再显示伪可执行“提交审批”，保留唯一“继续办理”路径并在动作前显示缺失依据。
- Floorplan 决策页不再重复渲染旧的 workflow evidence/action block。
- 只读验证器盘点受管 demo 候选的提交能力，为下一批真实执行闭环选择权威 fixture。

## 验证证据

- `python3 addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py`：PASS，70 tests。
- `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_core make local.dev.upgrade MODULE=smart_core`：PASS。
- `make local.dev.restart && make local.dev.health`：PASS；project=`sc-local-dev`，DB=`sc_dev_demo`，dbfilter=`^sc_dev_demo$`。
- `make verify.local.dev.payment_request.floorplan.readonly`：PASS；10 个语义区、blocked primary=0、无 mutation、390px overflow=0、业务指纹不变，第二真实模型继续复用 TDesign Floorplan。

## 回滚

回滚本批次提交即可恢复此前动作合并和旧动作区行为；本批次浏览器旅程未写入业务数据。
