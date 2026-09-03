# ADR-005：PDF 报告引擎与进程隔离边界

- 状态：Proposed（待批准；批准前 report.pdf 类 intent 不实施）
- 范围：custom-frontend-integration G5 / PDF 专题
- 决策项：PDF 引擎、进程隔离、字体许可、模板沙箱、签章边界

## 背景

总控计划 §18 决策待办：「PDF 引擎进程隔离、字体许可、模板沙箱和签章边界」。专题文档候选（WeasyPrint/PyPDF2/Jinja2/六类模板/iframe HTML 预览）均未获批准。前端预览只允许受控 PDF 文件流，禁止 iframe 直接信任任意 HTML/URL。

## 事实核查（2026-09-03）

| 引擎 | 许可证 | 维护 | JS 执行 | 关键事实 |
| --- | --- | --- | --- | --- |
| WeasyPrint v69 | BSD-3 | 活跃（8.4M 周下载，2-3 月一发版，CourtBouillon 商业支持） | 无 | 纯 Python + Pango/Cairo；CSS Paged Media 支持（@page/running elements/PDF-A）；CJK 经 Pango/HarfBuzz 正确整形 |
| wkhtmltopdf | LGPL/GPL2 | **2023-01 已归档** | 不可靠 | **CVE-2022-35583（SSRF，9.8 分）永不修复**；WebKit 冻结在 ~2016 |
| ReportLab | BSD（免费层）+ 商业 Plus | 活跃 | 无 | 非 HTML 输入，程序化绘制；适合发票/报表但不适合模板化文档 |
| Playwright/Chromium | Apache-2.0 | 活跃 | 完整 | 引擎保真度最高，但生产须带 ~200MB 浏览器进程；本期无 JS 渲染需求 |
| xhtml2pdf | Apache-2.0 | 维护中 | 无 | CSS 支持落后一代 |
| PyMuPDF | AGPL | 活跃 | 无 | **AGPL 传染风险，商业分发不可接受，直接排除** |

## 决策（建议）

1. **引擎 = WeasyPrint（BSD-3）**：模板化 HTML/CSS → PDF 与本产品「契约驱动模板」形态最匹配；无 JS 执行面即最小攻击面；CJK 靠 Pango 原生支持（中文报告硬需求）。**永久禁用 wkhtmltopdf 及其全部 Python 包装**（归档 + 未修复 CVE，守卫拦截新增引用）。
2. **进程隔离**：PDF 生成在受控 worker 子进程执行（超时/内存限额/崩溃不影响 Odoo 主进程），与 ADR-004 的 `sc.ops.job` 异步框架共用 job 通道；job 失败语义沿用现有结构化错误。
3. **模板沙箱**：模板渲染用 Jinja2 **SandboxedEnvironment + autoescape**；模板资源（图/字体/CSS）只允许服务端白名单引用，禁模板内任意 URL 抓取（SSRF 面）；模板变更走版本化契约，不接受运行时上传模板。
4. **字体许可**：内嵌字体必须有「可内嵌分发」授权（首选 OFL 系如思源黑体/思源宋体；系统字体不得直接拷贝内嵌）；字体文件与 filestore 备份链路成对管理。商业字体采购前不得进入模板。
5. **签章边界**：首期**不做**电子签章/数字签名（涉及 CA、合同法效力与密钥管理，独立立项）；PDF 只做内容生成与下载。
6. **前端预览**：只接受后端产出的 PDF 二进制流（受控 attachment 引用），Content-Disposition 内联渲染；禁止将任意 HTML/URL 交给 iframe 渲染成「PDF 预览」。

## 回退策略

- 引擎故障/job 超时 → 结构化降级错误经 intent 透传，前端不白屏。
- WeasyPrint 重大不兼容升级时，模板层（HTML/CSS）资产可迁移至任意 Paged Media 引擎（含未来 Chromium 侧车），契约与 intent 不变。

## 后果

- 后端新增 weasyprint + 系统库（pango/cairo）依赖；部署基线须记录 apt 依赖。
- 批准后 G6 才能开始报告 job + 预览 UI 实现；六类业务模板各自走 P1/P2 产品层契约设计。
