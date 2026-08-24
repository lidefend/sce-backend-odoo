# Professional Workflow Components v1

Phase 8A establishes shared P0 workflow presentation for task and workspace forms.

- Statusbar state remains owned by normalized workflow/native form authority.
- Task and workspace layouts consume one `CanonicalActionBar`.
- Disabled actions expose the backend reason code, with a fail-closed generic reason when absent.
- Primary and overflow tiers remain Presenter/Floorplan authority.
- Workflow confirmation uses project `ScDialog` and `ScButton` primitives.
- No model, action, menu, label, route, permission, or lifecycle special case is introduced.
