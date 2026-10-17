# Menu cache P0 follow-ups — 2026-10-17

Registered after PR #671 (merge `5dbf503d`) so each item is handled as its own
batch. No item is in scope for the merged candidate; nothing here is fixed yet.

Common boundary for all three: P0 platform kernel (`smart_core`), no frontend
change, no contract payload change, no deployment.

## F1 — `head.permissions` ACL snapshot is not part of the invalidation input

- Mechanism: `_head_from_act_window` calls `check_access_rights` once at
  generation time and the result is persisted inside `menu_tree`; the source
  digest covers menu/action/view rows only.
- Consequence: an ACL change that alters the hint does not move the digest, so
  the hint can stay stale for as long as no other input changes.
- Triage already done: the navigation output currently does not consume this
  snapshot, and no authorization bypass was found. It is a display-hint
  freshness defect, not an authorization path.
- Counter-example to write: change `ir.model.access` for the projected model,
  keep every menu/action/view row untouched, assert the projection is stale.
- Option to decide per implementation: drop the derived field, or recompute it
  at read time instead of persisting it.
- Benefit evidence: digest change detection on ACL-only edits; zero extra
  queries on the hot read if the field is removed.
- Rollback: single commit; the digest stays valid because removing a persisted
  derived field does not widen any permission decision.

## F2 — digest capture and tree read are not one consistent snapshot

- Mechanism: `_generate_from_menus` takes the digest first, then reads the
  source rows. A concurrent edit that lands between the two, and is then
  reverted before the next lookup, can persist a mid-state tree with the
  restored digest and be judged fresh.
- Scope: requires two interleaved edits; a single edit only causes one extra
  rebuild.
- Counter-example to write: deterministically interleave a write between digest
  and tree read using a test hook, then revert; assert the stored projection
  matches the reverted source or is rebuilt.
- Benefit evidence: no stale window under interleaving; must not add a second
  full source read on the warm path.
- Rollback: single commit.

## F3 — cold path computes the full digest twice

- Mechanism: `_menu_metadata_changed_since` computes the digest, then
  `_generate_from_menus` computes it again before reading the tree.
- Consequence: on every rebuild the five source tables are scanned twice.
  Correctness is unaffected.
- Counter-example/measurement to write: count digest computations (or SQL) on a
  rebuild; require exactly one full digest per rebuild and no change to the
  freshness decision in F1/F2 tests.
- Benefit evidence: rebuild SQL/queries drop measurably on `local.dev` with the
  same output tree; report the warm `system.init` p95 as an observation only.
- Rollback: single commit.
