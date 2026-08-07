# -*- coding: utf-8 -*-
from odoo import fields, models


class ScProjectCapabilityRoadmap(models.Model):
    _name = "sc.project.capability.roadmap"
    _description = "产品中心能力上线说明"
    _order = "center_name, sequence, id"

    center_name = fields.Char(string="所属中心", required=True, readonly=True, index=True, default="项目中心")
    name = fields.Char(string="能力域", required=True, readonly=True)
    capability_key = fields.Char(string="能力标识", required=True, readonly=True, index=True)
    release_status = fields.Selection(
        [("followup", "后续上线")],
        string="发布状态",
        required=True,
        default="followup",
        readonly=True,
    )
    planned_scope = fields.Text(string="规划范围", required=True, readonly=True)
    launch_note = fields.Text(string="上线条件", required=True, readonly=True)
    sequence = fields.Integer(default=10, readonly=True)

    _sql_constraints = [
        ("sc_project_capability_roadmap_key_unique", "unique(capability_key)", "能力标识必须唯一。"),
    ]
