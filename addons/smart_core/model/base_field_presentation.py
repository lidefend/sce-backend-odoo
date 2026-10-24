from odoo import api, models

from ..core.field_presentation_usage import field_presentation_usage


class BaseFieldPresentation(models.AbstractModel):
    _inherit = "base"

    def _valid_field_parameter(self, field, name):
        return name in {"sc_ui_usage", "sc_record_error", "sc_feedback_usage"} or super()._valid_field_parameter(field, name)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        # Internal source proof must never become page-authored field metadata.
        for metadata in result.values():
            metadata.pop("sc_record_error", None)
            metadata.pop("sc_feedback_usage", None)
        if attributes is None or "sc_ui_usage" in attributes:
            # Only annotate fields already allowed by native fields_get/field ACL.
            for name, metadata in result.items():
                metadata["sc_ui_usage"] = field_presentation_usage(getattr(self._fields[name], "sc_ui_usage", None))
        return result
