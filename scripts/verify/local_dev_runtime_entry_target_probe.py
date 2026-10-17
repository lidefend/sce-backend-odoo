"""Read-only runtime probe for declared admin-surface entry targets (P4 diagnostic).

The frontend may route to an admin surface only from a contract-declared
``entry_target``. This probe reads the real published route authority on the
registered ``sc_dev_demo`` database and proves that the two declared surfaces
(``business_config`` and ``menu_config``) reach the effective authority with
their declared surface and route, for both a configuration administrator and a
full-capability principal.

Read-only: commit is refused and the transaction is rolled back. The pure
helpers are importable without Odoo so the non-zero unit test can exercise the
violation rules; the executable part only runs when ``env`` is present.
"""
import json

DATABASE = "sc_dev_demo"
PRINCIPALS = (21, 55)
EXPECTED_SURFACES = {
    "business_config": "/admin/business-config",
    "menu_config": "/admin/menu-config",
}
# The demo business-configuration administrator is the principal that declares
# both surfaces; the full-capability principal is observed for the workbench
# only. Visibility beyond a principal's declared set is reported, not failed.
EXPECTED_BY_PRINCIPAL = {
    21: EXPECTED_SURFACES,
    55: {"business_config": EXPECTED_SURFACES["business_config"]},
}
REQUIRED_ROOT_MENU_SURFACE = "business_config"


def _collect_admin_surfaces(authority):
    found = {}
    for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
        rows = authority.get(bucket) if isinstance(authority, dict) else None
        for row in rows or []:
            target = row.get("entry_target") if isinstance(row, dict) else None
            if not isinstance(target, dict) or str(target.get("type") or "").strip() != "admin_surface":
                continue
            surface = str(target.get("surface") or "").strip()
            found.setdefault(surface, {
                "bucket": bucket,
                "action_xmlid": str(row.get("action_xmlid") or "").strip(),
                "menu_id": row.get("menu_id"),
                "action_id": row.get("action_id"),
                "route": str(target.get("route") or "").strip(),
                "root_menu_xmlid": str(target.get("root_menu_xmlid") or "").strip(),
            })
    return found


def _violations(found, expected=None, reject_extra=True):
    expected = EXPECTED_SURFACES if expected is None else expected
    violations = []
    for surface, route in expected.items():
        row = found.get(surface)
        if not row:
            violations.append(f"missing admin_surface={surface}")
            continue
        if row["route"] != route:
            violations.append(f"{surface} route={row['route'] or '<empty>'} expected={route}")
        if surface == REQUIRED_ROOT_MENU_SURFACE and not row["root_menu_xmlid"]:
            violations.append(f"{surface} missing root_menu_xmlid")
    for surface, row in found.items():
        if reject_extra and surface not in expected:
            violations.append(f"undeclared admin_surface={surface or '<empty>'}")
        if not row["route"].startswith("/"):
            violations.append(f"{surface} route is not absolute: {row['route'] or '<empty>'}")
    return violations


def _denied_rows(authority):
    rows = authority.get("denied_actions") if isinstance(authority, dict) else None
    return [row for row in rows or [] if isinstance(row, dict)]


def _denial_violations(authority):
    """A denial record must stay an explicit, identifiable denial.

    The backend publishes menu-only denials (a declared menu carrier that was
    not delivered): ``action_id == 0`` and an empty ``action_xmlid`` but a real
    ``menu_xmlid``.  Consumers accept that shape only when ``route_kind`` says
    DENIED, so the probe pins both invariants on the published payload.
    """
    violations = []
    for index, row in enumerate(_denied_rows(authority)):
        if str(row.get("route_kind") or "").strip() != "DENIED":
            violations.append(
                f"denied_actions[{index}] route_kind={row.get('route_kind') or '<empty>'}"
            )
        if not (str(row.get("action_xmlid") or "").strip() or str(row.get("menu_xmlid") or "").strip()):
            violations.append(f"denied_actions[{index}] has no action_xmlid or menu_xmlid")
    return violations


def _partial_declaration_violations(build_entry_target):
    """A partial ``sc_web_surface`` / ``sc_web_route`` declaration is a gap.

    It must project to an explicit ``admin_surface`` target with the missing
    field empty, so the consumer fails closed instead of degrading to the
    compatibility path.  A plain action that declares no surface at all keeps
    the compatibility path.
    """
    violations = []
    route_only = build_entry_target("{'sc_web_route': '/admin/business-config'}")
    if (
        route_only.get("type") != "admin_surface"
        or route_only.get("surface") != ""
        or route_only.get("route") != "/admin/business-config"
    ):
        violations.append("route-only declaration did not project to an incomplete admin_surface")
    surface_only = build_entry_target("{'sc_web_surface': 'business_config'}")
    if (
        surface_only.get("type") != "admin_surface"
        or surface_only.get("surface") != "business_config"
        or surface_only.get("route") != ""
    ):
        violations.append("surface-only declaration did not project to an incomplete admin_surface")
    if build_entry_target("{'search_default_visible': 1}") != {}:
        violations.append("plain action without a surface declaration left the compatibility path")
    return violations


def _probe(env):
    assert env.cr.dbname == DATABASE, "registered local.dev database required"
    env.cr.rollback()
    original_commit = env.cr.commit

    def refuse_commit(*args, **kwargs):
        raise RuntimeError("entry-target probe forbids commit")

    env.cr.commit = refuse_commit
    try:
        from odoo.addons.smart_core.core.navigation_entry_target import build_web_surface_entry_target
        from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority

        principals = []
        all_found = {}
        for uid in PRINCIPALS:
            principal_env = env(user=env["res.users"].browse(uid))
            authority = build_runtime_route_authority(principal_env)
            found = _collect_admin_surfaces(authority)
            denied = _denied_rows(authority)
            problems = _violations(found, EXPECTED_BY_PRINCIPAL.get(uid, EXPECTED_SURFACES), reject_extra=False)
            problems.extend(_denial_violations(authority))
            principals.append({
                "uid": uid,
                "login": principal_env.user.login,
                "admin_surfaces": found,
                "denied_count": len(denied),
                "menu_only_denials": [
                    str(row.get("menu_xmlid") or "").strip()
                    for row in denied
                    if not str(row.get("action_xmlid") or "").strip()
                ],
                "violations": problems,
            })
            for surface, row in found.items():
                all_found.setdefault(surface, row)
        violations = _violations(all_found)
        partial_declaration_violations = _partial_declaration_violations(build_web_surface_entry_target)
        violations.extend(partial_declaration_violations)
        report = {
            "status": "passed" if not violations else "failed",
            "database": DATABASE,
            "expected_surfaces": EXPECTED_SURFACES,
            "principals": principals,
            "partial_declaration_violations": partial_declaration_violations,
            "violations": violations,
            "limitations": [
                "two declared demo principals; bounded diagnostic, not a role matrix",
                "reads the published authority builder, not a deployed target environment",
            ],
        }
        env.cr.rollback()
        env.cr.commit = original_commit
        return report
    finally:
        env.cr.rollback()
        env.cr.commit = original_commit


if "env" in globals():
    _report = _probe(env)
    print("CONTRACT_ENTRY_TARGET_PROBE_REPORT " + json.dumps(_report, sort_keys=True, default=str))
    if _report["status"] != "passed":
        raise SystemExit(1)
