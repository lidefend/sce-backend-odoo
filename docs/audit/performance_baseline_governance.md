# Performance Baseline Governance

## Purpose

This document defines how performance baseline numbers are produced and consumed by regression gates.

## Baseline Metadata (Required)

- Baseline source report: `artifacts/backend/platform_sla_report.json`
- Baseline commit/tag: must be recorded in PR/Release notes when baseline is refreshed.
- Baseline environment:
  - DB name
  - role/login used
  - host/container mode
  - cache state policy (cold/warm)

## Sampling Policy

- Warmup requests per round: default `20`
- Measured rounds: default `3`
- Iterations per round:
  - `system.init`: `200`
  - `ui.contract`: `200`
  - `execute_button`: `1000`
- Metrics:
  - `P50`, `P95`, `P99`, `max`, `variance`
  - status/error rate

## Regression Grading

- `PASS`: all rounds under warn threshold, error rate `0`
- `WARN`: threshold warning exceeded in one or more rounds, but fail criteria not met
- `FAIL`:
  - non-2xx status exists, or
  - fail-threshold exceeded in at least `2/3` rounds (configurable)

## Threshold Policy

- Generic fail threshold: `max(baseline*1.10, baseline+abs_delta)`
- Generic warn threshold: `max(baseline*1.05, baseline+warn_abs_delta)`
- `execute_button` uses extra absolute floor (default fail floor `80ms`) to reduce noise sensitivity.

## Baseline Refresh Rule

Refresh baseline only when:

1. major infra/runtime condition changed, or
2. validated performance improvement is accepted.

Any baseline refresh must include:

- previous vs new baseline diff
- reason for refresh
- exact command and environment notes

## Extended Baseline Carrier (2026-10-16)

The sampling policy, regression grading and threshold policy above are unchanged and still
grade the SLA-guard numbers in `artifacts/backend/platform_sla_report.json`.

A separate normalized carrier now records broader runtime observations without redefining
those thresholds:

- engine: `scripts/verify/system_performance_baseline.py` (schema `system-performance-baseline/v1`)
- managed collection: `make local.dev.runtime.performance.baseline`
- unit test: `make verify.system.performance.baseline.unit`
- record: `artifacts/backend/system_performance_baseline.json`; view: `docs/ops/audit/system_performance_baseline.md`
- rules: missing timings are recorded as gaps and never as zero; nested stage values are never
  summed; the observed and retained sample counts must agree
- layers: `controlled_regression` / `daily_experience` / `capacity`, each independently
  satisfied; `daily_experience` stays `not_run` and `capacity` stays `target_unresolved` until
  their identities are confirmed

`platform-sla-guard/v1` declares no product-code hash, so its layer identity stays `unknown` by
design and it is not a controlled-regression identity carrier.
