# -*- coding: utf-8 -*-
import os

from odoo import api

from ..registry import SeedStep, register
from ...hooks import DEMO_USER_PASSWORD


def _resolve_lang(env, preferred="zh_CN", fallback="en_US"):
    Lang = env["res.lang"].sudo().with_context(active_test=False)
    for code in [preferred, fallback]:
        if not code:
            continue
        lang = Lang.search([("code", "=", code)], limit=1)
        if not lang:
            continue
        if not lang.active:
            lang.write({"active": True})
        return lang.code
    lang = Lang.search([("active", "=", True)], limit=1)
    if lang:
        return lang.code
    lang = Lang.search([], limit=1)
    if lang:
        if not lang.active:
            lang.write({"active": True})
        return lang.code
    return False


def _ensure_user(env, login, name, groups_xmlids, password, lang, tz):
    Users = env["res.users"].sudo()
    user = Users.search([("login", "=", login)], limit=1)
    groups = [env.ref(x) for x in groups_xmlids]
    vals = {
        "name": name,
        "login": login,
        "password": password,
        "tz": tz,
        "company_id": env.ref("base.main_company").id,
        "company_ids": [(6, 0, [env.ref("base.main_company").id])],
        "groups_id": [(6, 0, [g.id for g in groups])],
        "share": False,
        "active": True,
    }
    if lang:
        vals["lang"] = lang
    if user:
        user.write(vals)
    else:
        Users.create(vals)


def run(env):
    password = DEMO_USER_PASSWORD
    lang = _resolve_lang(env, preferred=os.getenv("SC_DEMO_LANG", "zh_CN"))
    tz = "Asia/Shanghai"

    _ensure_user(
        env,
        login="demo_pm",
        name="项目经理岗",
        groups_xmlids=[
            "smart_construction_core.group_sc_cap_project_manager",
            "smart_construction_core.group_sc_cap_contract_read",
            "smart_construction_core.group_sc_cap_cost_read",
            "smart_construction_core.group_sc_cap_purchase_read",
            "smart_construction_core.group_sc_cap_material_read",
            "smart_construction_core.group_sc_cap_settlement_read",
            "smart_construction_core.group_sc_cap_finance_read",
            "smart_construction_core.group_sc_cap_data_read",
        ],
        password=password,
        lang=lang,
        tz=tz,
    )
    _ensure_user(
        env,
        login="demo_finance",
        name="财务经办岗",
        groups_xmlids=[
            "smart_construction_core.group_sc_cap_finance_user",
        ],
        password=password,
        lang=lang,
        tz=tz,
    )
    _ensure_user(
        env,
        login="demo_cost",
        name="成本管理岗",
        groups_xmlids=[
            "smart_construction_core.group_sc_cap_cost_user",
        ],
        password=password,
        lang=lang,
        tz=tz,
    )
    _ensure_user(
        env,
        login="demo_audit",
        name="数据审计岗",
        groups_xmlids=[
            "smart_construction_core.group_sc_cap_data_read",
        ],
        password=password,
        lang=lang,
        tz=tz,
    )
    _ensure_user(
        env,
        login="demo_readonly",
        name="只读查询岗",
        groups_xmlids=[
            "smart_construction_core.group_sc_cap_project_read",
        ],
        password=password,
        lang=lang,
        tz=tz,
    )


register(
    SeedStep(
        name="demo_users",
        description="Create demo users (demo_pm/demo_finance/demo_cost/demo_audit/demo_readonly).",
        run=run,
    )
)


def run_accounting_user(env):
    """Refresh only the accounting demo identity through the normal seed path."""
    _ensure_user(
        env,
        login="sc_demo_accounting_manager",
        name="吴海燕",
        groups_xmlids=[
            "base.group_user",
            "smart_construction_core.group_sc_role_accounting_manager",
        ],
        password=DEMO_USER_PASSWORD,
        lang=_resolve_lang(env, preferred=os.getenv("SC_DEMO_LANG", "zh_CN")),
        tz="Asia/Shanghai",
    )
    user = env["res.users"].search([("login", "=", "sc_demo_accounting_manager")])
    role = env.ref("smart_construction_core.group_sc_role_accounting_manager")
    assert user and user.active and user.company_id == env.ref("base.main_company")
    assert user.sc_user_role_group_ids == role
    assert role.id in user._sc_explicit_group_roots(lock=False)


register(
    SeedStep(
        name="demo_accounting_user",
        description="Refresh only the accounting manager demo role and canonical demo login.",
        run=run_accounting_user,
    )
)


def run_accounting_roles(env):
    """Two ordinary accounting seats, with stable XML identities for rebuilds."""
    import json
    identities = []
    for suffix, label in (("read", "会计只读示例"), ("user", "会计经办示例")):
        login = "sc_demo_accounting_" + suffix
        role_xmlid = "smart_construction_core.group_sc_role_accounting_" + suffix
        _ensure_user(env, login, label, ["base.group_user", role_xmlid],
                     DEMO_USER_PASSWORD, _resolve_lang(env), "Asia/Shanghai")
        user = env["res.users"].search([("login", "=", login)])
        role = env.ref(role_xmlid)
        assert len(user) == 1 and user.active and user.company_id == env.ref("base.main_company")
        assert user.sc_user_role_group_ids == role
        assert role.id in user._sc_explicit_group_roots(lock=False)
        name = "user_sc_accounting_" + suffix + "_demo"
        identity = env["ir.model.data"].search([("module", "=", "smart_construction_demo"), ("name", "=", name)])
        if identity:
            assert identity.model == "res.users" and identity.res_id == user.id
        else:
            env["ir.model.data"].create({"module": "smart_construction_demo", "name": name,
                                       "model": "res.users", "res_id": user.id, "noupdate": False})
        identities.append({"login": login, "uid": user.id,
                           "company": user.company_id.id, "role": role_xmlid})

    from odoo.addons.smart_core.security import data_space_provisioning as provisioning
    provisioning.enroll_data_space_identities(env, purpose="demo")
    for identity in identities:
        print("ACCOUNTING_DEMO_IDENTITY " + json.dumps(identity, ensure_ascii=False))


register(SeedStep(name="demo_accounting_roles", description="Ensure readonly and clerk accounting demo seats.",
                  run=run_accounting_roles))
