#!/usr/bin/env python3
"""Observe the fixed nightly window; GitHub cron is not a punctuality SLA."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

CRON = '30 18 * * *'  # 02:30 Asia/Shanghai, without DST.


def scheduled_slot(created_at: str) -> str:
    created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    if created.tzinfo is None:
        raise ValueError('scheduled timestamp requires a timezone')
    created = created.astimezone(timezone.utc)
    slot = created.replace(hour=18, minute=30, second=0, microsecond=0)
    if created < slot:
        slot -= timedelta(days=1)
    return slot.isoformat()


def observation(run: dict) -> dict:
    if run.get('event') != 'schedule':
        raise ValueError('not a scheduled run')
    slot = scheduled_slot(run['created_at'])
    created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
    nominal = datetime.fromisoformat(slot)
    return {'nominal_slot_utc': slot,
            'nominal_slot_shanghai': nominal.astimezone(timezone(timedelta(hours=8))).isoformat(),
            'created_at': run['created_at'], 'attempt': run['run_attempt'],
            'attempt_started_at': run['run_started_at'],
            'trigger_delay_minutes': round((created - nominal).total_seconds() / 60, 1)}


def main() -> None:
    from backend_test_receipt import github_bytes
    run_id = os.environ['GITHUB_RUN_ID']
    if not run_id.isdigit():
        raise ValueError('invalid run id')
    run = json.loads(github_bytes(f'actions/runs/{run_id}'))
    if run.get('head_sha') != os.environ['GITHUB_SHA']:
        raise ValueError('schedule head mismatch')
    result = observation(run)
    with Path(os.environ['GITHUB_ENV']).open('a') as target:
        target.write(f"SCHEDULED_SLOT={result['nominal_slot_utc']}\n")
    with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as target:
        target.write('### Scheduled full validation\n\n')
        for key, value in result.items():
            target.write(f'- {key}: {value}\n')
        target.write('\nSlot inferred from the preceding daily 18:30 UTC boundary; '
                     'delays of 24 hours or more cannot be identified by GitHub schedule payloads. '
                     'Attempt start includes retries and is not first-run queue time.\n')
    if result['trigger_delay_minutes'] > 30:
        print(f"::warning::Scheduled trigger delayed {result['trigger_delay_minutes']} minutes; cron remained {CRON}")


if __name__ == '__main__':
    main()
