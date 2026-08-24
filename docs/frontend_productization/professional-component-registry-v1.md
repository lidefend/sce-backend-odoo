# Professional Component Registry v1

## Authority

The registry is the single P0 frontend authority that decides whether a
Contract V2 `componentKey` may enter the production form renderer. Backend
`layoutContract.componentRegistry` remains transport metadata; it does not
declare frontend readiness.

Every registration declares:

- component key and semantic type;
- supported field types, presentation modes, and render profiles;
- required capabilities;
- renderer and explicit fallback;
- readiness: `ready`, `readable_fallback`, or `fail_closed`.

## Production chain

```text
decoded Contract V2 widget
→ normalized store
→ canonical Presenter
→ professional registry resolver
→ FormSection renderer
→ data-component-* semantic evidence
```

Resolution is fail closed. An unknown key, incompatible field type, unsupported
presentation mode or render profile, or missing capability raises a precise
invariant error before the field reaches the renderer. There is no generic or
silent component fallback.

`readable_fallback` is a registered, explicit state. In v1 it is reserved for
hierarchical collection data whose readable representation is supported while
its specialized professional interaction is not yet authoritative.

## Boundaries

- The registry does not grant data, model, record, action, or mutation rights.
- It does not infer `task` or `workspace`; it consumes the Presenter identity.
- It contains no model, action, menu, label, or industry-specific branches.
- It authorizes existing generic rendering capabilities; Phase 7 owns their
  professional component-family expansion.
- A registration is not a dynamic component loader. Its renderer name is an
  auditable authorization target for the current production renderer.
