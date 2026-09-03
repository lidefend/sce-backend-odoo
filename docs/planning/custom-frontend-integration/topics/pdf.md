# P1-2: PDF 生成 — 技术方案

> 架构校正：报告生成机制属于 P0，施工模板与客户模板分别归 P1/P2；生成引擎和依赖需先通过 ADR。本文为候选设计，实施以根目录 [`README.md`](../../README.md) 为准。

> 执行状态：`ADR-PENDING`。WeasyPrint、PyPDF2、Jinja2、六类模板和直接 iframe HTML 预览均未获批准，不得据此实施。

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (Vue 3 + TypeScript)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ ScPdfPreview │  │ ScPdfButton   │  │ ScPrintTemplate  │  │
│  │ (预览+下载)  │  │ (触发入口)    │  │ (模板选择+配置)  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └─────────────────┼────────────────────┘            │
│  ┌────────────────────────┴────────────────────────────────┐ │
│  │              pdfApi.ts (Intent API 封装)                │ │
│  └────────────────────────┬────────────────────────────────┘ │
└───────────────────────────┼─────────────────────────────────┘
                            │ POST /api/v1/intent
                            │ intent: report.pdf / report.batch
┌───────────────────────────┼─────────────────────────────────┐
│                   后端 (Odoo + Python)                       │
│  ┌─────────────────────────┴──────────────────────────────┐ │
│  │              Report Job Service (engine TBD)            │ │
│  │  report.pdf   → HTML模板渲染 → PDF生成                   │ │
│  │  report.batch → 批量合并 → ZIP或合并PDF                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ HTML 模板     │  │ CSS 样式表    │  │ 数据渲染器      │  │
│  │ (Jinja2)      │  │ (print.css)  │  │ (model→context) │  │
│  └───────────────┘  └───────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 2. 核心模板清单

| 模板 | 模型 | 用途 | 关键内容 |
|------|------|------|----------|
| 合同 PDF | sc.general.contract | 合同打印/归档 | 合同编号、甲乙方、金额、条款、签章位 |
| 项目周报 | project.project | 周度汇报 | 本周进度、下周计划、问题、付款状态 |
| BOQ 清单 | project.boq.line | 工程量清单打印 | 层级树表格、汇总金额、分部小计 |
| 付款申请 | payment.request | 付款审批单 | 申请编号、金额、合同、收款方、审批链 |
| 资金月报 | sc.fund.account | 月度资金报告 | 收支汇总、分类统计、趋势图（含 ECharts 截图） |
| 项目总览 | project.dashboard | 项目看板打印 | 健康度、成本进度、合同统计、风险项 |

## 3. 后端实现要点

### 3.1 PDF 生成引擎（候选示意，禁止实施）

> **SUPERSEDED：**以下 WeasyPrint 代码只保留为历史候选。ADR 必须评估进程隔离、字体许可、模板沙箱、资源上限、合并能力、供应链和回退。

```python
from weasyprint import HTML, CSS

class PdfService:
    def generate(self, template_name, model, record_id, context=None):
        # 1. 加载记录
        record = env[model].browse(record_id)
        # 2. 构建 Jinja2 模板上下文
        ctx = self._build_context(record, context)
        # 3. 渲染 HTML 模板
        html = render_template(template_name, ctx)
        # 4. 加载打印样式
        css = CSS(string=PRINT_CSS)
        # 5. 生成 PDF
        pdf = HTML(string=html).write_pdf(stylesheets=[css])
        return pdf
```

### 3.2 批量打印

```python
def batch_generate(self, template_name, model, record_ids):
    """批量生成并合并为一个 PDF"""
    pdfs = [self.generate(template_name, model, rid) for rid in record_ids]
    return merge_pdfs(pdfs)
```

### 3.3 Intent API 设计

```json
{
  "intent": "report.pdf",
  "params": {
    "template": "contract",
    "model": "sc.general.contract",
    "record_id": 42,
    "contract_mode": "default"
  }
}
```

**响应**：PDF 二进制流（Content-Type: application/pdf）

### 3.4 模板预览（HTML 预览模式）

```json
{
  "intent": "report.preview",
  "params": {
    "template": "contract",
    "model": "sc.general.contract",
    "record_id": 42,
    "contract_mode": "default"
  }
}
```

**响应**：渲染后的 HTML（用于前端 iframe 预览）

## 4. 前端组件设计

### 4.1 ScPdfButton — 触发入口

- 列表行操作菜单：打印此记录
- 表单工具栏：打印 / 批量打印
- 通过 Contract 2.0 `printable` 标记控制可见性

### 4.2 ScPdfPreview — 预览组件

- iframe 渲染 PDF（Blob URL）
- 支持：预览 / 下载 / 打印（浏览器原生）
- 批量模式：多文档选项卡切换

### 4.3 ScPrintTemplate — 模板选择

- 下拉选择模板类型
- 模板参数配置（如：周报的日期范围）
- 预览 + 下载按钮

## 5. 模板渲染上下文

每个模板接收统一的上下文结构：

```python
{
    "record_projection": data,  # 经权限裁剪的不可执行数据投影
    "company": company,         # 公司信息
    "user": user,              # 打印人
    "now": datetime.now(),     # 打印时间
    "config": {                # 模板配置
        "show_qrcode": True,    # 显示二维码
        "watermark": "DRAFT",  # 水印
    },
}
```

## 6. 打印样式要点

- A4 纸张尺寸（210mm × 297mm）
- 中文字体：Noto Sans CJK SC / 思源黑体
- 页眉页脚：公司名 + 页码 + 打印日期
- 表格：斑马纹 + 边框 + 自动换行
- 签章位：预留盖章区域
- 水印：支持"草稿"/"正式"/"作废"水印

## 7. 里程碑

| 周次 | 交付物 |
|------|--------|
| ADR | 引擎隔离、字体许可、模板沙箱、job/存储、预览 CSP 与回退 |
| 获批后 | 先实现一个只读模板的异步生成、受权预览与下载闭环 |
| 后续 | 逐模板归属 P1/P2 并独立验收，不批量承诺六个模板 |

## 8. 依赖

WeasyPrint、Jinja2、PyPDF2 仅为待比较候选，不构成依赖清单。正式依赖由 ADR 和锁定的供应链清单产生。
