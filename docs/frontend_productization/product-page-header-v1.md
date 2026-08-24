# Product Page Header v1

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: frontend page-header presentation authority.
- Module: `frontend/apps/web`.
- Standard vs User-Specific: platform standard.

This batch establishes one standalone page-header structure for form, collection, and scene surfaces. It does not change Contract V2, routes, permissions, page patterns, dialog headers, or business-model presentation.

## Presentation model

The formal axes are `title`, `subtitle`, `breadcrumb`, `presentationMode`, `renderProfile`, `dirtyState`, `statusbar`, `primaryAction`, `overflowActions`, and `exitAction`.

`presentationMode` and `renderProfile` remain orthogonal. Task/workspace controls page purpose; create/edit/readonly controls interaction. Collection and dashboard identify non-form surfaces. A header may expose zero or one primary action. Readonly headers reject a save primary action.

## Ownership

`ProductPageHeader` owns standalone header structure and semantic DOM identity. Existing `ScPageHeader`, page, and template adapters retain their public APIs while delegating structure to it. `ContractFormProductHeader` retains form-specific workflow/status behavior and projects the formal axes into the shared header. Dialog and Drawer titles remain owned by their overlay primitives.

## Fail-closed behavior

- blank title is rejected;
- multiple primary actions are rejected;
- readonly plus save primary action is rejected;
- Contract form secondary primary claims are moved to overflow;
- AppShell does not emit a competing H1 on routes whose page owns the header.

## Candidate acceptance

The governed readonly browser probe covers one task/edit surface and one workspace/readonly surface. It requires exactly one page header and one H1, zero parallel body action bars, at most one primary action, no save action in readonly, no edit-transition action in edit, no 390px overflow, zero browser/HTTP errors, and zero business mutations.

## Exclusions

- navigation behavior;
- Contract/schema changes;
- task/workspace inference;
- page-pattern implementation;
- component registry;
- business model, action, menu, or label special cases.
