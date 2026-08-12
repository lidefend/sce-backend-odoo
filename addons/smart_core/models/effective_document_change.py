# -*- coding: utf-8 -*-
import json

from odoo import fields, models


class ScEffectiveDocumentChangeMixin(models.AbstractModel):
    """Neutral revision/audit carrier for changes to effective documents.

    The mixin deliberately knows nothing about contracts, projects, amounts or
    approvals.  Product modules own those semantics and call
    ``_sc_mark_change_effective`` only after their domain transition succeeds.
    """

    _name = "sc.effective.document.change.mixin"
    _description = "Effective Document Change Audit Mixin"

    sc_change_revision = fields.Integer(
        "变更版本", default=1, readonly=True, copy=False
    )
    sc_change_effective_at = fields.Datetime(
        "生效时间", readonly=True, copy=False
    )
    sc_change_effective_by = fields.Many2one(
        "res.users", string="生效操作人", readonly=True, copy=False
    )
    sc_change_previous_snapshot = fields.Text(
        "生效前快照", readonly=True, copy=False
    )
    sc_change_current_snapshot = fields.Text(
        "生效后快照", readonly=True, copy=False
    )

    def _sc_change_snapshot_fields(self):
        """Product models override this with their audited business fields."""
        return ()

    def _sc_change_snapshot_value(self, field_name):
        value = self[field_name]
        field = self._fields[field_name]
        if field.type == "many2one":
            return value.id if value else False
        if field.type in ("one2many", "many2many"):
            return value.ids
        if field.type == "date":
            return fields.Date.to_string(value) if value else False
        if field.type == "datetime":
            return fields.Datetime.to_string(value) if value else False
        return value

    def _sc_build_change_snapshot(self, field_names=None):
        self.ensure_one()
        names = tuple(field_names or self._sc_change_snapshot_fields())
        unknown = [name for name in names if name not in self._fields]
        if unknown:
            raise ValueError("Unknown effective-change snapshot fields: %s" % ", ".join(unknown))
        payload = {name: self._sc_change_snapshot_value(name) for name in names}
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)

    def _sc_mark_change_effective(self, field_names=None):
        for record in self:
            current_snapshot = record._sc_build_change_snapshot(field_names)
            already_effective = bool(record.sc_change_effective_at)
            record.with_context(sc_skip_effective_change_audit=True).write(
                {
                    "sc_change_revision": (
                        (record.sc_change_revision or 1) + 1
                        if already_effective
                        else (record.sc_change_revision or 1)
                    ),
                    "sc_change_previous_snapshot": (
                        record.sc_change_current_snapshot or "{}"
                    ),
                    "sc_change_current_snapshot": current_snapshot,
                    "sc_change_effective_at": fields.Datetime.now(),
                    "sc_change_effective_by": self.env.user.id,
                }
            )
        return True
