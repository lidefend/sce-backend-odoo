# Product View Structure Contract

## Authority

The product view-structure contract binds every released formal product menu to
its Odoo action and effective views. It is generated only from the governed
clean-install profile. Demo, sample, customer and runtime low-code data are not
authorities for this baseline.

The contract schema uses semantic version `1.0.0`; no `v1` schema alias is
published or accepted.

Source priority remains Odoo `ir.ui.view` XML and inheritance resolution,
contract governance projections, model metadata fallback, then technical field
names as the terminal fallback.

## Coverage Unit

The coverage key is `menu_xmlid`. Duplicate projections of one menu across
product-policy records are collapsed. Every released formal menu must resolve
to exactly one of:

- `resolved_view_action`: an `ir.actions.act_window` with all declared view
  modes plus its search view resolved successfully.
- `non_view_action`: an explicit client, URL, report or other non-view action.

Missing menus, missing actions, action/model mismatches and partial view
resolution are contract failures.

## Three Fingerprints

- `source_graph_sha256`: selected view and parent-source chain.
- `resolved_arch_sha256`: complete effective arch returned by Odoo `get_view`.
- `semantic_structure_sha256`: normalized ordered tags, semantic attributes,
  fields and buttons consumed by contract renderers.

The tracked baseline is
`contracts/generated/product_view_structure_contract.json`. Product snapshots
may reference a surface through `contract_ref` and the three hashes rather than
duplicating the full view structure.

## Governed Commands

```bash
make local.clean.view_structure_baseline
make local.clean.view_structure_gate
make verify.contract.view_structure
```

Do not run the exporter against `local.dev`, `local.sample`, a customer tenant
or a manually assembled Compose project/database. A candidate mismatch is
fail-closed and requires an intentional baseline update plus review.
