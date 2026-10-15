# -*- coding: utf-8 -*-
from odoo import models

from ..hooks import assert_demo_seed_principal, guard_demo_scope, guard_demo_data_space


class ProjectDemoBoqSeed(models.Model):
    _inherit = "project.project"

    def sc_demo_import_boq(self):
        assert_demo_seed_principal(self.env)
        guard_demo_scope(self.env)
        guard_demo_data_space(self.env)
        from ..tools.scenario_loader import (
            _ensure_s00_boq_visibility, _import_demo_boq, _bind_generated_demo_xmlid,
        )
        expected = self.env.ref("smart_construction_demo.sc_demo_project_001")
        if self != expected:
            raise ValueError("demo BOQ import must target the declared demo project")
        _ensure_s00_boq_visibility(self.env)
        version, batch = _import_demo_boq(self.env, self)
        _bind_generated_demo_xmlid(self.env, "sc_demo_boq_version_contract_v1", version)
        _bind_generated_demo_xmlid(self.env, "sc_demo_boq_import_batch_001", batch)
        for code, xmlid in (("010101", "sc_demo_boq_earthwork"), ("020202", "sc_demo_boq_concrete")):
            lines = version.line_ids.filtered(lambda line: line.code == code and line.line_type == "item")
            if len(lines) != 1:
                raise ValueError("demo BOQ import requires unique item: %s" % code)
            _bind_generated_demo_xmlid(self.env, xmlid, lines)
