# Action View capability transport closeout (2026-11-17)

## Boundary

- Formal Product Layer: P0
- Layer Target: contract request payload normalization before Action View Set projection
- Module: `smart_core`
- Reason: `ui.contract.v2` received `client_contract_capabilities`, but the legacy request normalizer dropped the field before `PageAssembler` evaluated View renderer support.
- Why Not Elsewhere: current user/company View availability remains owned by the backend Action/View projection; the frontend must not infer unsupported or selectable views.
- Blast Radius: every request that supplies client capabilities through the legacy contract service, especially Action-bound Form/Tree/Kanban pages.

## Defect

After the first main deployment, project Action `674` returned HTTP 200 with the correct active View, but every `rendererStatus` remained `unknown` even when the request declared:

```text
view.tree.v1
view.kanban.v1
view.form.v1
```

The downstream PageAssembler read was already correct. The field was removed earlier by the legacy `parse_payload()` allowlist, so absence and an explicit empty capability set were also indistinguishable at that boundary.

## Fix

`parse_payload()` now preserves `client_contract_capabilities` and its camel-case alias. Capability absence remains absent (`unknown`), while an explicit empty list remains an empty negotiated set (`unsupported` for registered renderers). This preserves legacy-client behavior and makes client negotiation effective.

The legacy `ui.contract` action dispatcher also rebuilt its downstream Action payload without the capability field. That second allowlist is now fixed for model, view and action-open paths, including the collection Action dispatch used by Tree/Kanban.

Regression coverage exercises the actual payload normalizer, including snake case, camel case, absence and explicit empty input, plus the `UiContractHandler` action-open path. The ORM test proves the handler forwards capabilities and Action View rows become renderer-ready.

## Verification

Source and deployment verification will be recorded after the exact candidate passes and the daily runtime is read back. Runtime UI acceptance remains separate from source checks.
