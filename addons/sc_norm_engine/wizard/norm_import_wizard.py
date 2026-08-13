import base64
import bisect
import hashlib
import json
import re
from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .workbook_adapter import SUPPORTED_EXTENSIONS, open_workbook


MAX_FILE_BYTES = 30 * 1024 * 1024
INDEX_SHEETS = ("专业章节", "专业章节(安装)")


def _clean(value):
    if value is None:
        return ""
    return str(value).replace("\n", "").replace("\r", "").replace("　", " ").strip()


def _to_float(value):
    text = _clean(value).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value, fallback=0):
    try:
        number = float(value)
        return int(number) if number.is_integer() else fallback
    except (TypeError, ValueError):
        return fallback


def _canonical_sheet_name(value):
    return _clean(value).replace("（", "(").replace("）", ")")


def _record_value_changed(record, field_name, target):
    field = record._fields[field_name]
    current = record[field_name]
    if field.type == "many2one":
        current = current.id or False
        target = int(target or 0) or False
    elif field.type in {"float", "monetary"}:
        return abs(float(current or 0.0) - float(target or 0.0)) > 0.000001
    elif field.type in {"char", "text", "selection"}:
        current = current or ""
        target = target or ""
    return current != target


def _changed_values(record, values):
    return {
        name: value
        for name, value in values.items()
        if _record_value_changed(record, name, value)
    }


def _detect_specialty_from_title(title):
    text = re.sub(r"^[▲■●]", "", _clean(title)).strip()
    match = re.match(r"^([A-Z])\s*(.+)$", text)
    if not match:
        return None, None
    return match.group(1), match.group(2).replace("定额", "").strip()


class ScNormImportWizard(models.TransientModel):
    _name = "sc.norm.import.wizard"
    _description = "定额库导入"

    state = fields.Selection(
        [("upload", "选择文件"), ("preview", "预检确认"), ("done", "导入完成")],
        default="upload",
        required=True,
        readonly=True,
    )
    data_file = fields.Binary("定额文件", required=True)
    filename = fields.Char("文件名")
    catalog_id = fields.Many2one(
        "sc.norm.catalog",
        string="目标定额库",
        required=True,
        domain="[('state', '!=', 'archived')]",
        default=lambda self: self.env.ref(
            "sc_norm_engine.catalog_sc_2015", raise_if_not_found=False
        ),
    )
    import_mode = fields.Selection(
        [("upsert", "增量更新"), ("replace", "全量替换")],
        string="导入方式",
        default="upsert",
        required=True,
    )
    confirm_replace = fields.Boolean("我已确认全量替换现有定额库")
    preview_digest = fields.Char(readonly=True)
    preview_catalog_id = fields.Many2one("sc.norm.catalog", readonly=True)
    preview_specialty_count = fields.Integer("专业", readonly=True)
    preview_chapter_count = fields.Integer("章节", readonly=True)
    preview_item_count = fields.Integer("定额项", readonly=True)
    preview_warning_count = fields.Integer("警告", readonly=True)
    preview_error_count = fields.Integer("错误", readonly=True)
    preview_log = fields.Text("预检结果", readonly=True)
    log = fields.Text("导入结果", readonly=True)

    def _check_import_authority(self):
        """Bind import execution to the real user's model and capability rights."""
        if not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_business_config_admin"
        ):
            raise AccessError(_("仅业务配置管理员可以导入定额库。"))
        self.env["sc.norm.catalog"].check_access_rights("read")
        for model_name in ("sc.norm.specialty", "sc.norm.chapter", "sc.norm.item", "sc.norm.resource", "sc.norm.rule"):
            model = self.env[model_name]
            for operation in ("read", "write", "create"):
                model.check_access_rights(operation)

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    def _decode_file(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_("请先上传定额文件。"))
        if not _clean(self.filename).lower().endswith(SUPPORTED_EXTENSIONS + (".json",)):
            raise UserError(_("仅支持 .xls、.xlsx、.xlsm 或正式定额 JSON 数据包。"))
        try:
            data = base64.b64decode(self.data_file, validate=True)
        except Exception as exc:
            raise UserError(_("文件内容无法解码：%s") % exc) from exc
        if not data:
            raise UserError(_("上传的文件为空。"))
        if len(data) > MAX_FILE_BYTES:
            raise UserError(_("文件超过 30MB 上限，请分批处理。"))
        return data

    def _open_workbook(self, data):
        try:
            return open_workbook(data, self.filename)
        except Exception as exc:
            raise UserError(_("无法读取 Excel 工作簿：%s") % exc) from exc

    def _parse_index_sheets(self, workbook):
        result = defaultdict(lambda: {"name": "", "sheet_name": "", "chapters": {}})
        for sheet_name in [name for name in workbook.sheetnames if _canonical_sheet_name(name) in INDEX_SHEETS]:
            ws = workbook[sheet_name]
            header_row = chapter_col = name_col = start_col = None
            for row_no in range(1, min(20, ws.max_row) + 1):
                values = [_clean(ws.cell(row=row_no, column=col).value) for col in range(1, ws.max_column + 1)]
                if "章节" in values and "名称" in values:
                    header_row = row_no
                    chapter_col = values.index("章节") + 1
                    name_col = values.index("名称") + 1
                    start_col = values.index("开始定额编码") + 1 if "开始定额编码" in values else None
                    break
            if not header_row:
                continue
            for row_no in range(header_row + 1, ws.max_row + 1):
                chapter_code = _clean(ws.cell(row=row_no, column=chapter_col).value)
                name = _clean(ws.cell(row=row_no, column=name_col).value)
                specialty_code, specialty_name = _detect_specialty_from_title(name)
                if specialty_code and specialty_name:
                    current_name = result[specialty_code]["name"]
                    if not current_name or "单独" in current_name:
                        result[specialty_code]["name"] = specialty_name
                if re.fullmatch(r"[A-Z]{2}(?:\d{2})*", chapter_code) and name:
                    start_code = _clean(ws.cell(row=row_no, column=start_col).value) if start_col else ""
                    parent_code = next(
                        (
                            chapter_code[:length]
                            for length in range(len(chapter_code) - 2, 1, -2)
                            if chapter_code[:length] in result[chapter_code[0]]["chapters"]
                        ),
                        "",
                    )
                    result[chapter_code[0]]["chapters"][chapter_code] = {
                        "name": name,
                        "parent_code": parent_code,
                        "level": len(chapter_code) // 2,
                        "sequence": row_no * 10,
                        "norm_code_start": start_code if re.fullmatch(r"[A-Z]{2}\d+", start_code) else "",
                        "source_row": row_no,
                    }
        for specialty_code, row in result.items():
            row["sheet_name"] = next(
                (
                    name
                    for name in workbook.sheetnames
                    if _clean(name).startswith(specialty_code)
                    and name not in INDEX_SHEETS
                ),
                "",
            )
        return dict(result)

    def _parse_workbook(self, data):
        workbook = self._open_workbook(data)
        try:
            warnings, errors = [], []
            specialties = self._parse_index_sheets(workbook)
            missing_parent_codes = [
                chapter_code
                for specialty in specialties.values()
                for chapter_code, chapter in specialty["chapters"].items()
                if chapter["level"] > 1 and not chapter["parent_code"]
            ]
            if missing_parent_codes:
                warnings.append(
                    "目录中有 %s 个章节缺少上级节点，已按专业直属节点保留：%s"
                    % (len(missing_parent_codes), "、".join(missing_parent_codes[:20]))
                )
            chapter_starts = {}
            for specialty_code, specialty in specialties.items():
                grouped = defaultdict(list)
                for chapter_code, chapter in specialty["chapters"].items():
                    if chapter["norm_code_start"]:
                        grouped[chapter["norm_code_start"]].append((chapter_code, chapter))
                chapter_starts[specialty_code] = {
                    "codes": sorted(grouped),
                    "rows": grouped,
                }
            canonical_names = {_canonical_sheet_name(name) for name in workbook.sheetnames}
            if not any(name in canonical_names for name in INDEX_SHEETS):
                errors.append("未找到“专业章节”或“专业章节(安装)”目录表。")
            items = {}
            parsed_sheets = []
            required_headers = ("定额名称", "项目名称", "单位")
            cost_integrity = {"total": 0, "direct": 0}
            for sheet_name in workbook.sheetnames:
                if _canonical_sheet_name(sheet_name) in INDEX_SHEETS:
                    continue
                ws = workbook[sheet_name]
                header_row = None
                column_map = {}
                for row_no in range(1, min(20, ws.max_row) + 1):
                    values = [_clean(ws.cell(row=row_no, column=col).value) for col in range(1, ws.max_column + 1)]
                    if all(header in values for header in required_headers):
                        header_row = row_no
                        column_map = {value: index + 1 for index, value in enumerate(values) if value}
                        break
                # Identification is structural, never based on a localized
                # sheet title. This includes support catalogs such as X/Y and
                # excludes the separate derived-rate table.
                if not header_row:
                    continue
                first_code = next((
                    _clean(ws.cell(row=row_no, column=column_map["定额名称"]).value)
                    for row_no in range(header_row + 1, ws.max_row + 1)
                    if re.fullmatch(r"[A-Z]{2}\d+", _clean(ws.cell(row=row_no, column=column_map["定额名称"]).value))
                ), "")
                if not first_code:
                    warnings.append(f"工作表“{sheet_name}”没有可识别的定额编号，已跳过。")
                    continue
                specialty_code = first_code[0]
                clean_name = _clean(sheet_name)
                specialty = specialties.setdefault(specialty_code, {
                    "name": clean_name[1:].replace("定额", "").strip() or specialty_code,
                    "sheet_name": sheet_name,
                    "chapters": {},
                })
                specialty["sheet_name"] = sheet_name
                parsed_sheets.append(sheet_name)
                machine_column = column_map.get("机械费")
                misc_column = column_map.get("综合费") or column_map.get("zhf")
                inferred_fee_column = (
                    machine_column + 1
                    if machine_column and misc_column == machine_column + 2
                    else None
                )

                def raw_cell(row_no, *headers, column=None):
                    target = column or next((column_map.get(header) for header in headers if column_map.get(header)), None)
                    return ws.cell(row=row_no, column=target).value if target else None

                for row_no in range(header_row + 1, ws.max_row + 1):
                    code = _clean(raw_cell(row_no, "定额名称"))
                    name = _clean(raw_cell(row_no, "项目名称"))
                    if not code and not name:
                        continue
                    if not re.fullmatch(r"[A-Z]{2}\d+", code) or not name:
                        warnings.append(f"工作表“{sheet_name}”第 {row_no} 行编号或名称无效，已跳过。")
                        continue
                    row_specialty_code = code[0]
                    if row_specialty_code != specialty_code:
                        errors.append(f"定额 {code} 与工作表专业 {specialty_code} 不一致（{sheet_name} 第 {row_no} 行）。")
                        continue
                    start_index = chapter_starts.get(specialty_code, {"codes": [], "rows": {}})
                    position = bisect.bisect_right(start_index["codes"], code) - 1
                    chapter_code = code[:2]
                    if position >= 0:
                        start_code = start_index["codes"][position]
                        chapter_code = max(
                            start_index["rows"][start_code],
                            key=lambda candidate: len(candidate[0]),
                        )[0]
                    if chapter_code not in specialty["chapters"]:
                        errors.append(f"定额 {code} 无法归属章节 {chapter_code}（{sheet_name} 第 {row_no} 行）。")
                        continue
                    key = (specialty_code, code)
                    if key in items:
                        errors.append(f"定额编号 {specialty_code}/{code} 在工作簿中重复。")
                        continue
                    cost_direct = _to_float(raw_cell(row_no, "直接费"))
                    cost_labor = _to_float(raw_cell(row_no, "人工费"))
                    cost_material = _to_float(raw_cell(row_no, "材料费"))
                    cost_machine = _to_float(raw_cell(row_no, "机械费"))
                    cost_misc = _to_float(raw_cell(row_no, "综合费", "zhf"))
                    raw_price_total = raw_cell(row_no, "综合单价")
                    price_total = _to_float(raw_price_total) if raw_price_total not in (None, "") else cost_direct + cost_misc
                    if abs(price_total - cost_direct - cost_misc) > 0.02:
                        cost_integrity["total"] += 1
                    if abs(cost_direct - cost_labor - cost_material - cost_machine) > 0.02:
                        cost_integrity["direct"] += 1
                    items[key] = {
                        "specialty_code": specialty_code,
                        "chapter_code": chapter_code,
                        "source_sheet": sheet_name,
                        "code": code,
                        "name": name,
                        "unit_raw": _clean(raw_cell(row_no, "单位")),
                        "price_total": price_total,
                        "cost_direct": cost_direct,
                        "cost_labor": cost_labor,
                        "cost_material": cost_material,
                        "cost_machine": cost_machine,
                        "fee_rate": _to_float(raw_cell(row_no, "费率", "机械费率", "fl", column=inferred_fee_column)),
                        "cost_misc": cost_misc,
                        "work_desc": _clean(raw_cell(row_no, "工作内容", "gcnr")),
                        "line_no": _to_int(raw_cell(row_no, "序号"), fallback=row_no),
                    }
            if cost_integrity["total"]:
                warnings.append(f"有 {cost_integrity['total']} 条定额不满足“综合单价=直接费+综合费”。")
            if cost_integrity["direct"]:
                warnings.append(f"有 {cost_integrity['direct']} 条定额不满足“直接费=人工费+材料费+机械费”。")
            if not parsed_sheets:
                errors.append("未找到可导入的定额数据表。")
            if not items and not errors:
                errors.append("工作簿中没有可导入的定额项。")
            chapter_count = sum(len(row["chapters"]) for row in specialties.values())
            return {
                "specialties": specialties, "items": list(items.values()), "sheets": parsed_sheets,
                "warnings": warnings, "errors": errors, "chapter_count": chapter_count,
            }
        finally:
            close = getattr(workbook, "close", None)
            if callable(close):
                close()

    def _parse_payload(self, data):
        if _clean(self.filename).lower().endswith(".json"):
            return self._parse_norm_dataset(data)
        return self._parse_workbook(data)

    def _parse_norm_dataset(self, data):
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UserError(_("定额 JSON 数据包无法解析：%s") % exc) from exc
        if payload.get("schema") != "sce.norm.dataset/v1":
            raise UserError(_("不支持的定额数据包 Schema。"))
        claimed_digest = payload.pop("dataset_sha256", "")
        actual_digest = hashlib.sha256(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        payload["dataset_sha256"] = claimed_digest
        if not claimed_digest or claimed_digest != actual_digest:
            raise UserError(_("定额数据包摘要不一致，文件可能被修改或不完整。"))
        catalog = payload.get("catalog") or {}
        if catalog.get("code") != self.catalog_id.code:
            raise UserError(_("数据包定额库编码 %s 与目标 %s 不一致。") % (catalog.get("code"), self.catalog_id.code))
        errors, warnings = [], []
        specialties = {
            row["code"]: {"name": row["name"], "sheet_name": row["code"], "chapters": {}}
            for row in payload.get("specialties", [])
        }
        for sequence, row in enumerate(payload.get("chapters", []), start=1):
            specialty = specialties.get(row.get("specialty_code"))
            if not specialty:
                errors.append("章节 %s 引用了不存在的专业。" % row.get("code"))
                continue
            specialty["chapters"][row["code"]] = {
                "name": row["name"], "parent_code": row.get("parent_code") or "",
                "level": int(row.get("level") or 1), "sequence": sequence * 10,
                "norm_code_start": row.get("norm_code_start") or "", "source_row": sequence,
            }
        items = []
        allowed = {
            "specialty_code", "chapter_code", "code", "name", "unit_raw", "price_total",
            "cost_direct", "cost_labor", "cost_material", "cost_machine", "cost_misc", "work_desc",
            "source_file", "source_pdf_page", "source_printed_page", "source_confidence", "source_digest",
        }
        for row in payload.get("items", []):
            item = {key: value for key, value in row.items() if key in allowed}
            item["source_sheet"] = row.get("book_id") or ""
            item["line_no"] = int(row.get("source_pdf_page") or 0)
            item["source_bbox"] = json.dumps(row.get("source_bbox") or [], ensure_ascii=False)
            item["_resources"] = row.get("resources") or []
            if item.get("specialty_code") not in specialties:
                errors.append("定额 %s 引用了不存在的专业。" % item.get("code"))
            elif item.get("chapter_code") not in specialties[item["specialty_code"]]["chapters"]:
                errors.append("定额 %s 引用了不存在的章节。" % item.get("code"))
            component_total = sum(
                float(item.get(field_name) or 0.0)
                for field_name in ("cost_labor", "cost_material", "cost_machine", "cost_misc")
            )
            if component_total and abs(float(item.get("price_total") or 0.0) - component_total) > 0.05:
                errors.append("定额 %s 的综合单价与费用构成不一致。" % item.get("code"))
            items.append(item)
        rules = payload.get("rules") or []
        blocking = [row for row in payload.get("review_issues", []) if row.get("severity") == "error"]
        if blocking:
            errors.append("数据包仍有 %s 个阻断复核项。" % len(blocking))
        return {
            "specialties": specialties, "items": items, "rules": rules,
            "sheets": [row.get("book_id") for row in payload.get("source_books", [])],
            "warnings": warnings, "errors": errors,
            "chapter_count": sum(len(row["chapters"]) for row in specialties.values()),
        }

    def _preview_text(self, plan):
        lines = [
            "【目标定额库】%s" % self.catalog_id.display_name,
            "【文件】%s" % self.filename,
            "【工作表】%s" % ("、".join(plan["sheets"]) or "-"),
            "【预计导入】专业 %s 个，章节 %s 个，定额项 %s 条"
            % (len(plan["specialties"]), plan["chapter_count"], len(plan["items"])),
        ]
        if plan["warnings"]:
            lines.extend(["", "【警告】"] + [f"- {row}" for row in plan["warnings"][:30]])
        if plan["errors"]:
            lines.extend(["", "【必须修复】"] + [f"- {row}" for row in plan["errors"][:50]])
            if len(plan["errors"]) > 50:
                lines.append(f"- 其余 {len(plan['errors']) - 50} 条未展开")
        else:
            lines.extend(["", "预检通过，可执行%s。" % ("增量更新" if self.import_mode == "upsert" else "全量替换")])
        return "\n".join(lines)

    def action_preflight(self):
        self.ensure_one()
        self._check_import_authority()
        if not self.catalog_id or self.catalog_id.state == "archived":
            raise UserError(_("请选择一个可用且未归档的目标定额库。"))
        data = self._decode_file()
        plan = self._parse_payload(data)
        self.write({
            "state": "preview", "preview_digest": hashlib.sha256(data).hexdigest(),
            "preview_catalog_id": self.catalog_id.id,
            "preview_specialty_count": len(plan["specialties"]), "preview_chapter_count": plan["chapter_count"],
            "preview_item_count": len(plan["items"]), "preview_warning_count": len(plan["warnings"]),
            "preview_error_count": len(plan["errors"]), "preview_log": self._preview_text(plan), "log": False,
        })
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.write({
            "state": "upload",
            "confirm_replace": False,
            "preview_digest": False,
            "preview_catalog_id": False,
        })
        return self._reopen()

    def action_import(self):
        self.ensure_one()
        self._check_import_authority()
        if self.state != "preview" or not self.preview_digest:
            raise UserError(_("请先执行预检。"))
        if self.catalog_id != self.preview_catalog_id:
            raise UserError(_("目标定额库已变更，请重新预检。"))
        if self.import_mode == "replace" and not self.confirm_replace:
            raise ValidationError(_("全量替换会删除现有定额数据，请勾选确认后再执行。"))
        data = self._decode_file()
        if hashlib.sha256(data).hexdigest() != self.preview_digest:
            raise UserError(_("文件已变更，请重新预检。"))
        plan = self._parse_payload(data)
        if plan["errors"]:
            self.write({"preview_error_count": len(plan["errors"]), "preview_log": self._preview_text(plan)})
            raise UserError(_("预检未通过，请根据“必须修复”明细调整文件。"))

        Specialty, Chapter, Item, Resource, Rule = (
            self.env[name]
            for name in ("sc.norm.specialty", "sc.norm.chapter", "sc.norm.item", "sc.norm.resource", "sc.norm.rule")
        )
        target_catalog = self.catalog_id
        if self.import_mode == "replace":
            # Direct unlink remains denied by model ACL. Full replacement is
            # the only elevated path and is protected by capability, explicit
            # confirmation, a successful preflight and an unchanged digest.
            target_specialties = Specialty.sudo().search(
                [("catalog_id", "=", target_catalog.id)]
            )
            Rule.sudo().search([("catalog_id", "=", target_catalog.id)]).unlink()
            Item.sudo().search([("specialty_id", "in", target_specialties.ids)]).unlink()
            Chapter.sudo().search([("specialty_id", "in", target_specialties.ids)]).unlink()
            target_specialties.unlink()
        stats = defaultdict(int)
        specialty_records, chapter_records = {}, {}
        for sequence, (code, row) in enumerate(sorted(plan["specialties"].items()), start=1):
            specialty = Specialty.search(
                [("catalog_id", "=", target_catalog.id), ("code", "=", code)], limit=1
            )
            values = {
                "catalog_id": target_catalog.id,
                "code": code,
                "name": row["name"] or code,
                "sheet_name": row["sheet_name"],
                "sequence": sequence * 10,
            }
            if specialty:
                changes = _changed_values(specialty, values)
                if changes:
                    specialty.write(changes); stats["specialty_updated"] += 1
                else:
                    stats["specialty_unchanged"] += 1
            else:
                specialty = Specialty.create(values); stats["specialty_created"] += 1
            specialty_records[code] = specialty
            existing_chapters = {
                chapter.code: chapter
                for chapter in Chapter.search([("specialty_id", "=", specialty.id)])
            }
            for chapter_code, chapter_row in sorted(
                row["chapters"].items(), key=lambda pair: (len(pair[0]), pair[1]["sequence"], pair[0])
            ):
                chapter = existing_chapters.get(chapter_code)
                parent = chapter_records.get((code, chapter_row["parent_code"]))
                chapter_values = {
                    "specialty_id": specialty.id,
                    "parent_id": parent.id if parent else False,
                    "code": chapter_code,
                    "name": chapter_row["name"],
                    "level": chapter_row["level"],
                    "sequence": chapter_row["sequence"],
                    "norm_code_start": chapter_row["norm_code_start"],
                    "source_row": chapter_row["source_row"],
                }
                if chapter:
                    changes = _changed_values(chapter, chapter_values)
                    if changes:
                        chapter.write(changes); stats["chapter_updated"] += 1
                    else:
                        stats["chapter_unchanged"] += 1
                else:
                    chapter = Chapter.create(chapter_values); stats["chapter_created"] += 1
                chapter_records[(code, chapter_code)] = chapter
        existing_items = {
            (item.specialty_id.id, item.code): item
            for item in Item.search([("specialty_id", "in", [record.id for record in specialty_records.values()])])
        }
        create_values = []
        pending_resources = []
        for row in plan["items"]:
            specialty = specialty_records[row["specialty_code"]]
            chapter = chapter_records[(row["specialty_code"], row["chapter_code"])]
            resources = row.get("_resources") or []
            values = {key: value for key, value in row.items() if key not in ("specialty_code", "chapter_code", "_resources")}
            values.update({"specialty_id": specialty.id, "chapter_id": chapter.id})
            item = existing_items.get((specialty.id, row["code"]))
            if item:
                changes = _changed_values(item, values)
                if changes:
                    item.write(changes); stats["item_updated"] += 1
                else:
                    stats["item_unchanged"] += 1
                if resources:
                    item.resource_ids.sudo().unlink()
                    pending_resources.extend((item, resource) for resource in resources)
            else:
                item = Item.create(values)
                stats["item_created"] += 1
                pending_resources.extend((item, resource) for resource in resources)
        for item, resource in pending_resources:
            Resource.create({
                "item_id": item.id, "sequence": resource.get("sequence") or 10,
                "resource_type": resource.get("resource_type") or "other", "name": resource.get("name"),
                "unit_raw": resource.get("unit_raw"), "unit_price": resource.get("unit_price") or 0.0,
                "quantity": resource.get("quantity") or 0.0,
                "quantity_confidence": resource.get("quantity_confidence") or 0.0,
                "source_bbox": json.dumps(resource.get("source_bbox") or [], ensure_ascii=False),
            })
        for row in plan.get("rules", []):
            specialty = specialty_records.get(row.get("specialty_code"))
            chapter = chapter_records.get((row.get("specialty_code"), row.get("chapter_code")))
            values = {
                "catalog_id": target_catalog.id, "specialty_id": specialty.id if specialty else False,
                "chapter_id": chapter.id if chapter else False, "code": row["code"], "title": row["title"],
                "rule_type": row["rule_type"], "content": row["content"], "source_file": row["source_file"],
                "source_pdf_page": row["source_pdf_page"], "source_printed_page": row.get("source_printed_page"),
                "source_confidence": row.get("source_confidence") or 0.0, "source_digest": row.get("source_digest"),
            }
            rule = Rule.search([("catalog_id", "=", target_catalog.id), ("code", "=", row["code"])], limit=1)
            if rule:
                changes = _changed_values(rule, values)
                if changes: rule.write(changes); stats["rule_updated"] += 1
                else: stats["rule_unchanged"] += 1
            else:
                Rule.create(values); stats["rule_created"] += 1
        self.write({
            "state": "done",
            "log": "\n".join([
                "导入成功（%s）" % ("增量更新" if self.import_mode == "upsert" else "全量替换"),
                "目标定额库：%s" % target_catalog.display_name,
                "专业：新增 %s，更新 %s，未变化 %s" % (stats["specialty_created"], stats["specialty_updated"], stats["specialty_unchanged"]),
                "章节：新增 %s，更新 %s，未变化 %s" % (stats["chapter_created"], stats["chapter_updated"], stats["chapter_unchanged"]),
                "定额项：新增 %s，更新 %s，未变化 %s" % (stats["item_created"], stats["item_updated"], stats["item_unchanged"]),
                "警告：%s" % len(plan["warnings"]),
            ])
        })
        return self._reopen()
