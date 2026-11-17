# Mainline documentation link recovery (2026-11-17)

## Identity and classification

- Branch: `fix/mainline-docs-links-20261117`
- Baseline main: `bec4a38da10f15d6f4008af355db3bcc4332e13d`
- Formal product layer: P4 ops delivery tool
- Failure owners: `baseline_evidence_defect` and `validation_tool_defect`

## Observed failure

`make verify.docs.all` stops at `verify.docs.links` with
`missing_count=72 > max_missing_allowed=0`.

The missing references are limited to four documents:

- `docs/audit/native-scene-01/native_view_inventory.md`: 10 links use
  `%20` inside source paths although the checked-in parser files contain
  spaces and the link checker does not decode those destinations.
- `docs/ops/iterations/fe_ux_entry_continuity_01.md`: 21 permanent links
  target ignored `.runtime/` files that no longer exist.
- `docs/ops/iterations/fe_ux_walkthrough_01/evidence.md`: 36 permanent links
  target ignored `.runtime/` files that no longer exist.
- `docs/ops/iterations/fe_ux_walkthrough_01/journeys.md`: 5 permanent links
  target ignored `.runtime/` files that no longer exist.

The parser-file targets exist and the references use standard Markdown
destinations containing spaces. The current checker neither strips the
CommonMark `<...>` destination delimiters nor percent-decodes `%20`, so those
10 references are validation-tool false positives.

## Ownership and boundary

The durable fix is documentation metadata: retained evidence paths remain
visible as text, but historical `.runtime/` files are not represented as
permanent Markdown links. The link checker is corrected to resolve standard
angle destinations and percent-encoded spaces, with focused regression tests.
The incremental planner maps the checker and its test to `verify.docs.links`,
so future changes execute the owning gate instead of stopping as unmapped
paths.
The existing parser source files still receive clickable source links. The
zero-missing threshold and every documentation gate remain unchanged.

Product source, tests, workflows, databases, deployment, and runtime evidence
are excluded.

## Validation

The repair was validated in resumable stages:

| Entry | Result | Evidence |
| --- | --- | --- |
| `make verify.native_scene.inventory.unit` | PASS, 2 tests | native scene inventory `--check` |
| focused link checker tests | PASS, 5 tests | `python3 -m unittest scripts.verify.test_docs_links` |
| `make verify.docs.links` | PASS, 0 missing links | `artifacts/docs/docs_links_report.json` |
| `make verify.docs.all` | PASS end to end | inventory, links, temp guard, contract sync, product boundary, native-scene inventory |
| `make ci.local.iteration` | PASS, 4 required targets | agent ledger, docs links, frontend incremental, resume unit |
| `make ci.delivery.freeze.prepare` | PASS, generated evidence current | generated inventories and complexity reports refreshed |

The threshold remains `max_missing_allowed=0`. The initial 62 stale
`.runtime/` links were removed from permanent Markdown destinations; their
paths remain visible in code spans. The 10 valid parser links now resolve
through a focused checker correction that strips CommonMark angle delimiters
and percent-decodes path components.
