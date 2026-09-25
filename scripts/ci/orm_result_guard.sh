#!/usr/bin/env bash
# Shared Odoo ORM result guard.
#
# Sourced by the isolated container ORM runner so the real execution and the
# rejection rules cannot drift apart, and runnable standalone via `--self-test`
# on executors that cannot host a database container. Rejecting an absent test
# report matters as much as reporting a failure: Odoo exits zero when
# `--test-tags` matches nothing.
#
# The guard checks identity, collected count and the final result, not just the
# presence of any success summary: a log that reports success and then reports a
# failure (or a truncated/late report) must not pass.
#
# Collection and identity are proven from module-qualified test start lines
# (`odoo.addons.<module>.tests.<file>: Starting <Class>.<method>`). A bare
# `Starting ` match is not usable evidence: Odoo also logs lifecycle lines such
# as `odoo.service.server: Starting post tests`, which inflate the count and
# would reject a clean run whose count is pinned.
#
# Exit codes returned by evaluate_orm_outcome:
#   0  the run reported the expected identity/count and ended without failure
#   2  invalid caller configuration (timeout budget or expected count)
#   4  the run completed without any parsable test report, or reported zero
#   5  the expected test identity is absent from the log
#   6  the reported test count does not match the expectation/executions
#   7  the run exceeded its budget
#   8  a failure summary is present, or the log is internally inconsistent
#   n  any other non-zero Odoo process status, passed through unchanged
set -euo pipefail

orm_timeout_max_seconds="${ORM_TIMEOUT_MAX_SECONDS:-7200}"
# Empty means "not pinned": the count is then checked against the number of
# tests actually observed to start.
orm_expect_count="${orm_expect_count:-}"
# Space separated substrings that must appear on a module-qualified test start
# line (test module identity). A token that only shows up somewhere else in the
# log - a module listing, a traceback, a tag declaration - is not proof that the
# test executed.
orm_expect_identity="${orm_expect_identity:-}"

validate_orm_timeout() {
  local value="${1:-}"
  case "${value}" in
    (*[!0-9]*|'')
      echo "[orm-guard][FATAL] ORM timeout is not a positive integer: '${value}'" >&2
      return 2
      ;;
  esac
  if [[ "${value}" -eq 0 ]]; then
    echo "[orm-guard][FATAL] ORM timeout 0 disables the budget; a positive budget is required" >&2
    return 2
  fi
  if [[ "${value}" -gt "${orm_timeout_max_seconds}" ]]; then
    echo "[orm-guard][FATAL] ORM timeout ${value}s exceeds the ${orm_timeout_max_seconds}s ceiling" >&2
    return 2
  fi
  return 0
}

validate_orm_expect_count() {
  local value="${1:-}"
  [[ -z "${value}" ]] && return 0
  case "${value}" in
    (*[!0-9]*|'')
      echo "[orm-guard][FATAL] expected ORM test count is not a positive integer: '${value}'" >&2
      return 2
      ;;
  esac
  if [[ "${value}" -eq 0 ]]; then
    echo "[orm-guard][FATAL] expected ORM test count 0 would accept an empty run" >&2
    return 2
  fi
  return 0
}

# All `<failed> failed, <errors> error(s) of <total> tests` summaries, in order.
orm_summaries() {
  local log="$1"
  grep -Eo '[0-9]+ failed, [0-9]+ error\(s\) of [0-9]+ tests' "${log}" || true
}

# Odoo logs one start line per collected test case:
#   INFO db odoo.addons.<module>.tests.<file>: Starting <Class>.<method> ...
# Only that shape proves a test case was collected and executed.
orm_test_start_pattern='odoo\.addons\.[[:alnum:]_.]+: Starting [[:alpha:]_][[:alnum:]_]*\.'

orm_test_starts() {
  local log="$1"
  grep -E -- "${orm_test_start_pattern}" "${log}" || true
}

evaluate_orm_outcome() {
  local status="$1"
  local log="$2"
  local summaries last_summary last_total observed started expected

  if [[ "${status}" -eq 124 || "${status}" -eq 137 ]]; then
    echo "[orm-guard][FATAL] ORM test exceeded ${orm_timeout_seconds:-unset}s" >&2
    return 7
  fi
  if [[ "${status}" -ne 0 ]]; then
    echo "[orm-guard][FATAL] real ORM test process failed with ${status}" >&2
    return "${status}"
  fi
  if [[ ! -f "${log}" ]]; then
    echo "[orm-guard][FATAL] ORM test log is missing" >&2
    return 4
  fi

  validate_orm_expect_count "${orm_expect_count}" || return 2

  summaries="$(orm_summaries "${log}")"
  if [[ -z "${summaries}" ]]; then
    echo "[orm-guard][FATAL] Odoo did not report any executed ORM test" >&2
    return 4
  fi

  # A single passing summary is not enough: every summary must be clean and the
  # last one is the final word.
  if [[ "$(printf '%s\n' "${summaries}" | grep -c '^0 failed, 0 error(s) of ' || true)" -ne "$(printf '%s\n' "${summaries}" | grep -c . )" ]]; then
    echo "[orm-guard][FATAL] the ORM report contains a failing summary:" >&2
    printf '%s\n' "${summaries}" | sed 's/^/[orm-guard]   /' >&2
    return 8
  fi

  last_summary="$(printf '%s\n' "${summaries}" | tail -n 1)"
  last_total="$(printf '%s' "${last_summary}" | sed -n 's/^0 failed, 0 error(s) of \([0-9]\+\) tests$/\1/p')"
  if [[ -z "${last_total}" ]]; then
    echo "[orm-guard][FATAL] unusable final ORM summary: ${last_summary}" >&2
    return 8
  fi
  if [[ "${last_total}" -eq 0 ]]; then
    echo "[orm-guard][FATAL] Odoo reported zero executed ORM tests" >&2
    return 4
  fi

  # Collected count: pinned expectation when provided, otherwise the number of
  # tests the log itself shows starting.
  starts="$(orm_test_starts "${log}")"
  started="$(printf '%s\n' "${starts}" | grep -c . || true)"
  observed="${started}"
  if [[ -n "${orm_expect_count}" ]]; then
    expected="${orm_expect_count}"
    if [[ "${last_total}" -ne "${expected}" ]]; then
      echo "[orm-guard][FATAL] collected ${last_total} tests, expected ${expected}" >&2
      return 6
    fi
    if [[ "${started}" -ne "${expected}" ]]; then
      echo "[orm-guard][FATAL] log shows ${started} test starts, expected ${expected}" >&2
      return 6
    fi
  else
    if [[ "${started}" -eq 0 ]]; then
      echo "[orm-guard][FATAL] no test start line in the log; collection is unproven" >&2
      return 8
    fi
    if [[ "${started}" -ne "${last_total}" ]]; then
      echo "[orm-guard][FATAL] summary reports ${last_total} tests but ${started} started" >&2
      return 6
    fi
  fi

  # Identity: the expected test module(s) must appear on a test start line, so
  # a token that merely occurs somewhere in the log cannot satisfy the pin.
  if [[ -z "${starts}" ]]; then
    echo "[orm-guard][FATAL] no module-qualified test start line; collection is unproven" >&2
    return 8
  fi
  local token
  for token in ${orm_expect_identity}; do
    if ! printf '%s\n' "${starts}" | grep -qF -- "${token}"; then
      echo "[orm-guard][FATAL] expected test identity never started in the log: ${token}" >&2
      return 5
    fi
  done

  echo "[orm-guard] ORM_RESULT_GUARD=PASS tests=${observed} expected=${orm_expect_count:-self}" \
       "identity=${orm_expect_identity:-unpinned}"
  return 0
}

if [[ "${1:-}" == "--self-test" ]]; then
  selftest_dir="$(mktemp -d)"
  trap 'find "${selftest_dir:?}" -depth -delete' EXIT
  identity_token="test_payment_settlement_component_profile"
  starting_line="2026-09-24 00:00:00,000 1 INFO db odoo.addons.smart_construction_core.tests.${identity_token}: Starting TestPaymentSettlementComponentProfile.test_case ..."

  # A real log carries server lifecycle lines that also contain "Starting "
  # (`odoo.service.server: Starting post tests`). They must not be counted as
  # collected tests, so every fixture log below carries one.
  lifecycle_decoy="2026-09-24 00:00:00,000 1 INFO db odoo.service.server: Starting post tests "

  write_log() { # $1=file $2=count $3=summary
    local i
    : >"$1"
    printf '%s\n' "${lifecycle_decoy}" >>"$1"
    for ((i = 0; i < $2; i++)); do printf '%s\n' "${starting_line}" >>"$1"; done
    printf '%s\n' "$3" >>"$1"
  }

  write_log "${selftest_dir}/pass.log" 7 '0 failed, 0 error(s) of 7 tests'
  write_log "${selftest_dir}/zero.log" 0 '0 failed, 0 error(s) of 0 tests'
  write_log "${selftest_dir}/short.log" 6 '0 failed, 0 error(s) of 6 tests'
  printf 'misc output\n' >"${selftest_dir}/empty.log"
  write_log "${selftest_dir}/mixed.log" 7 '0 failed, 0 error(s) of 7 tests'
  printf '1 failed, 0 error(s) of 7 tests\n' >>"${selftest_dir}/mixed.log"
  write_log "${selftest_dir}/failed.log" 7 '1 failed, 0 error(s) of 7 tests'
  write_log "${selftest_dir}/error.log" 7 '0 failed, 2 error(s) of 7 tests'
  write_log "${selftest_dir}/summary_only.log" 0 '0 failed, 0 error(s) of 7 tests'
  write_log "${selftest_dir}/mismatch.log" 6 '0 failed, 0 error(s) of 7 tests'
  write_log "${selftest_dir}/foreign.log" 7 '0 failed, 0 error(s) of 7 tests'
  printf '%s\n' "${starting_line/test_payment_settlement_component_profile/test_some_other_suite}" >"${selftest_dir}/foreign.log"
  for ((i = 1; i < 7; i++)); do printf '%s\n' "${starting_line/test_payment_settlement_component_profile/test_some_other_suite}" >>"${selftest_dir}/foreign.log"; done
  printf '0 failed, 0 error(s) of 7 tests\n' >>"${selftest_dir}/foreign.log"
  # Identity text that never reaches a test start line (module listing only)
  # must not satisfy the identity pin: the executed tests come from another
  # suite while the pinned token only shows up in a loading line.
  write_log "${selftest_dir}/identity_offline.log" 0 '0 failed, 0 error(s) of 7 tests'
  for ((i = 0; i < 7; i++)); do
    printf '%s\n' "${starting_line/test_payment_settlement_component_profile/test_some_other_suite}" \
      >>"${selftest_dir}/identity_offline.log"
  done
  printf '%s\n' \
    "2026-09-24 00:00:00,000 1 INFO db odoo.modules.loading: loading ${identity_token}/tests/x.xml" \
    >>"${selftest_dir}/identity_offline.log"

  checks=0
  expect_code() { # $1=expected $2=count_pin $3=identity $4=status $5=log
    local expected="$1" actual
    orm_expect_count="$2"
    orm_expect_identity="$3"
    set +e
    evaluate_orm_outcome "$4" "$5" >/dev/null 2>&1
    actual="$?"
    set -e
    if [[ "${actual}" -ne "${expected}" ]]; then
      echo "[orm-guard][FATAL] expected exit ${expected}, got ${actual} for ${5}" >&2
      exit 2
    fi
    checks=$((checks + 1))
  }

  # timeout budget validation
  expect_timeout_code() { # $1=expected $2=value
    local expected="$1" actual
    set +e
    ( validate_orm_timeout "$2" ) >/dev/null 2>&1
    actual="$?"
    set -e
    if [[ "${actual}" -ne "${expected}" ]]; then
      echo "[orm-guard][FATAL] timeout '${2}': expected ${expected}, got ${actual}" >&2
      exit 2
    fi
    checks=$((checks + 1))
  }

  expect_code 0 7 "${identity_token}" 0 "${selftest_dir}/pass.log"
  expect_code 4 7 "${identity_token}" 0 "${selftest_dir}/zero.log"
  expect_code 4 7 "${identity_token}" 0 "${selftest_dir}/empty.log"
  expect_code 4 7 "${identity_token}" 0 "${selftest_dir}/does-not-exist.log"
  expect_code 6 7 "${identity_token}" 0 "${selftest_dir}/short.log"
  expect_code 6 7 "${identity_token}" 0 "${selftest_dir}/summary_only.log"
  expect_code 8 7 "${identity_token}" 0 "${selftest_dir}/mixed.log"
  expect_code 8 7 "${identity_token}" 0 "${selftest_dir}/failed.log"
  expect_code 8 7 "${identity_token}" 0 "${selftest_dir}/error.log"
  expect_code 5 7 "${identity_token}" 0 "${selftest_dir}/foreign.log"
  expect_code 5 7 "${identity_token}" 0 "${selftest_dir}/identity_offline.log"
  expect_code 5 "" "${identity_token}" 0 "${selftest_dir}/identity_offline.log"
  # unpinned: the count must still agree with the executions the log shows
  expect_code 0 "" "${identity_token}" 0 "${selftest_dir}/pass.log"
  expect_code 6 "" "${identity_token}" 0 "${selftest_dir}/mismatch.log"
  expect_code 8 "" "${identity_token}" 0 "${selftest_dir}/summary_only.log"
  expect_code 1 7 "${identity_token}" 1 "${selftest_dir}/pass.log"
  expect_code 7 7 "${identity_token}" 124 "${selftest_dir}/pass.log"
  expect_code 7 7 "${identity_token}" 137 "${selftest_dir}/pass.log"
  expect_code 2 0 "${identity_token}" 0 "${selftest_dir}/pass.log"
  # a missing identity pin must be rejected by the guard and by the validator
  expect_code 5 "" "${identity_token}" 0 "${selftest_dir}/foreign.log"
  expect_timeout_code 0 3600
  expect_timeout_code 0 45
  expect_timeout_code 2 0
  expect_timeout_code 2 -5
  expect_timeout_code 2 7201
  expect_timeout_code 2 ''
  expect_timeout_code 2 '1h'

  echo "[orm-guard] ORM_RESULT_GUARD_SELFTEST=PASS checks=${checks}"
  exit 0
fi
