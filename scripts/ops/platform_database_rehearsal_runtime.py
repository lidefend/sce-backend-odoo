"""In-container execution for the fixed isolated P4 database rehearsal."""
from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import uuid

import psycopg2
from psycopg2 import sql

from scripts.ops import platform_database_lifecycle_apply as lifecycle
from scripts.ops import platform_database_register as registration
from scripts.ops.platform_database_receipt import validate_success

SPEC = Path("/workspace/config/platform_database_rehearsal.json")
AUTHORITY = Path("/authority")
EVIDENCE = Path("/evidence")


def spec():
    declared = json.loads(SPEC.read_text())
    if declared != json.loads((AUTHORITY / "identity.json").read_text()):
        raise ValueError("REHEARSAL_DECLARATION_DRIFT")
    return declared


def validate_maintenance_identity(declared, passwords, maintenance):
    expected = {"host": "db", "port": 5432, "user": declared["maintenance_role"],
                "password": passwords["maintenance"]}
    if {key: value for key, value in maintenance.items() if key != "cluster_system_identifier"} != expected:
        raise ValueError("REHEARSAL_MAINTENANCE_CREDENTIAL_DRIFT")


def connect(which, database=None):
    declared = spec()
    passwords = json.loads((AUTHORITY / "credentials.json").read_text())
    validate_maintenance_identity(declared, passwords, json.loads((AUTHORITY / "maintenance.json").read_text()))
    db = database or ("postgres" if which == "maintenance" else declared[which + "_database"])
    connection = psycopg2.connect(host="db", port=5432, dbname=db,
                                  user=declared[which + "_role"], password=passwords[which], connect_timeout=5)
    connection.autocommit = True
    return connection


def scalar(connection, query, args=()):
    with connection.cursor() as cursor:
        cursor.execute(query, args)
        return cursor.fetchone()[0]


def catalog_identity(connection):
    declared = spec()
    return {
        "project": declared["project"],
        "cluster_system_identifier": str(scalar(connection, "SELECT system_identifier FROM pg_control_system()")),
        "control_database": declared["control_database"], "target_database": declared["target_database"],
    }


def verify_binding(connection):
    observed = catalog_identity(connection)
    if observed != json.loads((EVIDENCE / "cluster.json").read_text()):
        raise ValueError("REHEARSAL_CLUSTER_BINDING_MISMATCH")
    declared = spec()
    for which in ("control", "target"):
        owner = scalar(connection, "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",
                       (declared[which + "_database"],))
        if owner != declared[which + "_role"]:
            raise ValueError("REHEARSAL_DATABASE_OWNER_MISMATCH")
    return observed


def bootstrap():
    declared = spec()
    passwords = json.loads((AUTHORITY / "credentials.json").read_text())
    with closing(connect("maintenance")) as connection:
        connection.autocommit = True
        marker = EVIDENCE / "cluster.json"
        if marker.exists():
            verify_binding(connection)
            return
        for which in ("control", "target"):
            if scalar(connection, "SELECT count(*) FROM pg_database WHERE datname=%s", (declared[which + "_database"],)):
                raise ValueError("REHEARSAL_UNBOUND_EXISTING_DATABASE")
            if scalar(connection, "SELECT count(*) FROM pg_roles WHERE rolname=%s", (declared[which + "_role"],)):
                raise ValueError("REHEARSAL_UNBOUND_EXISTING_ROLE")
        with connection.cursor() as cursor:
            for which in ("control", "target"):
                role, database = declared[which + "_role"], declared[which + "_database"]
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %s").format(sql.Identifier(role)), (passwords[which],))
                cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(database), sql.Identifier(role)))
                cursor.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        marker.write_text(json.dumps(catalog_identity(connection), indent=2) + "\n")
        verify_binding(connection)
    print("[platform.database.rehearsal] bootstrap PASS isolated owners and cluster bound")


def install():
    with closing(connect("maintenance")) as connection:
        verify_binding(connection)
    with closing(connect("control")) as connection:
        exists = scalar(connection, "SELECT to_regclass('public.ir_module_module') IS NOT NULL")
        if exists and scalar(connection, "SELECT count(*) FROM ir_module_module WHERE name='smart_core' AND state='installed'") == 1:
            print("[platform.database.rehearsal] platform installation already present")
            return
    subprocess.run(["odoo", "-c", "/authority/control.conf", "-i", "smart_core", "--without-demo=all",
                    "--stop-after-init", "--no-http"], check=True)


def expected_request(declared, operation, reason):
    if operation == "register":
        return {
            registration.TARGET_ENV: declared["target_database"],
            registration.ROLE_ENV: declared["target_environment_role"],
            registration.PURPOSE_ENV: declared["target_data_purpose"],
            registration.TENANT_ENV: declared["tenant"],
            registration.DBFILTER_ENV: "^" + declared["target_database"] + "$",
            registration.REASON_ENV: reason,
        }
    return {lifecycle.TARGET_ENV: declared["target_database"], lifecycle.OPERATION_ENV: operation,
            lifecycle.REASON_ENV: reason}


def verify_audit_receipt(audit, receipt, declared):
    identity = audit.result["operation_request"]
    module = registration if audit.operation == "register" else lifecycle
    if (receipt.get("operation_id") != audit.id or receipt.get("registration_readback") != audit.result
            or receipt.get("entry") != module.ENTRY or receipt.get("db_name") != declared["target_database"]
            or receipt.get("operation", "register") != audit.operation):
        raise ValueError("REHEARSAL_RECEIPT_AUDIT_MISMATCH")
    validate_success(receipt, identity["execution_id"],
                     expected_request(declared, audit.operation, identity["reason"]))


def run_operation(env, operation):
    declared = spec()
    execution_id = uuid.uuid4().hex
    if operation == "register":
        module = registration
        request = {
            module.CONFIRM_ENV: module.CONFIRM_VALUE, module.TARGET_ENV: declared["target_database"],
            module.ROLE_ENV: declared["target_environment_role"], module.PURPOSE_ENV: declared["target_data_purpose"],
            module.TENANT_ENV: declared["tenant"], module.DBFILTER_ENV: "^" + declared["target_database"] + "$",
            module.REASON_ENV: "Owner-authorized isolated physical lifecycle rehearsal",
        }
    else:
        module = lifecycle
        request = {module.CONFIRM_ENV: module.CONFIRM_VALUE, module.TARGET_ENV: declared["target_database"],
                   module.OPERATION_ENV: operation, module.REASON_ENV: "Owner-authorized isolated " + operation}
    request.update(PLATFORM_DATABASE_EXECUTION_ID=execution_id)
    request[module.OUTPUT_ENV] = str(EVIDENCE / (execution_id + ".json"))
    result = module.run(env, request)
    bound = {key: value for key, value in request.items()
             if key.startswith("PLATFORM_DATABASE_") and key not in ("PLATFORM_DATABASE_EXECUTION_ID", module.OUTPUT_ENV)}
    validate_success(json.loads(Path(request[module.OUTPUT_ENV]).read_text()), execution_id, bound)
    return result


def assert_target_connectable():
    with closing(connect("target")) as connection:
        if scalar(connection, "SELECT 1") != 1:
            raise ValueError("TARGET_CONNECTION_FAILED")


def _restore_admission_after_audit():
    """Emergency recovery restores admission only, never invents native success."""
    with closing(connect("maintenance")) as connection:
        binding = verify_binding(connection)
        with closing(connect("maintenance", spec()["control_database"])) as audit_connection, audit_connection.cursor() as cursor:
            cursor.execute("SELECT lifecycle_state FROM sc_platform_database_registration WHERE db_name=%s", (spec()["target_database"],))
            row = cursor.fetchone()
        if row and row[0] not in ("declared", "provisioned", "active"):
            raise ValueError("RECOVERY_REQUIRES_NATIVE_RESUME")
        before = lifecycle.database_facts(connection, spec()["target_database"])
        lifecycle.apply_connection_effect(connection, spec()["target_database"], "allow_connections")
        after = lifecycle.database_facts(connection, spec()["target_database"])
        lifecycle.assert_effect_reached("allow_connections", after)
    assert_target_connectable()
    (EVIDENCE / ("recovery-" + uuid.uuid4().hex + ".json")).write_text(json.dumps({
        "binding": binding, "before": before, "after": after,
        "scope": "connection_admission_only", "native_audit_reconciliation_required": True,
        "terminated_transactions_restored": False,
    }, indent=2) + "\n")


def recover(env):
    """Reconcile the committed native state before choosing a recovery action."""
    if env.cr.dbname != spec()["control_database"]:
        raise ValueError("RECOVERY_CONTROL_IDENTITY_MISMATCH")
    with closing(connect("maintenance")) as connection:
        verify_binding(connection)
    with closing(connect("maintenance", spec()["control_database"])) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT lifecycle_state FROM sc_platform_database_registration WHERE db_name=%s",
                       (spec()["target_database"],))
        row = cursor.fetchone()
    env.invalidate_all()
    if row and row[0] == "suspended":
        run_operation(env, "resume")
    elif row and row[0] == "retired":
        raise ValueError("RECOVERY_RETIRED_TARGET_REFUSED")
    else:
        _restore_admission_after_audit()
    assert_target_connectable()


def exercise(env, resume=False):
    declared = spec()
    if env.cr.dbname != declared["control_database"]:
        raise ValueError("REHEARSAL_CONTROL_DATABASE_MISMATCH")
    with closing(connect("maintenance")) as connection:
        binding = verify_binding(connection)
    Registry = env["sc.platform.database.registration"]
    existing = Registry.search([("db_name", "=", declared["target_database"])])
    previous = []
    if existing:
        if not resume or len(existing) != 1 or existing.lifecycle_state != "active":
            raise ValueError("REHEARSAL_ALREADY_EXECUTED_RECONCILE_EXISTING_EVIDENCE")
        if (existing.tenant_key != declared["tenant"] or existing.data_purpose != declared["target_data_purpose"]
                or existing.environment_role != declared["target_environment_role"]):
            raise ValueError("REHEARSAL_EXISTING_REGISTRATION_IDENTITY_MISMATCH")
        audits = existing.operation_ids.sorted("id")
        if audits.mapped("operation") != ["register", "provision", "activate"]:
            raise ValueError("REHEARSAL_RESUME_PREFIX_MISMATCH")
        for audit in audits:
            execution_id = audit.result["operation_request"]["execution_id"]
            receipt = json.loads((EVIDENCE / (execution_id + ".json")).read_text())
            verify_audit_receipt(audit, receipt, declared)
            previous.append(receipt)
        assert_target_connectable()
    elif resume:
        raise ValueError("REHEARSAL_RESUME_REQUIRES_REGISTERED_PREFIX")
    if env["ir.module.module"].search_count([("name", "like", "smart_construction%"), ("state", "=", "installed")]):
        raise ValueError("REHEARSAL_CONTROL_CONTAINS_INDUSTRY_MODULE")
    attempt_id = uuid.uuid4().hex
    report_path = EVIDENCE / ("acceptance-" + attempt_id + ".json")
    report_path.write_text(json.dumps({"ok": False, "status": "pending", "execution_id": attempt_id, "binding": binding}))
    results = previous
    target_session = None
    try:
        if not resume:
            results.append(run_operation(env, "register"))
            results.append(run_operation(env, "provision"))
            results.append(run_operation(env, "activate"))
        target_session = connect("target")
        pid = scalar(target_session, "SELECT pg_backend_pid()")
        results.append(run_operation(env, "suspend"))
        try:
            unexpected = connect("target")
        except psycopg2.OperationalError as error:
            if "not currently accepting connections" not in str(error):
                raise
        else:
            unexpected.close()
            raise ValueError("SUSPENDED_TARGET_ACCEPTED_CONNECTION")
        with closing(connect("maintenance")) as connection:
            if scalar(connection, "SELECT count(*) FROM pg_stat_activity WHERE pid=%s", (pid,)):
                raise ValueError("TARGET_SESSION_NOT_TERMINATED")
        with closing(connect("control")) as connection:
            if scalar(connection, "SELECT 1") != 1:
                raise ValueError("CONTROL_PLANE_NOT_AVAILABLE")
        results.append(run_operation(env, "resume"))
        assert_target_connectable()
        try:
            lifecycle.assert_control_plane_is_not_cut_off({"connection_effect": "deny_connections", "db_name": env.cr.dbname}, env.cr.dbname)
        except lifecycle.LifecycleApplyError:
            control_cutoff_refused = True
        else:
            raise ValueError("CONTROL_CUTOFF_NOT_REFUSED")
        # Fault injection after actual PostgreSQL cutoff: rollback must restore
        # admission, retain the failed receipt, and not append a native success.
        original = lifecycle.apply_connection_effect
        count = len(Registry._resolve_entry(declared["target_database"]).operation_ids)
        def fail_after_cutoff(connection, database, effect):
            result = original(connection, database, effect)
            if effect == "deny_connections":
                raise RuntimeError("REHEARSAL_INJECTED_AFTER_PHYSICAL_CUTOFF")
            return result
        lifecycle.apply_connection_effect = fail_after_cutoff
        try:
            try:
                run_operation(env, "suspend")
            except RuntimeError as error:
                if str(error) != "REHEARSAL_INJECTED_AFTER_PHYSICAL_CUTOFF":
                    raise
            else:
                raise ValueError("EXPECTED_INJECTED_FAILURE")
        finally:
            lifecycle.apply_connection_effect = original
        env.invalidate_all()
        record = Registry._resolve_entry(declared["target_database"])
        if record.lifecycle_state != "active" or len(record.operation_ids) != count:
            raise ValueError("FAILED_OPERATION_CHANGED_NATIVE_AUDIT")
        assert_target_connectable()
        report = {"ok": True, "execution_id": attempt_id, "binding": binding, "operations": results,
                  "control_cutoff_refused": control_cutoff_refused,
                  "terminated_target_pid": pid, "fault_injection_admission_recovery": True,
                  "scope": "isolated PostgreSQL lifecycle; not tenant application/user acceptance"}
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print("[platform.database.rehearsal] PASS suspend/resume/session termination/control availability/compensation receipt=" + str(report_path))
    except BaseException:
        # Do not compensate an unknown or committed operation here. Preserve
        # evidence; the separate recover entry first reads committed native
        # state and chooses a public resume or bounded admission recovery.
        env.cr.rollback()
        raise
    finally:
        if target_session is not None:
            target_session.close()


def readback(env):
    declared = spec()
    if env.cr.dbname != declared["control_database"]:
        raise ValueError("READBACK_CONTROL_IDENTITY_MISMATCH")
    with closing(connect("maintenance")) as connection:
        binding = verify_binding(connection)
        facts = lifecycle.database_facts(connection, declared["target_database"])
        lifecycle.assert_effect_reached("allow_connections", facts)
        with connection.cursor() as cursor:
            cursor.execute("SELECT rolname, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname IN (%s,%s)",
                           (declared["control_role"], declared["target_role"]))
            roles = cursor.fetchall()
        if len(roles) != 2 or any(any(row[1:]) for row in roles):
            raise ValueError("REHEARSAL_APPLICATION_ROLE_PRIVILEGE_DRIFT")
    record = env["sc.platform.database.registration"]._resolve_entry(declared["target_database"])
    audits = record.operation_ids.sorted("id")
    if record.lifecycle_state != "active" or audits.mapped("operation") != ["register", "provision", "activate", "suspend", "resume"]:
        raise ValueError("REHEARSAL_FINAL_NATIVE_STATE_MISMATCH")
    for audit in audits:
        identity = audit.result["operation_request"]["execution_id"]
        verify_audit_receipt(audit, json.loads((EVIDENCE / (identity + ".json")).read_text()), declared)
    for actor, database in (("control", declared["target_database"]), ("target", declared["control_database"])):
        try:
            unexpected = connect(actor, database)
        except psycopg2.OperationalError as error:
            if "permission denied for database" not in str(error):
                raise
        else:
            unexpected.close()
            raise ValueError("REHEARSAL_CROSS_DATABASE_ACCESS_ALLOWED")
    with closing(connect("target")) as connection:
        if scalar(connection, "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')"):
            raise ValueError("REHEARSAL_TARGET_NOT_EMPTY")
    if env["ir.module.module"].search_count([("name", "like", "smart_construction%"), ("state", "=", "installed")]):
        raise ValueError("REHEARSAL_INDUSTRY_MODULE_IN_CONTROL")
    result = {"ok": True, "binding": binding, "native_audit_count": len(audits),
              "state": record.lifecycle_state, "catalog": facts, "cross_database_denied": True,
              "target_empty": True, "application_roles_unprivileged": True,
              "readback_scope": "request/audit/cluster identity and database isolation; no physical replay"}
    (EVIDENCE / ("readback-" + uuid.uuid4().hex + ".json")).write_text(json.dumps(result, indent=2) + "\n")
    print("[platform.database.rehearsal] readback PASS audit=5 state=active cross_database_denied=true")


def export_evidence():
    # Receipts contain no credentials. Make originals readable to the host
    # evidence archiver; the authority directory is never traversed.
    for path in EVIDENCE.glob("*.json"):
        if path.is_symlink():
            raise ValueError("REHEARSAL_EVIDENCE_SYMLINK_REFUSED")
        path.chmod(0o644)


def cleanup_check():
    with closing(connect("maintenance")) as connection:
        verify_binding(connection)
        lifecycle.assert_effect_reached("allow_connections", lifecycle.database_facts(connection, spec()["target_database"]))
    assert_target_connectable()
    with closing(connect("control")) as connection:
        scalar(connection, "SELECT 1")


if __name__ == "__main__":
    {"bootstrap": bootstrap, "install": install, "cleanup_check": cleanup_check, "export_evidence": export_evidence}[sys.argv[1]]()
