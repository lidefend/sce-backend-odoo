# -*- coding: utf-8 -*-
import os


ENVIRONMENT_ROLE = "platform_internal_demo"
DEMO_TENANT_KEY = "sc-demo-main"
# The showcase deliberately uses one simple password for every seeded demo
# identity. Keeping it in the carrier, rather than only in the host secret,
# makes a rebuild or reseed reproduce the published demo login.
DEMO_USER_PASSWORD = "123456"


def assert_demo_seed_principal(env):
    """Only the managed installation/shell principal may delegate demo actions."""
    from odoo import SUPERUSER_ID
    from odoo.exceptions import AccessError

    if env.uid != SUPERUSER_ID or not env.su:
        raise AccessError("DEMO_SEED_PRINCIPAL_REQUIRED")


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

    Onboarding is not complete with the registration row: the demo's operating
    identities must also be enrolled into the non-customer data realm, or the
    data space exists and nobody can read it. Identity enrollment is therefore
    part of this same idempotent act, never a per-user assembly in demo data.
    """
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    provisioning.declare_environment_role(env, ENVIRONMENT_ROLE)
    if not provisioning.onboarded_registrations(env, purpose="demo"):
        provisioning.onboard_environment_main_company(env, tenant_key=DEMO_TENANT_KEY)
    return provisioning.enroll_data_space_identities(env, purpose="demo")


def guard_demo_data_space(env):
    """A demo database seeds only against a retired bootstrap marker."""
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    onboard_platform_data_space(env)
    provisioning.assert_business_data_space_ready(env, purpose="demo")
    provisioning.assert_data_space_identities_enrolled(env, purpose="demo")
    carriers = provisioning.bootstrap_company_ids(env)
    if carriers:
        raise RuntimeError(
            "smart_construction_demo requires a retired bootstrap marker, still: %s"
            % (carriers,)
        )


def apply_demo_user_passwords(env):
    guard_demo_scope(env)
    guard_demo_data_space(env)
    rows = env["ir.model.data"].sudo().search(
        [("module", "=", "smart_construction_demo"), ("model", "=", "res.users")]
    )
    user_ids = [row.res_id for row in rows.exists()]
    users = env["res.users"].sudo().with_context(active_test=False).browse(user_ids).exists()
    if users:
        users.write({"password": DEMO_USER_PASSWORD})


def pre_init_hook(env):
    guard_demo_scope(env)
    guard_demo_data_space(env)


def post_init_hook(env):
    apply_demo_user_passwords(env)
