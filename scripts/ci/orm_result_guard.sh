#!/usr/bin/env bash
# Shared Odoo ORM result guard.
#
# Sourced by the isolated container ORM runner so the real execution and the
# rejection rules cannot drift apart, and runnable standalone via `--self-test`
# on executors that cannot host a database container. Rejecting an absent test
# report matters as much as reporting a failure: Odoo exits zero when
# `--test-tags` matches nothing.
#
# Exit codes returned by evaluate_orm_outcome:
#   0  a real run reported at least one executed test and no failure
#   4  the run completed but reported zero tests (or no parsable report)
#   7  the run exceeded its budget
#   n  any other non-zero Odoo process status, passed through unchanged
set -euo pipefail

evaluate_orm_outcome() {
  local status="$1"
  local log="$2"

  if [[ "$status" -eq 124 || "$status" -eq 137 ]]; then
    echo "[orm-guard][FATAL] ORM test exceeded ${orm_timeout_seconds:-unset}s" >&2
    return 7
  fi
  if [[ "$status" -ne 0 ]]; then
    echo "[orm-guard][FATAL] real ORM test process failed with ${status}" >&2
    return "$status"
  fi
  if [[ ! -f "$log" ]]; then
    echo "[orm-guard][FATAL] ORM test log is missing" >&2
    return 4
  fi
  if ! grep -Eq "0 failed, 0 error\\(s\\) of [1-9][0-9]* tests" "$log"; then
    echo "[orm-guard][FATAL] Odoo did not report any executed ORM test" >&2
    return 4
  fi
  return 0
}

if [[ "${1:-}" == "--self-test" ]]; then
  selftest_dir="$(mktemp -d)"
  trap 'find "${selftest_dir:?}" -depth -delete' EXIT
  printf '0 failed, 0 error(s) of 7 tests\n' >"${selftest_dir}/pass.log"
  printf '0 failed, 0 error(s) of 0 tests\n' >"${selftest_dir}/zero.log"
  printf 'misc output\n' >"${selftest_dir}/empty.log"

  checks=0
  expect_code() {
    local expected="$1"
    shift
    local actual
    set +e
    evaluate_orm_outcome "$@" >/dev/null 2>&1
    actual="$?"
    set -e
    if [[ "$actual" -ne "$expected" ]]; then
      echo "[orm-guard][FATAL] expected exit ${expected}, got ${actual}" >&2
      exit 2
    fi
    checks=$((checks + 1))
  }

  expect_code 0 0 "${selftest_dir}/pass.log"
  expect_code 4 0 "${selftest_dir}/zero.log"
  expect_code 4 0 "${selftest_dir}/empty.log"
  expect_code 4 0 "${selftest_dir}/does-not-exist.log"
  expect_code 1 1 "${selftest_dir}/pass.log"
  expect_code 7 124 "${selftest_dir}/pass.log"
  expect_code 7 137 "${selftest_dir}/pass.log"

  echo "[orm-guard] ORM_RESULT_GUARD_SELFTEST=PASS checks=${checks}"
  exit 0
fi
