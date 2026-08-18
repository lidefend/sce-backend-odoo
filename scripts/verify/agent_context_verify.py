from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / 'AGENTS.md'
AGENT_DIR = ROOT / '.agent'
CONTEXT = AGENT_DIR / 'context.yaml'
GOALS_DIR = AGENT_DIR / 'goals'
DECISIONS_DIR = AGENT_DIR / 'decisions'
RUNS_DIR = AGENT_DIR / 'runs'


def fail(msg: str) -> int:
    print(msg)
    return 1


def main() -> int:
    agents_text = AGENTS.read_text(encoding='utf-8') if AGENTS.exists() else ''
    if '.agent/context.yaml' not in agents_text and '.agent/' not in agents_text:
        return fail('AGENTS_MISSING_AGENT_CONTEXT_REFERENCE')

    if not CONTEXT.exists():
        return fail('MISSING_CONTEXT_FILE')

    goals = list(GOALS_DIR.glob('*.yaml'))
    if not goals:
        return fail('MISSING_GOALS')

    decisions = list(DECISIONS_DIR.glob('*.yaml'))
    if not decisions:
        return fail('MISSING_DECISIONS')

    runs = list((RUNS_DIR).glob('*'))
    run_goal_yaml_exists = any((run / 'goal.yaml').exists() for run in runs if run.is_dir())
    if not run_goal_yaml_exists:
        return fail('MISSING_RUN_GOAL_RECORD')

    print('ENGINEERING_CONTEXT_READY')
    return 0


if __name__ == '__main__':
    sys.exit(main())
