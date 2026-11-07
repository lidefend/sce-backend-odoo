#!/usr/bin/env python3
"""Classify a change set into a fail-closed CI risk lane."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

try:
    from scripts.ci import ci_path_ownership
except ImportError:  # Direct script execution adds scripts/ci to sys.path.
    import ci_path_ownership


ROOT = Path(__file__).resolve().parents[2]
POLICY_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/ci/risk_tiering_v1.json"


@dataclass(frozen=True)
class Classification:
    lane: str
    paths: tuple[str, ...]
    reasons: tuple[str, ...]
    frontend_changed: bool
    backend_changed: bool
    control_plane_changed: bool
    backend_runtime_changed: bool
    ownership_categories: tuple[str, ...]
    frontend_full_required: bool
    orm_required: bool = True

    @property
    def frontend_mode(self) -> str:
        if self.lane == "RELEASE" or self.frontend_full_required:
            return "full"
        if self.frontend_changed:
            return "standard"
        return "skip"

    @property
    def professional_mode(self) -> str:
        if self.lane in {"HIGH_RISK", "RELEASE"}:
            return "full"
        if self.lane == "STANDARD" and self.backend_runtime_changed:
            return "standard_backend"
        if self.lane == "STANDARD":
            if self.frontend_changed:
                return "standard_frontend"
            if self.backend_changed or self.control_plane_changed:
                return "governance"
        return "fast"

    @property
    def orm_scopes(self) -> tuple[str, ...]:
        if not self.orm_required:
            return ()
        # Preserve the whole-PR module suite; dedicated regressions are additive.
        scopes = {'module_suite'}
        shared = ('addons/smart_core/**', 'Dockerfile*', 'docker-compose*',
                  'requirements*', 'config/requirements*', 'scripts/test/**',
                  'scripts/ci/orm_*', 'scripts/ci/*_orm_*',
                  'make/dev_test.mk', 'Makefile')
        payment = ('addons/smart_construction_core/**/*payment*',
                   'addons/smart_construction_core/**/*settlement*',
                   'addons/smart_construction_core/**/*component*profile*')
        navigation = ('addons/**/*navigation*', 'addons/**/*scenario*',
                      'addons/**/*menu*', 'addons/**/*business_scene*',
                      'addons/smart_construction_scene/models/product_policy.py',
                      'addons/smart_construction_scene/models/scene_company_enablement.py',
                      'addons/smart_construction_scene/services/enterprise_readiness_diagnosis.py',
                      'addons/smart_construction_scene/services/tenant_scene_activation.py')
        expand = (self.lane == 'RELEASE' or 'unknown_path_fail_closed' in self.reasons
                  or 'invalid_path' in self.reasons or any(_matches(p, shared) for p in self.paths))
        if expand or any(_matches(p, payment) for p in self.paths):
            scopes.add('payment_settlement')
        if expand or any(_matches(p, navigation) for p in self.paths):
            scopes.add('navigation_maintenance')
        return tuple(sorted(scopes))

    @property
    def managed_orm_required(self) -> bool:
        return ('navigation_maintenance' in self.orm_scopes or any(
            path.startswith('addons/smart_construction_acceptance_fixture/tests/') for path in self.paths))

    def outputs(self) -> dict[str, str]:
        return {
            "lane": self.lane,
            "frontend_mode": self.frontend_mode,
            "professional_mode": self.professional_mode,
            "frontend_changed": str(self.frontend_changed).lower(),
            "backend_changed": str(self.backend_changed).lower(),
            "control_plane_changed": str(self.control_plane_changed).lower(),
            "backend_runtime_changed": str(self.backend_runtime_changed).lower(),
            "ownership_categories_json": json.dumps(
                self.ownership_categories, separators=(",", ":")
            ),
            "orm_required": str(self.orm_required).lower(),
            "orm_scopes": ",".join(self.orm_scopes),
            "managed_orm_required": str(self.managed_orm_required).lower(),
            "payment_orm_required": str("payment_settlement" in self.orm_scopes).lower(),
            "frontend_full_required": str(self.frontend_full_required).lower(),
            "changed_path_count": str(len(self.paths)),
            "changed_paths_json": json.dumps(self.paths, separators=(",", ":")),
            "reasons_json": json.dumps(self.reasons, separators=(",", ":")),
        }


def validate_path_ownership_policy(data: dict) -> str:
    registry = data.get("path_ownership_registry")
    if (not isinstance(registry, str) or not registry
            or Path(registry).is_absolute() or ".." in Path(registry).parts
            or not (POLICY_ROOT / registry).is_file()):
        raise ValueError("path ownership registry must be an existing repository-relative file")
    return registry


def load_policy(path: Path = POLICY_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("default_lane") != "HIGH_RISK":
        raise ValueError("CI risk policy must fail closed to HIGH_RISK")
    validate_path_ownership_policy(data)
    return data


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _normalize_paths(paths: Iterable[str]) -> tuple[str, ...]:
    normalized: set[str] = set()
    for raw in paths:
        value = raw.strip().replace("\\", "/")
        if not value:
            continue
        pure = PurePosixPath(value)
        if pure.is_absolute() or ".." in pure.parts:
            normalized.add(f"__INVALID_PATH__/{value}")
        else:
            normalized.add(pure.as_posix())
    return tuple(sorted(normalized))


def backend_recipe_only(before: str, after: str) -> bool:
    """Recognize only literal Python recipe edits in the existing backend lock.

    Not a Make evaluator: retain every other byte, including the target's
    prerequisites, shared variables, directives, comments and echo commands.
    Dynamic expansion, shell composition and recipe continuations cannot be
    erased by this proof. The backend professional lane still runs this lock.
    """
    header = 'verify.ci.workflow.contract: guard.prod.forbid verify.ci.orm_selection.unit\n'
    command = re.compile(
        r'\t@python3 (?:scripts/(?:ci|verify)/[A-Za-z0-9_]+\.py'
        r'|-m unittest scripts\.(?:ci|verify)\.[A-Za-z0-9_]+'
        r'|-m py_compile scripts/(?:ci|verify)/[A-Za-z0-9_]+\.py)\n'
    )

    def retained(text: str) -> str | None:
        lines = text.splitlines(keepends=True)
        if lines.count(header) != 1:
            return None
        result = []
        inside = False
        for line in lines:
            if line == header:
                inside = True
            elif inside and not line.startswith('\t'):
                inside = False
            if not (inside and command.fullmatch(line)):
                result.append(line)
        return ''.join(result)

    old, new = retained(before), retained(after)
    return before != after and old is not None and old == new


def git_backend_recipe_only(base: str, head: str) -> bool:
    """Use the same merge base as changed_paths; never inspect dirty files."""
    if not all(re.fullmatch(r'[0-9a-f]{40}', sha) for sha in (base, head)):
        return False
    def git(*args: str) -> str:
        # Decode bytes explicitly: text=True would normalize CRLF/CR and hide
        # changes outside the owned recipe from the equality proof.
        return subprocess.run(['git', *args], cwd=ROOT, check=True,
                              capture_output=True, timeout=15).stdout.decode('utf-8')
    try:
        ancestor = git('merge-base', base, head).strip()
        texts = []
        for sha in (ancestor, head):
            entry = git('ls-tree', sha, '--', 'make/ci.mk')
            if not re.fullmatch(r'100644 blob [0-9a-f]{40}\tmake/ci\.mk\n', entry):
                return False
            texts.append(git('show', f'{sha}:make/ci.mk'))
        return backend_recipe_only(*texts)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False


def classify(
    paths: Iterable[str],
    *,
    event_name: str,
    ref: str = "",
    policy: dict | None = None,
    base: str = '',
    head: str = '',
) -> Classification:
    policy = policy or load_policy()
    ownership_registry = validate_path_ownership_policy(policy)
    orm_paths = policy.get("orm_runtime_paths")
    context_paths = policy.get("orm_non_runtime_context_paths", [])
    if (not isinstance(orm_paths, list) or not orm_paths
            or not all(isinstance(path, str) and path for path in orm_paths)
            or not isinstance(context_paths, list)
            or not all(isinstance(path, str) and path for path in context_paths)):
        raise ValueError("ORM dependency policy requires bounded string lists")
    changed = _normalize_paths(paths)
    ownership = ci_path_ownership.classify_paths(
        changed,
        registry_path=POLICY_ROOT / ownership_registry,
    )
    if event_name == "schedule":
        # A scheduled run has no PR base and no push `before` SHA, so the
        # change set is deliberately empty. It is still an owner-authorized
        # full audit of main, not an unclassified mutation: classify it as a
        # release-lane full audit instead of failing closed on the empty set.
        return Classification(
            "RELEASE",
            changed,
            ("schedule_full_audit",),
            True,
            True,
            True,
            True,
            tuple(sorted(set(ownership.assignments.values()))),
            True,
        )
    if event_name == "workflow_dispatch" or _matches(ref, policy["release_refs"]):
        return Classification(
            "RELEASE",
            changed,
            ("release_event",),
            True,
            True,
            True,
            True,
            tuple(sorted(set(ownership.assignments.values()))),
            True,
        )
    if not changed:
        return Classification(
            "HIGH_RISK",
            changed,
            ("empty_change_set_fail_closed",),
            True,
            True,
            True,
            True,
            (),
            True,
        )

    frontend = ownership.frontend_changed
    backend = ownership.backend_changed
    control_plane = ownership.control_plane_changed
    backend_runtime = ownership.backend_runtime_changed
    ownership_categories = tuple(sorted(set(ownership.assignments.values())))
    high_risk_override = tuple(
        path for path in changed
        if _matches(path, policy.get("high_risk_override_paths", ()))
    )
    high = tuple(
        path for path in changed
        if _matches(path, policy["high_risk_paths"])
        and path not in high_risk_override
    )
    high = high or tuple(
        path for path in changed
        if ownership.category_for(path) and ownership.category_for(path).risk == "high"
        and path not in high_risk_override
    )
    invalid = ownership.invalid_paths
    frontend_full = bool(ownership.frontend_full_required) or any(
        _matches(path, policy["frontend_full_paths"]) for path in changed
    )
    recipe_scoped = 'make/ci.mk' in changed and git_backend_recipe_only(base, head)
    if recipe_scoped:
        frontend_full = any(
            _matches(path, policy["frontend_full_paths"]) for path in changed
            if path != "make/ci.mk"
        )
    unknown = ownership.unknown_paths
    orm_required = bool(invalid or unknown or any(
        _matches(path, policy["orm_runtime_paths"]) for path in changed
    ))

    if high or invalid or unknown:
        reasons = []
        if high:
            reasons.append("high_risk_path")
        if invalid:
            reasons.append("invalid_path")
        if unknown:
            reasons.append("unknown_path_fail_closed")
        if recipe_scoped:
            reasons.append('make_ci_backend_recipe_only_exact_git_scope')
        return Classification(
            "HIGH_RISK",
            changed,
            tuple(reasons),
            frontend,
            backend,
            control_plane,
            backend_runtime,
            ownership_categories,
            frontend_full,
            orm_required,
        )
    if frontend or backend:
        return Classification(
            "STANDARD",
            changed,
            ("standard_runtime_change",),
            frontend,
            backend,
            control_plane,
            backend_runtime,
            ownership_categories,
            frontend_full,
            orm_required,
        )
    return Classification(
        "FAST",
        changed,
        ("non_runtime_change",),
        frontend,
        backend,
        control_plane,
        backend_runtime,
        ownership_categories,
        frontend_full,
        False,
    )


def changed_paths(base: str, head: str) -> tuple[str, ...]:
    if not base or not head:
        raise ValueError("base and head SHA are required")
    command = ["git", "diff", "--name-only", "--no-renames", f"{base}...{head}", "--"]
    result = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True)
    return tuple(result.stdout.splitlines())


def write_github_output(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            if "\n" in value:
                raise ValueError(f"multiline GitHub output is forbidden: {key}")
            stream.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--event", required=True)
    parser.add_argument("--ref", default="")
    parser.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    paths = tuple(args.paths or ())
    if not paths and args.event != "workflow_dispatch":
        paths = changed_paths(args.base or "", args.head or "")
    result = classify(paths, event_name=args.event, ref=args.ref,
                      base=(args.base or '') if not args.paths else '',
                      head=(args.head or '') if not args.paths else '')
    outputs = result.outputs()
    report = {
        "schema_version": "ci-risk-classification/v1",
        **outputs,
        "changed_paths": list(result.paths),
        "reasons": list(result.reasons),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    output_path = args.github_output or (
        Path(os.environ["GITHUB_OUTPUT"]) if os.environ.get("GITHUB_OUTPUT") else None
    )
    if output_path:
        write_github_output(output_path, outputs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
