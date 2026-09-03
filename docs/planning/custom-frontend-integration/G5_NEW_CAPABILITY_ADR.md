# G5 新能力 ADR — 起草进展

> 阶段：G5（进入条件：G3 结论可用——挂接已完成 ✅，验收待环境 ⏸）。
> 定位：把总控计划 §18 五项决策待办落成正式 ADR（docs/adr/ADR-002~006），全部 **Proposed**，待批准后方可进入 G6 实施。
> 事实核查时间：2026-09-03（版本/许可证/维护状态/漏洞以当日公开源为准，批准实施前须复核）。

## ADR 清单与结论摘要

| ADR | 专题 | 建议决策 | 一句话理由 |
| --- | --- | --- | --- |
| [ADR-002](../../adr/ADR-002-frontend-chart-engine-echarts.md) | Chart | **批准引入** echarts@6.1.0（tree-shake、≤120KB gzip、懒加载、契约先行） | Apache-2.0、无已知漏洞、tree-shake 后体积可控 |
| [ADR-003](../../adr/ADR-003-gantt-renderer-deferred.md) | Gantt | **本期否决建设**，锁定候选基准（frappe-gantt 优先） | P1 任务契约不存在；调度功能全归后端使库优势失效 |
| [ADR-004](../../adr/ADR-004-excel-engine-and-security-boundary.md) | Excel | xlsxwriter 导出 + openpyxl+defusedxml 导入 + 既有 sc.ops.job | openpyxl 默认不防 XML 炸弹是硬前置；Odoo 已依赖 xlsxwriter |
| [ADR-005](../../adr/ADR-005-pdf-engine-and-isolation-boundary.md) | PDF | WeasyPrint + job 子进程隔离 + Jinja2 沙箱；永久禁 wkhtmltopdf | wkhtmltopdf 归档且有未修复 CVE-2022-35583；PyMuPDF AGPL 排除 |
| [ADR-006](../../adr/ADR-006-editor-format-and-sanitization.md) | Editor | restricted_html + nh3 服务端净化（sanitize-on-save） | bleach 2026-06-05 停止维护是硬事实；Markdown/私有 JSON 均否决 |

## 关键事实核查记录（2026-09-03）

- **echarts 6.1.0**（2026-05-19）：Apache-2.0（d3 子组件 BSD-3），Snyk 无已知漏洞，运行时依赖仅 tslib+zrender，全量 ~360KB / 按需原型估算 ~95KB gzip。
- **bleach**：2026-06-05 官方宣布不再维护（含安全修复），指引迁移 nh3。
- **wkhtmltopdf**：2023-01 归档，CVE-2022-35583（SSRF 9.8）永不修复。
- **dhtmlx-gantt**：现行 v10 为 MIT 社区版 + PRO 商业分层——专题文档「商业授权」结论已过时，但因调度功能归后端，体积（300KB+）仍是主要否决因素。
- **openpyxl**：MIT，官方文档明示默认不防 quadratic blowup/billion laughs，须 defusedxml。
- **WeasyPrint**：BSD-3，v69 活跃（8.4M 周下载），纯 Python 无 JS 执行面，CJK 经 Pango 正确整形。

## 与总控计划的对照

- §18 五项待办全部有 ADR 覆盖（ECharts 版本与预算 / Gantt 算法归属 / Excel 引擎与扫描边界 / PDF 隔离与字体 / Editor format 与净化库）。
- 全部 ADR 遵守 §3 表格禁令：前端不自行计算业务事实、浏览器不绕过权限、iframe 不信任任意 URL、净化不依赖浏览器。
- ADR-002 引入首个新前端生产依赖，批准即触发总控「新增大型依赖须过体积/安全/许可证/维护性评审」条款——评审证据即 ADR 事实核查节。

## 批准后进入 G6 的顺序建议

1. Excel（ADR-004）：复用 G2/G3 已闭环的 BOQ 导入与 job 框架，增量最小。
2. Editor（ADR-006）：restricted_html 契约 + nh3 净化 + 只读渲染先行。
3. Chart（ADR-002）：capability 契约 + 懒加载 renderer。
4. PDF（ADR-005）：job 隔离 + 沙箱模板，部署基线变更最大。
5. Gantt：维持否决，待 P1 契约立项后按 ADR-003 基准重启。
