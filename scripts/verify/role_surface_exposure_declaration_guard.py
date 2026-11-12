#!/usr/bin/env python3
"""Lock the declared divergence between menu-layer capability reachability and the
published navigation surface.

``ROLE_SURFACE_OVERRIDES`` (and the frontend navigation manifest) decide what a role
actually gets on the published navigation surface.  The menu XML ``groups``
declaration decides what the same role can reach at the menu/ACL layer.  For several
roles those two authorities deliberately disagree: the capability is reachable but the
entry is intentionally not registered on the release surface.

That divergence is a product decision, not a defect.  It must therefore be declared
explicitly in ``config/frontend/role_surface_exposure_declarations_v1.json`` and locked
by this guard: any drift in either direction (a newly reachable but undocumented entry,
a declared entry that quietly became reachable, a delivery-mode change, an identity
group change, a new entry in the acceptance universe) fails closed until the owner
re-declares it.

The guard is static: it reads the acceptance entry universe, the role policy map, the
role/capability group XML and the declaration file.  It never relaxes ACLs, field
permissions, acceptance assertions or the release navigation surface.
"""

from __future__ import annotations

import ast
import csv
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"
UNIVERSE_PATH = ROOT / "docs/product/frontend_business_entry_acceptance_v1.csv"
DECLARATIONS_PATH = ROOT / "config/frontend/role_surface_exposure_declarations_v1.json"
GROUP_SOURCE_PATHS = (
    ROOT / "addons/smart_construction_core/security/sc_role_groups.xml",
    ROOT / "addons/smart_construction_core/security/sc_capability_groups.xml",
)

SCHEMA_VERSION = "role-surface-exposure-declarations/v1"
DELIVERY_MODES = ("declared_whitelist", "capability_discover", "denied")
DELIVERED_FIELDS = ("primary_menu_xmlids", "role_home_menu_xmlids")
DEFAULT_MODULE = "smart_construction_core."

_RECORD_RE = re.compile(r'<record id="([^"]+)" model="res\.groups">(.*?)</record>', re.S)
_IMPLIED_RE = re.compile(r'<field name="implied_ids"\s+eval="([^"]*)"', re.S)
_REF_RE = re.compile(r"ref\(\s*'([^']+)'\s*\)")


def _qualify(xmlid: str, default_module: str = DEFAULT_MODULE) -> str:
    value = str(xmlid).strip()
    if not value:
        return ""
    return value if "." in value else f"{default_module}{value}"


def load_group_graph(paths=GROUP_SOURCE_PATHS) -> dict[str, list[str]]:
    """Parse res.groups ``implied_ids`` declarations from the role/capability XML."""
    graph: dict[str, list[str]] = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        for match in _RECORD_RE.finditer(text):
            group = _qualify(match.group(1))
            implied = _IMPLIED_RE.search(match.group(2))
            refs: list[str] = []
            if implied:
                refs = [_qualify(ref) for ref in _REF_RE.findall(implied.group(1))]
            graph[group] = refs
    return graph


def group_closure(group: str, graph: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [group]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, []))
    return seen


def load_role_policy(path=POLICY_PATH) -> dict:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "ROLE_SURFACE_OVERRIDES"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, dict):
                return value
    raise ValueError("ROLE_SURFACE_OVERRIDES is missing")


def load_entry_universe(path=UNIVERSE_PATH) -> tuple[list[dict], dict[str, str]]:
    """Return (resolved entries, pending entries).

    An entry is ``pending`` when its ``role_authority`` has not been resolved from the
    current contract yet; pending entries are declared, never dropped.
    """
    entries: list[dict] = []
    pending: dict[str, str] = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            menu = str(row.get("menu_xmlid") or "").strip()
            if not menu:
                continue
            try:
                authority = json.loads(row.get("role_authority") or "")
            except (TypeError, ValueError):
                pending[menu] = f"{row.get('label')} / {row.get('model')}: {row.get('role_authority')}"
                continue
            entries.append(
                {
                    "menu": menu,
                    "chain": authority.get("menu_chain") or [],
                    "actions": authority.get("action_groups") or [],
                }
            )
    return entries, pending


def reachable_entries(principals, closures: dict[str, set[str]], entries) -> set[str]:
    capability = set()
    for group in principals:
        capability |= closures.get(_qualify(group), set())
    reachable: set[str] = set()
    for entry in entries:
        ok = True
        for layer in entry.get("chain") or []:
            declared = {_qualify(item) for item in (layer.get("groups") or []) if str(item).strip()}
            if declared and not (declared & capability):
                ok = False
                break
        if ok:
            actions = {_qualify(item) for item in (entry.get("actions") or []) if str(item).strip()}
            if actions and not (actions & capability):
                ok = False
        if ok:
            reachable.add(entry["menu"])
    return reachable


def delivered_surface(role_policy: dict, universe: set[str]) -> set[str]:
    declared = {
        str(item).strip()
        for field in DELIVERED_FIELDS
        for item in (role_policy.get(field) or [])
        if str(item).strip()
    }
    denied = {str(item).strip() for item in (role_policy.get("denied_menu_xmlids") or [])}
    return (declared - denied) & universe


def validate(declarations: dict, policy: dict, entries, pending, closures) -> list[str]:
    errors: list[str] = []

    if not isinstance(declarations, dict):
        return ["declaration file must be a JSON object"]
    version = declarations.get("schema_version")
    if version != SCHEMA_VERSION:
        errors.append(f"schema_version={version!r} expected={SCHEMA_VERSION!r}")

    roles = declarations.get("roles")
    excluded = declarations.get("excluded_roles") or {}
    if not isinstance(roles, dict):
        return errors + ["declarations.roles must be an object"]
    if not isinstance(excluded, dict):
        return errors + ["declarations.excluded_roles must be an object"]

    covered = set(roles) | set(excluded)
    missing = sorted(set(policy) - covered)
    unknown = sorted(covered - set(policy))
    if missing:
        errors.append(f"policy roles missing from declarations={missing}")
    if unknown:
        errors.append(f"declared roles not present in policy={unknown}")

    universe = {entry["menu"] for entry in entries}
    if len(entries) != len(universe):
        errors.append("acceptance universe contains duplicate menu_xmlid rows")

    declared_pending = declarations.get("authority_pending_entries")
    if not isinstance(declared_pending, dict):
        errors.append("authority_pending_entries must be an object")
        declared_pending = {}
    if set(declared_pending) != set(pending):
        errors.append(
            "authority_pending_entries drift "
            f"missing={sorted(set(pending) - set(declared_pending))} "
            f"unexpected={sorted(set(declared_pending) - set(pending))}"
        )
    if set(declared_pending) & universe:
        errors.append("authority_pending_entries overlaps the resolved entry universe")

    reachability_roles: list[str] = []
    role_reach: dict[str, set[str]] = {}
    for role in sorted(roles):
        row = roles[role] or {}
        if not isinstance(row, dict):
            errors.append(f"{role}: role declaration must be an object")
            continue
        reason = str(row.get("rationale") or "").strip()
        if not reason:
            errors.append(f"{role}: rationale is required")
        identity = row.get("identity_groups") or []
        if not identity:
            errors.append(f"{role}: identity_groups is required")
            continue
        unknown_groups = [group for group in identity if _qualify(group) not in closures]
        if unknown_groups:
            errors.append(f"{role}: identity groups unresolvable={unknown_groups}")
            continue

        mode = row.get("delivery_mode")
        if mode not in DELIVERY_MODES:
            errors.append(f"{role}: delivery_mode={mode!r} not in {list(DELIVERY_MODES)}")
            continue
        role_policy = policy.get(role) or {}
        discover = bool(role_policy.get("discover_installed_capabilities"))
        deny_all = bool(role_policy.get("deny_all_navigation"))
        if mode == "capability_discover" and not discover:
            errors.append(f"{role}: capability_discover but discover_installed_capabilities is false")
        if mode != "capability_discover" and discover:
            errors.append(f"{role}: discover_installed_capabilities is true but delivery_mode={mode}")
        if mode == "denied" and not deny_all:
            errors.append(f"{role}: denied but deny_all_navigation is false")
        if mode != "denied" and deny_all:
            errors.append(f"{role}: deny_all_navigation is true but delivery_mode={mode}")

        reachable = reachable_entries(identity, closures, entries)
        delivered = delivered_surface(role_policy, universe)
        role_reach[role] = reachable
        reachability_roles.append(role)

        declared_narrowed = {str(item).strip() for item in row.get("capability_reachable_not_delivered") or []}
        declared_beyond = {str(item).strip() for item in row.get("delivered_without_declared_capability") or []}
        for label, values in (("capability_reachable_not_delivered", declared_narrowed), ("delivered_without_declared_capability", declared_beyond)):
            outside = sorted(value for value in values if value not in universe)
            if outside:
                errors.append(f"{role}: {label} outside the acceptance universe={outside}")
        if declared_narrowed & delivered:
            errors.append(f"{role}: narrowed/delivered overlap={sorted(declared_narrowed & delivered)}")

        if mode == "capability_discover":
            expected_narrowed: set[str] = set()
            if not delivered <= reachable:
                errors.append(f"{role}: delivered surface outside capability reach={sorted(delivered - reachable)}")
        elif mode == "denied":
            expected_narrowed = reachable
            if delivered:
                errors.append(f"{role}: denied role still delivers={sorted(delivered)}")
        else:
            expected_narrowed = reachable - delivered
        if declared_narrowed != expected_narrowed:
            errors.append(
                f"{role}: capability_reachable_not_delivered drift "
                f"undeclared={sorted(expected_narrowed - declared_narrowed)} "
                f"stale={sorted(declared_narrowed - expected_narrowed)}"
            )
        expected_beyond = delivered - reachable
        if declared_beyond != expected_beyond:
            errors.append(
                f"{role}: delivered_without_declared_capability drift "
                f"undeclared={sorted(expected_beyond - declared_beyond)} "
                f"stale={sorted(declared_beyond - expected_beyond)}"
            )

    union: set[str] = set()
    for role in reachability_roles:
        union |= role_reach[role]
    declared_no_role = {str(item).strip() for item in declarations.get("capability_reachable_by_no_role") or []}
    expected_no_role = universe - union
    if declared_no_role != expected_no_role:
        errors.append(
            "capability_reachable_by_no_role drift "
            f"undeclared={sorted(expected_no_role - declared_no_role)} "
            f"stale={sorted(declared_no_role - expected_no_role)}"
        )
    return errors


def main() -> int:
    declarations = json.loads(DECLARATIONS_PATH.read_text(encoding="utf-8"))
    policy = load_role_policy()
    entries, pending = load_entry_universe()
    graph = load_group_graph()
    closures = {group: group_closure(group, graph) for group in graph}
    errors = validate(declarations, policy, entries, pending, closures)
    if errors:
        print("[role_surface_exposure_declaration_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 2
    narrowed = sum(
        len((row or {}).get("capability_reachable_not_delivered") or [])
        for row in (declarations.get("roles") or {}).values()
    )
    print(
        "[role_surface_exposure_declaration_guard] PASS "
        f"roles={len(declarations.get('roles') or {})} "
        f"excluded={len(declarations.get('excluded_roles') or {})} "
        f"universe={len(entries)} pending={len(pending)} "
        f"narrowed={narrowed} no_role={len(declarations.get('capability_reachable_by_no_role') or [])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
