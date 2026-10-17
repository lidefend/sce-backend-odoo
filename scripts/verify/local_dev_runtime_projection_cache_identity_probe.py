"""Read-only runtime probe for assembled-cache identity invalidation (P0/P4).

The record-free assembled hit returns after re-sealing; it does not re-run the
entitlement, policy, action, modifier or trim projection. Its safety therefore
rests on the cache key (principal groups, company, request identity) and the
source token (ACL, rules, user row, business-policy definitions, code identity).

This probe exercises both halves on the registered ``sc-local-dev`` /
``sc_dev_demo`` profile:

* inside a savepoint, remove one group from the declared demo principal, then
  recompute the key and token; both must move;
* inside a savepoint, change one field policy (or, when none applies, one
  business-config contract definition), then recompute the token; it must move.

Both writes are rolled back and commit is refused. After the rollbacks the probe
recomputes the baseline identities and requires them to be unchanged, so a
reported invalidation cannot come from a leaked write.
"""
import json


DATABASE = "sc_dev_demo"
MODEL = "payment.request"
ACTION_ID = 878
ROLE_XMLID = "smart_construction_demo.user_demo_role_finance"


class _RollbackProbe(Exception):
    def __init__(self, result):
        super().__init__("probe rollback")
        self.result = result


def _identity(api, env, user, company, *, model=MODEL, action_id=ACTION_ID):
    from odoo.addons.smart_core.utils.load_contract_response_cache import (
        build_projection_cache_key,
        build_projection_source_token,
    )

    actor = api.Environment(
        env.cr, user.id, {"allowed_company_ids": [company], "lang": "zh_CN"}
    )
    context = {"allowed_company_ids": [company], "lang": "zh_CN"}
    cache_key = build_projection_cache_key(
        actor,
        namespace="ui.contract.v2.source.single-assembly.v1",
        params={"model": model, "action_id": action_id, "op": "action_open"},
        model_name=model,
        view_types="form",
        context=context,
    )
    source_token = build_projection_source_token(
        actor, model_name=model, action_id=action_id
    )
    return cache_key, source_token, sorted(int(group_id) for group_id in actor.user.groups_id.ids)


def _probe(env):
    from odoo import api

    assert env.cr.dbname == DATABASE, "registered local.dev database required"
    env.cr.rollback()
    original_commit = env.cr.commit

    def _refuse_commit(*_args, **_kwargs):
        raise RuntimeError("projection cache identity probe forbids commit")

    env.cr.commit = _refuse_commit

    user = env.ref(ROLE_XMLID)
    assert user.active and not user.share, "declared demo principal unavailable"
    company = user.company_id.id
    baseline_key, baseline_token, baseline_groups = _identity(api, env, user, company)
    assert baseline_key and baseline_token, "projection identity is unavailable"

    role_result = {"status": "not_run"}
    try:
        with env.cr.savepoint():
            protected = {
                env.ref("base.group_user").id,
                env.ref("base.group_portal").id,
                env.ref("base.group_public").id,
            }
            candidates = [
                group for group in user.groups_id if group.id not in protected
            ]
            candidates.sort(key=lambda group: group.id)
            if not candidates:
                role_result = {
                    "status": "not_applicable",
                    "reason": "the principal has no removable non-base group",
                }
            else:
                group = candidates[-1]
                user.sudo().write({"groups_id": [(3, group.id)]})
                env.cr.flush()
                env.invalidate_all()
                changed_key, changed_token, changed_groups = _identity(
                    api, env, user, company
                )
                role_result = {
                    "status": "observed",
                    "removed_group_id": group.id,
                    "removed_group_xmlid": group.get_external_id().get(group.id) or "",
                    "cache_key_changed": changed_key != baseline_key,
                    "source_token_changed": changed_token != baseline_token,
                    "groups_before": baseline_groups,
                    "groups_after": changed_groups,
                }
            raise _RollbackProbe(role_result)
    except _RollbackProbe as exc:
        role_result = exc.result
    except Exception as exc:
        role_result = {
            "status": "error",
            "error": "%s: %s" % (type(exc).__name__, exc),
        }

    env.cr.rollback()
    env.invalidate_all()

    policy_result = {"status": "not_run"}
    try:
        with env.cr.savepoint():
            policy_model = env["ui.form.field.policy"]
            # Any policy row is a valid carrier: the token binds the definition
            # set for the model/action domain, so use the row's own domain
            # rather than requiring one for the payment.request probe target.
            policy = policy_model.sudo().with_context(active_test=False).search(
                [], order="id", limit=1
            )
            if policy:
                original_label = policy.label
                policy_model_name = str(policy.model or MODEL)
                policy_action_id = int(policy.action_id.id or ACTION_ID)
                _, policy_baseline_token, _ = _identity(
                    api, env, user, company,
                    model=policy_model_name, action_id=policy_action_id,
                )
                policy.sudo().write({"label": "%s [probe]" % (original_label or "")})
                env.cr.flush()
                env.invalidate_all()
                _, changed_token, _ = _identity(
                    api, env, user, company,
                    model=policy_model_name, action_id=policy_action_id,
                )
                policy_result = {
                    "status": "observed",
                    "carrier": "ui.form.field.policy",
                    "record_id": policy.id,
                    "model": policy_model_name,
                    "action_id": policy_action_id,
                    "field": "label",
                    "source_token_changed": changed_token != policy_baseline_token,
                }
            else:
                contract = env["ui.business.config.contract"].sudo().with_context(
                    active_test=False
                ).search([
                    ("status", "=", "draft"),
                ], order="id", limit=1)
                if not contract:
                    policy_result = {
                        "status": "not_applicable",
                        "reason": "no field policy row and no draft business-config contract",
                    }
                else:
                    contract_model_name = str(contract.model or MODEL)
                    contract_action_id = int(contract.action_id.id or ACTION_ID)
                    _, contract_baseline_token, _ = _identity(
                        api, env, user, company,
                        model=contract_model_name, action_id=contract_action_id,
                    )
                    contract.sudo().write({"priority": int(contract.priority or 100) + 1})
                    env.cr.flush()
                    env.invalidate_all()
                    _, changed_token, _ = _identity(
                        api, env, user, company,
                        model=contract_model_name, action_id=contract_action_id,
                    )
                    policy_result = {
                        "status": "observed",
                        "carrier": "ui.business.config.contract",
                        "record_id": contract.id,
                        "model": contract_model_name,
                        "action_id": contract_action_id,
                        "field": "priority",
                        "source_token_changed": changed_token != contract_baseline_token,
                    }
            raise _RollbackProbe(policy_result)
    except _RollbackProbe as exc:
        policy_result = exc.result
    except Exception as exc:
        policy_result = {
            "status": "error",
            "error": "%s: %s" % (type(exc).__name__, exc),
        }

    env.cr.rollback()
    env.invalidate_all()
    restored_key, restored_token, restored_groups = _identity(api, env, user, company)
    report = {
        "schema": "runtime-projection-cache-identity-probe/v1",
        "database": DATABASE,
        "instrumentation": "none",
        "principal": ROLE_XMLID,
        "uid": user.id,
        "company_id": company,
        "baseline": {
            "cache_key": baseline_key,
            "source_token": baseline_token,
            "groups": baseline_groups,
        },
        "role_revocation": role_result,
        "policy_change": policy_result,
        "rollback_restored": {
            "cache_key": restored_key == baseline_key,
            "source_token": restored_token == baseline_token,
            "groups": restored_groups == baseline_groups,
        },
        "commit_refused": True,
        "acceptance_pass": (
            role_result.get("status") == "observed"
            and role_result.get("cache_key_changed") is True
            and role_result.get("source_token_changed") is True
            and policy_result.get("status") == "observed"
            and policy_result.get("source_token_changed") is True
            and restored_key == baseline_key
            and restored_token == baseline_token
            and restored_groups == baseline_groups
        ),
    }
    env.cr.commit = original_commit
    return report


if "env" in globals():
    print(
        "PROJECTION_CACHE_IDENTITY_PROBE_REPORT "
        + json.dumps(_probe(env), sort_keys=True, default=str)
    )
