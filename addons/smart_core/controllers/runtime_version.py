# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request

from odoo.addons.smart_core.utils.product_release import runtime_release_identity


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
        payload = runtime_release_identity(request.env.cr.dbname)
        return request.make_response(
            json.dumps(payload, ensure_ascii=False),
            headers=[("Content-Type", "application/json; charset=utf-8")],
            status=200,
        )
