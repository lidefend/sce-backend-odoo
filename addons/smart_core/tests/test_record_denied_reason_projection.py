#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A denied record action must publish the layer that denied it.

Two separate facts are proven here and recorded separately:

1. ``PageAssembler._record_capability_block`` derives ``denied_reason`` from the
   authority it actually observed (model ACL vs record rule vs missing record),
   so the same model can report different reasons for the same operation.  A
   constant would silently reintroduce "the terminal explains a disabled control
   out of nothing".
2. ``unified_page_contract_v2_assembler._assemble_ui_contract`` publishes that
   block on the real contract path as
   ``statusContract.globalStatus.recordDeniedReasons`` and publishes nothing at
   all when no operation was denied.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE_DIR = ROOT / "addons/smart_core/core"
PAGE_ASSEMBLER_PATH = ROOT / "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py"


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _clear_odoo_modules():
    for name in list(sys.modules):
        if name == "odoo" or name.startswith("odoo."):
            sys.modules.pop(name, None)


def _load_page_assembler():
    """Load PageAssembler with only the collaborators it touches stubbed."""
    _clear_odoo_modules()
    odoo = _install_module("odoo", _=lambda value: value)
    _install_module("odoo.exceptions", AccessError=type("AccessError", (Exception,), {}))
    _install_module("odoo.http", request=types.SimpleNamespace(env=None))
    odoo.http = sys.modules["odoo.http"]
    _install_module("odoo.addons")
    smart_core = _install_module("odoo.addons.smart_core")
    app_config = _install_module("odoo.addons.smart_core.app_config_engine")
    services = _install_module("odoo.addons.smart_core.app_config_engine.services")
    assemblers = _install_module("odoo.addons.smart_core.app_config_engine.services.assemblers")
    utils = _install_module("odoo.addons.smart_core.utils")
    smart_core.__path__ = [str(ROOT / "addons/smart_core")]
    app_config.__path__ = [str(ROOT / "addons/smart_core/app_config_engine")]
    services.__path__ = [str(ROOT / "addons/smart_core/app_config_engine/services")]
    assemblers.__path__ = [str(ROOT / "addons/smart_core/app_config_engine/services/assemblers")]
    utils.__path__ = [str(ROOT / "addons/smart_core/utils")]
    _install_module(
        "odoo.addons.smart_core.utils.delete_policy",
        resolve_unlink_policy=lambda *_args, **_kwargs: {},
    )
    _install_module(
        "odoo.addons.smart_core.utils.extension_hooks",
        call_extension_hook_first=lambda *_args, **_kwargs: None,
    )
    _install_module("odoo.addons.smart_core.app_config_engine.utils.misc", safe_eval=lambda value: value)
    _install_module(
        "odoo.addons.smart_core.app_config_engine.utils.view_utils",
        extract_tree_columns_strict=lambda *_args, **_kwargs: ([], None),
        normalize_cols_safely=lambda value, *_args, **_kwargs: value,
    )
    module_name = "odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, PAGE_ASSEMBLER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.PageAssembler


def _load_v2_assembler():
    """Load the real v2 contract assembler with its sibling core modules."""
    _clear_odoo_modules()
    _install_module("odoo")
    _install_module("odoo.addons")
    smart_core = _install_module("odoo.addons.smart_core")
    smart_core.__path__ = [str(CORE_DIR.parent)]
    core = _install_module("odoo.addons.smart_core.core")
    core.__path__ = [str(CORE_DIR)]
    for name in (
        "action_semantics_vocabulary",
        "contract_lifecycle",
        "source_authority",
        "unified_page_contract_v2_permissions",
        "unified_page_contract_v2_runtime_actions",
        "unified_page_contract_v2_action",
        "unified_page_contract_v2_form_structure",
    ):
        module_name = f"odoo.addons.smart_core.core.{name}"
        spec = importlib.util.spec_from_file_location(module_name, CORE_DIR / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        assert spec and spec.loader
        spec.loader.exec_module(module)
    module_name = "odoo.addons.smart_core.core.unified_page_contract_v2_assembler"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, CORE_DIR / "unified_page_contract_v2_assembler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _FakeRecord:
    def __init__(self, model, exists):
        self._model = model
        self._exists = exists

    def exists(self):
        return self if self._exists else None

    def check_access_rule(self, operation):
        if not self._model.rule_allows(operation, check_rule=True):
            raise sys.modules["odoo.exceptions"].AccessError(operation)
        return True

    def _filter_access_rules(self, operation):
        return self._model.rule_allows(operation, check_rule=False)


class _FakeModel:
    """A model whose three authorities are set independently.

    ``rule_denied`` drives ``check_access_rule`` (what ``_record_rule_rights``
    sees), ``filter_denied`` drives ``_filter_access_rules`` (what the denial
    classifier sees) and ``acl_denied`` drives ``check_access_rights``.  Keeping
    them separate is what lets a test distinguish "model ACL denied" from
    "record rule denied" from "the two disagree".
    """

    def __init__(self, *, exists=True, rule_denied=(), filter_denied=(), acl_denied=(), acl_raises=False):
        self.exists_flag = exists
        self.rule_denied = set(rule_denied)
        self.filter_denied = set(filter_denied)
        self.acl_denied = set(acl_denied)
        self.acl_raises = acl_raises

    def browse(self, _record_id):
        return _FakeRecord(self, self.exists_flag)

    def rule_allows(self, operation, *, check_rule):
        denied = self.rule_denied if check_rule else self.filter_denied
        return operation not in denied

    def check_access_rights(self, operation, raise_exception=False):
        if self.acl_raises:
            raise RuntimeError("acl authority unavailable")
        return operation not in self.acl_denied


def _env(**kwargs):
    return {"x.document": _FakeModel(**kwargs)}


class RecordCapabilityDenialReasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.PageAssembler = _load_page_assembler()

    def _reasons(self, **kwargs):
        return self.PageAssembler._record_rule_denied_reasons(
            _env(**kwargs), "x.document", 7, self.PageAssembler._record_rule_rights(_env(**kwargs), "x.document", 7)
        )

    def test_model_acl_denial_is_named_as_model_access(self):
        model = _FakeModel(rule_denied={"write"}, acl_denied={"write"})
        rights = self.PageAssembler._record_rule_rights({"x.document": model}, "x.document", 7)
        self.assertFalse(rights["write"])
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": model}, "x.document", 7, rights),
            {"write": "MODEL_ACCESS_DENIED"},
        )

    def test_record_rule_denial_is_named_as_record_rule(self):
        model = _FakeModel(rule_denied={"unlink"}, filter_denied={"unlink"})
        rights = self.PageAssembler._record_rule_rights({"x.document": model}, "x.document", 7)
        self.assertFalse(rights["unlink"])
        self.assertTrue(model.check_access_rights("unlink", raise_exception=False))
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": model}, "x.document", 7, rights),
            {"unlink": "RECORD_RULE_DENIED"},
        )

    def test_missing_record_is_reported_as_not_found_not_as_a_rule_denial(self):
        model = _FakeModel(exists=False)
        rights = self.PageAssembler._record_rule_rights({"x.document": model}, "x.document", 7)
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": model}, "x.document", 7, rights),
            {
                "write": "RECORD_NOT_FOUND",
                "unlink": "RECORD_NOT_FOUND",
                "duplicate": "RECORD_NOT_FOUND",
            },
        )

    def test_disagreeing_authorities_are_reported_as_unresolved(self):
        model = _FakeModel(rule_denied={"write"})
        rights = self.PageAssembler._record_rule_rights({"x.document": model}, "x.document", 7)
        self.assertFalse(rights["write"])
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": model}, "x.document", 7, rights),
            {"write": "RECORD_AUTHORITY_UNRESOLVED"},
        )

    def test_duplicate_reads_follow_the_read_authority(self):
        acl = _FakeModel(rule_denied={"read"}, filter_denied={"read"}, acl_denied={"read"})
        acl_rights = self.PageAssembler._record_rule_rights({"x.document": acl}, "x.document", 7)
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": acl}, "x.document", 7, acl_rights),
            {"read": "MODEL_ACCESS_DENIED", "duplicate": "MODEL_ACCESS_DENIED"},
        )
        rule = _FakeModel(rule_denied={"read"}, filter_denied={"read"})
        rule_rights = self.PageAssembler._record_rule_rights({"x.document": rule}, "x.document", 7)
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": rule}, "x.document", 7, rule_rights),
            {"read": "RECORD_RULE_DENIED", "duplicate": "RECORD_RULE_DENIED"},
        )

    def test_unavailable_acl_authority_fails_closed_to_model_access(self):
        model = _FakeModel(rule_denied={"unlink"}, filter_denied={"unlink"}, acl_raises=True)
        rights = self.PageAssembler._record_rule_rights({"x.document": model}, "x.document", 7)
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": model}, "x.document", 7, rights),
            {"unlink": "MODEL_ACCESS_DENIED"},
        )

    def test_allowed_record_publishes_no_reason(self):
        model = _FakeModel()
        rights = self.PageAssembler._record_rule_rights({"x.document": model}, "x.document", 7)
        self.assertEqual(rights, {"read": True, "write": True, "create": True, "unlink": True, "duplicate": True})
        self.assertEqual(
            self.PageAssembler._record_rule_denied_reasons({"x.document": model}, "x.document", 7, rights), {}
        )

    def test_create_is_never_reported_as_a_record_level_denial(self):
        model = _FakeModel(acl_denied={"create"})
        rights = self.PageAssembler._record_rule_rights({"x.document": model}, "x.document", 7)
        reasons = self.PageAssembler._record_rule_denied_reasons({"x.document": model}, "x.document", 7, rights)
        self.assertNotIn("create", reasons)

    def test_unusable_record_identity_publishes_no_reason(self):
        model = _FakeModel()
        env = {"x.document": model}
        rights = {"read": True, "write": False, "create": True, "unlink": False, "duplicate": False}
        for record_id in (None, 0, "abc", ""):
            self.assertEqual(self.PageAssembler._record_rule_denied_reasons(env, "x.document", record_id, rights), {})

    def test_the_reason_is_computed_from_the_observed_authority(self):
        """Same operation, same False right, two different authorities."""
        acl_model = _FakeModel(rule_denied={"write"}, acl_denied={"write"})
        acl_rights = self.PageAssembler._record_rule_rights({"x.document": acl_model}, "x.document", 7)
        unresolved_model = _FakeModel(rule_denied={"write"})
        unresolved_rights = self.PageAssembler._record_rule_rights({"x.document": unresolved_model}, "x.document", 7)
        self.assertEqual(acl_rights, unresolved_rights)
        acl_reason = self.PageAssembler._record_rule_denied_reasons(
            {"x.document": acl_model}, "x.document", 7, acl_rights
        )["write"]
        unresolved_reason = self.PageAssembler._record_rule_denied_reasons(
            {"x.document": unresolved_model}, "x.document", 7, unresolved_rights
        )["write"]
        self.assertNotEqual(acl_reason, unresolved_reason)

    def test_capability_block_carries_rights_identity_and_reason_together(self):
        model = _FakeModel(rule_denied={"unlink"}, filter_denied={"unlink"})
        block = self.PageAssembler._record_capability_block({"x.document": model}, "x.document", 41)
        self.assertEqual(block["record_id"], 41)
        self.assertFalse(block["rights"]["unlink"])
        self.assertEqual(block["denied_reason"], {"unlink": "RECORD_RULE_DENIED"})

    def test_record_capability_block_is_what_both_permission_roots_receive(self):
        """The producer must publish the classifier, not a bare rights dict."""
        source = PAGE_ASSEMBLER_PATH.read_text()
        self.assertIn("record_capability = self._record_capability_block(env, model, requested_record_id)", source)
        self.assertIn('permissions["record"] = self._record_capability_block(self.env, model_name, record_id)', source)


class RecordDeniedReasonPublishedOnContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembler = _load_v2_assembler()

    def _contract(self, record_block):
        source = {
            "model": "sc.general.contract",
            "view_type": "form",
            "record_id": 11,
            "permissions": {"record": record_block} if record_block else {},
        }
        return self.assembler._assemble_ui_contract(
            source, client_type="web", request_id="req-1", source_type="ui.contract"
        )

    def _published(self, contract):
        return contract["statusContract"]["globalStatus"].get("recordDeniedReasons")

    def test_projected_reasons_reach_the_published_contract(self):
        contract = self._contract({
            "rights": {"read": True, "write": False, "create": True, "unlink": False, "duplicate": True},
            "record_id": 11,
            "denied_reason": {"unlink": "RECORD_RULE_DENIED", "write": "MODEL_ACCESS_DENIED"},
        })
        self.assertEqual(
            self._published(contract),
            {"unlink": "RECORD_RULE_DENIED", "write": "MODEL_ACCESS_DENIED"},
        )

    def test_an_allowed_record_publishes_no_reason_key(self):
        contract = self._contract({
            "rights": {"read": True, "write": True, "create": True, "unlink": True, "duplicate": True},
            "record_id": 11,
            "denied_reason": {},
        })
        self.assertIsNone(self._published(contract))

    def test_a_contract_without_a_record_block_publishes_no_reason_key(self):
        self.assertIsNone(self._published(self._contract(None)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
