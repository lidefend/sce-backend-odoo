# P1-1: Excel 导入导出 — 技术方案

> 架构校正：导入导出机制属于 P0，业务模板与字段策略属于相应 P1/P2 产品；权限裁剪和写入必须由后端专用 intent 承担。本文为候选设计，实施以根目录 [`README.md`](../../README.md) 为准。

> 执行状态：`ADR-PENDING`。通用 Excel 平台能力延后；首批只审计并接入 BOQ 已有服务端 CSV/XLS/XLSX 导入。下文客户端 SheetJS、通用模型 API、Base64 传输和客户端导出路径均为 `SUPERSEDED`，禁止实施。

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (Vue 3 + TypeScript)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ ScExcelExport│  │ ScExcelImport│  │ ScExportButton   │  │
│  │ (列配置+生成) │  │ (4步向导)    │  │ (列表工具栏集成) │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                   │             │
│  ┌──────┴─────────────────┴───────────────────┴─────────┐  │
│  │              excelApi.ts (Intent API 封装)            │  │
│  └──────────────────────┬────────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────────┘
                          │ POST /api/v1/intent
                          │ intent: api.export / api.import.*
┌─────────────────────────┼───────────────────────────────────┐
│                    后端 (Odoo + Python)                      │
│  ┌──────────────────────┴────────────────────────────────┐  │
│  │           Intent Router (api_base.py)                 │  │
│  │  api.export     → ExcelExportService                   │  │
│  │  api.import.preview → ExcelImportService.preview()     │  │
│  │  api.import.execute → ExcelImportService.execute()     │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ openpyxl      │  │ xlsxwriter    │  │ Field Mapping  │  │
│  │ (读取/解析)    │  │ (生成/写入)    │  │ Engine         │  │
│  └───────────────┘  └───────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 2. 前端组件设计

### 2.1 ScExcelExport — 导出组件

**职责**：将列表数据导出为 Excel 文件

**功能**：
- 列选择：从 Contract 字段定义中选择要导出的列
- 排序：拖拽调整列顺序
- 筛选：导出当前筛选结果 / 导出全部 / 导出选中行
- 格式：xlsx（默认）/ csv
- 所有数据量：由服务端基于字段权限、记录规则和审计策略生成；阈值只影响同步/异步 job

**Props**：
```typescript
interface ScExcelExportProps {
  capabilityRef: string      // 后端批准的导出能力引用
  selectionRef?: string      // 受权选择集引用；不接受任意 model/domain
}
```

### 2.2 ScExcelImport — 导入向导

**职责**：从 Excel 文件导入数据

**4 步流程**：
1. **上传**：拖拽/点击上传 xlsx/xls/csv，显示文件信息
2. **预览**：服务端解析并返回受限预览、字段候选和错误；浏览器不解析业务文件
3. **映射**：Excel 列 → 模型字段映射（自动匹配 + 手动调整）
4. **导入**：校验 → 执行导入 → 显示结果（成功/失败/跳过）

**Props**：
```typescript
interface ScExcelImportProps {
  importCapabilityRef: string      // 后端批准的导入能力引用
  uploadRef?: string               // 专用上传得到的临时引用，不传 Base64
}
```

### 2.3 ScExportButton — 导出按钮

**职责**：列表工具栏集成，点击弹出导出配置面板

**集成方式**：
- Contract 2.0 列表视图工具栏
- 通过 `exportable: true` 字段标记控制可见性

## 3. Intent API 设计

### 3.1 导出

```json
{
  "intent": "api.export",
  "params": {
    "capability_ref": "approved-export-capability",
    "selection_ref": "authorized-selection",
    "format": "xlsx",
    "limit": 10000,
    "contract_mode": "default"
  }
}
```

**响应**：二进制文件流（Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet）

### 3.2 导入预览

```json
{
  "intent": "api.import.preview",
  "params": {
    "import_capability_ref": "approved-import-capability",
    "upload_ref": "authorized-temporary-upload",
    "sheet_name": "Sheet1",
    "header_row": 1,
    "contract_mode": "default"
  }
}
```

**响应**：
```json
{
  "ok": true,
  "data": {
    "total_rows": 150,
    "preview_rows": [...20行],
    "detected_columns": [
      {"excel_column": "A", "header": "项目名称", "suggested_field": "name", "confidence": 0.95}
    ],
    "warnings": ["第3行缺少必填字段'编码'"]
  }
}
```

### 3.3 导入执行

```json
{
  "intent": "api.import.execute",
  "params": {
    "import_capability_ref": "approved-import-capability",
    "upload_ref": "authorized-temporary-upload",
    "field_mapping": {
      "A": "name",
      "B": "code",
      "C": "amount_total"
    },
    "import_mode": "append",
    "unique_key": "code",
    "contract_mode": "default"
  }
}
```

**响应**：
```json
{
  "ok": true,
  "data": {
    "total": 150,
    "success": 142,
    "failed": 5,
    "skipped": 3,
    "errors": [
      {"row": 15, "field": "code", "error": "编码已存在"},
      {"row": 28, "field": "amount_total", "error": "金额格式错误"}
    ]
  }
}
```

## 4. 服务端导出策略

> **SUPERSEDED / 禁止实施：**浏览器使用 SheetJS 生成 xlsx 的方案会绕过字段权限、记录规则和统一审计，不因数据少于 5000 行而放行。

前端只提交后端批准的 capability/selection 引用；服务端重新执行权限裁剪并生成同步响应或异步 job。下载使用限时、一次性或受权资源引用。

## 5. 后端实现要点（Python）

### 5.1 ExcelExportService

```python
class ExcelExportService:
    def export(self, model, fields, domain, limit):
        # 1. 查询数据
        records = env[model].search(domain, limit=limit)
        # 2. 构建 xlsx
        wb = xlsxwriter.Workbook(output_buffer)
        ws = wb.add_worksheet('Export')
        # 3. 写表头 + 数据
        for i, field in enumerate(fields):
            ws.write(0, i, field['label'])
        for row_idx, record in enumerate(records):
            for col_idx, field in enumerate(fields):
                ws.write(row_idx + 1, col_idx, record[field['name']])
        # 4. 返回二进制
        wb.close()
        return output_buffer.getvalue()
```

### 5.2 ExcelImportService

```python
class ExcelImportService:
    def preview(self, import_capability_ref, upload_ref, sheet_name, header_row):
        # 通过受控临时上传引用读取；拒绝任意模型和 Base64 JSON
        wb = load_authorized_upload(upload_ref)
        ws = wb[sheet_name]
        # 自动列检测：表头 → 字段名匹配
        ...

    def execute(self, import_capability_ref, upload_ref, field_mapping, import_mode):
        # 1. 解析数据
        # 2. 按 import_mode 处理（append/replace/update）
        # 3. 逐行创建/更新 + 错误收集
        # 4. 返回结果统计
        ...
```

## 6. Contract 2.0 集成

### 字段标记扩展

```json
{
  "fields": {
    "name": {
      "type": "char",
      "label": "项目名称",
      "exportable": true,
      "importable": true,
      "import_required": true
    },
    "amount_total": {
      "type": "float",
      "label": "总金额",
      "exportable": true,
      "importable": true,
      "export_format": "currency"
    }
  },
  "view_config": {
    "toolbar": {
      "export": {"enabled": true, "default_fields": ["name", "code", "amount_total"]},
      "import": {"enabled": true, "template": "project_import_template.xlsx"}
    }
  }
}
```

### 页面契约扩展

在统一页面 envelope 中注入受版本控制的 import/export block，引用专项 payload schema；不默认新增顶层 `view_type` 或独立 capability 宿主。

## 7. 模板下载

提供标准导入模板下载功能：
- 后端根据 Contract 字段定义自动生成空模板 xlsx
- 包含表头 + 数据验证 + 填写说明 Sheet
- 前端 ScExcelImport 向导第一步提供"下载模板"入口

## 8. 里程碑

| 周次 | 交付物 |
|------|--------|
| G2/G3 | 复用 BOQ 既有服务端解析并完成最小真实闭环 |
| ADR | 决定通用上传、扫描、job、存储、格式和供应链边界 |
| 获批后 | 建立受权 capability、薄 UI、审计和错误回执 |

## 9. 依赖

任何前后端依赖均须由 ADR 固定版本、来源、许可证、漏洞扫描、资源预算和回退方式。SheetJS、openpyxl、xlsxwriter 均不是本文预先批准的通用平台依赖；BOQ 已有运行依赖按现状审计处理。
