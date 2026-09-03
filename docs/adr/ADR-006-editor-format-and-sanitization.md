# ADR-006：Editor canonical format 与服务端净化

- 状态：Proposed（待批准；批准前 `content.rich_text` capability 不实施）
- 范围：custom-frontend-integration G5 / Editor 专题
- 决策项：canonical format、净化库与净化时机、附件边界

## 背景

总控计划 §18 决策待办：「Editor canonical format 与服务端净化库」。专题文档边界：编辑器正文是运行时记录内容，不嵌入 capability 定义；可编辑范围、净化、附件权限归后端；首期不含任意 HTML、脚本、内联样式、iframe、外部媒体嵌入与插件市场。

## 事实核查（2026-09-03）

| 净化库 | 许可证 | 维护 | 关键事实 |
| --- | --- | --- | --- |
| **bleach** | Apache-2.0 | **2026-06-05 官方宣布停止维护，安全漏洞不再修复**，官方指引迁移 nh3 | 不再可选 |
| **nh3**（Rust ammonia 绑定） | MIT（安装前复核 wheel 元数据） | 活跃；需跟踪底层 RUSTSEC 公告 | 白名单式；默认白名单过宽（~75 标签），必须显式收紧；历史漏洞经版本升级已修 |
| DOMPurify | Apache-2.0 / MPL-2.0 双许可 | 活跃 | 仅前端；客户端净化可被裸 POST 绕过，不能作为唯一防线 |

## 决策（建议）

1. **Canonical format = `restricted_html`（受限 HTML 子集）**：与契约 `format` 字段直接对齐；子集 = 段落/标题/列表/粗斜体/链接/受控表格（对齐专题首期范围）。**不选 Markdown**（业务字段语义呈现需要结构而非源码文本）与**不选编辑器私有 JSON**（ProseMirror/Tiptap 文档格式绑定编辑器实现，违背 renderer 可替换原则）。
2. **服务端净化 = nh3**（bleach 已死是硬事实，不是偏好问题）：显式白名单（只放行 canonical 子集标签 + `a[href]` 且 `url_schemes={http,https,mailto}`）；**sanitize-on-save**（保存时净化一次入库，读取直渲染，不在读取路径反复净化）。
3. **前端防线仅作纵深**：编辑器组件内置粘贴纯化/输入约束，但安全权威在服务端；`restricted_html` 入库前必须经服务端净化，裸 POST 绕过前端不产生存量风险。
4. **长度与字段绑定**：`max_length` 由契约下发（默认 20000）；编辑器启用与否由后端 capability + 字段策略决定，共享前端禁止按模型名/页面名启用（既有禁令）。
5. **附件边界**：编辑器正文只保存受控引用（正式上传 intent 产出的 attachment id），不保存内联 base64/外链媒体；引用解析在后端渲染层完成并校验 ACL。
6. **并发语义**：编辑保存走既有乐观锁/版本号机制（避免多端编辑互相覆盖），dirty/saving/conflict 状态机归前端 presenter（复用既有 useEditTx 模式）。

## 替代方案与否决理由

- **lxml Cleaner**：黑名单式/维护弱于白名单式 ammonia，不符合「allowlist 优先」安全基线。
- **前端唯一净化（DOMPurify only）**：可绕过性已被社区共识否定，不设为权威。
- **服务端白名单正则自研**：HTML 解析边缘案例（畸形嵌套/实体混淆）自研覆盖率不可证，采用维护中的专业库。

## 回退策略

- 净化失败/超长 → 结构化 validation error 经 intent 透传，编辑器进入 validation error 态（不白屏、不丢用户输入）。
- nh3 若出现不可修复的供应链事故，白名单配置与 canonical 子集定义不变，可替换为任一白名单净化器（ bleach 已排除）。

## 后果

- 后端新增 nh3 依赖（含 Rust wheel；目标环境 glibc/musl 矩阵均有轮子）。
- 批准后 G6 才能开始受限编辑器实现；具体业务字段可编辑性逐字段走 P1 契约。
