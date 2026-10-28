# FEPC-13R 当前运行时标题核验

当前重复标题仍存在，09-04 不能作为已消失的历史问题关闭。本轮只读取证，不实施标题隐藏、去重或契约扩展。结果仅适用于当前账号、公司、项目及视口。

## 当前运行时事实

采集时间见 [浏览器记录](runtime-title-observation.json)（2026-10-28 UTC）。GitHub main 重新回读仍为 `b918f2a01fbbea01b7665d8c3448ed820050ffae`；源码分析分支为 `bca43728c2f1737b9000860e323c77a6e395dbb6`。Demo 独立读取到 `3da65c5c6f3909cb81c0316c85f8a622c952965a`，数据库 sc_demo、环境 demo，构建指纹 `c565398e8482eda9b7a8a17d6742bfb3149b615011cf8cf8faeafc881d46f92f`；浏览器采集前后身份一致。不得把 main 作为部署身份。

账号 wutao，用户 41、business_full、公司 1，项目 15。Linux Chromium、1440×1000、DPR=1，具体浏览器版本与 viewport 在 JSON 中。没有存活的可复用会话，复用 FEPC-11 的已授权登录和 token 进程管道；不保存密码、Cookie、Token 或 Authorization 头。沿用既有只读观察器、Playwright launcher 和请求白名单，不新增 Make/CI 浏览器车道。

| 对象 | 当前实际观察 |
| --- | --- |
| 页头标题 | H1：“城东片区安置房二期工程（归档阶段）”；x=256、y=137，高32px，字号24px，可见 |
| 原生标题 | H2：同一名称；x=298、y=295，高32px，字号24px，可见 |
| 原生标题行 | data-field-name=name；x=256、y=295，宽450px；无输入框 |
| 收藏 | aria-label=在仪表板上显示项目；按钮可见、disabled=true；未点击 |
| 页头操作 | 返回、更多操作、删除按钮存在；未点击，不将按钮存在当成动作成功证明 |
| 页面模式 | 页头 data-render-profile=readonly、dirty-state=clean，页面状态 ok；与输入框缺失及收藏禁用一致 |
| 固定页头 | 当前 computed position=sticky；本轮未做滚动回归，不声称 sticky 行为已验收 |

历史测量也为 y=137/y=295；上表来自本次 page.evaluate/getBoundingClientRect，数值相同不代表复用旧坐标。

## 实际生效标题声明

[有效声明投影](effective-title-declarations.json)保存实际浏览器请求的 readonly 契约和相同请求改为 edit profile 的只读返回；两者 HTTP 200、应用 ok=true。另补读 statusContract 的两个 widget 状态，均 HTTP 200、ok=true。保存的是限定标题的响应投影与完整选中 h1 子树，不是完整响应。

最终 layoutContract 节点：

- containerId：`h1.native.3.children.5.children.0`，与当前 DOM 容器属性一致。
- nativeLocator：`/form[1]/sheet[1]/div[2]/h1[1]`。
- h1 的 title/label 为空，attributes.class=`d-flex flex-row`。
- 两个 children 依次为 `is_favorite`（boolean_favorite，field[1]）与 `name`（text，field[2]）。widgetList 是对应两个字段的控件声明载体，不是另外两个业务孩子。
- name 必填、声明 readonly=false；favorite 非必填、声明 readonly=false。name 的 options.line_breaks=false；这些原生声明没有被修改。
- 本样本选中 h1 子树没有额外静态文本、第三个字段或额外子节点；不能推广为其他表单都没有额外语义。

这是服务端返回的**最终有效布局投影**。没有通过数据库/管理入口读取原始 XML 的完整继承链、每个继承 view ID 及优先级；这部分尚未验证，不把 nativeLocator 冒充完整视图谱系。

## 查看态与编辑态：三个层次不能混用

| 证据层 | readonly 请求 | edit 请求 |
| --- | --- | --- |
| globalStatus.effectiveRenderProfile / pageAuth | readonly / read | edit / edit |
| name widgetStatus | visible=true、readonly=false、required=true、disabled=false、auth=edit | 相同 |
| favorite widgetStatus | visible=true、readonly=false、required=false、disabled=false、auth=edit | 相同 |
| 浏览器最终呈现 | H2、无名称输入、收藏 disabled=true | 未验证；未点击编辑、未导航编辑页 |

字段可编辑能力与当前页面只读模式是不同维度，不能根据 widget readonly=false 就声称查看页可编辑，也不能根据 edit 契约就宣称编辑页实际输入可用。本轮没有写入测试。

## 业务身份与冗余声明

当前 dataContract.mainData 的 name 和 display_name 都是上述项目名称；DOM 原生标题绑定 name occurrence，页头显示同一记录的身份文本。FEPC-13 已追踪的页头取值链和本次响应支持“两处呈现同一记录名称”的判断，并非仅以文本相等作推断。

但同一记录身份不等于原生 h1 整体冗余：该节点还有收藏控件。已采集的有效 h1 attributes、fieldInfo、componentConfig、widgetList 及身份信息中，没有发现把该 occurrence 标记为可隐藏的纯身份副本的权威关系。该结论限定于采集范围，不声称其他未采集配置绝无此机制。

源码事实复用 FEPC-13：页头链负责主要身份、动作与 sticky 壳；原生链负责名称输入/只读文本与收藏 field-change。对 ContractFormPage、ContractFormProductHeader、NativeFormTreeRenderer、canonicalNativeFormBridge、pageIdentityAdapters 比较 Demo 声明 SHA 与当前分析 HEAD，均无文件差异。源码相同不替代浏览器运行证明。

## 请求、安全与限制

浏览器18个允许请求均 HTTP200、应用成功；唯一阻断为白名单外 global.message.conversations，伴随1条 ERR_BLOCKED_BY_CLIENT 控制台错误。该错误是只读观察器造成的限制，不归为标题产品异常；未出现 pageerror。完整请求摘要在浏览器 JSON 中。

采集器先保存标题字段投影，随后补齐完整选中 h1 子树及 widgetStatus，因此发生了限定范围复读；没有扩大记录范围。探针位于既有忽略区 `.runtime/fepc13r/`，只扩展旧观察器的采集字段；截图仅作为本地辅助证据并记录哈希，不用于推断未观察的编辑态。没有记录完整用户资料、会话转储或认证后 HTML。

## 交接结论

- 已证明：当前查看页仍有两个同内容、同字号/高度的标题层；有效原生节点只含名称与收藏两个字段；只读全局模式与字段授权状态分离。
- 未证明：原生标题是允许隐藏的纯身份副本；编辑页 DOM/操作行为；原始继承 XML 全链；滚动回归。
- 按用户决策规则进入“重复仍存在、尚无明确副本声明”分支，交由 GPT 裁定是否另行批准最小契约设计。此处不新增字段，不先做隐藏或文本相等去重。

F1 保持待核实、暂不修复。无产品代码、契约、配置、数据库或权限变更；不部署、不合并。当前新增证据待审，不自动开始实现。
