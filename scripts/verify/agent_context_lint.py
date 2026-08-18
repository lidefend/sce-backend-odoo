from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]


def check_yaml(path: Path) -> None:
    with path.open() as f:
        yaml.safe_load(f)


def main() -> int:
    agent_dir = ROOT / ".agent"

    required_context = agent_dir / "context.yaml"
    required_goals_dir = agent_dir / "goals"
    required_decisions_dir = agent_dir / "decisions"

    for item in (required_context, required_goals_dir, required_decisions_dir):
        if not item.exists():
            print(f"MISSING: {item}")
            return 1

    try:
        check_yaml(required_context)
        for path in required_goals_dir.glob("*.yaml"):
            check_yaml(path)
        for path in required_decisions_dir.glob("*.yaml"):
            check_yaml(path)
    except Exception as exc:
        print(f"INVALID_YAML: {exc}")
        return 1

    print("AGENT_CONTEXT_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
