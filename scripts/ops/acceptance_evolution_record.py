#!/usr/bin/env python3
"""Record exact-head acceptance evidence for the evolution binding guard.

Every ``--suite`` value is validated against the suite's declared adapter
before it is written to the manifest. The recorder therefore cannot turn an
arbitrary JSON file into "acceptance evidence": the file must carry the suite's
schema, a passing status, and the same exact head as the change under review.

Usage:
  python3 scripts/ops/acceptance_evolution_record.py \
    --base <merge-base> --head <head> \
    --suite daily_runtime_entry=.runtime/final-acceptance/daily-runtime-entry-verify.json \
    --suite path_namespace_identity=.runtime/final-acceptance/path-ns-c-acceptance.json \
    --output .runtime/acceptance-evolution/evidence.v1.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "verify"))

import acceptance_evolution_binding_guard as binding  # noqa: E402

DEFAULT_REGISTRY = ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
DEFAULT_OUTPUT = ROOT / ".runtime" / "acceptance-evolution" / "evidence.v1.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_suite_args(values: list[str]) -> dict[str, list[Path]]:
    suites: dict[str, list[Path]] = {}
    for value in values:
        suite_id, separator, raw_path = value.partition("=")
        if not separator or not suite_id or not raw_path:
            raise binding.BindingError(f"--suite must be ID=PATH, got {value!r}")
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / raw_path
        suites.setdefault(suite_id, []).append(path)
    return suites


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--base", help="base commit; defaults to BASE_SHA or origin/main merge-base")
    parser.add_argument("--head", help="head commit; defaults to HEAD_SHA or HEAD")
    parser.add_argument("--suite", action="append", default=[], metavar="ID=PATH")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    try:
        registry = binding.load_registry(Path(args.registry))
        head = binding.resolve_head(args.head)
        base = binding.resolve_base(args.base, head)
        plan = binding.build_plan(registry, binding.changed_files(base, head), base, head)
        if plan["status"] != "PASS":
            raise binding.BindingError(
                "change set is not fully classified; fix the registry before recording evidence"
            )
        provided = parse_suite_args(args.suite)
        unknown = sorted(set(provided) - set(registry["suites"]))
        if unknown:
            raise binding.BindingError(f"unknown suites: {unknown}")
        missing = sorted(set(plan["required_evidence_suites"]) - set(provided))
        if missing:
            raise binding.BindingError(
                "missing evidence for required suites: " + ", ".join(missing)
            )
        recorded: dict[str, dict] = {}
        for suite_id, paths in provided.items():
            evidence_contract = registry["suites"][suite_id].get("evidence")
            if not evidence_contract:
                raise binding.BindingError(
                    f"suite {suite_id} is covered by its governed lane and takes no evidence file"
                )
            adapter = evidence_contract["adapter"]
            items = []
            for path in paths:
                if not path.is_file():
                    raise binding.BindingError(f"evidence file missing: {path}")
                counts = binding.validate_evidence_file(path, adapter, head)
                items.append(
                    {
                        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                        "sha256": _sha256(path),
                        "adapter": adapter,
                        **counts,
                    }
                )
                print(f"[acceptance_evolution.record] {suite_id} <= {path}")
            recorded[suite_id] = {"status": "pass", "evidence": items}
        unrequested = sorted(set(recorded) - set(plan["required_evidence_suites"]))
        if unrequested:
            print(
                "[acceptance_evolution.record] note: non-required suites recorded: "
                + ", ".join(unrequested)
            )
        manifest = {
            "schema": binding.EVIDENCE_SCHEMA,
            "head_sha": head,
            "base_sha": base,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "suites": recorded,
        }
        binding.write_json(Path(args.output), manifest)
        print(
            f"[acceptance_evolution.record] PASS head={head[:12]} "
            f"suites={','.join(recorded) or 'none'} output={args.output}"
        )
        return 0
    except binding.BindingError as exc:
        print(f"[acceptance_evolution.record] FAIL {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
