# ADR-006：Editor canonical format 与服务端净化

- 状态：**Accepted**（2026-09-06 用户批准；决策 1–7 全部生效）
- 批准记录：G7.2/G7.3 收口后呈报（含 2026-09-06 部署复核：nh3==0.3.7 wheel 目标容器实测可取）；首切片 = 单字段 restricted_html 净化写入 + kill switch 默认关（G6 式后端先行，前端编辑器切片随后）
- 范围：custom-frontend-integration G5 / Editor 专题
- 决策项：canonical format、净化库与净化时机、附件边界

## 背景

总控计划 §18 决策待办：「Editor canonical format 与服务端净化库」。专题文档边界：编辑器正文是运行时记录内容，不嵌入 capability 定义；可编辑范围、净化、附件权限归后端；首期不含任意 HTML、脚本、内联样式、iframe、外部媒体嵌入与插件市场。

## 事实核查（2026-09-03 首查；2026-09-06 复核）

| 净化库 | 许可证 | 维护 | 关键事实 |
| --- | --- | --- | --- |
| **bleach** | Apache-2.0 | **2026-06-05 官方宣布停止维护，安全漏洞不再修复**，官方指引迁移 nh3 | 不再可选 |
| **nh3**（Rust ammonia 绑定） | MIT（安装前复核 wheel 元数据） | 活跃；需跟踪底层 RUSTSEC 公告 | 白名单式；默认白名单过宽（~75 标签），必须显式收紧；历史漏洞经版本升级已修 |
| DOMPurify | Apache-2.0 / MPL-2.0 双许可 | 活跃 | 仅前端；客户端净化可被裸 POST 绕过，不能作为唯一防线 |

**2026-09-06 部署复核（目标运行时实测）**：dev 栈 odoo 容器 Python 3.10.12（cp38-abi3 兼容），`pip download nh3` 实测取到 `nh3-0.3.7-cp38-abi3-manylinux_2_17_x86_64.whl`（832KB，纯 wheel 无编译）；依赖注入路径 = 既有 `requirements-odoo.txt` 钉版模式（与 ADR-004 openpyxl 同路径，供应链管理方式零新增）。

## 决策（建议）

1. **Canonical format = `restricted_html`（受限 HTML 子集）**：与契约 `format` 字段直接对齐；子集 = 段落/标题/列表/粗斜体/链接/受控表格（对齐专题首期范围）。**不选 Markdown**（业务字段语义呈现需要结构而非源码文本）与**不选编辑器私有 JSON**（ProseMirror/Tiptap 文档格式绑定编辑器实现，违背 renderer 可替换原则）。
2. **服务端净化 = nh3**（bleach 已死是硬事实，不是偏好问题）：显式白名单（只放行 canonical 子集标签 + `a[href]` 且 `url_schemes={http,https,mailto}`）；**sanitize-on-save**（保存时净化一次入库，读取直渲染，不在读取路径反复净化）。
3. **前端防线仅作纵深**：编辑器组件内置粘贴纯化/输入约束，但安全权威在服务端；`restricted_html` 入库前必须经服务端净化，裸 POST 绕过前端不产生存量风险。
4. **长度与字段绑定**：`max_length` 由契约下发（默认 20000）；编辑器启用与否由后端 capability + 字段策略决定，共享前端禁止按模型名/页面名启用（既有禁令）。
5. **附件边界**：编辑器正文只保存受控引用（正式上传 intent 产出的 attachment id），不保存内联 base64/外链媒体；引用解析在后端渲染层完成并校验 ACL。
6. **并发语义 = G7-INFRA 统一幂等基建（2026-09-06 修订）**：编辑保存 intent 走 `claim_write_idempotency`/`complete_write_idempotency` 定式（PR #439 已收口的 sc.idempotency.record 部分唯一索引并发仲裁），指纹绑定客户端幂等键 + expected 基线（G7.2 BOQ patch 同款 TOCTOU 防护，PR #441 先例）；dirty/saving/conflict 状态机归前端 presenter（复用 G7.2-FE 会话状态机模式）。原「既有乐观锁/版本号机制」表述由基建实际取代。
7. **高风险写入治理 = G7.1 kill switch 模式（2026-09-06 修订）**：Editor 写入能力按总控 §14 走独立 feature flag（config_parameter kill switch，默认关）+ 专用权限组，不并入既有业务组；复用 G7.1 危险导入的开关数据文件与 intent 中间件 gate 次序（先组检查后 flag gate）。

## 替代方案与否决理由

- **lxml Cleaner**：黑名单式/维护弱于白名单式 ammonia，不符合「allowlist 优先」安全基线。
- **前端唯一净化（DOMPurify only）**：可绕过性已被社区共识否定，不设为权威。
- **服务端白名单正则自研**：HTML 解析边缘案例（畸形嵌套/实体混淆）自研覆盖率不可证，采用维护中的专业库。

## 回退策略

- 净化失败/超长 → 结构化 validation error 经 intent 透传，编辑器进入 validation error 态（不白屏、不丢用户输入）。
- nh3 若出现不可修复的供应链事故，白名单配置与 canonical 子集定义不变，可替换为任一白名单净化器（ bleach 已排除）。

## 后果

- 后端新增 nh3==0.3.7 依赖（纯 manylinux wheel，目标容器实测可取；走 requirements-odoo.txt 钉版）。
- 批准后 G7 才能开始受限编辑器实现（G6 式切片化推进：首切片建议 = 单字段 restricted_html 净化写入 + kill switch 默认关）；具体业务字段可编辑性逐字段走 P1 契约。
