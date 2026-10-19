# -*- coding: utf-8 -*-
"""Keep demo seed labels attributed to the right language key.

Translatable fields are stored as a JSONB map keyed by language code.  Module
data is loaded with ``en_US`` as the active language, so a Chinese label
declared in XML lands in the ``en_US`` slot and ``zh_CN`` stays empty.  Odoo
falls back to ``en_US``, which hides the defect visually, but language
switching and later translation maintenance then operate on inconsistent data.

This hook mirrors an existing ``en_US`` value into ``zh_CN`` only when the
``zh_CN`` slot is missing.  Existing translations are never overwritten.
"""

from odoo import api, models


class DemoLocaleNormalize(models.AbstractModel):
    _name = "demo.locale.normalize"
    _description = "Normalize demo seed labels across language keys"

    _TARGETS = (
        ("hr.department", "name"),
        ("hr.job", "name"),
        ("product.template", "name"),
        ("project.project", "name"),
        ("account.analytic.plan", "name"),
    )

    @api.model
    def run(self):
        for model_name, field_name in self._TARGETS:
            if model_name not in self.env:
                continue
            model = self.env[model_name].sudo()
            field = model._fields.get(field_name)
            if not field or not field.translate:
                continue
            self._fill_missing_language(model, field_name)
        return True

    @api.model
    def _fill_missing_language(self, model, field_name):
        query = """
            SELECT id, "{field}"
              FROM "{table}"
             WHERE "{field}" IS NOT NULL
               AND jsonb_typeof("{field}") = 'object'
        """.format(field=field_name, table=model._table)
        self.env.cr.execute(query)
        for record_id, payload in self.env.cr.fetchall():
            if not isinstance(payload, dict):
                continue
            source = payload.get("en_US")
            if not source or payload.get("zh_CN"):
                continue
            model.browse(record_id).with_context(lang="zh_CN").write(
                {field_name: source}
            )
