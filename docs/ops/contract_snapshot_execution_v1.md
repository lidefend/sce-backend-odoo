# Contract Snapshot Execution

Use the governed local development wrapper. Do not assemble Compose, database, or credential arguments manually.

```bash
# Full registry
make local.dev.contract_snapshot

# Resume at a failed case, including all following cases
make local.dev.contract_snapshot CONTRACT_START_CASE=cost_tracking_record_create_intent_admin

# Export exactly one registered case
make local.dev.contract_snapshot CONTRACT_CASE_ONLY=project_form_pm
```

`CONTRACT_START_CASE` and `CONTRACT_CASE_ONLY` are mutually exclusive. An unknown case fails with exit code 2. Every selected case retains atomic publication and unexpected-error guards.
