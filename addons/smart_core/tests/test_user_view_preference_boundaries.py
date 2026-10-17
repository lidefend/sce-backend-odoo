# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _BaseIntentHandler:
    def __init__(self, env=None, params=None, payload=None, context=None):
        self.env = env
        self.params = params or {}
        self.payload = payload or {}
        self.context = context or {}


class _EmptyRecord:
    def __bool__(self):
        return False


class _Record:
    id = 5
    value_json = {"density": "compact"}

    def write(self, vals):
        self.value_json = vals.get("value_json", self.value_json)


class _PreferenceModel:
    """Mirrors addons/smart_core/models/user_view_preference.py semantics."""

    def __init__(self):
        self.sudo_calls = 0
        self.searches = 0
        self.search_domains = []
        self.created_vals = None

    def sudo(self):
        self.sudo_calls += 1
        return self

    def normalize_preference_key(self, value):
        key = str(value or "list_columns").strip() or "list_columns"
        return key if key in {"list_columns", "scene_ui_driver"} else "list_columns"

    def build_scope_key(self, *, preference_key, view_type, action_id, model_name):
        key = self.normalize_preference_key(preference_key)
        view = str(view_type or "list").strip() or "list"
        try:
            action = int(action_id or 0)
        except (TypeError, ValueError):
            action = 0
        model = str(model_name or "").strip()
        if action <= 0 and not model:
            raise ValueError("preference scope requires an action_id or model")
        target = f"action:{action}" if action > 0 else f"model:{model}"
        return f"ui:{key}:{view}:{target}"

    def search(self, domain, limit=None, **kwargs):
        self.searches += 1
        self.search_domains.append(domain)
        return _EmptyRecord()

    def create(self, vals):
        self.created_vals = vals
        return _Record()


class _Field:
    def __init__(self, name=""):
        self.string = name
        self.type = "char"


class _ModelStub:
    """Fake res model exposing declared native tree-view columns."""

    def __init__(self, columns=(), *, unreadable=(), readable=True):
        self._fields = {name: _Field(name) for name in columns}
        self._arch = "<tree>" + "".join(f'<field name="{name}"/>' for name in columns) + "</tree>"
        self._unreadable = set(unreadable)
        self._readable = readable
        self.access_checks = 0

    def get_view(self, view_id=False, view_type="tree"):
        return {"arch": self._arch}

    def check_access_rights(self, operation, raise_exception=False):
        self.access_checks += 1
        if self._readable:
            return True
        if raise_exception:
            raise Exception(f"no read access on model ({operation})")
        return False

    def check_field_access_rights(self, operation, names):
        blocked = [name for name in names if name in self._unreadable]
        if blocked:
            raise Exception(f"no read access: {blocked}")
        return None


class _ActionRecord:
    """Faithful subset of the two real action models.

    ``type`` is declared on the abstract ``ir.actions.actions`` base, while
    ``res_model`` is declared only on the concrete ``ir.actions.act_window``.
    The stub keeps that split so a resolver that reads ``res_model`` off the
    base is caught here instead of only at runtime.
    """

    def __init__(self, action_type="", res_model="", *, exists=True, exposes_res_model=False):
        self.type = action_type
        self._exists = exists
        if exposes_res_model and res_model:
            self.res_model = res_model

    def exists(self):
        return self._exists


class _ActionsModel:
    def __init__(self, records=None, *, concrete=False):
        self._records = dict(records or {})
        self._concrete = concrete
        self.browse_calls = 0
        self.sudo_calls = 0

    def sudo(self):
        # Action metadata is a trusted read-only platform fact; the model
        # layer exposes it to every principal through sudo, exactly like
        # delivery/menu_service.py.
        self.sudo_calls += 1
        return self

    def browse(self, action_id):
        self.browse_calls += 1
        row = self._records.get(int(action_id))
        if row is None:
            return _ActionRecord(exists=False)
        action_type, res_model = row
        if self._concrete and action_type != "ir.actions.act_window":
            return _ActionRecord(exists=False)
        return _ActionRecord(
            action_type, res_model, exists=True, exposes_res_model=self._concrete,
        )


class _BoomService:
    """Any touch means the effective path compiled a page instead of declaring."""

    def __getattr__(self, name):
        raise AssertionError(f"page assembler must not be used: {name}")


# Declarations the stubbed P0 registry serves; a test sets this to declare an
# action-scoped lock exactly like the industry layer does.
_FORMAL_LIST_LOCK_DECLARATIONS = []


class _Env(dict):
    uid = 42
    context = {}


class _ModelDataStub:
    """Fake ``ir.model.data`` used to resolve declared action external ids."""

    def __init__(self, rows=None):
        self.rows = dict(rows or {})

    def sudo(self):
        return self

    def search_read(self, domain, fields=None, **kwargs):
        wanted_modules = None
        wanted_names = None
        for condition in domain:
            if not isinstance(condition, tuple) or len(condition) < 3:
                continue
            if condition[0] == "module":
                wanted_modules = set(condition[2])
            elif condition[0] == "name":
                wanted_names = set(condition[2])
        rows = []
        for xmlid, res_id in self.rows.items():
            module, _, name = str(xmlid).partition(".")
            if wanted_modules is not None and module not in wanted_modules:
                continue
            if wanted_names is not None and name not in wanted_names:
                continue
            rows.append({"module": module, "name": name, "res_id": res_id})
        return rows


def _actions():
    records = {
        878: ("ir.actions.act_window", "x.model"),
        506: ("ir.actions.act_window", "project.project"),
        600: ("ir.actions.server", "x.model"),
    }
    return _ActionsModel(records), _ActionsModel(records, concrete=True)


def _load_handler():
    root = Path(__file__).resolve().parents[1]
    addons_mod = types.ModuleType("odoo.addons")
    smart_core_mod = types.ModuleType("odoo.addons.smart_core")
    handlers_mod = types.ModuleType("odoo.addons.smart_core.handlers")
    core_mod = types.ModuleType("odoo.addons.smart_core.core")
    utils_mod = types.ModuleType("odoo.addons.smart_core.utils")
    smart_core_mod.__path__ = [str(root)]
    handlers_mod.__path__ = [str(root / "handlers")]
    core_mod.__path__ = [str(root / "core")]
    utils_mod.__path__ = [str(root / "utils")]
    base_mod = types.ModuleType("odoo.addons.smart_core.core.base_handler")
    base_mod.BaseIntentHandler = _BaseIntentHandler
    registry_mod = types.ModuleType("odoo.addons.smart_core.utils.contract_governance_registry")
    registry_mod.formal_list_lock_declarations = lambda: list(_FORMAL_LIST_LOCK_DECLARATIONS)
    sys.modules.update(
        {
            "odoo.addons": addons_mod,
            "odoo.addons.smart_core": smart_core_mod,
            "odoo.addons.smart_core.handlers": handlers_mod,
            "odoo.addons.smart_core.core": core_mod,
            "odoo.addons.smart_core.utils": utils_mod,
            "odoo.addons.smart_core.utils.contract_governance_registry": registry_mod,
            "odoo.addons.smart_core.core.base_handler": base_mod,
        }
    )
    module_name = "odoo.addons.smart_core.handlers.user_view_preference"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "user_view_preference.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _env(*, columns=("name", "business_nature", "manager_id"), unreadable=(), **extra):
    readable = bool(extra.pop("readable", True))
    actions, window_actions = _actions()
    base = {
        "sc.user.view.preference": _PreferenceModel(),
        "ir.actions.actions": actions,
        "ir.actions.act_window": window_actions,
        "ir.model.data": _ModelDataStub(extra.pop("model_data", None)),
    }
    if columns is not None:
        base["x.model"] = _ModelStub(columns, unreadable=unreadable, readable=readable)
        base["project.project"] = _ModelStub(columns, unreadable=unreadable, readable=readable)
    base.update(extra)
    return _Env(base)


class TestUserViewPreferenceBoundaries(unittest.TestCase):
    # ------------------------------------------------------------ illegal identity
    def test_get_without_action_or_model_is_rejected_before_query(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env, payload={})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(env["sc.user.view.preference"].searches, 0)

    def test_set_without_action_or_model_is_rejected_before_write(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(env=env, payload={"preference": {"visible_columns": ["name"]}})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertIsNone(Preference.created_vals)
        self.assertEqual(Preference.searches, 0)

    def test_unknown_action_is_rejected(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(
            env=env, payload={"action_id": 123456, "preference_key": "list_columns"}
        )
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertIn("action_id", result["error"]["message"])
        self.assertEqual(env["sc.user.view.preference"].searches, 0)

    def test_action_without_list_surface_is_rejected(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env, payload={"action_id": 600})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertIn("600", result["error"]["message"])

    def test_model_action_mismatch_is_rejected_for_read_and_write(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        reader = module.UserViewPreferenceGetHandler(env=env, payload={"action_id": 878, "model": "project.project"})
        read_result = reader.handle()
        self.assertFalse(read_result["ok"])
        self.assertEqual(read_result["code"], 400)
        self.assertIn("不一致", read_result["error"]["message"])
        writer = module.UserViewPreferenceSetHandler(
            env=env,
            payload={"action_id": 878, "model": "project.project", "preference_key": "list_columns",
                     "preference": {"visible_columns": ["name"]}},
        )
        write_result = writer.handle()
        self.assertFalse(write_result["ok"])
        self.assertEqual(write_result["code"], 400)
        self.assertIsNone(Preference.created_vals)
        self.assertEqual(Preference.searches, 0)

    def test_model_only_identity_requires_a_registered_model(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env, payload={"model": "ghost.model"})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertIn("ghost.model", result["error"]["message"])

    def test_scope_key_can_never_produce_the_model_unknown_sentinel(self):
        Preference = _PreferenceModel()
        with self.assertRaises(ValueError):
            Preference.build_scope_key(preference_key="list_columns", view_type="list", action_id=0, model_name="")
        self.assertEqual(
            Preference.build_scope_key(preference_key="list_columns", view_type="list", action_id=0, model_name="project.project"),
            "ui:list_columns:list:model:project.project",
        )

    def test_no_write_ever_records_the_model_unknown_sentinel(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        # Empty identity refuses before scope resolution.
        writer = module.UserViewPreferenceSetHandler(env=env, payload={"preference_key": "list_columns", "preference": {}})
        self.assertFalse(writer.handle()["ok"])
        self.assertIsNone(Preference.created_vals)
        # A legal target records the authoritative action identity.
        legal = module.UserViewPreferenceSetHandler(
            env=env, payload={"action_id": 878, "preference_key": "list_columns", "preference": {"visible_columns": ["name"]}}
        )
        self.assertTrue(legal.handle()["ok"])
        self.assertEqual(Preference.created_vals["scope_key"], "ui:list_columns:list:action:878")
        self.assertNotIn("model:unknown", Preference.created_vals["scope_key"])

    # ------------------------------------------------------- stored vs effective
    def test_stored_read_never_resolves_page_policy_and_retains_user_scope(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        record = _Record()
        record.value_json = {"hidden_columns": ["formerly_visible"], "column_order": ["formerly_visible"]}
        original = Preference.search

        def search(domain, limit=None, **kwargs):
            original(domain, limit=limit)
            return record

        Preference.search = search
        handler = module.UserViewPreferenceGetHandler(env=env)

        def forbidden(**kwargs):
            self.fail("stored preference read resolved a list preference policy")

        handler._resolve_list_preference_policy = forbidden
        handler._apply_list_preference_policy = forbidden
        result = handler.handle({"params": {"model": "x.model", "projection": "stored", "user_id": 99}})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["projection"], "stored")
        self.assertEqual(result["data"]["policy_source"], "current_page_contract")
        self.assertEqual(result["data"]["preference"]["hidden_columns"], ["formerly_visible"])
        self.assertNotIn("preference_contract", result["meta"])
        self.assertIn(("user_id", "=", 42), Preference.search_domains[0])
        self.assertEqual(Preference.sudo_calls, 0)

    def test_stored_read_never_compiles_a_page(self):
        module = _load_handler()
        env = _env(**{"app.contract.service": _BoomService()})
        handler = module.UserViewPreferenceGetHandler(env=env)
        result = handler.handle({"params": {"action_id": 878, "projection": "stored"}})
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["projection"], "stored")

    def test_effective_read_projects_declared_native_columns_without_a_page(self):
        module = _load_handler()
        env = _env(**{"app.contract.service": _BoomService()})
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceGetHandler(env=env, payload={"model": "x.model", "preference_key": "list_columns"})
        result = handler.handle()
        self.assertTrue(result["ok"])
        contract = result["meta"]["preference_contract"]
        self.assertEqual(contract["columns"], ["name", "business_nature", "manager_id"])
        self.assertEqual(contract["preference_policy"]["must_request_columns"], ["name", "business_nature", "manager_id"])
        self.assertEqual(contract["preference_policy"]["locked_columns"], [])
        self.assertTrue(contract["preference_policy"]["allow_visibility"])
        self.assertEqual(Preference.sudo_calls, 0)

    def test_effective_read_honours_declared_permission_filtering(self):
        module = _load_handler()
        env = _env(unreadable=("business_nature",))
        handler = module.UserViewPreferenceGetHandler(env=env, payload={"model": "x.model", "preference_key": "list_columns"})
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(result["meta"]["preference_contract"]["columns"], ["name", "manager_id"])

    def test_missing_declared_policy_is_refused_not_defaulted(self):
        module = _load_handler()
        env = _env(columns=())
        reader = module.UserViewPreferenceGetHandler(env=env, payload={"model": "x.model", "preference_key": "list_columns"})
        read_result = reader.handle()
        self.assertFalse(read_result["ok"])
        self.assertEqual(read_result["code"], 422)
        Preference = env["sc.user.view.preference"]
        writer = module.UserViewPreferenceSetHandler(
            env=env,
            payload={"model": "x.model", "preference_key": "list_columns", "preference": {"visible_columns": ["name"]}},
        )
        write_result = writer.handle()
        self.assertFalse(write_result["ok"])
        self.assertEqual(write_result["code"], 422)
        self.assertIsNone(Preference.created_vals)

    def test_effective_policy_constraints_are_applied_before_write(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(env=env)
        handler._resolve_list_preference_policy = lambda **kwargs: {
            "columns": ["name", "business_nature", "manager_id"],
            "fact_columns": ["business_nature"],
            "preference_policy": {
                "allow_visibility": True, "allow_order": False, "allow_width": False,
                "locked_columns": ["name"], "must_request_columns": ["business_nature"],
            },
        }
        handler.handle({"params": {
            "action_id": 878,
            "preference_key": "list_columns",
            "preference": {
                "visible_columns": ["name"],
                "hidden_columns": ["name", "business_nature", "manager_id"],
                "column_order": ["manager_id", "name"],
                "column_widths": {"name": 160, "manager_id": 220},
            },
        }})
        self.assertEqual(Preference.created_vals["value_json"], {
            "visible_columns": ["name"],
            "hidden_columns": ["business_nature", "manager_id"],
            "column_order": [],
            "column_widths": {},
        })

    # ------------------------------------------------- declared list-surface lock
    def _declare_lock(self, xmlid, res_id, **overrides):
        declaration = {
            "declaration_key": "user_confirmed_formal_list_lock",
            "action_xmlids": [xmlid],
            "model_name": "",
            "scope": "ui_only",
            "allow_visibility": False,
            "allow_order": False,
            "allow_width": False,
            "source": "smart_construction_core.user_confirmed_formal_list_lock",
        }
        declaration.update(overrides)
        _FORMAL_LIST_LOCK_DECLARATIONS.append(declaration)
        return {"model_data": {xmlid: res_id}}

    def tearDown(self):
        _FORMAL_LIST_LOCK_DECLARATIONS.clear()

    def test_declared_lock_is_reported_instead_of_a_second_verdict(self):
        module = _load_handler()
        env = _env(**self._declare_lock("smart_construction_core.action_locked", 878))
        handler = module.UserViewPreferenceGetHandler(env=env)
        result = handler.handle({"params": {"action_id": 878, "preference_key": "list_columns"}})
        self.assertTrue(result["ok"])
        contract = result["meta"]["preference_contract"]
        policy = contract["preference_policy"]
        self.assertTrue(policy["locked"])
        self.assertFalse(policy["allow_visibility"])
        self.assertFalse(policy["allow_order"])
        self.assertEqual(policy["locked_columns"], contract["columns"])
        self.assertEqual(contract["policy_declarations"], ["smart_construction_core.user_confirmed_formal_list_lock"])

    def test_locked_surface_refuses_to_hide_a_locked_column(self):
        module = _load_handler()
        env = _env(**self._declare_lock("smart_construction_core.action_locked", 878))
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(env=env)
        result = handler.handle({"params": {
            "action_id": 878,
            "preference_key": "list_columns",
            "preference": {
                "visible_columns": [],
                "hidden_columns": ["name"],
                "column_order": ["manager_id", "name"],
                "column_widths": {"name": 160},
            },
        }})
        self.assertTrue(result["ok"])
        stored = Preference.created_vals["value_json"]
        self.assertEqual(stored, {
            "visible_columns": [],
            "hidden_columns": [],
            "column_order": [],
            "column_widths": {},
        })

    def test_locked_surface_keeps_the_dimensions_the_declaration_still_allows(self):
        module = _load_handler()
        env = _env(**self._declare_lock(
            "smart_construction_core.action_locked", 878, allow_width=True,
        ))
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(env=env)
        result = handler.handle({"params": {
            "action_id": 878,
            "preference_key": "list_columns",
            "preference": {
                "visible_columns": [],
                "hidden_columns": ["name"],
                "column_widths": {"name": 160},
            },
        }})
        self.assertTrue(result["ok"])
        stored = Preference.created_vals["value_json"]
        self.assertEqual(stored["hidden_columns"], [])
        self.assertEqual(stored["column_widths"], {"name": 160})

    def test_undeclared_surface_stays_adjustable(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env)
        result = handler.handle({"params": {"action_id": 878, "preference_key": "list_columns"}})
        policy = result["meta"]["preference_contract"]["preference_policy"]
        self.assertFalse(policy["locked"])
        self.assertTrue(policy["allow_visibility"])
        self.assertEqual(policy["locked_columns"], [])
        self.assertEqual(result["meta"]["preference_contract"]["policy_declarations"], [])

    def test_revoked_model_read_access_is_refused_not_projected(self):
        module = _load_handler()
        env = _env(readable=False, **self._declare_lock("smart_construction_core.action_locked", 878))
        Preference = env["sc.user.view.preference"]
        reader = module.UserViewPreferenceGetHandler(env=env)
        read_result = reader.handle({"params": {"action_id": 878, "preference_key": "list_columns"}})
        self.assertFalse(read_result["ok"])
        self.assertEqual(read_result["code"], 403)
        self.assertEqual(env["x.model"].access_checks, 1)
        writer = module.UserViewPreferenceSetHandler(env=env)
        write_result = writer.handle({"params": {
            "action_id": 878, "preference_key": "list_columns",
            "preference": {"hidden_columns": ["name"]},
        }})
        self.assertFalse(write_result["ok"])
        self.assertEqual(write_result["code"], 403)
        self.assertIsNone(Preference.created_vals)

    def test_declared_scope_key_carries_no_company_component(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        scopes = {
            Preference.build_scope_key(
                preference_key="list_columns", view_type="list", action_id=878, model_name="x.model",
            )
            for _company in (1, 2)
        }
        self.assertEqual(len(scopes), 1)
        self.assertEqual(scopes.pop(), "ui:list_columns:list:action:878")

    def test_declaration_for_another_action_never_locks_this_surface(self):
        module = _load_handler()
        env = _env(**self._declare_lock("smart_construction_core.action_other", 506))
        handler = module.UserViewPreferenceGetHandler(env=env)
        result = handler.handle({"params": {"action_id": 878, "preference_key": "list_columns"}})
        policy = result["meta"]["preference_contract"]["preference_policy"]
        self.assertFalse(policy["locked"])
        self.assertTrue(policy["allow_visibility"])

    def test_declared_model_mismatch_never_locks_another_models_surface(self):
        module = _load_handler()
        env = _env(**self._declare_lock(
            "smart_construction_core.action_locked", 878, model_name="project.project",
        ))
        handler = module.UserViewPreferenceGetHandler(env=env)
        result = handler.handle({"params": {"action_id": 878, "preference_key": "list_columns"}})
        policy = result["meta"]["preference_contract"]["preference_policy"]
        self.assertFalse(policy["locked"])
        self.assertTrue(policy["allow_visibility"])

    # ------------------------------------------------------- input sanitisation
    def test_unknown_projection_fails_before_preference_query(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env)
        for value in ["raw", None, [], {}, True]:
            result = handler.handle({"params": {"projection": value}})
            self.assertFalse(result["ok"])
        self.assertEqual(env["sc.user.view.preference"].searches, 0)

    def test_get_uses_current_user_model_without_sudo(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceGetHandler(env=env, payload={"model": "x.model"})
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(Preference.sudo_calls, 0)
        self.assertIn(("user_id", "=", 42), Preference.search_domains[0])

    def test_set_uses_current_user_model_without_sudo(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(env=env, payload={"model": "x.model", "preference": {"density": "compact"}})
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(Preference.sudo_calls, 0)
        self.assertEqual(Preference.created_vals["user_id"], 42)
        self.assertEqual(Preference.created_vals["value_json"], {
            "visible_columns": [], "hidden_columns": [], "column_order": [], "column_widths": {},
        })

    def test_get_rejects_invalid_action_id(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env, payload={"action_id": "bad"})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "action_id 无效")
        self.assertEqual(env["sc.user.view.preference"].searches, 0)

    def test_set_rejects_invalid_action_id(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(env=env, payload={"action_id": "bad", "preference": {}})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "action_id 无效")
        self.assertIsNone(Preference.created_vals)

    def test_get_rejects_invalid_params_shape(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env, payload=["model", "x.model"])
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "params 无效")
        self.assertEqual(env["sc.user.view.preference"].searches, 0)

    def test_get_rejects_invalid_view_type(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(env=env, payload={"model": "x.model", "view_type": ["list"]})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "view_type 无效")
        self.assertEqual(env["sc.user.view.preference"].searches, 0)

    def test_set_rejects_invalid_model(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(env=env, payload={"model": ["x.model"], "preference": {}})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "model 无效")
        self.assertIsNone(Preference.created_vals)

    def test_set_sanitizes_list_column_payload(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(
            env=env,
            payload={
                "model": "x.model",
                "preference_key": "list_columns",
                "preference": {
                    "visible_columns": ["name", "name", "  ", None, "manager_id"],
                    "hidden_columns": ["manager_id", "business_nature", "", "business_nature"],
                    "column_order": ["business_nature", "unknown", "name"],
                    "column_widths": {"name": 20, "manager_id": 900, "unknown": 300, "business_nature": "320"},
                    "random_noise": True,
                },
            },
        )
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(Preference.created_vals["value_json"], {
            "visible_columns": ["name", "manager_id"],
            "hidden_columns": ["business_nature"],
            "column_order": ["business_nature", "name"],
            "column_widths": {"name": 80, "manager_id": 640, "business_nature": 320},
        })

    # ------------------------------------------------------------ scene driver
    def test_get_scene_driver_preference_does_not_require_list_action_context(self):
        module = _load_handler()
        env = _env()
        handler = module.UserViewPreferenceGetHandler(
            env=env, payload={"model": "x.model", "preference_key": "scene_ui_driver", "view_type": "list"}
        )
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["preference"], {"kit": ""})
        self.assertEqual(result["meta"]["preference_contract"]["columns"], [])

    def test_set_sanitizes_scene_driver_preference(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(
            env=env,
            payload={"model": "x.model", "preference_key": "scene_ui_driver",
                     "preference": {"kit": "tdesign-modern", "noise": "ignored"}},
        )
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(Preference.created_vals["value_json"], {"kit": "tdesign-modern"})

    def test_set_rejects_unknown_scene_driver_by_clearing_value(self):
        module = _load_handler()
        env = _env()
        Preference = env["sc.user.view.preference"]
        handler = module.UserViewPreferenceSetHandler(
            env=env,
            payload={"model": "x.model", "preference_key": "scene_ui_driver", "preference": {"kit": "unknown-vendor"}},
        )
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(Preference.created_vals["value_json"], {"kit": ""})


if __name__ == "__main__":
    unittest.main()
