"""Composition admission for platform-maintained business capability definitions.

This is not an ACL executor. Only trusted registry declarations belong here;
client role selections supply capability keys, never authorization mappings.
Navigation prerequisites are deliberately not interpreted as grants.
"""


VERSION = "business.capability.authorization.v1"
OPERATIONS = frozenset({"read", "create", "write", "unlink", "submit", "approve", "import", "export"})


class CapabilityCompositionError(ValueError):
    pass


def _strings(value):
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() == x and x for x in value) and len(value) == len(set(value))


def _native_boundary(contract):
    """Trusted, explicit qualification boundary; never an ACL implementation."""
    graph = contract.get('native_group_edges')
    access = contract.get('native_model_access')
    return (
        isinstance(graph, dict) and bool(graph)
        and _strings(list(graph))
        and all(_strings(edges) for edges in graph.values())
        and set(contract.get('native_groups', [])) <= set(graph)
        and isinstance(access, dict) and bool(access)
        and _strings(list(access))
        and all(_strings(ops) and bool(ops) and set(ops) <= {'read', 'write', 'create', 'unlink'}
                for ops in access.values())
    )


def composition_surface(definition):
    """Public business-only verdict; no native group or evidence internals."""
    reason = "AUTHORIZATION_UNDECLARED"
    contract = definition.get("authorization")
    if definition.get("identity_kind") != "business_capability" or definition.get("business_capability") is not True:
        reason = "NOT_BUSINESS_CAPABILITY"
    elif definition.get("status") != "ga" or definition.get("visible") is not True:
        reason = "CAPABILITY_NOT_RELEASED"
    elif isinstance(contract, dict):
        reason = "AUTHORIZATION_INVALID"
        if contract.get("version") == VERSION and contract.get("state") == "draft":
            reason = "AUTHORIZATION_UNVERIFIED"
        elif (
            contract.get("version") == VERSION
            and contract.get("state") == "verified"
            and contract.get("composable") is True
            and _strings(contract.get("operations")) and contract["operations"]
            and set(contract["operations"]) <= OPERATIONS
            and _strings(contract.get("native_groups")) and contract["native_groups"]
            and _native_boundary(contract)
            and _strings(contract.get("dependencies"))
            and _strings(contract.get("exclusions"))
            and _strings(contract.get("verification_refs")) and contract["verification_refs"]
            and contract.get("scope_policy") == "company_and_record_rules"
            and type(contract.get("sensitive")) is bool
        ):
            # Role-code predicates cannot be satisfied by arbitrary enterprise roles.
            reason = "FIXED_ROLE_DEPENDENCY" if definition.get("required_roles") else ""
            if contract["sensitive"] or "approve" in contract["operations"]:
                reason = "SEPARATE_AUTHORIZATION_REQUIRED"
    return {
        "contract_version": VERSION,
        "composable": not bool(reason),
        "reason_code": reason,
        "operations": list(contract["operations"]) if not reason else [],
    }


def resolve_composition(definitions, selected_keys):
    """Validate the entire dependency closure before returning any business keys.

    This function does not mutate users, flatten company scopes or grant groups.
    Qualified mappings still need source-tracked assignment and native execution.
    """
    if not _strings(selected_keys):
        raise CapabilityCompositionError("INVALID_CAPABILITY_SELECTION")
    catalog = {}
    for definition in definitions:
        key = definition.get("key")
        if not isinstance(key, str) or not key or key in catalog:
            raise CapabilityCompositionError("INVALID_CAPABILITY_CATALOG")
        catalog[key] = definition
    resolved, visiting = set(), set()

    def visit(key):
        if key in visiting:
            raise CapabilityCompositionError("CAPABILITY_DEPENDENCY_CYCLE")
        if key in resolved:
            return
        definition = catalog.get(key)
        if definition is None:
            raise CapabilityCompositionError("UNKNOWN_CAPABILITY:" + key)
        verdict = composition_surface(definition)
        if not verdict["composable"]:
            raise CapabilityCompositionError(verdict["reason_code"] + ":" + key)
        visiting.add(key)
        for dependency in definition["authorization"]["dependencies"]:
            visit(dependency)
        visiting.remove(key)
        resolved.add(key)

    for key in selected_keys:
        visit(key)
    for key in sorted(resolved):
        if resolved.intersection(catalog[key]["authorization"]["exclusions"]):
            raise CapabilityCompositionError("CAPABILITY_COMBINATION_CONFLICT:" + key)
    return sorted(resolved)

