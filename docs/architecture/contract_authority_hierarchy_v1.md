# Contract Authority Hierarchy v1

## Decision

The product runtime has one ordered authority chain. The layers are not peers
and must not be used as fallback truths for one another:

1. **Database routing context** selects the tenant database for every probe and
   runtime intent.
2. **Scene-ready contract** selects the product scene, route, action and menu
   identity that the current user may open.
3. **Unified Page Contract v2** projects that verified Scene action into page
   layout, data, status and interaction contracts.
4. **Odoo ORM, access rules and record rules** remain authoritative for business
   records and operation authorization.
5. **Generic frontend renderers** consume final status and semantic contracts;
   they do not infer permissions from group membership or invent product policy.

## Mandatory Runtime Binding

Any `ui.contract.v2` request opened from a Scene must carry both `scene_key` and
`action_id`. The backend resolves the current user's Scene registry and rejects
the request when the Scene is missing, has no action binding or points to a
different action. A model-only request may omit Scene identity only when it is
not entered from a product Scene.

## Permission Projection

Group membership is evaluated on the backend. The v2 `statusContract.buttonStatus`
publishes the final visible/disabled result and reason code. The browser may use
record values for interaction feedback, but it must not reproduce access-group
authorization decisions.

## Fail-Closed Rules

- Missing database evidence cannot satisfy a runtime release gate.
- An empty Scene source report cannot satisfy Scene coverage or burn-down gates.
- A Scene/action mismatch returns a contract error; the client must not retry the
  same action through a model-only or legacy contract path.
- An unknown or unresolved access group disables the action.
- `ui.contract.v2` is a Scene-bound page projection, not an alternative product
  navigation authority.

## Verification

- `make verify.contract.probe_routing.unit`
- `make verify.contract.authority_hierarchy.guard`
- `make verify.scene.ready.strict_gap.full_audit`
- `make verify.contract.mode.smoke`
- `make verify.frontend.product.ready`
