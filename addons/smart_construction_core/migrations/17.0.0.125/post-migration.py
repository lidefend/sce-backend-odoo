# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import SUPERUSER_ID, api


PARAM_KEY = "smart_core.lowcode.system_config_menu_xmlids"
PROMOTED_ADMINISTRATION_XMLIDS = {
    "smart_construction_core.menu_sc_company_document_archive",
    "smart_construction_core.menu_sc_organization_department",
}


def migrate(cr, version):
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env["ir.config_parameter"].sudo()
    raw = params.get_param(PARAM_KEY, "") or ""
    current = {
        value.strip()
        for value in str(raw).split(",")
        if value.strip()
    }
    normalized = sorted(current - PROMOTED_ADMINISTRATION_XMLIDS)
    if normalized != sorted(current):
        params.set_param(PARAM_KEY, ",".join(normalized))
