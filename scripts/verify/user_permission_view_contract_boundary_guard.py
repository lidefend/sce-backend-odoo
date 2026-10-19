# -*- coding: utf-8 -*-
"""Guard user-permission maintenance view contract boundaries.

Run with:
  make verify.user_permission_view_contract_boundary.guard DB_NAME=<db>

This script expects to be executed by ``odoo shell`` and uses the global
``env`` object. It verifies that the custom frontend contract consumes Odoo
facts with the intended source priority:

  ir.ui.view XML surface facts > contract governance projection > fields_get.
"""

PERSONNEL_ACTION = "smart_construction_core.action_sc_runtime_user_management"
PERSONNEL_FORM_VIEW = "smart_construction_core.view_sc_runtime_user_form"
PERSONNEL_TREE_VIEW = "smart_construction_core.view_sc_runtime_user_tree"
PERSONNEL_SEARCH_VIEW = "smart_construction_core.view_sc_runtime_user_search"
DATA_PERMISSION_ACTION = "smart_construction_core.action_sc_product_data_permission_v1"
DATA_PERMISSION_MENU = "smart_construction_core.menu_sc_product_data_permission_v1"
DATA_PERMISSION_FORM_VIEW = "smart_construction_core.view_sc_data_permission_user_form"

PERSONNEL_FIELD_LABELS = {
    "login": "登录账号",
    "name": "姓名",
    "active": "账号启用",
    "password": "重置密码",
    "phone": "手机号",
    "email": "邮箱",
    "company_id": "主公司",
}

PERSONNEL_GROUP_LABELS = [
    "人员资料",
    "基本资料",
    "组织与岗位",
    "头像与档案",
    "登录与账号",
    "账号管理",
    "账号归属公司",
]

PERSONNEL_FORBIDDEN_FIELDS = {
    "company_ids": "允许公司",
    "sc_user_role_group_ids": "业务角色组",
    "sc_project_member_assignment_ids": "项目成员授权",
}

PERSONNEL_FORBIDDEN_LABELS = {
    "允许公司",
    "主公司与允许公司",
    "授权维护（兼容入口）",
    "业务角色",
    "项目成员授权",
}

DATA_PERMISSION_FIELD_LABELS = {
    "name": "姓名",
    "login": "登录账号",
    "active": "账号启用",
    "company_id": "主公司",
    "company_ids": "允许公司",
}

DATA_PERMISSION_REQUIRED_FIELDS = {
    "sc_user_permission_group_ids",
    "sc_project_member_assignment_ids",
}

DATA_PERMISSION_GROUP_LABELS = [
    "人员身份",
    "主公司与允许公司",
    "业务权限角色",
    "项目数据范围",
]

DATA_PERMISSION_FORBIDDEN_FIELDS = {
    "sc_user_role_group_ids": "业务角色组",
}

DATA_PERMISSION_FORBIDDEN_LABELS = {
    "授权维护（兼容入口）",
    "业务角色",
}

FORBIDDEN_ACTION_LABELS = {
    "创建员工",
    "发送重置密码说明",
    "全部撤销",
    "修改密码",
    "action_totp_disable",
    "action_totp_enable_wizard",
}

def _env():
    return globals()["env"]


def _fail(errors):
    if errors:
        for error in errors:
            print("USER_PERMISSION_VIEW_CONTRACT_BOUNDARY_ERROR=%s" % error)
        raise AssertionError("; ".join(errors))


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _contract_for(login, action_xmlid, render_profile="create"):
    from odoo import api
    from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

    env = _env()
    action = env.ref(action_xmlid)
    user = env["res.users"].with_context(active_test=False).search([("login", "=", login)], limit=1)
    if not user:
        raise AssertionError("missing user: %s" % login)
    user_env = api.Environment(env.cr, user.id, dict(env.context, lang="zh_CN"))
    params = {
        "op": "action_open",
        "action_id": action.id,
        "client_type": "web_pc",
        "delivery_profile": "full",
        "render_profile": render_profile,
        "contract_surface": "user",
        "source_mode": "governance_pipeline",
    }
    if render_profile != "create":
        params["record_id"] = user.id
        params["res_id"] = user.id
    result = UiContractV2Handler(user_env, payload={"params": params}).handle(params, {})
    envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    if not envelope.get("ok", True):
        raise AssertionError("ui.contract.v2 failed for %s: %s" % (login, envelope))
    return envelope.get("data") or {}


def _contract_login(preferred="weihuguanliyuan"):
    env = _env()
    group = env.ref(
        "smart_construction_core.group_sc_cap_business_config_admin",
        raise_if_not_found=False,
    )
    if not group:
        raise AssertionError(
            "read-only guard requires group_sc_cap_business_config_admin; "
            "missing prerequisites must fail instead of creating fixture users"
        )
    users = env["res.users"].sudo().with_context(active_test=False)
    domain = [("groups_id", "in", [group.id]), ("share", "=", False), ("active", "=", True)]
    candidate = users.search(domain + [("login", "=", preferred)], limit=1)
    if not candidate:
        candidate = users.search(domain, limit=1)
    if candidate:
        return candidate.login
    raise AssertionError(
        "read-only guard requires an existing active business config admin; "
        "no account was created"
    )


def _field_labels(contract):
    labels = {}
    containers = ((contract.get("layoutContract") or {}).get("containerTree") or [])
    form_structure = contract.get("formStructureContract") or []
    form_layout = (((contract.get("views") or {}).get("form") or {}).get("layout") or [])
    for row in list(_walk(containers)) + list(_walk(form_structure)) + list(_walk(form_layout)):
        code = row.get("fieldCode") or row.get("field_code") or row.get("name")
        if not isinstance(code, str):
            continue
        label = row.get("label") or row.get("string") or ""
        if label:
            labels.setdefault(code, set()).add(label)
    return labels


def _field_codes(contract):
    codes = set()
    containers = ((contract.get("layoutContract") or {}).get("containerTree") or [])
    form_layout = (((contract.get("views") or {}).get("form") or {}).get("layout") or [])
    for row in list(_walk(containers)) + list(_walk(form_layout)):
        code = row.get("fieldCode") or row.get("field_code")
        if not code and str(row.get("type") or row.get("kind") or "").lower() == "field":
            code = row.get("name")
        if isinstance(code, str) and code:
            codes.add(code)
    return codes


def _layout_labels(contract):
    labels = []
    containers = ((contract.get("layoutContract") or {}).get("containerTree") or [])
    form_layout = (((contract.get("views") or {}).get("form") or {}).get("layout") or [])
    for row in list(_walk(containers)) + list(_walk(form_layout)):
        label = row.get("label") or row.get("title") or row.get("string")
        if isinstance(label, str) and label:
            labels.append(label)
    return labels


def _actions_in_contract(contract):
    labels = []
    for row in _walk(contract):
        kind = str(row.get("kind") or row.get("type") or row.get("buttonType") or "").lower()
        label = row.get("label") or row.get("title") or row.get("string") or row.get("name")
        if isinstance(label, str) and label and (
            "action" in kind
            or row.get("methodName")
            or row.get("buttonType")
            or row.get("payload")
            or row.get("action")
        ):
            labels.append(label)
    return labels


def _check_xml_view():
    env = _env()
    errors = []
    personnel_arch = env.ref(PERSONNEL_FORM_VIEW).arch_db or ""
    personnel_surfaces = {
        PERSONNEL_FORM_VIEW: personnel_arch,
        PERSONNEL_TREE_VIEW: env.ref(PERSONNEL_TREE_VIEW).arch_db or "",
        PERSONNEL_SEARCH_VIEW: env.ref(PERSONNEL_SEARCH_VIEW).arch_db or "",
    }
    for label in PERSONNEL_FIELD_LABELS.values():
        if ('string="%s"' % label) not in personnel_arch:
            errors.append("personnel form XML missing field string: %s" % label)
    for label in PERSONNEL_GROUP_LABELS:
        if ('string="%s"' % label) not in personnel_arch:
            errors.append("personnel form XML missing group string: %s" % label)
    for field_name, label in PERSONNEL_FORBIDDEN_FIELDS.items():
        for xmlid, surface in personnel_surfaces.items():
            if ('name="%s"' % field_name) in surface:
                errors.append("personnel surface %s still carries field %s" % (xmlid, field_name))
            if ('string="%s"' % label) in surface:
                errors.append("personnel surface %s still carries label %s" % (xmlid, label))
    for label in PERSONNEL_FORBIDDEN_LABELS:
        if ('string="%s"' % label) in personnel_arch:
            errors.append("personnel form XML still carries label: %s" % label)

    permission_arch = env.ref(DATA_PERMISSION_FORM_VIEW).arch_db or ""
    for field_name in DATA_PERMISSION_FIELD_LABELS:
        if ('name="%s"' % field_name) not in permission_arch:
            errors.append("data permission form XML missing field: %s" % field_name)
    for label in DATA_PERMISSION_GROUP_LABELS:
        if ('string="%s"' % label) not in permission_arch:
            errors.append("data permission form XML missing group string: %s" % label)
    for field_name in DATA_PERMISSION_FORBIDDEN_FIELDS:
        if ('name="%s"' % field_name) in permission_arch:
            errors.append("data permission form XML still carries field: %s" % field_name)
    for label in DATA_PERMISSION_FORBIDDEN_LABELS:
        if ('string="%s"' % label) in permission_arch:
            errors.append("data permission form XML still carries label: %s" % label)

    _fail(errors)
    print("USER_PERMISSION_XML_VIEWS=personnel:%s,data_permission:%s" % (
        env.ref(PERSONNEL_FORM_VIEW).id,
        env.ref(DATA_PERMISSION_FORM_VIEW).id,
    ))


def _check_entry_authority():
    env = _env()
    business_admin = env.ref("smart_construction_core.group_sc_cap_business_config_admin")
    industry_admin = env.ref("smart_construction_core.group_sc_cap_config_admin")
    errors = []
    for xmlid in (DATA_PERMISSION_MENU, DATA_PERMISSION_ACTION):
        record = env.ref(xmlid)
        if business_admin not in record.groups_id:
            errors.append("%s must remain reachable by business config admin" % xmlid)
        if industry_admin not in record.groups_id:
            errors.append("%s must remain reachable by industry config admin" % xmlid)
    _fail(errors)
    print("USER_PERMISSION_ENTRY_AUTHORITY=%s,%s groups=config_admin,business_config_admin" % (
        DATA_PERMISSION_MENU,
        DATA_PERMISSION_ACTION,
    ))


def _check_acl():
    env = _env()
    group = env.ref("smart_construction_core.group_sc_cap_business_config_admin")
    model = env["ir.model"]._get("res.users")
    acl = env["ir.model.access"].search([("model_id", "=", model.id), ("group_id", "=", group.id)], limit=1)
    errors = []
    if not acl:
        errors.append("missing res.users ACL for business config admin")
    else:
        if not (acl.perm_read and acl.perm_write and acl.perm_create):
            errors.append(
                "business config admin res.users ACL must be read/write/create: read=%s write=%s create=%s"
                % (acl.perm_read, acl.perm_write, acl.perm_create)
            )
        if acl.perm_unlink:
            errors.append("business config admin must not unlink res.users")
    _fail(errors)
    print("USER_PERMISSION_ACL=%s read=%s write=%s create=%s unlink=%s" % (acl.name, acl.perm_read, acl.perm_write, acl.perm_create, acl.perm_unlink))


def _maintainable_user_errors(users, *, company_ids, privileged_ids, internal_id, template_id):
    """Check declared eligibility, never infer a person's legitimacy from their name."""
    errors = []
    if not users:
        errors.append("personnel acceptance requires at least one eligible existing user")
    for user in users:
        groups = set(user.groups_id.ids)
        if (user.id == template_id or user.share or not user.login
                or user.company_id.id not in company_ids
                or internal_id not in groups or groups & privileged_ids):
            errors.append("runtime user action leaked an ineligible user id=%s" % user.id)
    return errors


def _check_action_domain(login):
    from odoo import api
    from odoo.tools.safe_eval import safe_eval

    env = _env()
    actor = env["res.users"].search([("login", "=", login)], limit=1)
    if not actor:
        raise AssertionError("missing domain-check actor")
    actor_env = api.Environment(env.cr, actor.id, dict(env.context, allowed_company_ids=actor.company_ids.ids))
    action = actor_env.ref(PERSONNEL_ACTION)
    domain = safe_eval(action.domain or "[]") if isinstance(action.domain, str) else (action.domain or [])
    users_model = actor_env["res.users"]
    users = users_model.with_context(active_test=False).search(domain)
    template = actor_env.ref("base.default_user", raise_if_not_found=False)
    internal = actor_env.ref("base.group_user")
    privileged = users_model._sc_runtime_privileged_groups()
    _fail(_maintainable_user_errors(
        users, company_ids=set(actor.company_ids.ids), privileged_ids=set(privileged.ids),
        internal_id=internal.id, template_id=template.id if template else None,
    ))
    candidates = users_model.sudo().with_context(active_test=False).search([
        ("company_id", "in", actor.company_ids.ids),
    ])
    expected = {u.id for u in candidates if not _maintainable_user_errors(
        [u], company_ids=set(actor.company_ids.ids), privileged_ids=set(privileged.ids),
        internal_id=internal.id, template_id=template.id if template else None,
    )}
    _fail(["personnel action omitted eligible existing users"] if expected - set(users.ids) else [])
    print("USER_PERMISSION_ACTION_DOMAIN_VISIBLE_COUNT=%s" % len(users))
    print("USER_PERMISSION_EXISTING_INACTIVE_COUNT=%s" % len(users.filtered(lambda u: not u.active)))


def _check_contract(
    login,
    action_xmlid,
    expected_field_labels,
    expected_group_labels,
    *,
    required_fields=(),
    forbidden_fields=(),
    forbidden_labels=(),
    render_profile="create",
):
    contract = _contract_for(login, action_xmlid, render_profile=render_profile)
    scope = "%s/%s" % (login, action_xmlid)
    errors = []
    field_labels = _field_labels(contract)
    field_codes = _field_codes(contract)
    for field_name, expected_label in expected_field_labels.items():
        actual = field_labels.get(field_name, set())
        if expected_label not in actual:
            errors.append(
                "field %s label expected=%s actual=%s [%s]"
                % (field_name, expected_label, ",".join(sorted(actual)), scope)
            )

    labels = _layout_labels(contract)
    for group_label in expected_group_labels:
        if group_label not in labels:
            errors.append("missing group label in contract for %s: %s" % (scope, group_label))

    for field_name in required_fields:
        if field_name not in field_codes:
            errors.append("missing required field in contract for %s: %s" % (scope, field_name))
    for field_name, field_label in forbidden_fields.items():
        if field_name in field_codes:
            errors.append("contract still carries forbidden field %s for %s" % (field_name, scope))
        if field_label and field_label in labels:
            errors.append("contract still carries forbidden label %s for %s" % (field_label, scope))
    for label in forbidden_labels:
        if label in labels:
            errors.append("contract still carries forbidden label %s for %s" % (label, scope))

    form = (((contract.get("meta") or {}).get("compat") or {}).get("ui_contract") or {}).get("ui_contract", {}).get("views", {}).get("form", {})
    statusbar = form.get("statusbar") if isinstance(form, dict) else {}
    statusbar_nodes = []
    if isinstance(statusbar, dict) and (statusbar.get("field") or statusbar.get("states")):
        statusbar_nodes.append(statusbar)
    if statusbar_nodes:
        errors.append("user permission form contract leaked native statusbar for %s" % scope)

    action_labels = set(_actions_in_contract(contract))
    leaked = sorted(FORBIDDEN_ACTION_LABELS & action_labels)
    if leaked:
        errors.append("user permission form contract leaked native actions for %s: %s" % (scope, leaked))

    global_status = (contract.get("statusContract") or {}).get("globalStatus") or {}
    if global_status.get("pageAuth") != "edit":
        errors.append("contract pageAuth for %s expected=edit actual=%s" % (scope, global_status.get("pageAuth")))

    _fail(errors)
    print("USER_PERMISSION_CONTRACT=%s pageAuth=%s labels=%s" % (
        scope,
        global_status.get("pageAuth"),
        ",".join("/".join(sorted(field_labels.get(name, set()))) for name in expected_field_labels),
    ))


def main():
    print("USER_PERMISSION_GUARD_MODE=read_only")
    _check_xml_view()
    _check_entry_authority()
    _check_acl()
    contract_login = _contract_login()
    _check_action_domain(contract_login)
    _check_contract(
        contract_login,
        PERSONNEL_ACTION,
        PERSONNEL_FIELD_LABELS,
        PERSONNEL_GROUP_LABELS,
        forbidden_fields=PERSONNEL_FORBIDDEN_FIELDS,
        forbidden_labels=PERSONNEL_FORBIDDEN_LABELS,
    )
    _check_contract(
        "admin",
        PERSONNEL_ACTION,
        PERSONNEL_FIELD_LABELS,
        PERSONNEL_GROUP_LABELS,
        forbidden_fields=PERSONNEL_FORBIDDEN_FIELDS,
        forbidden_labels=PERSONNEL_FORBIDDEN_LABELS,
    )
    _check_contract(
        contract_login,
        DATA_PERMISSION_ACTION,
        DATA_PERMISSION_FIELD_LABELS,
        DATA_PERMISSION_GROUP_LABELS,
        required_fields=DATA_PERMISSION_REQUIRED_FIELDS,
        forbidden_fields=DATA_PERMISSION_FORBIDDEN_FIELDS,
        forbidden_labels=DATA_PERMISSION_FORBIDDEN_LABELS,
        render_profile="edit",
    )
    print("[user_permission_view_contract_boundary_guard] PASS")


def _rehearse_candidate_views():
    """Temporary metadata-only rehearsal; never a deployed-view acceptance receipt."""
    import hashlib
    import json
    import os
    from pathlib import Path
    from xml.etree import ElementTree as ET
    from psycopg2 import sql
    from odoo.addons import smart_construction_core

    env = _env()
    assert env.cr.dbname == "sc_dev_demo", "requires exact local.dev database"
    source = Path(smart_construction_core.__file__).parent / "views/support/runtime_user_management_views.xml"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == os.environ.get("SC_ACCEPTANCE_USER_PERMISSION_SOURCE_SHA256"), "candidate XML identity mismatch"
    views = (PERSONNEL_FORM_VIEW, PERSONNEL_TREE_VIEW, PERSONNEL_SEARCH_VIEW)
    roots = ET.parse(source).getroot()
    replacements = {}
    for xmlid in views:
        record = roots.find("record[@id='%s']" % xmlid.split(".", 1)[1])
        assert record is not None and record.get("model") == "ir.ui.view"
        arch = record.find("field[@name='arch']")
        assert arch is not None and len(arch) == 1
        replacements[xmlid] = ET.tostring(arch[0], encoding="unicode")

    tables = [env[model]._table for model in (
        "res.users", "res.company", "res.partner", "hr.employee", "res.groups",
        "sc.project.member.assignment", "mail.followers", "sc.tenant.company.registration",
    )]
    tables += [env["res.users"]._fields[name].relation for name in ("groups_id", "company_ids")]

    def facts():
        result = {}
        for table in sorted(set(tables)):
            env.cr.execute(sql.SQL("SELECT count(*), md5(COALESCE(string_agg(row_to_json(t)::text, '' ORDER BY row_to_json(t)::text), '')) FROM {} t").format(sql.Identifier(table)))
            result[table] = env.cr.fetchone()
        return result

    env.cr.rollback()
    env.invalidate_all(flush=False)
    before = facts()
    original = {xmlid: env.ref(xmlid).with_context(lang=None).arch_db for xmlid in views}
    commit = env.cr.commit
    def reject_commit(*args, **kwargs):
        raise AssertionError("candidate view rehearsal forbids commit")
    env.cr.commit = reject_commit
    try:
        for xmlid, arch in replacements.items():
            env.ref(xmlid).with_context(lang=None).write({"arch_db": arch})
        main()
        env.flush_all()
        assert facts() == before, "business or authorization facts changed during rehearsal"
    finally:
        env.cr.rollback()
        env.cr.commit = commit
        env.invalidate_all(flush=False)
        assert facts() == before, "business fact restoration mismatch"
        assert {xmlid: env.ref(xmlid).with_context(lang=None).arch_db for xmlid in views} == original, "view restoration mismatch"
        print("USER_PERMISSION_REHEARSAL_RESTORED=true")
    print("USER_PERMISSION_REHEARSAL=" + json.dumps({
        "status": "passed", "database": env.cr.dbname, "source_sha256": digest,
        "views": list(views), "fact_tables": sorted(before), "facts_unchanged": True,
        "views_restored": True, "deployed": False,
    }, ensure_ascii=False))


if "env" in globals():
    import os
    if os.environ.get("SC_ACCEPTANCE_USER_PERMISSION_REHEARSE") == "1":
        _rehearse_candidate_views()
    else:
        main()
