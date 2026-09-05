# -*- coding: utf-8 -*-
"""BOQ 导出服务（G6.3，ADR-004 决策 1）。

- 引擎 xlsxwriter（BSD-2，Odoo 运行时自带，供应链零新增）；生成全在后端，
  文件经 ir.attachment 引用下发，浏览器不接触全量数据。
- 列按授权组显式裁剪：成控组全列；项目只读组裁掉金额列并在
  cropped_columns 明示（不静默）。
- 大批量（> EXPORT_ROW_LIMIT）由 handler 返回结构化 EXPORT_TOO_LARGE；
  异步 job 路径按 G7 首切片立项，本期不实施。

模块级依赖保持纯标准库（hashlib/io/base64），xlsxwriter 惰性导入：
桩测试（无 Odoo/xlsxwriter 环境）只测列策略与行投影纯函数。
"""
from __future__ import annotations

import base64
import hashlib
import io

EXPORT_SCHEMA = "sc.boq.export.v1"
EXPORT_ROW_LIMIT = 5000

XLSX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# (field_key, column_header, is_amount)
BASE_COLUMNS = [
    ("hierarchy_code", "层级编码", False),
    ("code", "清单编码", False),
    ("name", "清单名称", False),
    ("division_name", "分部工程", False),
    ("single_name", "单项工程", False),
    ("unit_name", "单位工程", False),
    ("major_name", "专业", False),
    ("uom", "单位", False),
    ("quantity", "工程量", False),
    ("section_type", "工程类别", False),
]
AMOUNT_COLUMNS = [
    ("price", "单价", True),
    ("imported_amount", "来源合价", True),
    ("amount", "合价", True),
]

CROP_REASON = (
    "金额列（单价/来源合价/合价）仅成控组"
    "（group_sc_cap_cost_manager / group_sc_cap_cost_user）可导出"
)


def resolve_columns(has_cost_access):
    """列策略纯函数：返回 (columns, cropped_keys, crop_reason)。

    has_cost_access 为 True 时全列；否则裁掉金额列并附原因。
    """
    if has_cost_access:
        columns = list(BASE_COLUMNS) + list(AMOUNT_COLUMNS)
        return columns, [], ""
    return list(BASE_COLUMNS), [key for key, _label, _amt in AMOUNT_COLUMNS], CROP_REASON


def build_row_values(line, section_label_resolver):
    """把一条 project.boq.line 记录投影为按字段 key 取值的 dict。

    line 为 Odoo recordset（单条）；section_label_resolver(value) 返回
    工程类别 selection 展示名。纯数据投影，不做任何聚合。
    """
    values = {
        "hierarchy_code": line.hierarchy_code or "",
        "code": line.code or "",
        "name": line.name or "",
        "division_name": line.division_name or "",
        "single_name": line.single_name or "",
        "unit_name": line.unit_name or "",
        "major_name": line.major_name or "",
        "uom": (line.uom_id.name or "") if line.uom_id else "",
        "quantity": float(line.quantity or 0.0),
        "section_type": section_label_resolver(line.section_type),
        "price": float(line.price or 0.0),
        "imported_amount": float(line.imported_amount or 0.0),
        "amount": float(line.amount or 0.0),
    }
    return values


def build_workbook_bytes(header_rows, row_value_dicts):
    """生成 xlsx 字节流（xlsxwriter 惰性导入）。

    header_rows: [(field_key, header, is_amount), ...]（resolve_columns 输出）
    row_value_dicts: [dict, ...]（build_row_values 输出）
    """
    import xlsxwriter  # 惰性导入：宿主桩测试环境无 xlsxwriter

    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    sheet = workbook.add_worksheet("BOQ")

    amount_fmt = workbook.add_format({"num_format": "#,##0.00"})
    for col_index, (_key, header, _is_amount) in enumerate(header_rows):
        sheet.write(0, col_index, header)
        sheet.set_column(col_index, col_index, 14)

    for row_index, values in enumerate(row_value_dicts, start=1):
        for col_index, (key, _header, is_amount) in enumerate(header_rows):
            value = values.get(key)
            if is_amount:
                sheet.write_number(row_index, col_index, float(value or 0.0), amount_fmt)
            elif isinstance(value, (int, float)):
                sheet.write_number(row_index, col_index, value)
            else:
                sheet.write(row_index, col_index, value if value is not None else "")
    workbook.close()
    payload = buffer.getvalue()
    buffer.close()
    return payload


def digest_bytes(payload):
    """sha256 摘要（审计对账用，不改业务事实）。"""
    return hashlib.sha256(payload).hexdigest()


def attachment_values(filename, payload):
    """ir.attachment 字段字典（datas 为 base64 文本）。"""
    return {
        "name": filename,
        "datas": base64.b64encode(payload).decode("ascii"),
        "mimetype": XLSX_MIMETYPE,
    }


def build_filename(project_name, version_code):
    """导出文件名：BOQ_<项目名>_<版本号>.xlsx（去除路径分隔符）。"""
    safe_project = (project_name or "project").replace("/", "_").replace("\\", "_")
    safe_version = (version_code or "version").replace("/", "_").replace("\\", "_")
    return "BOQ_%s_%s.xlsx" % (safe_project, safe_version)
