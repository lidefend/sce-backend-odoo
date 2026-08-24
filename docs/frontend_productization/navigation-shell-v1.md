# Canonical Navigation Shell v1

## Product boundary

Phase 3 establishes one P0 navigation authority and one product shell. It does
not redesign Page Header, page patterns, Contract forms or business-domain
components.

The authority split is explicit:

- Backend: visibility, parent chain, exact action/menu pairing, disabled
  reason, order and hierarchy.
- Frontend: expanded state, selected presentation, mobile Drawer, keyboard
  focus and responsive behavior.

The final `system.init.navigation.nav` tree carries a
`canonical_navigation` v1 projection on every node. The frontend validates
that projection against the authenticated route-authority principal before it
marks navigation ready. Missing, duplicated or conflicting identity fails
closed.

## Production chain

```text
authenticated role/menu facts
→ route authority filtering
→ canonical navigation projection
→ session decoder and integrity checks
→ CanonicalNavigationModel
→ ProductAppShell / ProductSideNavigation
→ MenuTree semantic identity
```

`ProductMobileNavigationDrawer`, `NavigationBreadcrumb` and
`WorkspaceContextIndicator` are shell presentation components. They do not
create menu authority or infer permissions.

Synthetic directory tree ids are never treated as formal menu ids. When a
directory is backed by an Odoo menu, `config_menu_id` or its formal config
reference is the identity consumed by both producer and frontend validator.

## Acceptance contract

- Three-level navigation remains representable and expandable.
- A selected leaf has one exact action/menu identity and one `aria-current`.
- Refresh and browser back/forward preserve the exact deep link.
- Non-active expansion preferences survive refresh.
- Mobile navigation is a modal Drawer with Escape closure and focus return.
- Unknown or conflicting authority does not create a client-side menu.
- Readonly navigation journeys produce no business mutation.

The representative governed journey uses project workspace action 859 only as
test data. No corresponding model, action, menu or label appears in production
navigation logic.
