# P1 Demo Settlement Seed Read-Only Alignment

## Product result

The standard demo can be rebuilt from the current source after
`project.settlement` became a read-only historical compatibility model.

## Failure

A governed fresh rebuild of the daily `demo` duty reached the S73 scenario and
failed because `10_risk_settlement_records.xml` still created
`project.settlement` and `project.settlement.line`. The current product rejects
direct writes to that historical model.

The failure occurred after the governed recovery point was captured at:

```text
/data/backups/daily-demo-dev/sc_demo-20261123T121334Z-393cf745
```

`sc_platform_control` was not selected or changed.

## Change

- S73 now creates one `sc.settlement.order` with two formal settlement lines.
- The S73 verification checks the formal settlement model and its computed
  amount.
- Scenario lifecycle declarations no longer drive actions on the read-only
  compatibility model.
- The scenario manifest declares formal settlement create and submit intents.
- The demo supplemental test scans every scenario XML file and fails if a
  read-only legacy settlement record is introduced again.
- The rental payment seed uses a masked, realistic display value instead of a
  16-digit account-like value. This preserves the demo's business appearance and
  removes the repeated personal-data scanner hit without adding another
  blob-specific exemption.
- Projects that are declared for warranty or closed display stages complete
  their formal settlement before the final lifecycle transition, satisfying the
  real project-terminal guard instead of bypassing it.

## Validation

- `python3 demo_addons/smart_construction_demo/tests/test_demo_supplemental_flows.py`
  passed, 84 tests.
- `python3 -m unittest scripts.verify.test_demo_scenario_step`
  passed, 9 tests.
- XML parse, scenario manifest JSON parse and `bash -n scripts/demo/verify.sh`
  passed.

Remote PR integration and the post-merge daily rebuild remain pending.
