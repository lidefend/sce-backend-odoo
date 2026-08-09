# -*- coding: utf-8 -*-
import re

from odoo import fields, models


def _compact(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


class ProjectBoqVersionNormCatalog(models.Model):
    _inherit = "project.boq.version"

    norm_catalog_id = fields.Many2one(
        "sc.norm.catalog",
        string="匹配定额库",
        ondelete="restrict",
        readonly=True,
        help="综合单价分析导入时用于匹配定额编号的地区和版本库。",
    )


class ProjectBoqAnalysisNormReference(models.Model):
    _inherit = "project.boq.analysis.norm.line"

    norm_item_id = fields.Many2one(
        "sc.norm.item", string="对应定额子目", readonly=True, ondelete="restrict", index=True
    )
    norm_match_state = fields.Selection(
        [("matched", "已匹配"), ("unmatched", "未匹配"), ("ambiguous", "多项候选")],
        string="定额匹配状态",
        readonly=True,
        index=True,
    )
    norm_match_note = fields.Char("定额匹配说明", readonly=True)


class ProjectBoqAnalysisNormResolver(models.Model):
    _inherit = "project.boq.analysis"

    def _resolve_norm_links(self):
        Item = self.env["sc.norm.item"]
        for analysis in self:
            catalog = analysis.version_id.norm_catalog_id
            for line in analysis.norm_line_ids:
                raw = re.sub(r"\s+", "", line.norm_code or "")
                base = re.sub(r"(?:换|调|补|\[.*)$", "", raw)
                variants = list(dict.fromkeys(value for value in (raw, base) if value))
                domain = [("code", "in", variants)]
                if catalog:
                    domain.append(("catalog_id", "=", catalog.id))
                candidates = Item.search(domain)
                if len(candidates) > 1 and analysis.major_name:
                    major = _compact(analysis.major_name)
                    scoped = candidates.filtered(
                        lambda item: _compact(item.specialty_id.name) == major
                        or _compact(item.specialty_id.name) in major
                        or major in _compact(item.specialty_id.name)
                    )
                    if scoped:
                        candidates = scoped
                if len(candidates) == 1:
                    line.write(
                        {
                            "norm_item_id": candidates.id,
                            "norm_match_state": "matched",
                            "norm_match_note": "按定额库、专业和编号匹配",
                        }
                    )
                elif candidates:
                    line.write(
                        {
                            "norm_item_id": False,
                            "norm_match_state": "ambiguous",
                            "norm_match_note": "存在 %s 个候选定额子目" % len(candidates),
                        }
                    )
                else:
                    line.write(
                        {
                            "norm_item_id": False,
                            "norm_match_state": "unmatched",
                            "norm_match_note": "指定定额库中未找到编号" if catalog else "未指定定额库且未找到唯一编号",
                        }
                    )
        return True
