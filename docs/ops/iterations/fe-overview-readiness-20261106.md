# FE-OVERVIEW-READINESS-20261106 记录

分支 `fix/project-overview-native-text-rendering`，基线 main `5b842bdde0d483413bde708b32aa3523992c6e77`（已合入 #826）。

## ITEM-1 立项完成度（原生 inline text 渲染）

- `nativeChildSequence.ts` / `NativeFormTreeRenderer.vue`：`text` 节点成为独立分段并按声明顺序渲染。
- 新增 `frontend/apps/web/scripts/native_child_sequence_test.ts` 与 `verify.frontend.native_child_sequence.unit`。
- 代码层通过；最终浏览器回执（PM 打开草稿 FE Project A 按序读“立项完成度：1 / 3”，非草稿隐藏）待采集。

## ITEM-2 办理前检查（页头 notice 收敛）

- `unified_page_contract_v2_assembler.py`：注入 `noticeContract.submissionReadiness` 并在密封前抑制正文 `submission_readiness_display` 布局节点可见性（不删 children、不动字段值/权限/XML）；新建记录传 `None` 取 `no_data` 投影；后端声明视觉 `state`。
- `schema.ts` / `types.ts`：声明并解码 `noticeContract`，严格拒绝未知键。
- `ContractFormPage.vue`：页头 `#notice` 槽消费 `submissionReadiness`，不按业务 `status` 字面量推导 UI 状态。
- 旧浏览器断言替换为“页头一条、正文零条”，并补项目/付款离开可见状态的反例。
- 代码层通过（后端纯 Python 148 项、前端 typecheck、解码回归、decision_authority.guard、ci.generated_evidence.preflight）。

## 阻塞

- readiness/overview 浏览器回执待采集：`sc_dev_demo` 当前绑定 FE-converge 候选分支，需等待或改绑独立候选载体。
