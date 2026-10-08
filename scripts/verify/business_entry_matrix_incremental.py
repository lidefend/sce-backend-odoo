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
  ``--full --reason`` flag, so the expensive path is never the default.

The probe itself is unchanged: this entry only supplies the key set and folds
the resulting ``summary.json`` back into the ledger.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK = 'verify.frontend.business_entry.matrix.browser'
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
    args = parser.parse_args(argv)

    require_environment()
    if args.full:
        _require(bool(args.reason.strip()), '--full re-collects every entry and requires an explicit --reason')

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
    run_checked(['python3', ENGINE, 'record', '--units', str(units_path), '--ledger', ledger,
                 '--results', str(results_path), '--json-out', str(run_dir / 'record.json')])
    print(f"[business-entry-incremental] recorded {len(execute)} entries into {ledger}")
    return 0 if probe.returncode == 0 else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except IncrementalError as exc:
        print(f"[business-entry-incremental] DENY {exc}", file=sys.stderr)
        raise SystemExit(2)
