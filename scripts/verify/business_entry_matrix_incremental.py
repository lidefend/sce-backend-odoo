#!/usr/bin/env python3
"""Reuse-first entry for the declaration-driven business-entry matrix.

This is the governed way to (re)validate the business-entry matrix.  It never
decides by itself what to run: it declares the matrix surface as evidence units,
asks the systemic reuse engine (``scripts/ops/evidence_scope.py``) what is still
affected under the current inputs, executes exactly that key set through the
existing browser probe, and records the outcome back into the ledger.

Consequences that the caller can rely on:

* an unchanged, already-passed entry is **not** re-collected (``reuse first``);
* a targeted rerun of a covered entry is refused unless ``--reverify-reason``
  states why re-collecting is justified;
* a failed entry is not silently retried; it stays blocked until its inputs
  change or the recovery is stated;
* a full re-walk of every declared entry is only possible with the explicit
  ``--full --reason`` flag, so the expensive path is never the default;
* a corrected *mapping* can be re-applied to an already-collected observation
  through ``--record-existing --record-existing-reason``, which executes nothing
  and re-folds the bound ``summary.json`` instead of re-walking the surface.

The probe itself is unchanged: this entry only supplies the key set and folds
the resulting ``summary.json`` back into the ledger.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = 'verify.frontend.business_entry.matrix.browser'
RUNTIME_VERSION_PATH = '/api/runtime-version'
BUNDLE_IDENTITY_KEY = 'frontend_build_sha256'
BUNDLE_IDENTITY_ENV = 'SC_ACCEPTANCE_FRONTEND_BUILD_SHA'
BUNDLE_FINGERPRINT = re.compile(r'^[0-9a-f]{64}$')
SCOPE_ADAPTER = 'scripts/verify/business_entry_matrix_scope.mjs'
BROWSER_PROBE = 'scripts/verify/business_entry_matrix_browser.mjs'
ENGINE = 'scripts/ops/evidence_scope.py'

# Evidence must land in a stable, declared location. The governed Make target
# forwards SC_ACCEPTANCE_OUTPUT_DIR even when the caller left it unset, so an
# empty/blank value must fall back to the default directory instead of resolving
# to the repository root (Path('') == '.') and leaking summary.json into the
# worktree.
#
# The fallback is also per-run: the ledger records the summary.json each unit
# was folded from, so a *fixed* default path would let a later, narrower run
# overwrite an earlier run's evidence and silently break those source pointers.
# That would make a targeted reverification destroy an unrelated unit's proof,
# which is exactly what the reuse-first ledger must never allow.
DEFAULT_OUTPUT_DIR = 'artifacts/frontend-business-entry-matrix/incremental'


def default_run_dir(stamp: str, selection: str) -> Path:
    digest = hashlib.sha256(selection.encode('utf-8')).hexdigest()[:12]
    return Path(DEFAULT_OUTPUT_DIR) / f'{stamp}-{digest}'


def resolve_output_dir(env: dict | None = None, *, stamp: str | None = None, selection: str = '') -> Path:
    """Resolve this run's evidence directory.

    An explicit ``SC_ACCEPTANCE_OUTPUT_DIR`` is honoured verbatim. Without one
    the evidence stays under the declared default directory but in a per-run
    subdirectory, so no run can overwrite another run's recorded evidence.
    """
    source = os.environ if env is None else env
    explicit = (source.get('SC_ACCEPTANCE_OUTPUT_DIR') or '').strip()
    if explicit:
        return Path(explicit)
    resolved_stamp = stamp or datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return default_run_dir(resolved_stamp, selection)


class IncrementalError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IncrementalError(message)


def run(command: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, env=env, check=False, text=True, capture_output=True)


def run_checked(command: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    result = run(command, env)
    if result.returncode != 0:
        raise IncrementalError(
            f"{' '.join(command)} failed ({result.returncode}): "
            f"{(result.stderr or result.stdout).strip()[:400]}"
        )
    return result


def load_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise IncrementalError(f"cannot read the JSON document {path}: {exc}") from exc


def resolve_reuse_bundle_identity(base_url: str, *, timeout: float = 20.0) -> str:
    """Read the served frontend bundle identity the reuse decision must bind.

    The deployed commit changes on every mainline merge, including merges that
    never rebuild the frontend, so binding it re-walked every declared entry on
    every deployment. The served artifact fingerprint the runtime publishes as
    ``frontend_build_sha256`` changes exactly when the served bundle changed,
    which is the input the entry assertions actually depend on.

    This is deliberately fail-closed rather than fail-hard: a runtime that does
    not publish a bundle fingerprint cannot prove cross-bundle equivalence, so
    the caller degrades to the deployed revision (the previous, conservative
    behaviour) and reports the degraded key instead of silently reusing across
    bundles. The probe independently refuses any bundle that does not match the
    value bound here, so the observation stays bound to the bundle it names.
    """
    url = str(base_url or '').strip().rstrip('/')
    if not url:
        return ''
    try:
        with urllib.request.urlopen(f'{url}{RUNTIME_VERSION_PATH}', timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (OSError, ValueError, urllib.error.URLError):
        return ''
    value = str(payload.get(BUNDLE_IDENTITY_KEY) or '').strip().lower() if isinstance(payload, dict) else ''
    return value if BUNDLE_FINGERPRINT.fullmatch(value) else ''


def require_environment() -> dict:
    required = {
        'SC_ACCEPTANCE_FRONTEND_URL': os.environ.get('SC_ACCEPTANCE_FRONTEND_URL', '').strip(),
        'SC_ACCEPTANCE_TARGET_SHA': os.environ.get('SC_ACCEPTANCE_TARGET_SHA', '').strip(),
        'ACCEPTANCE_LOGIN': os.environ.get('ACCEPTANCE_LOGIN', '').strip(),
        'ACCEPTANCE_PASSWORD': os.environ.get('ACCEPTANCE_PASSWORD', '').strip(),
    }
    missing = [name for name, value in required.items() if not value]
    _require(not missing, f"the registered runtime is not fully bound; missing {missing}")
    return required



def record_existing(summary_path: Path, plan_path: Path, *, run_dir: Path, ledger: str,
                    environment: dict, database: str) -> int:
    """Re-fold an already-collected probe summary into the ledger.

    This exists for exactly one situation: the *mapping* from an observation to
    a recorded per-unit status was wrong, so the ledger mis-states a run that
    was actually collected correctly. Re-executing the surface to repair a
    recording bug would re-collect evidence under unchanged inputs, which the
    reuse-first contract forbids; re-folding the bound observation repairs the
    record without touching the runtime.

    It is fail-closed: the summary must be the declared schema, must belong to
    the exact bound target revision and database, must name the declared entries
    it covered, and the plan that binds ``planned_affected`` must be supplied.
    A summary that still carries non-success entries exits non-zero, so a
    re-fold can never be mistaken for a fresh passing walk.
    """
    _require(summary_path.exists(), f"the recorded observation {summary_path} does not exist")
    summary = load_json(summary_path)
    _require(summary.get('schema') == 'business_entry_matrix_browser.v1',
             f"{summary_path}: unexpected schema {summary.get('schema')!r}")
    expected = environment['SC_ACCEPTANCE_TARGET_SHA']
    _require(str(summary.get('target_sha') or '') == expected,
             f"{summary_path}: target_sha {summary.get('target_sha')!r} != bound SC_ACCEPTANCE_TARGET_SHA {expected!r}")
    served = str(summary.get('served_revision') or '')
    _require(not served or served == expected,
             f"{summary_path}: served_revision {served!r} != bound target {expected!r}")
    observed_database = str(summary.get('database') or '')
    _require(not database or not observed_database or observed_database == database,
             f"{summary_path}: database {observed_database!r} != bound database {database!r}")
    keys = [str(key) for key in (summary.get('selection') or {}).get('keys') or []]
    _require(bool(keys), f"{summary_path}: the observation names no selected entry, so it cannot cover the surface")
    _require(plan_path.exists(), f"{plan_path} is required to bind planned_affected for the re-fold")

    results_path = run_dir / 'results.json'
    run_checked(['node', SCOPE_ADAPTER, '--emit-results', str(results_path),
                 '--summary', str(summary_path), '--plan', str(plan_path)])
    recorded = load_json(results_path)
    statuses = recorded.get('results') or {}
    non_success = sorted(key for key, status in statuses.items()
                         if str(status) not in ('passed', 'checked', 'declared', 'reused'))
    run_checked(['python3', ENGINE, 'record', '--units', str(run_dir / 'units.json'), '--ledger', ledger,
                 '--results', str(results_path), '--source', f'{summary_path}#record_only',
                 '--json-out', str(run_dir / 'record.json')])
    print(f"[business-entry-incremental] RECORD-ONLY re-folded {len(statuses)} entries from {summary_path} "
          f"({len(non_success)} non-success); no probe was executed")
    if non_success:
        print(f"[business-entry-incremental] still non-success: {non_success[:10]}")
        return 1
    return 0


def partial_fold_plan(folded: dict, selected_count: int) -> dict:
    """Decide what a (possibly partial) probe observation may be folded into.

    The engine never silently retries a recorded failure, so an interrupted run
    that stamped its unreached entries as ``failed`` would block the very
    entries the next pass must resume. The probe therefore declares
    ``completeness:partial`` and carries only the conclusions it actually
    reached; this decides how many of them may be folded, and whether the
    surface is still incomplete. A partial observation that concluded nothing
    records nothing, keeping the whole selection affected for the next pass.
    """
    executed = folded.get('executed_units') or []
    partial = folded.get('partial') is True
    folded_count = len(executed)
    return {
        'partial': partial,
        'record': bool(executed),
        'folded': folded_count,
        'selected': selected_count,
        'unreached': selected_count - folded_count if partial else 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--requested', default=os.environ.get('SC_ENTRY_MATRIX_KEYS', '').strip(),
                        help='comma separated entries the caller wants re-executed')
    parser.add_argument('--reverify-reason', default=os.environ.get('SC_ENTRY_SCOPE_REVERIFY_REASON', '').strip(),
                        help='justification required to re-execute covered entries')
    parser.add_argument('--full', action='store_true', default=os.environ.get('SC_ENTRY_SCOPE_FULL', '').strip() in ('1', 'true', 'yes'),
                        help='re-walk every declared entry (requires --reason)')
    parser.add_argument('--reason', default=os.environ.get('SC_ENTRY_SCOPE_FULL_REASON', '').strip(),
                        help='justification required for --full')
    parser.add_argument('--run-dir', default='', help='override the working directory for units/selection/results')
    parser.add_argument('--ledger', default=os.environ.get('SC_ENTRY_SCOPE_LEDGER', '').strip(),
                        help='override the evidence ledger path')
    parser.add_argument('--record-existing', default=os.environ.get('SC_ENTRY_SCOPE_RECORD_EXISTING', '').strip(),
                        help='re-fold this already-collected summary.json with the current mapping; executes nothing')
    parser.add_argument('--record-existing-reason', default=os.environ.get('SC_ENTRY_SCOPE_RECORD_EXISTING_REASON', '').strip(),
                        help='justification required to re-fold an existing observation')
    parser.add_argument('--plan', default=os.environ.get('SC_ENTRY_SCOPE_PLAN', '').strip(),
                        help='plan document that binds planned_affected when re-folding existing evidence')
    args = parser.parse_args(argv)

    environment = require_environment()
    bundle_identity = resolve_reuse_bundle_identity(environment['SC_ACCEPTANCE_FRONTEND_URL'])
    if bundle_identity:
        os.environ[BUNDLE_IDENTITY_ENV] = bundle_identity
        print(f"[business-entry-incremental] reuse identity binds {BUNDLE_IDENTITY_KEY}={bundle_identity}")
    else:
        os.environ.pop(BUNDLE_IDENTITY_ENV, None)
        print(f"[business-entry-incremental] WARN the runtime published no {BUNDLE_IDENTITY_KEY}; reuse degrades "
              f"to the deployed revision and every entry re-opens on a new deployment")
    if args.full:
        _require(bool(args.reason.strip()), '--full re-collects every entry and requires an explicit --reason')
    if args.record_existing:
        _require(bool(args.record_existing_reason.strip()),
                 '--record-existing re-folds already-collected evidence and requires an explicit '
                 '--record-existing-reason')

    run_dir = Path(args.run_dir) if args.run_dir else ROOT / '.runtime' / 'evidence-scope' / CHECK
    run_dir.mkdir(parents=True, exist_ok=True)
    units_path = run_dir / 'units.json'
    selection_path = run_dir / 'selection.json'
    results_path = run_dir / 'results.json'
    ledger = args.ledger or str(ROOT / '.runtime' / 'evidence-scope' / f'{CHECK}.json')

    run_checked(['node', SCOPE_ADAPTER, '--emit-units', str(units_path)])
    emitted = load_json(units_path)
    declared = [str(unit['id']) for unit in emitted['units']]
    print(f"[business-entry-incremental] declared={len(declared)} units")

    if args.record_existing:
        # Re-fold a bound observation instead of walking the surface. This runs
        # before the select step on purpose: select would overwrite the original
        # run's selection.json, and the re-fold must bind the *original* plan.
        _require(bool(args.plan.strip()),
                 '--record-existing requires --plan so planned_affected is bound to the run that produced '
                 'the observation')
        return record_existing(
            Path(args.record_existing),
            Path(args.plan),
            run_dir=run_dir,
            ledger=ledger,
            environment=environment,
            database=os.environ.get('SC_ACCEPTANCE_DATABASE', '') or os.environ.get('DB_NAME', ''),
        )

    if args.full:
        selection = {
            'schema': 'evidence_scope.selection.v1',
            'check': CHECK,
            'execute': declared,
            'affected': [],
            'requested': declared,
            'reused': [],
            're_evidenced': [],
            're_evidence_reason': args.reason,
            'reuse_first': False,
            'full_reason': args.reason,
        }
        selection_path.write_text(json.dumps(selection, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    else:
        run_checked([
            'python3', ENGINE, 'select',
            '--units', str(units_path), '--ledger', ledger,
            '--requested', args.requested, '--reverify-reason', args.reverify_reason,
            '--json-out', str(selection_path),
        ])
        selection = load_json(selection_path)
        print(f"[business-entry-incremental] reusable={len(selection['reused'])} affected={len(selection['affected'])}")

    execute = [str(key) for key in selection['execute']]
    if not execute:
        print('[business-entry-incremental] REUSE-FIRST nothing to execute; every declared entry is covered '
              'by unchanged inputs')
        return 0

    # Resolve the evidence directory only once the executed key set is known, so
    # the per-run fallback directory is derived from the inputs that produced it.
    output_dir = resolve_output_dir(selection=','.join(execute))

    print(f"[business-entry-incremental] executing {len(execute)} entr{'y' if len(execute) == 1 else 'ies'}")
    env = dict(os.environ)
    env['SC_ENTRY_MATRIX_KEYS'] = ','.join(execute)
    env['SC_ENTRY_MATRIX_INCLUDE_PASSED'] = '1'
    env['SC_ACCEPTANCE_OUTPUT_DIR'] = str(output_dir)
    probe = run(['node', BROWSER_PROBE], env)
    sys.stdout.write(probe.stdout)
    sys.stderr.write(probe.stderr)

    summary_path = output_dir / 'summary.json'
    _require(summary_path.exists(), f"the probe did not produce {summary_path}")
    run_checked(['node', SCOPE_ADAPTER, '--emit-results', str(results_path),
                 '--summary', str(summary_path), '--plan', str(selection_path)])
    decision = partial_fold_plan(load_json(results_path), len(execute))
    if not decision['record']:
        # An interrupted probe that reached no entry leaves nothing to fold. The
        # whole selection stays unrecorded, so the next pass resumes from it
        # instead of being refused as a set of unchanged failures.
        print('[business-entry-incremental] PARTIAL the probe concluded no entry; nothing was recorded and '
              'the selection stays affected for the next pass')
        return 1
    run_checked(['python3', ENGINE, 'record', '--units', str(units_path), '--ledger', ledger,
                 '--results', str(results_path), '--json-out', str(run_dir / 'record.json')])
    print(f"[business-entry-incremental] recorded {decision['folded']} of {decision['selected']} selected entries "
          f"into {ledger}")
    if decision['partial']:
        print(f"[business-entry-incremental] PARTIAL {decision['unreached']} selected entries were not reached; "
              f"they stay unrecorded and the next pass resumes from them")
    return 0 if probe.returncode == 0 else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except IncrementalError as exc:
        print(f"[business-entry-incremental] DENY {exc}", file=sys.stderr)
        raise SystemExit(2)
