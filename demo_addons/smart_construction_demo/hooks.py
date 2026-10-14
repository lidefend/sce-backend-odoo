# -*- coding: utf-8 -*-
import os


ENVIRONMENT_ROLE = "platform_internal_demo"
DEMO_TENANT_KEY = "sc-demo-main"


def guard_demo_scope(env):
    db_name = str(env.cr.dbname or "").strip()
    if not (
        db_name in {"sc_demo", "sc_dev_demo"} or db_name.startswith("sc_demo_")
    ):
        raise RuntimeError("smart_construction_demo requires an authorized demo database")
    if os.environ.get("SC_ENVIRONMENT") != "demo":
        raise RuntimeError("smart_construction_demo requires SC_ENVIRONMENT=demo")
    if os.environ.get("SC_ALLOW_DEMO_DATA") != "1":
        raise RuntimeError("smart_construction_demo requires SC_ALLOW_DEMO_DATA=1")
    if not str(os.environ.get("SC_DEMO_USER_PASSWORD") or "").strip():
        raise RuntimeError("smart_construction_demo requires SC_DEMO_USER_PASSWORD")


def onboard_platform_data_space(env):
    """Onboard this demo database's main company as the demo data space.

    Owner ruling DEMO_IS_FIRST_ONBOARDED_COMPANY: in the demo role the
    environment main company IS the first onboarded business company, so demo
    seeding runs only after that company owns a registration instead of a
    technical-carrier marker. Re-runs are idempotent and the marketing/demo
    lane never manufactures its own registration.
    """
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    provisioning.declare_environment_role(env, ENVIRONMENT_ROLE)
    if not provisioning.onboarded_registrations(env, purpose="demo"):
        provisioning.onboard_environment_main_company(env, tenant_key=DEMO_TENANT_KEY)


def guard_demo_data_space(env):
    """A demo database seeds only against a retired bootstrap marker."""
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    onboard_platform_data_space(env)
    provisioning.assert_business_data_space_ready(env, purpose="demo")
    carriers = provisioning.bootstrap_company_ids(env)
    if carriers:
        raise RuntimeError(
            "smart_construction_demo requires a retired bootstrap marker, still: %s"
            % (carriers,)
        )


def apply_demo_user_passwords(env):
    guard_demo_scope(env)
    guard_demo_data_space(env)
    password = os.environ["SC_DEMO_USER_PASSWORD"].strip()
    rows = env["ir.model.data"].sudo().search(
        [("module", "=", "smart_construction_demo"), ("model", "=", "res.users")]
    )
    user_ids = [row.res_id for row in rows.exists()]
    users = env["res.users"].sudo().with_context(active_test=False).browse(user_ids).exists()
    if users:
        users.write({"password": password})


def pre_init_hook(env):
    guard_demo_scope(env)
    guard_demo_data_space(env)


def post_init_hook(env):
    apply_demo_user_passwords(env)
