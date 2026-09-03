# ADR-004：Excel 导入导出引擎与安全边界

- 状态：Proposed（待批准；批准前通用 Excel 平台能力不实施）
- 范围：custom-frontend-integration G5 / Excel 专题
- 决策项：导入/导出引擎、异步 job、解析安全边界、病毒扫描边界

## 背景

总控计划 §18 决策待办：「Excel 文件处理引擎、异步 job、对象存储和病毒扫描边界」。专题文档已 SUPERSEDED 客户端 SheetJS 路径：导入导出机制属 P0，字段权限、模板与写入必须由后端专用 intent 承担；首批只审计并接入 BOQ 既有服务端导入（G2/G3 已完成闭环）。

## 事实核查（2026-09-03）

| 库 | 许可证 | 读写 | 维护 | 关键安全事实 |
| --- | --- | --- | --- | --- |
| xlsxwriter 3.2.x | BSD-2 | 仅写 | 活跃（2025-09 发版，113M 月下载，无已知漏洞） | 纯 Python、零运行时依赖 |
| openpyxl 3.1.x | MIT | 读+写 | 志愿者维护 | **默认不防 quadratic blowup / billion laughs XML 攻击，官方文档明示需 defusedxml** |
| SheetJS/ce | Apache-2.0（社区版） | 前端 | 功能滞后于 Pro 商业版 | 客户端路径已被 SUPERSEDED，仅记录不采用 |

Odoo 运行时本身已依赖 xlsxwriter（标准报表导出路径），供应链零新增。

## 决策（建议）

1. **导出引擎 = xlsxwriter**（BSD-2，纯 Python，与 Odoo 既有导出同源）。导出一律后端生成，按字段权限裁剪列；浏览器不接触全量数据。
2. **导入引擎 = openpyxl + defusedxml**：解析必须经 defusedxml 包装（防 XML 炸弹/外部实体），这是采纳 openpyxl 的硬前置条件；文件大小、行数、单元格长度在解析前强制限额（沿用 BOQ 导入向导既有 digest 绑定与限额模式）。
3. **异步 job = 既有 `sc.ops.job`**：大批量导入/导出走既有 job 框架，不新建队列基础设施；job 权限与审计沿用现有机制。
4. **病毒扫描边界**：上传→扫描→解析三段分离；扫描器以接口抽象（`scan_upload`）注入，首期可退化为「扩展名+MIME+结构白名单」校验，ClamAV/侧车容器在部署环境具备后接入，不改业务代码。
5. **对象存储**：本期附件仍走 Odoo ir.attachment + filestore（与 ADR-001 备份链路一致）；独立对象存储须单独立项。
6. **客户端路径永久禁止**：任何浏览器端解析/生成 Excel 的实现（含 SheetJS）由守卫拦截——浏览器绕过权限批量导出/写入是总控明令禁令。

## 替代方案与否决理由

- pandas.to_excel：引入重型科学计算依赖链，仅做薄封装得不偿失。
- xlrd：2.0 起不支持 .xlsx，已出局。
- LibreOffice headless 转换：进程隔离与体积成本只在「保真模板填充」场景才值得，首期无该需求。

## 回退策略

- 导入解析失败/超限 → 结构化错误经既有 intent 透传（复用 G3.1 BATCH_NOT_FOUND 模式），前端四态降级不白屏。
- 引擎替换（xlsxwriter↔openpyxl 写路径）局限在 service 层单点，契约与 intent 不变。

## 后果

- 后端新增 defusedxml 依赖（纯 Python，MIT/PSF 系许可证，低风险）。
- 批准后 G6 才能开始通用导入导出 wizard 的只读/异步实现。
