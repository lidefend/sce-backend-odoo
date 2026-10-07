# -*- coding: utf-8 -*-
"""Real-ORM lock on the declared form-surface capability probe.

``UiContractV2Handler._model_surface_capabilities`` is the only declared-surface
path that talks to the real Odoo field API.  Its previous implementation called
``fields_get`` with a keyword this Odoo build does not accept; the resulting
``TypeError`` was swallowed into an empty name set, so every contract published
``formStructureContract.surfaces = []``.  The client treats an empty list as a
declaration ("this page publishes no region"), so the collaboration region
disappeared from every form while each pure-unittest boundary test kept passing
because it injected ``capabilities`` directly and never exercised this path.
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler


@tagged("post_install", "-at_install", "form_structure_surface_capability_orm")
class TestFormStructureSurfaceCapabilityOrm(TransactionCase):
    """The declared region must follow the real model capability."""

    def _handler(self):
        return UiContractV2Handler(self.env, su_env=self.env)

    def test_chatter_model_declares_the_collaboration_surface(self):
        handler = self._handler()
        caps = handler._model_surface_capabilities("res.partner")
        self.assertTrue(caps["collaboration"], caps)
        self.assertTrue(caps["remarks"], caps)
        declared = handler._form_structure_surfaces(model="res.partner")
        self.assertEqual([row["surface"] for row in declared], ["activity"])
        self.assertEqual(declared[0]["contentKind"], "collaboration-panel")
        self.assertTrue(declared[0]["capabilities"]["timeline"])

    def test_model_without_chatter_declares_no_surface(self):
        handler = self._handler()
        caps = handler._model_surface_capabilities("ir.model.fields")
        self.assertFalse(caps["collaboration"], caps)
        self.assertFalse(caps["attachments"], caps)
        self.assertEqual(handler._form_structure_surfaces(model="ir.model.fields"), [])

    def test_unknown_model_is_the_only_silent_no_capability_answer(self):
        handler = self._handler()
        self.assertEqual(
            handler._model_surface_capabilities("x.smart_core_missing_model"),
            {"collaboration": False, "remarks": False, "attachments": False},
        )

    def test_field_api_failure_is_not_converted_into_a_wrong_default(self):
        handler = self._handler()
        model_class = type(self.env["res.partner"])
        original = model_class.fields_get

        def _broken_fields_get(*args, **kwargs):
            raise TypeError(
                "BaseModel.fields_get() got an unexpected keyword argument 'load'"
            )

        model_class.fields_get = _broken_fields_get
        try:
            with self.assertRaises(TypeError):
                handler._model_surface_capabilities("res.partner")
        finally:
            model_class.fields_get = original
