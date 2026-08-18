# Platform Performance Smoke

- target_count: 2
- iterations: 8
- error_count: 0
- warning_count: 1

| intent | avg_ms | p95_ms | max_payload_bytes | status_codes | p95_threshold | payload_threshold |
|---|---:|---:|---:|---|---:|---:|
| system.init | 1134.41 | 1384.12 | 178680 | 200 | 4000.00 | 3000000 |
| ui.contract | 998.58 | 1295.89 | 289109 | 200 | 3000.00 | 3000000 |

## Errors

- none
