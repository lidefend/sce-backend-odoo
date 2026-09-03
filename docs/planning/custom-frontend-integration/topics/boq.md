# P0-1: BOQ 前端组件技术方案

> 架构校正：通用树表 renderer 可属于 P0，BOQ 事实、汇总、权限与动作属于 P1 `smart_construction_core`。本文为候选设计，实施以根目录 [`README.md`](../../README.md) 为准。

## 1. 目标

在后端 BOQ 引擎（`project.boq.line` + `project.boq.import.wizard`）基础上，开发前端交付界面，使核心能力可见可用。

## 2. 后端 API 对接

### 2.1 数据模型（已确认）

**模型**: `project.boq.line`

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_id` | Many2one | 所属项目 |
| `parent_id` / `child_ids` | Self-rel | 层级树 |
| `parent_path` | Char | 层级路径（`12/45/78/`） |
| `level` | Integer(compute) | 层级深度（根=1） |
| `line_type` | Selection | major/division/group/item |
| `code` | Char | 清单编号（12位） |
| `name` | Char | 项目名称 |
| `spec` | Char | 规格/项目特征 |
| `uom_id` | Many2one | 计量单位 |
| `quantity` | Float | 清单数量 |
| `qty_planned` | Float(related) | 计划数量 |
| `qty_done` | Float | 累计完成数量 |
| `qty_remain` | Float(compute) | 剩余数量 |
| `price` | Monetary | 单价 |
| `amount` | Monetary(compute, recursive) | 金额（叶子=qty×price，分组=子项之和） |
| `amount_leaf` | Monetary(compute) | 叶子金额 |
| `section_type` | Selection | building/installation/decoration/landscape/other |
| `boq_category` | Selection | boq/unit_measure/total_measure/fee/tax/other |
| `category` | Selection | subitem/measure/other |
| `hierarchy_code` | Char | 层级编码（1, 1.1, 1.1.2） |
| `code_cat` ~ `code_item` | Char(compute) | 12位编码分段 |
| `source_type` | Selection | tender/contract/settlement |
| `version` | Char | 版本标识 |
| `is_provisional` | Boolean | 暂估/暂列 |
| `has_warning` | Boolean | 警告标志 |

### 2.2 API 调用（Intent 协议）

```typescript
// 列表/树查询
POST /api/v1/intent
{
  "intent": "api.data",
  "params": {
    "model": "project.boq.line",
    "op": "list",
    "contract_mode": "default",
    "limit": 200,
    "filters": [["project_id", "=", projectId], ["boq_category", "=", "boq"]],
    "order": "parent_path, sequence, id"
  }
}

// 读取单条
{
  "intent": "api.data",
  "params": {
    "model": "project.boq.line",
    "op": "read",
    "ids": [lineId],
    "fields": ["code", "name", "quantity", "price", "amount", ...]
  }
}

// 创建
{
  "intent": "api.data",
  "params": {
    "model": "project.boq.line",
    "op": "create",
    "values": { "project_id": 1, "code": "01", "name": "土方工程", ... }
  }
}

// 更新
{
  "intent": "api.data",
  "params": {
    "model": "project.boq.line",
    "op": "write",
    "ids": [lineId],
    "values": { "quantity": 120.5 }
  }
}

// 删除
{
  "intent": "api.data",
  "params": {
    "model": "project.boq.line",
    "op": "unlink",
    "ids": [lineId]
  }
}

// BOQ 导入
{
  "intent": "api.data",
  "params": {
    "model": "project.boq.import.wizard",
    "op": "create",
    "values": {
      "project_id": 1,
      "section_type": "building",
      "boq_category": "boq",
      "source_type": "contract",
      "version": "V1",
      "clear_mode": "append",
      "file": "<base64>",
      "filename": "boq.xlsx"
    }
  }
}
// 然后调用 action_import 方法
{
  "intent": "api.data",
  "params": {
    "model": "project.boq.import.wizard",
    "op": "call_method",
    "method": "action_import",
    "ids": [wizardId]
  }
}
```

### 2.3 Contract 集成

BOQ 视图需要后端输出 Contract JSON，新增：
- `view_type: "boq_tree"` — 树形列表视图
- `view_type: "boq_import"` — 导入向导视图
- `fields` 中增加 `line_type`、`hierarchy_code`、`boq_category` 等字段定义
- 在统一页面 envelope 中增加版本化 BOQ payload/ref；不新增独立顶层宿主

## 3. 组件设计

### 3.1 ScBoqTreeView（核心树视图）

```
┌──────────────────────────────────────────────────────────────────┐
│ ScBoqTreeView                                                     │
├──────────────────────────────────────────────────────────────────┤
│ 工具栏: [导入] [导出] [新增] [展开全部] [折叠全部] [筛选▼]      │
├──────────────────────────────────────────────────────────────────┤
│ 层级 │ 编码    │ 名称           │ 规格  │ 单位 │ 数量  │ 单价  │ 金额    │
├──────┼─────────┼────────────────┼───────┼──────┼───────┼───────┼─────────┤
│ ▼ 1  │         │ 土方工程        │       │      │       │       │ 125,300 │
│   ▼ 1.1│ 010101│ 挖掘土方       │ m³    │ m³   │ 1,200 │   45  │  54,000 │
│   ▼ 1.2│ 010102│ 回填土方       │ m³    │ m³   │  800  │   25  │  20,000 │
│ ▼ 2  │         │ 钢筋工程        │       │      │       │       │  89,500 │
│   ► 2.1│ 020101│ 钢筋制作       │ t     │ t    │   15  │ 4,200 │  63,000 │
├──────────────────────────────────────────────────────────────────┤
│ 合计:                                                         │ 214,800│
└──────────────────────────────────────────────────────────────────┘
```

**功能清单**:
- [x] 多级树展开/折叠（基于 parent_path + level）
- [x] 行内编辑（quantity, price → 自动重算 amount）
- [x] 分组行金额递归汇总（parent = sum(children)）
- [x] 按 boq_category 切换 Tab（分部分项/单价措施/总价措施/费用/税金）
- [x] 按 section_type 过滤（建筑/安装/装饰/景观）
- [x] 搜索（code/name/hierarchy_code 模糊匹配）
- [x] 拖拽排序（更新 sequence + parent_id）
- [x] 右键菜单（新增子项/编辑/删除/冻结）
- [x] 完成进度条（qty_done / qty_planned）
- [x] 警告标记（has_warning）
- [x] 暂估标记（is_provisional）

**Props**:
```typescript
interface ScBoqTreeViewProps {
  projectId: number
  boqCategory?: 'boq' | 'unit_measure' | 'total_measure' | 'fee' | 'tax' | 'other'
  sectionType?: 'building' | 'installation' | 'decoration' | 'landscape' | 'other'
  editable?: boolean
  showProgress?: boolean  // 是否显示完成进度
  pageSize?: number
}
```

### 3.2 ScBoqImportWizard（导入向导）

```
┌──────────────────────────────────────────────────┐
│ 步骤: ① 上传文件 → ② 配置选项 → ③ 预览 → ④ 导入  │
├──────────────────────────────────────────────────┤
│                                                  │
│  ② 配置选项                                      │
│  ┌────────────────────────────────────────┐     │
│  │ 分部类型:     [建筑 ▼]                  │     │
│  │ 清单类别:     [分部分项清单 ▼]           │     │
│  │ 来源类型:     [合同清单 ▼]              │     │
│  │ 版本:         [V1]                      │     │
│  │ 导入模式:     [追加 ◉] [替换] [按编码]  │     │
│  │ 单项名称:     [___________]              │     │
│  │ 单位名称:     [___________]              │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  [上一步]              [下一步: 预览]            │
└──────────────────────────────────────────────────┘
```

**步骤**:
1. **上传文件**: 复用既有 `project.boq.import.wizard` 的上传约束；前端只做非权威的即时提示
2. **配置选项**: 分部类型、清单类别、来源类型、版本、导入模式
3. **预览**: 由既有服务端 CSV/XLS/XLSX 解析能力返回权威预览和错误；前端不解析业务文件
4. **导入**: 接入既有 wizard/action，显示服务端返回的进度、校验和日志

### 3.3 ScBoqSummaryBar（汇总栏）

在树视图顶部显示关键指标：
- 清单总金额
- 分部类型分布（饼图小图）
- 完成进度
- 暂估项数量
- 警告项数量

## 4. 技术约束

- **框架**: Vue 3 + TypeScript + `<script setup>`
- **样式**: 复用现有 `@sc/design-tokens`、`@sc/ui` 与应用 CSS；不得引入平行样式体系
- **状态管理**: Pinia store `useBoqStore`
- **API 调用**: 走现有 Intent 协议（POST /api/v1/intent）
- **Contract 集成**: 优先扩展统一页面 envelope 的 BOQ payload/ref，不默认新增顶层 view/wizard 类型
- **文件解析**: 复用后端 `project.boq.import.wizard` 已有 CSV/XLS/XLSX 解析；SheetJS 路径已 `SUPERSEDED`，禁止实施
- **依赖**: 不以“零三方”或指定库为结论，任何新增依赖必须通过 ADR

## 5. 文件结构

```
boq-frontend/src/
├── components/
│   ├── ScBoqTreeView.vue          # 树视图主组件
│   ├── ScBoqTreeRow.vue           # 树行组件（递归）
│   ├── ScBoqImportWizard.vue      # 导入向导
│   ├── ScBoqSummaryBar.vue        # 汇总栏
│   └── ScBoqCategoryTabs.vue     # 类别 Tab 切换
├── stores/
│   └── useBoqStore.ts             # Pinia store
├── api/
│   └── boqApi.ts                  # Intent API 封装
├── types/
│   └── boq.ts                     # TypeScript 类型定义
└── utils/
    ├── boqTree.ts                  # 树构建工具
    └── boqImport.ts                # 导入预览解析
```

## 6. 里程碑

| 周次 | 交付物 |
|------|--------|
| G2 | 只读审计既有 wizard、action、权限、CSV/XLS/XLSX 和失败语义 |
| G3.1 | 统一 envelope 中定义 BOQ 只读数据引用与安全降级 |
| G3.2 | 接入既有导入入口和服务端预览，不新增浏览器解析器 |
| G3.3 | 用真实角色、1k/10k 数据与五视口验收最小闭环 |
| 后续 | 行内编辑、汇总和危险导入模式另行 ADR，不纳入首批 |
