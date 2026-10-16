# Platform SLA Report

- iterations: 6
- target_count: 3
- error_count: 0
- warning_count: 1

| intent | p95_ms | p95_limit | max_payload_bytes | payload_limit | statuses |
|---|---:|---:|---:|---:|---|
| system.init | 626.31 | 8000.00 | 238316 | 3500000 | 200 |
| ui.contract | 823.10 | 5000.00 | 621388 | 3500000 | 200 |
| execute_button | 22.94 | 3000.00 | 683 | 600000 | 403 |

## Errors

- none

## Warnings

- execute_button has non-2xx statuses in SLA run: [403]
