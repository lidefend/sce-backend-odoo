# Platform SLA Report

- iterations: 6
- target_count: 3
- error_count: 0
- warning_count: 1

| intent | p95_ms | p95_limit | max_payload_bytes | payload_limit | statuses |
|---|---:|---:|---:|---:|---|
| system.init | 697.27 | 8000.00 | 238927 | 3500000 | 200 |
| ui.contract | 885.45 | 5000.00 | 621388 | 3500000 | 200 |
| execute_button | 26.10 | 3000.00 | 683 | 600000 | 403 |

## Denials

- execute_button: http=403 code=PERMISSION_DENIED message=ACTION_CONTRACT_AUTHORITY_MISSING reason_code=PERMISSION_DENIED classification=fail_closed_undeclared_action_authority

## Errors

- none

## Warnings

- execute_button has non-2xx statuses in SLA run: [403] (code=PERMISSION_DENIED, message=ACTION_CONTRACT_AUTHORITY_MISSING, reason_code=PERMISSION_DENIED, classification=fail_closed_undeclared_action_authority)
