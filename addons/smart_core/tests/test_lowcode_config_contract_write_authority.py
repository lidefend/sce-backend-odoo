# -*- coding: utf-8 -*-
"""Low-code config -> runtime contract -> write enforcement binding.

This is the authoritative anchor for the verification chain:

    配置输入(模型/视图/权限/角色/规则/低代码配置)
    -> 平台 API
    -> 运行时契约
    -> 前端消费(忠实执行契约承诺)

It pins two previously unowned invariants:

1. A low-code view fragment that declares a field readonly must surface that
   readonly in the assembled runtime contract (config -> contract).
2. The same field must be rejected by the platform write proxy when the
   contract treats it as non-writable (contract promise == API enforcement).

The API-side write authority is the platform write allowlist
(``ApiDataWriteHandler.ALLOWED_MODELS``), not the view modifier; a view-level
readonly is UI-only by Odoo semantics.  This test binds a field that is outside
the write allowlist so both surfaces agree on "not writable".
"""
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.handlers.api_data_write import ApiDataWriteHandler


def _field_node_modifiers(contract, field_name):
    """Return the first ``field`` node modifiers for ``field_name`` in layout."""
    stack = list((contract or {}).get("layout") or [])
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        if node.get("type") == "field" and node.get("name") == field_name:
            return node.get("modifiers") or {}
        stack.extend(node.get("children") or [])
    return {}


@tagged("post_install", "-at_install", "lowcode_contract_write_authority")
class TestLowcodeConfigContractWriteAuthority(TransactionCase):
    BOUND_FIELD = "website"

    def _build_config_with_readonly_fragment(self):
        fragment = self.env["app.view.fragment"].sudo().create({
            "name": "lowcode readonly %s fragment" % self.BOUND_FIELD,
            "category": "custom",
            "view_type": "form",
            "contract": {"field_modifiers": {self.BOUND_FIELD: {"readonly": True}}},
        })
        return self.env["app.view.config"].sudo().create({
            "name": "lowcode readonly partner form",
            "model": "res.partner",
            "view_type": "form",
            "projection_scope": "test:lowcode_contract_write_authority:res.partner:form",
            "arch_parsed": {
                "layout": [{"type": "sheet", "children": [{"type": "group", "children": [
                    {"type": "field", "name": "name"},
                    {"type": "field", "name": self.BOUND_FIELD},
                ]}]}],
                "field_modifiers": {"name": {}, self.BOUND_FIELD: {}},
                "header_buttons": [],
                "button_box": [],
                "statusbar": {"field": None, "states": []},
                "chatter": {"enabled": False},
                "attachments": {"enabled": False},
            },
            "fragment_ids": [(6, 0, [fragment.id])],
        })

    def test_lowcode_readonly_field_binds_contract_and_write_authority(self):
        config = self._build_config_with_readonly_fragment()
        contract = config.build_final_contract()

        modifiers = (contract or {}).get("field_modifiers") or {}
        self.assertIs(modifiers[self.BOUND_FIELD]["readonly"], True)

        result = ApiDataWriteHandler(self.env).handle({
            "intent": "api.data.write",
            "params": {
                "model": "res.partner",
                "id": 999999999,
                "vals": {self.BOUND_FIELD: "https://example.com"},
            },
        })

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["reason_code"], "USER_ERROR")

    def test_model_readonly_field_projects_contract_readonly(self):
        """Same-source half: the authoritative ``ir.model.fields.readonly``
        flag is what ``_generate_from_ir_model`` projects into the contract.
        """
        model_config = self.env["app.model.config"].with_context(
            contract_projection_readonly=True,
        )._generate_from_ir_model("res.partner", fields_get_snapshot={
            "x_locked_note": {
                "type": "char",
                "string": "Locked note",
                "required": False,
                "readonly": True,
                "help": "",
            },
        })

        field_by_name = {
            item["name"]: item
            for item in (model_config.fields_def or {}).get("fields", [])
        }
        self.assertTrue(field_by_name["x_locked_note"]["readonly"])

    def test_native_view_dynamic_readonly_preserves_contract_expression(self):
        """Database view metadata -> contract, including dynamic attributes.

        A dynamic attribute is not pre-evaluated into a boolean: the contract
        must preserve the native expression so the consumer can evaluate it
        against the actual record at render time.  Two different record states
        must therefore project the *same* normalized expression.
        """
        view = self.env["ir.ui.view"].sudo().create({
            "name": "lowcode dynamic readonly partner form",
            "model": "res.partner",
            "type": "form",
            "arch": (
                "<form><sheet><group>"
                '<field name="active" invisible="1"/>'
                '<field name="name"/>'
                '<field name="phone" readonly="not active"/>'
                "</group></sheet></form>"
            ),
        })
        active = self.env["res.partner"].sudo().create({
            "name": "Active partner",
            "active": True,
        })
        archived = self.env["res.partner"].sudo().create({
            "name": "Archived partner",
            "active": False,
        })

        def readonly_modifier(record):
            view_data = self.env["res.partner"].browse(record.id).get_view(
                view_id=view.id,
                view_type="form",
            )
            projection = self.env["app.view.config"].with_context(
                contract_view_id=view.id,
                contract_projection_readonly=True,
            )._generate_from_fields_view_get(
                "res.partner",
                "form",
                view_data=view_data,
            )
            return _field_node_modifiers(
                projection.arch_parsed or {},
                "phone",
            ).get("readonly")

        expected = {
            "kind": "not",
            "expr": {"kind": "field_truthy", "field": "active"},
            "raw": "not active",
        }
        self.assertEqual(readonly_modifier(active), expected)
        self.assertEqual(readonly_modifier(archived), expected)
