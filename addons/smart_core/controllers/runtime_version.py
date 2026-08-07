# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from odoo.addons.smart_core.utils.product_release import runtime_release_identity

from .platform_ops_controller import _ok


class RuntimeVersionController(http.Controller):
    @http.route(
        "/api/runtime-version",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def runtime_version(self, **_params):
        return _ok(runtime_release_identity(request.env.cr.dbname))
