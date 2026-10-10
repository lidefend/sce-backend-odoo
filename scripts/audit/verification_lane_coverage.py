#!/usr/bin/env python3
"""Verification-system lane coverage audit (read-only instrument).

Why this exists
---------------
The repository drives two very different audiences from one ``make`` surface:
the remote required gates (``public_guard`` / ``merge_policy_gate`` /
``professional_quality_gate`` / ``frontend_release_gate``) and the governed
local lane (``ci.local.quick``).  Both are hand-maintained target lists, so they
drift.  A guard executed only by ``ci.local.quick`` merges green remotely and
only fails at the local exact-head Quick; a guard executed only remotely makes a
local pass prove something different from a remote pass.  That divergence is
the structural reason a remote result cannot be reused locally, and it is the
reason "CI green / local red" keeps recurring.

This instrument measures that divergence instead of arguing about it:

  * make target inventory plus its prerequisite / ``$(MAKE)`` recursion graph;
  * which targets each declared gate anchor can reach;
  * which guard scripts each execution lane actually executes;
  * which targets and scripts are referenced nowhere at all (dead surface).

``--check`` compares the measurement with ``verification_lane_baseline.json``.
The baseline freezes today's known debt and forbids growth, so a batch can only
shrink the number.  ``--check`` is the only mode that can exit non-zero, and it
does so only when the surface grew past the frozen baseline.

Read-only by default.  ``--json`` writes only to the path you pass;
``--write-baseline`` rewrites the baseline and is a deliberate, reviewed
governance action, never part of ordinary measurement.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = Path(__file__).resolve().parent / "verification_lane_baseline.json"
DEFAULT_EXEMPTIONS = Path(__file__).resolve().parent / "verification_lane_exemptions.json"
DEFAULT_DISPOSITIONS = Path(__file__).resolve().parent / "verification_lane_dispositions.json"

NAME = r"[A-Za-z0-9_][A-Za-z0-9_.\-]*"
VAR_RE = re.compile(r"^\s*(?:export\s+|override\s+|private\s+)?[A-Za-z_][A-Za-z0-9_.\-]*\s*(?::=|\+=|\?=|=)")
DIRECTIVE_RE = re.compile(r"^\s*(ifeq|ifneq|ifdef|ifndef|else|endif|include|-include|sinclude|define|endef|vpath)\b")
RULE_RE = re.compile(r"^((?:" + NAME + r")(?:\s+" + NAME + r")*)\s*:(?!=)\s*(.*)$")
# Every script suffix a make recipe can name literally. A .mjs/.cjs/.ts probe
# was invisible to the earlier (py|sh|js) frame, so its reference neither marked
# a script live nor revealed an absent one; the frame is the measurement, so it
# has to cover the surface it claims to measure.
#
# The leading negative lookbehind is not cosmetic: without it the pattern also
# matched the tail of a *different* surface, so
# ``frontend/apps/web/scripts/foo_test.ts`` was read as a repo-root
# ``scripts/foo_test.ts`` - a path that does not exist. That turned 138 live
# frontend tests into "absent recipe paths" and inflated the lane-divergence
# metric. A script path only counts where a path can start.
SCRIPT_RE = re.compile(r"(?<![A-Za-z0-9_./\-])(scripts/[A-Za-z0-9_./\-]+\.(?:py|sh|js|mjs|cjs|ts))")
# A module consumed without its extension (``require('./x')``,
# ``from x import y``) is invisible to both SCRIPT_RE and the basename index,
# so a live guard was reported as dead surface.  Capture the specifier and
# resolve it against the live surface; see resolve_module_specifier.
REQUIRE_SPEC_RE = re.compile(r"""(?:\brequire|\bjest\.mock|\bimport)\s*\(\s*['"]([^'"]+)['"]\s*\)""")
PY_FROM_IMPORT_RE = re.compile(r"^[ \t]*from[ \t]+([A-Za-z_][A-Za-z0-9_.]*)[ \t]+import\b", re.M)
PY_IMPORT_RE = re.compile(r"^[ \t]*import[ \t]+([A-Za-z_][A-Za-z0-9_.]*)", re.M)
MAKE_CALL_RE = re.compile(r"\$\(MAKE\)(?:\s+-[A-Za-z\-]+(?:\s+\S+)?)*\s+((?:" + NAME + r")(?:\s+" + NAME + r")*)")
IDENT_RE = re.compile(NAME)
WF_MAKE_RE = re.compile(r"\bmake\s+((?:" + NAME + r")(?:\s+" + NAME + r")*)")

TEXT_EXT = (
    ".mk", ".yml", ".yaml", ".md", ".sh", ".py", ".json", ".js", ".ts", ".tsx",
    ".vue", ".txt", ".cfg", ".toml", ".ini", ".sql", ".xml",
)

# Declared execution lanes.  A lane is a make entrypoint that a governed gate or
# the local exact-head lane really runs.  ``remote:*`` lanes are enforced by
# required CI; ``local:*`` lanes are enforced only on the developer machine.
LANES: dict[str, list[str]] = {
    "local.iteration": ["ci.local.iteration"],
    # Both entries belong to this lane: ci.local.quick is the sharded default a
    # developer or gate actually types, ci.local.quick.run is the declared target
    # list it must cover exactly. The lane's reachable set is their union.
    "local.quick": ["ci.local.quick.run", "ci.local.quick"],
    "remote.professional.backend.verify": ["ci.professional.backend.shard-verify"],
    "remote.professional.backend.tests": ["ci.professional.backend.shard-tests"],
    "remote.professional.backend.reports": ["ci.professional.backend.shard-reports"],
    "remote.standard_backend": ["test.unit", "test.contract", "test.e2e.preflight"],
    "remote.frontend.standard": ["verify.frontend.pr.unit"],
    "remote.frontend.full": ["verify.frontend.release.audit"],
}
REMOTE_PREFIX = "remote."
LOCAL_PREFIX = "local."

VERIFY_LIFECYCLE_PREFIX = "scripts/verify/"

# A dead script whose owner registered one of these dispositions is required
# structure (not debt a batch sweep may delete), e.g. a package marker.
RETAINED_SCRIPT_DISPOSITIONS = ("package-marker", "retain")

# Closed vocabulary for registered dead surface.  The point of a closed set is
# that registering debt is a deliberate classification, not a free-text escape:
# a new disposition has to be argued for in review and added here.  Values
# already used for targets are kept so the two halves speak one language.
SCRIPT_DISPOSITION_VOCABULARY = frozenset(
    {
        # required structure, not debt
        "package-marker",
        "retain",
        # dead surface pending wire-or-retire (explicitly marked as an open item)
        "candidate",
        # classified: capability still wanted, currently manual/on-demand
        "runtime_audit_probe",
        "browser_acceptance_probe",
        "local_diagnostic",
        "diagnostic_cli",
        "audit_tooling",
        "audit_runbook",
        "ops_tooling",
        "ops_runbook",
        "product_tooling",
        "tenant_runbook",
        "demo_runbook",
        "release_runbook",
        "migration_runbook",
        "history_probe_runbook",
        # classified: superseded/legacy, tracked until a batch retires it
        "ci_legacy_tooling",
        "deprecated_shim",
        "one_shot_repair_verifier",
    }
)


# Make targets and scripts share most disposition meanings, but the target
# registry already classifies make-only shapes that a script can never be.
# Keeping one closed vocabulary per half (with the shared core inherited) means
# registration still argues for a classification, and a target sweep cannot
# smuggle in a free-text label.
TARGET_DISPOSITION_VOCABULARY = SCRIPT_DISPOSITION_VOCABULARY | frozenset(
    {
        # a one-shot data projection or replay whose recipe already ran
        "one_shot_projection_write",
        "one_shot_replay_adapter",
        # a developer loop that is typed by hand, not dispatched by a lane
        "frontend_develop",
        # an entry a batch is holding as a gate candidate
        "gate_candidate",
    }
)


def read_make_files(root: Path) -> list[Path]:
    files = [root / "Makefile"]
    files += sorted((root / "make").glob("*.mk"))
    return [p for p in files if p.exists()]


def join_continuations(lines: list[str]) -> list[str]:
    """Join backslash-continued make lines the way GNU make does.

    A rule may spread its prerequisites over several lines, each ending in a
    backslash; ``make`` folds them into one logical line before parsing.  This
    repository already writes `.PHONY` and any long prerequisite list that way,
    so a parser that reads physical lines silently drops every prerequisite
    after the first, under-reporting lane coverage.  The first physical line
    keeps its leading tab (recipe detection depends on it); continuation lines
    contribute a single separating space.
    """
    joined: list[str] = []
    pending: str | None = None
    for line in lines:
        if pending is not None:
            line = pending + " " + line.lstrip()
            pending = None
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            pending = stripped[:-1].rstrip()
            continue
        joined.append(line)
    if pending is not None:
        joined.append(pending)
    return joined


def parse_make(root: Path):
    targets: dict[str, str] = {}
    recipes: dict[str, list[str]] = defaultdict(list)
    prereqs: dict[str, list[str]] = defaultdict(list)
    phony: set[str] = set()

    for path in read_make_files(root):
        rel = str(path.relative_to(root))
        lines = join_continuations(
            path.read_text(encoding="utf-8", errors="replace").split("\n")
        )
        i, current, body = 0, None, []
        while i < len(lines):
            line = lines[i]
            if line.startswith("\t"):
                if current:
                    body.append(line[1:])
                i += 1
                continue
            if current:
                recipes[current].extend(body)
                current, body = None, []
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or DIRECTIVE_RE.match(stripped):
                i += 1
                continue
            if stripped.startswith(".PHONY"):
                phony.update(stripped.split(":", 1)[1].split(";", 1)[0].split())
                i += 1
                continue
            match = RULE_RE.match(stripped)
            if match and not VAR_RE.match(line):
                names = match.group(1).split()
                deps = [
                    d for d in match.group(2).split(";", 1)[0].split()
                    if d and not d.startswith("$") and not d.startswith("-")
                ]
                keep = [n for n in names if "%" not in n and not n.startswith(".")]
                if keep:
                    current = keep[0]
                    for name in keep:
                        targets.setdefault(name, f"{rel}:{i + 1}")
                        prereqs[name].extend(deps)
                i += 1
                continue
            i += 1
        if current:
            recipes[current].extend(body)
    return targets, recipes, prereqs, phony


def build_graph(targets, recipes, prereqs):
    edges: dict[str, set[str]] = defaultdict(set)
    make_ref: dict[str, set[str]] = defaultdict(set)
    script_ref: dict[str, set[str]] = defaultdict(set)
    for target in set(list(recipes) + list(targets)):
        for dep in prereqs.get(target, ()):
            edges[target].add(dep)
            make_ref[dep].add(f"prereq:{target}")
        for line in recipes.get(target, ()):
            for call in MAKE_CALL_RE.finditer(line):
                for callee in call.group(1).split():
                    edges[target].add(callee)
                    make_ref[callee].add(f"recursive:{target}")
            for script in SCRIPT_RE.findall(line):
                script_ref[script].add(f"make:{target}")
    return edges, make_ref, script_ref


def closure(seeds, edges):
    seen, stack = set(), list(seeds)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        for nxt in edges.get(current, ()):
            if nxt not in seen:
                stack.append(nxt)
    return seen


JS_SUFFIXES = (".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx", ".vue")


def _relative_candidates(base: Path, consumer_suffix: str) -> tuple[str, ...]:
    """The files a relative specifier can resolve to, per consumer language.

    A ``.js`` consumer resolves like Node (``.js``/``.ts``/``index.js``) and
    never to a sibling ``.py`` of the same stem; a ``.py`` consumer resolves
    like Python (``.py``/``__init__.py``).  Mixing the extensions would make a
    stem shared by a ``.js`` and a ``.py`` file ambiguous and hide a live one.
    """
    if consumer_suffix in JS_SUFFIXES:
        return (f"{base}.js", f"{base}.ts", f"{base}/index.js", f"{base}/index.ts", str(base))
    if consumer_suffix == ".py":
        return (f"{base}.py", f"{base}/__init__.py", str(base))
    if consumer_suffix == ".sh":
        return (f"{base}.sh", str(base))
    return (f"{base}.js", f"{base}.py", f"{base}.sh", f"{base}/index.js", str(base))


def resolve_module_specifier(
    spec: str,
    rel_path: str,
    live_scripts: set[str],
    dotted_modules: dict[str, str],
    unique_stem: dict[str, str],
) -> str | None:
    """Resolve a module specifier to a live script path, or ``None``.

    Handles the extension-less idioms a real consumer uses: a relative Node
    require/import (``./x``, ``../lib/y``), an explicit repo path without a
    suffix (``scripts/a/b``), and a bare Python module name (``from x import``).
    Resolution is language-aware and only an unambiguous result is returned, so
    a stem shared by several files can never mark unrelated surface as live.
    """
    consumer = Path(rel_path).suffix
    if spec.startswith("."):
        base = Path(rel_path).parent / spec
        hits = [c for c in _relative_candidates(base, consumer) if str(Path(c)) in live_scripts]
        hits = [str(Path(c)) for c in hits]
        return hits[0] if len(hits) == 1 else None
    if spec.startswith("scripts/"):
        for candidate in (f"{spec}.py", f"{spec}.sh", f"{spec}.js", spec):
            if candidate in live_scripts:
                return candidate
        return None
    if spec in dotted_modules:
        return dotted_modules[spec]
    if "." in spec:
        return None
    # A bare module name only resolves for a Python consumer, where the
    # importing file's own directory is on the module search path.
    if consumer == ".py":
        return unique_stem.get(spec)
    return None


def read_workflow_invocations(root: Path, targets):
    calls: dict[str, set[str]] = defaultdict(set)
    for wf in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        text = wf.read_text(encoding="utf-8", errors="replace")
        for line in text.split("\n"):
            for match in WF_MAKE_RE.finditer(line):
                for target in match.group(1).split():
                    if target in targets:
                        calls[target].add(str(wf.relative_to(root)))
    return calls


# Only these documents *declare* an execution entry point. Everything else
# under docs/ narrates: an audit report, inventory or matrix that happens to
# quote a target name is describing the surface, not owning it. Reading the
# whole docs/ tree made writing about a dead target revive it -- the same
# defect already fixed for scripts, and it silently flattered the metric.
NORMATIVE_DOCS = (
    "docs/ops/codex_execution_allowlist.md",
    "docs/ops/codex_workspace_execution_rules.md",
)

# The auditor's own data files enumerate the registered surface.  They are
# generated or edited by this instrument, never by a consumer, so they narrate
# exactly like docs and .agent ledgers do.  Excluding them is what keeps a
# committed registry from reviving every entry it registers.
SELF_DATA_FILES = (
    "scripts/audit/verification_lane_baseline.json",
    "scripts/audit/verification_lane_dispositions.json",
    "scripts/audit/verification_lane_exemptions.json",
    "scripts/retired/retirements.json",
)


def read_doc_invocations(root: Path, targets):
    calls: dict[str, set[str]] = defaultdict(set)
    for rel in NORMATIVE_DOCS:
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in WF_MAKE_RE.finditer(text):
            if match.group(1) in targets:
                calls[match.group(1)].add(rel)
    return calls


def is_prose(rel: str) -> bool:
    """True when a file narrates the surface instead of consuming it.

    Documentation and agent ledgers describe what exists; they never execute a
    target or import a script.  Letting them count is not a harmless extra
    signal: a generated inventory lists every name, and an audit report quotes
    the names it discusses, so either one silently revives whatever it mentions
    (measured: writing one audit paragraph moved 7 dead targets to "referenced").
    Only the two binding execution-policy documents declare entry points.

    The auditor's own registries narrate the surface in the same way: the
    baseline, disposition, exemption and retirement files each list every
    registered name. Counting them as consumers is not a theoretical risk - it
    was measured: the moment these files were first committed, all 760
    registered targets and 103 registered scripts flipped to stale at once, and
    a clean frozen head failed its own coverage check. A file that enumerates
    the surface can never be evidence that the surface is consumed.
    """
    if rel in NORMATIVE_DOCS:
        return False
    if rel in SELF_DATA_FILES:
        return True
    return rel.startswith("docs/") or rel.startswith(".agent/")


def tracked_files(root: Path) -> list[Path]:
    import subprocess

    out = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    ).stdout
    files = []
    for rel in out.split("\n"):
        if not rel or rel.startswith(".git/"):
            continue
        if not (rel.endswith(TEXT_EXT) or Path(rel).name == "Makefile"):
            continue
        path = root / rel
        try:
            if path.is_file() and path.stat().st_size <= 4_000_000:
                files.append(path)
        except OSError:
            continue
    return files


def read_anchors(root: Path) -> list[str]:
    anchors = []
    for line in (root / "scripts" / "verify" / "registry.yaml").read_text(
        encoding="utf-8"
    ).split("\n"):
        match = re.match(r"^- target:\s*(\S+)", line)
        if match:
            anchors.append(match.group(1))
    return anchors


def read_exemptions(path: Path) -> dict[str, set[str]]:
    """Registered lane divergence, by direction.

    Every divergence between the local exact-head lane and the remote required
    gates must be removed or explicitly registered with a reason. An
    unregistered divergence is the defect; a registered one is acknowledged
    debt with an owner and a review date.
    """
    if not path.is_file():
        return {"local_only": set(), "remote_only": set()}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "local_only": {e["script"] for e in data.get("local_only", [])},
        "remote_only": {e["script"] for e in data.get("remote_only", [])},
    }


def read_dispositions(path: Path) -> dict[str, set[str]]:
    """Registered dispositions for dead surface (wire-or-retire, third path).

    A make target or guard script that nothing references is either wired to an
    execution lane, retired, or explicitly registered here with an owner, a
    reason and a review date.  Registration is not an exemption from the raw
    shrink-only ratchet: the raw zero-reference count still may only decrease.
    What registration buys is that the *unregistered* count must stay at zero,
    so a new piece of dead surface fails ``--check`` until someone dispositions
    it.  A stale entry (registered but no longer dead) also fails.
    """
    if not path.is_file():
        return {"targets": set(), "scripts": set()}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "targets": set(data.get("targets", {})),
        "scripts": set(data.get("scripts", {})),
    }


def read_disposition_entries(path: Path) -> dict:
    """The registry as written, not just its key sets.

    ``read_dispositions`` answers "is this name registered"; the missing-asset
    check additionally needs each entry's recorded evidence, so it reads the
    full mapping. Both views come from the same file.
    """
    if not path.is_file():
        return {"targets": {}, "scripts": {}, "absent_assets": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "targets": dict(data.get("targets") or {}),
        "scripts": dict(data.get("scripts") or {}),
        "absent_assets": dict(data.get("absent_assets") or {}),
    }


def missing_asset_state(missing_asset: dict, registered: dict) -> dict:
    """Classify make targets whose recipe calls a path absent from the tree.

    Such a target cannot run: ``make`` hands the shell a path that is not there,
    so the recipe fails before it does any work.  That is the cheapest possible
    dead-surface proof, and it is exactly the kind of surface that inflates a
    "verification" count while verifying nothing.  The registry records the
    measured paths verbatim, so the classification is evidence, not prose, and a
    later recipe edit invalidates it (the recorded list stops matching).

    A registered target that has no absent path any more is stale: the rule was
    either fixed or retired, and the record must go with it.
    """
    unregistered, stale = [], []
    for target, paths in sorted(missing_asset.items()):
        recorded = (registered.get(target) or {}).get("missing_asset")
        if not isinstance(recorded, list) or sorted(recorded) != sorted(paths):
            unregistered.append(target)
    for target, entry in sorted(registered.items()):
        if entry.get("missing_asset") and target not in missing_asset:
            stale.append(target)
    # A recorded path list that no longer matches the recipe is the same defect
    # as an unregistered one: the registry would otherwise describe a rule that
    # has since been edited, which is exactly the rot this check exists to stop.
    return {
        "targets_missing_asset_unregistered": unregistered,
        "stale_missing_asset_dispositions": stale,
    }


def disposition_state(zero_reference_targets, unreferenced_scripts, dispositions: dict) -> dict:
    """Split raw dead surface into registered vs unregistered, and find stale entries.

    ``dispositions`` is the output of :func:`read_dispositions`.  The raw sets
    are the truth; this only classifies them.  A registered name that is no
    longer dead is ``stale``: keeping it would turn the registry into a
    permanent allowlist, so it must be removed.
    """
    zr, us = set(zero_reference_targets), set(unreferenced_scripts)
    return {
        "targets_zero_reference_unregistered": sorted(zr - dispositions["targets"]),
        "stale_target_dispositions": sorted(dispositions["targets"] - zr),
        "scripts_unreferenced_unregistered": sorted(us - dispositions["scripts"]),
        "stale_script_dispositions": sorted(dispositions["scripts"] - us),
    }


def measure(root: Path, exemptions_path: Path = DEFAULT_EXEMPTIONS, dispositions_path: Path = DEFAULT_DISPOSITIONS) -> dict:
    targets, recipes, prereqs, phony = parse_make(root)
    edges, make_ref, script_ref = build_graph(targets, recipes, prereqs)
    anchors = read_anchors(root)
    anchor_targets = {a: sorted(closure([a], edges)) for a in anchors}
    anchor_union: set[str] = set()
    for reached in anchor_targets.values():
        anchor_union |= set(reached)

    lane_targets, lane_scripts = {}, {}
    for lane, seeds in LANES.items():
        reached = closure(seeds, edges)
        lane_targets[lane] = sorted(reached)
        scripts: set[str] = set()
        for target in reached:
            for line in recipes.get(target, ()):
                scripts |= set(SCRIPT_RE.findall(line))
        lane_scripts[lane] = sorted(scripts)

    every_script = sorted(
        str(p.relative_to(root))
        for p in (root / "scripts").rglob("*")
        if p.is_file()
        and p.suffix in (".py", ".sh", ".js")
        and "node_modules" not in p.parts
        and "__pycache__" not in p.parts
    )
    # ``scripts/retired/**`` is the governed park for intentionally retired
    # one-shot runbooks. Parked files stay on disk (recovery value preserved) but
    # are not live surface, so they do not count as unreferenced debt.
    retired_scripts = [s for s in every_script if "/retired/" in s]
    all_scripts = [s for s in every_script if "/retired/" not in s]
    # scripts/verify/**/*.py|sh already have a governed lifecycle: registry.yaml
    # plus guard_registry_audit.py, which is a required gate that fails closed on
    # an unacknowledged orphan and on a stale entry.  They stay in the reference
    # universe (so a cross-reference still resolves) but are not counted as this
    # instrument's dead surface: counting them too would either double-register
    # them or let registry.yaml's own basename enumeration make them look
    # consumed.  The split is by owner, declared here, not by accident.
    verify_lifecycle_suffixes = (".py", ".sh")
    owned_scripts = [
        s for s in all_scripts
        if not (
            s.startswith(VERIFY_LIFECYCLE_PREFIX)
            and s.endswith(verify_lifecycle_suffixes)
        )
    ]

    # A ``.py`` guard consumed only through a dotted import (``from
    # scripts.contract.x_common import ...``) is not referenced by its path, so a
    # path-only index reports it as dead.  Index the dotted module name too, so
    # "never referenced" means never referenced in any of the ways a module can
    # be named: filesystem path, dotted module, basename in a non-source
    # manifest, or the extension-less module specifier of a real import/require
    # (the last three only where the name resolves unambiguously).
    dotted_modules = {
        s[:-3].replace("/", "."): s for s in all_scripts if s.endswith(".py")
    }
    # A shell/CI manifest may consume a script by basename (``$DIR/ensure_testdeps.sh``)
    # without the ``scripts/`` prefix, which the path regex cannot see.  Index the
    # basename only when it is unique across the live surface, and never count a
    # reference coming from a documentation or evidence file: those narrate the
    # scripts rather than consume them, and counting them would mask real debt.
    basename_counts = collections.Counter(Path(s).name for s in all_scripts)
    unique_basename = {
        Path(s).name: s for s in all_scripts if basename_counts[Path(s).name] == 1
    }
    live_scripts = set(all_scripts)
    py_stem_counts = collections.Counter(Path(s).stem for s in all_scripts if s.endswith(".py"))
    unique_stem_py = {
        Path(s).stem: s for s in all_scripts
        if s.endswith(".py") and py_stem_counts[Path(s).stem] == 1
    }

    workflow_calls = read_workflow_invocations(root, targets)
    doc_calls = read_doc_invocations(root, targets)

    # Literal-presence index: a target is "reachable" only if something other
    # than its own definition names it.  Uses token equality, never a regex
    # substring, so a dotted target name can never be "found" inside the prose
    # words that happen to contain the same letters.
    interest = set(targets) | set(anchors)
    token_index: dict[str, set[str]] = defaultdict(set)
    script_index: dict[str, set[str]] = defaultdict(set)
    for path in tracked_files(root):
        rel = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        prose = is_prose(rel)
        if not prose:
            for token in set(IDENT_RE.findall(text)):
                if token in interest:
                    token_index[token].add(rel)
        # A doc or an agent ledger narrates the surface, it never consumes it.
        # The rule must hold for every way a script can be named - path, dotted
        # module, basename or module specifier - or documenting a dead script
        # would silently revive it (which is how one prose mention of a
        # retained package-marker path hid the entry).
        if not prose:
            for script in set(SCRIPT_RE.findall(text)):
                script_index[script].add(rel)
        if not prose:
            for token in set(IDENT_RE.findall(text)):
                dotted_owner = dotted_modules.get(token)
                if dotted_owner is not None:
                    script_index[dotted_owner].add(rel)
                basename_owner = unique_basename.get(token)
                if basename_owner is not None:
                    script_index[basename_owner].add(rel)
        if not prose:
            specs = set(REQUIRE_SPEC_RE.findall(text))
            specs |= set(PY_FROM_IMPORT_RE.findall(text))
            specs |= set(PY_IMPORT_RE.findall(text))
            for spec in specs:
                owner = resolve_module_specifier(
                    spec, rel, live_scripts, dotted_modules, unique_stem_py
                )
                if owner is not None:
                    script_index[owner].add(rel)

    remote_scripts: set[str] = set()
    local_quick_scripts: set[str] = set()
    for lane, scripts in lane_scripts.items():
        if lane.startswith(LOCAL_PREFIX) and lane.endswith("quick"):
            local_quick_scripts |= set(scripts)
        elif lane.startswith(REMOTE_PREFIX):
            remote_scripts |= set(scripts)

    zero_reference_targets, unreached_targets = [], []
    for target in sorted(targets):
        owning_file = targets[target].split(":")[0]
        named_elsewhere = token_index.get(target, set()) - {owning_file}
        referenced = (
            bool(make_ref.get(target))
            or bool(workflow_calls.get(target))
            or bool(doc_calls.get(target))
            or bool(named_elsewhere)
        )
        if not referenced:
            zero_reference_targets.append(target)
        if target not in anchor_union:
            unreached_targets.append(target)

    unreferenced_scripts = sorted(s for s in owned_scripts if not script_index.get(s))

    exemptions = read_exemptions(exemptions_path)
    local_only = sorted(local_quick_scripts - remote_scripts)
    remote_only = sorted(remote_scripts - local_quick_scripts)

    dispositions = read_dispositions(dispositions_path)
    disposition = disposition_state(zero_reference_targets, unreferenced_scripts, dispositions)

    # "The recipe names a file that is not here" is a target that cannot run.
    # Measured over every defined rule, not only the ones nothing references: a
    # broken recipe is broken whether or not something types its name.
    missing_asset = {}
    for target in sorted(set(recipes)):
        absent = sorted(
            {
                script
                for line in recipes[target]
                for script in SCRIPT_RE.findall(line)
                if not (root / script).exists()
            }
        )
        if absent:
            missing_asset[target] = absent
    entry_registry = read_disposition_entries(dispositions_path)
    missing_asset_classification = missing_asset_state(
        missing_asset, entry_registry["absent_assets"]
    )

    return {
        "schema_version": "verification-lane-coverage/v1",
        "targets_defined": len(targets),
        "phony_targets": len(phony),
        "gate_anchors": anchors,
        "anchor_reachable_targets": {a: len(v) for a, v in anchor_targets.items()},
        "anchor_union_targets": len(anchor_union),
        "targets_unreached_from_anchor": len(unreached_targets),
        "lanes": {
            lane: {"targets": len(lane_targets[lane]), "scripts": len(lane_scripts[lane])}
            for lane in LANES
        },
        "lane_scripts": lane_scripts,
        "scripts_on_disk": len(all_scripts),
        "scripts_owned_surface": len(owned_scripts),
        "scripts_verify_lifecycle_owned": len(all_scripts) - len(owned_scripts),
        "scripts_retired": len(retired_scripts),
        "scripts_unreferenced_anywhere": unreferenced_scripts,
        "targets_zero_reference": zero_reference_targets,
        "local_only_scripts": local_only,
        "remote_only_scripts": remote_only,
        "unregistered_local_only_scripts": sorted(set(local_only) - exemptions["local_only"]),
        "unregistered_remote_only_scripts": sorted(set(remote_only) - exemptions["remote_only"]),
        "stale_local_only_exemptions": sorted(exemptions["local_only"] - set(local_only)),
        "stale_remote_only_exemptions": sorted(exemptions["remote_only"] - set(remote_only)),
        **disposition,
        "targets_missing_asset": missing_asset,
        **missing_asset_classification,
    }


# Metric corrections are recorded in the instrument, not only in the JSON
# baseline. --write-baseline rewrites the file, so a note that lived only in the
# file would be lost exactly when the number it explains is re-frozen. Each
# entry records an *observed* count right after a measurement defect was fixed;
# it is evidence, not an allowance, so the recorded maximum may still shrink.
BASELINE_METRIC_CORRECTIONS = [
    {
        "metric": "max_scripts_unreferenced_anywhere",
        "previous_reading": 1,
        "observed_after_correction": 104,
        "batch": "B2",
        "defect": "The reference index counted a *mention* as a consumer. Guard "
                   "registries, inventories and audit reports list every script by "
                   "name, so writing about dead surface silently revived it and the "
                   "raw count stayed flattering. Fixed by indexing real imports only.",
    },
    {
        "metric": "max_targets_zero_reference",
        "previous_reading": 336,
        "observed_after_correction": 759,
        "batch": "B3",
        "defect": "Same defect on the make-target half: every docs/*.md $() mention "
                   "counted as an invocation. Only the two binding execution-policy "
                   "documents declare an entry point; a report that quotes a target "
                   "name narrates it. Fixed, which added the 423 targets that this "
                   "batch registered.",
    },
    {
        "metric": "max_remote_only_scripts",
        "previous_reading": 74,
        "observed_after_correction": 83,
        "batch": "B3",
        "defect": "The recipe script token frame listed only .py/.sh/.js and had no path "
                   "boundary, so the Node/TS probe surface was invisible to the "
                   "lane-divergence count. Widening the frame to .mjs/.cjs/.ts exposed 9 "
                   "genuinely remote-only frontend probes (registered), and the boundary "
                   "fix removed 138 false 'absent path' readings that came from reading "
                   "frontend/apps/web/scripts/* as a repo-root scripts/*.",
    },
    {
        "metric": "recorded_targets_missing_asset",
        "previous_reading": None,
        "observed_after_correction": 226,
        "batch": "B3",
        "defect": "New hard-checked register: a make target whose recipe calls a path that "
                   "is absent from the tree cannot run. 226 targets qualify (187 references "
                   "to scripts/migration/*, which .gitignore line 116 keeps out of the clean "
                   "product repository as customer migration collateral, plus relocated or "
                   "never-added verify/root scripts). Each is registered with an owner, a "
                   "reason and a review date; 0 may be unregistered.",
    },
]


def baseline_payload(result: dict) -> dict:
    return {
        "schema_version": result["schema_version"],
        "rationale": (
            "Frozen debt ratchet for the verification surface. Every list is an "
            "allowance, never a target: a batch may only shrink it. Growth fails "
            "--check until it is explicitly reviewed and the baseline is "
            "deliberately rewritten."
        ),
        "review_by": "2026-12-31",
        "metric_corrections": BASELINE_METRIC_CORRECTIONS,
        # Hard-checked debt: surface with no owner and no enforcement.
        "max_targets_zero_reference": len(result["targets_zero_reference"]),
        "max_scripts_unreferenced_anywhere": len(result["scripts_unreferenced_anywhere"]),
        # A target whose recipe calls a path that is not in the tree cannot run.
        # Kept at zero-unregistered: the measured absent paths are recorded in
        # the registry, so a new broken rule fails until it is registered (or
        # its script restored).
        "max_targets_missing_asset_unregistered": 0,
        "max_stale_missing_asset_dispositions": 0,
        "recorded_targets_missing_asset": len(result.get("targets_missing_asset") or {}),
        # Registered dead surface must stay fully dispositioned: anything not in
        # verification_lane_dispositions.json fails, and a stale entry (no longer
        # dead) fails too, so the registry cannot rot into a permanent allowlist.
        "max_targets_zero_reference_unregistered": 0,
        "max_scripts_unreferenced_unregistered": 0,
        "max_stale_target_dispositions": 0,
        "max_stale_script_dispositions": 0,
        "max_local_only_scripts": len(result["local_only_scripts"]),
        "max_remote_only_scripts": len(result["remote_only_scripts"]),
        # Registered divergence must stay at zero: a divergence that is neither
        # removed nor registered in verification_lane_exemptions.json is the
        # defect this audit exists to stop.
        "max_unregistered_local_only_scripts": 0,
        "max_unregistered_remote_only_scripts": 0,
        "max_stale_local_only_exemptions": 0,
        "max_stale_remote_only_exemptions": 0,
        # Recorded size, deliberately NOT hard-checked. A manual or diagnostic
        # lane is legitimate surface even when no gate reaches it, so failing on
        # +1 would block real work without reducing debt. Re-reviewed at review_by.
        "recorded_targets_defined": result["targets_defined"],
        "recorded_targets_unreached_from_anchor": result["targets_unreached_from_anchor"],
        "recorded_anchor_union_targets": result["anchor_union_targets"],
    }


def compare(result: dict, baseline: dict) -> list[str]:
    current = {
        "targets_zero_reference": len(result["targets_zero_reference"]),
        "scripts_unreferenced_anywhere": len(result["scripts_unreferenced_anywhere"]),
        "targets_zero_reference_unregistered": len(result["targets_zero_reference_unregistered"]),
        "scripts_unreferenced_unregistered": len(result["scripts_unreferenced_unregistered"]),
        "stale_target_dispositions": len(result["stale_target_dispositions"]),
        "stale_script_dispositions": len(result["stale_script_dispositions"]),
        "targets_missing_asset_unregistered": len(result.get("targets_missing_asset_unregistered") or []),
        "stale_missing_asset_dispositions": len(result.get("stale_missing_asset_dispositions") or []),
        "local_only_scripts": len(result["local_only_scripts"]),
        "remote_only_scripts": len(result["remote_only_scripts"]),
        "unregistered_local_only_scripts": len(result["unregistered_local_only_scripts"]),
        "unregistered_remote_only_scripts": len(result["unregistered_remote_only_scripts"]),
        "stale_local_only_exemptions": len(result["stale_local_only_exemptions"]),
        "stale_remote_only_exemptions": len(result["stale_remote_only_exemptions"]),
    }
    regressions = []
    for key, value in current.items():
        allowed = baseline.get(f"max_{key}")
        if allowed is None:
            continue
        if value > allowed:
            regressions.append(f"{key}: {value} > frozen baseline {allowed}")
    return regressions


def render_summary(result: dict) -> str:
    lines = [
        "[verification-lane-coverage] read-only measurement",
        f"  targets defined            : {result['targets_defined']}"
        f" (phony {result['phony_targets']})",
        f"  reachable from any anchor  : {result['anchor_union_targets']}"
        f" -> unreached {result['targets_unreached_from_anchor']}",
        f"  zero-reference targets     : {len(result['targets_zero_reference'])}"
        f"  (unregistered {len(result['targets_zero_reference_unregistered'])};"
        f" stale {len(result['stale_target_dispositions'])})",
        f"  scripts on disk            : {result['scripts_on_disk']}"
        f"  (owned surface {result['scripts_owned_surface']};"
        f" verify-registry lifecycle {result['scripts_verify_lifecycle_owned']})",
        f"  targets, absent-asset recipe: {len(result.get('targets_missing_asset') or {})}"
        f"  (unregistered {len(result.get('targets_missing_asset_unregistered') or [])};"
        f" stale {len(result.get('stale_missing_asset_dispositions') or [])})",
        f"  scripts never referenced   : {len(result['scripts_unreferenced_anywhere'])}"
        f"  (unregistered {len(result['scripts_unreferenced_unregistered'])};"
        f" stale {len(result['stale_script_dispositions'])})",
    ]
    for lane, stats in result["lanes"].items():
        lines.append(f"  lane {lane:<38}: {stats['targets']} targets / {stats['scripts']} scripts")
    lines.append(
        f"  local.quick-only scripts   : {len(result['local_only_scripts'])}"
        "  (merge green remotely, fail only on the local exact-head lane)"
    )
    lines.append(
        f"  remote-only scripts        : {len(result['remote_only_scripts'])}"
        "  (a local pass proves less than a remote pass)"
    )
    lines.append(
        f"  UNREGISTERED divergence    : local {len(result['unregistered_local_only_scripts'])}"
        f" / remote {len(result['unregistered_remote_only_scripts'])} (must be 0)"
    )
    lines.append(
        f"  stale exemptions           : {len(result['stale_local_only_exemptions'])}"
        f" / {len(result['stale_remote_only_exemptions'])} (must be 0)"
    )
    return "\n".join(lines)


def _git_move(root: Path, src: Path, dest: Path) -> None:
    """Move a tracked file preserving rename history, falling back to a copy."""
    result = subprocess.run(
        ["git", "mv", str(src.relative_to(root)), str(dest.relative_to(root))],
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dest)


def _retire_one(root: Path, dispositions_path: Path, script: str, reason: str, dead: set) -> int:
    """Move one verified-unreferenced script into the retired park."""
    if script not in dead:
        print(
            f"[verification-lane-coverage] refusing to retire '{script}': not an "
            "unreferenced script under scripts/ (still referenced or unknown)"
        )
        return 3
    src = root / script
    if not src.is_file():
        print(f"[verification-lane-coverage] '{script}' is not a file")
        return 3
    dest = root / "scripts" / "retired" / Path(script).relative_to("scripts")
    if dest.exists():
        print(f"[verification-lane-coverage] destination already exists: {dest.relative_to(root)}")
        return 3
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git_move(root, src, dest)

    date = subprocess.run(
        ["git", "log", "-1", "--format=%as", "--", script],
        cwd=root, capture_output=True, text=True,
    ).stdout.strip() or "unknown"
    log_path = root / "scripts" / "retired" / "retirements.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    log[script] = {
        "retired_to": str(dest.relative_to(root)),
        "reason": reason.strip(),
        "last_commit": date,
    }
    log_path.write_text(
        json.dumps(log, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if dispositions_path.exists():
        doc = json.loads(dispositions_path.read_text(encoding="utf-8"))
        scripts = doc.get("scripts") or {}
        if script in scripts:
            del scripts[script]
            doc["scripts"] = dict(sorted(scripts.items()))
            dispositions_path.write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
    print(f"[verification-lane-coverage] retired: {script} -> {dest.relative_to(root)}")
    return 0


def _require_reason(reason: str) -> bool:
    if not (reason or "").strip():
        print("[verification-lane-coverage] retirement requires --reason (audit trail)")
        return False
    return True


def _batch_entries(payload, bucket: str) -> list[dict]:
    """Read one bucket out of a batch manifest.

    A batch manifest is either the legacy ``{scripts: [...]}`` mapping, a
    ``{targets: [...], scripts: [...]}`` mapping, or a bare list.  The bare list
    and the single-key mapping keep older manifests working; the two-bucket form
    lets one reviewed sweep classify make targets and scripts together.
    """
    if isinstance(payload, list):
        return list(payload) if bucket == "scripts" else []
    if not isinstance(payload, dict):
        return []
    entries = payload.get(bucket)
    return list(entries) if isinstance(entries, list) else []


def _dead_bucket(result: dict, bucket: str) -> set:
    key = "targets_zero_reference" if bucket == "targets" else "scripts_unreferenced_anywhere"
    return set(result[key])


def _entry_name(entry: dict) -> str:
    """A batch entry names its surface as ``name``, ``target`` or ``script``.

    ``script`` stays first-class for the legacy script manifests; ``target``
    reads naturally in a make-target sweep; ``name`` is the neutral spelling a
    mixed manifest uses.
    """
    for key in ("name", "script", "target"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def cmd_register_batch(root: Path, dispositions_path: Path, manifest: Path) -> int:
    """Register a reviewed family of dead make targets and/or scripts at once.

    A batch sweep has to classify dozens of surfaces with the same family
    argument, so it gets one governed entry instead of N hand edits: the
    manifest is the reviewed artifact, every entry is validated against the
    same invariants as :func:`cmd_register`, and the registry is written once.
    Nothing is written if any entry is invalid.
    """
    payload = json.loads(Path(manifest).read_text(encoding="utf-8"))
    buckets = {
        "targets": _batch_entries(payload, "targets"),
        "scripts": _batch_entries(payload, "scripts"),
    }
    if not any(buckets.values()):
        print("[verification-lane-coverage] batch manifest must be a non-empty list "
              "(or {scripts: [...]}/{targets: [...]})")
        return 2

    result = measure(root, DEFAULT_EXEMPTIONS, dispositions_path)
    doc = {"schema_version": "verification-lane-dispositions/v1", "targets": {}, "scripts": {}}
    if dispositions_path.exists():
        doc = json.loads(dispositions_path.read_text(encoding="utf-8"))
    doc.setdefault("targets", {})
    doc.setdefault("scripts", {})

    errors: list[str] = []
    planned: dict[str, dict[str, dict]] = {"targets": {}, "scripts": {}}
    for bucket, entries in buckets.items():
        dead = _dead_bucket(result, bucket)
        vocabulary = (
            TARGET_DISPOSITION_VOCABULARY if bucket == "targets" else SCRIPT_DISPOSITION_VOCABULARY
        )
        registered = doc[bucket]
        label = "target" if bucket == "targets" else "script"
        for entry in entries:
            name = _entry_name(entry)
            disposition = entry.get("disposition", "")
            reason = (entry.get("reason") or "").strip()
            owner = (entry.get("owner") or "").strip()
            review_by = (entry.get("review_by") or "").strip()
            if not name:
                errors.append(f"(unnamed): a {label} entry needs name/script/target")
                continue
            if name not in dead:
                errors.append(f"{name}: not a zero-reference {label} in the current measurement")
                continue
            if disposition not in vocabulary:
                errors.append(f"{name}: unknown {label} disposition '{disposition}'")
                continue
            if not reason or not owner or not review_by:
                errors.append(f"{name}: reason, owner and review_by are required")
                continue
            existing = registered.get(name)
            if existing and existing.get("disposition") != disposition:
                errors.append(f"{name}: already registered as '{existing.get('disposition')}'")
                continue
            planned[bucket][name] = {
                "disposition": disposition,
                "owner": owner,
                "review_by": review_by,
                "reason": reason,
            }

    if errors:
        for line in errors:
            print(f"[verification-lane-coverage] batch rejected: {line}")
        return 3

    for bucket in ("targets", "scripts"):
        if planned[bucket]:
            doc[bucket].update(planned[bucket])
            doc[bucket] = dict(sorted(doc[bucket].items()))
    dispositions_path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    parts = []
    for bucket in ("targets", "scripts"):
        counts: dict[str, int] = {}
        for entry in planned[bucket].values():
            counts[entry["disposition"]] = counts.get(entry["disposition"], 0) + 1
        if counts:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            parts.append(f"{len(planned[bucket])} {bucket} ({summary})")
    print("[verification-lane-coverage] registered " + "; ".join(parts))
    return 0


def cmd_record_missing_assets(
    root: Path,
    dispositions_path: Path,
    reason: str,
    owner: str,
    review_by: str,
) -> int:
    """Record the measured absent recipe paths under their own register.

    A target whose recipe calls a path that is not in the tree cannot run; that
    is a property of the recipe, not of how many other targets name it, so it
    gets its own register instead of being folded into the zero-reference one.
    The paths are *measured*, never typed: the register is a copy of the
    measurement plus the owning team's reason and review date, and
    ``--check`` fails if the two ever disagree.
    """
    if not _require_reason(reason):
        return 2
    if not (owner or "").strip() or not (review_by or "").strip():
        print("[verification-lane-coverage] --owner and --review-by are required")
        return 2
    result = measure(root, DEFAULT_EXEMPTIONS, dispositions_path)
    missing_asset = result["targets_missing_asset"]
    doc = {"schema_version": "verification-lane-dispositions/v1", "targets": {}, "scripts": {}}
    if dispositions_path.exists():
        doc = json.loads(dispositions_path.read_text(encoding="utf-8"))
    register = doc.setdefault("absent_assets", {})
    changed = 0
    for target, paths in sorted(missing_asset.items()):
        entry = register.get(target) or {}
        if (entry.get("missing_asset") == paths and entry.get("owner") == owner.strip()
                and entry.get("review_by") == review_by.strip()
                and entry.get("reason") == reason.strip()):
            continue
        register[target] = {
            "missing_asset": paths,
            "owner": owner.strip(),
            "review_by": review_by.strip(),
            "reason": reason.strip(),
        }
        changed += 1
    dropped = sorted(set(register) - set(missing_asset))
    for target in dropped:
        del register[target]
    if changed or dropped:
        doc["absent_assets"] = dict(sorted(register.items()))
        dispositions_path.write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"[verification-lane-coverage] absent-asset register: {changed} written, "
          f"{len(dropped)} dropped as no-longer-absent, {len(missing_asset)} measured")
    return 0


def cmd_unregister_script(root: Path, dispositions_path: Path, script: str, reason: str) -> int:
    """Remove a registration that is no longer true.

    Registration means "this script is dead surface with an owner".  Once a
    batch wires the script to a make target the statement stops being true, and
    ``--check`` fails on a stale entry.  Removal has to be an explicit, argued
    action too - otherwise the register could be emptied to silence a real
    finding - so it requires a reason and refuses while the script is still
    unreferenced.
    """
    if not _require_reason(reason):
        return 2
    result = measure(root, DEFAULT_EXEMPTIONS, dispositions_path)
    dead = set(result["scripts_unreferenced_anywhere"])
    if script in dead:
        print(f"[verification-lane-coverage] refusing: '{script}' is still unreferenced; "
              "wire it or retire it, do not unregister a true statement")
        return 3
    doc = {"schema_version": "verification-lane-dispositions/v1", "targets": {}, "scripts": {}}
    if dispositions_path.exists():
        doc = json.loads(dispositions_path.read_text(encoding="utf-8"))
    scripts = doc.setdefault("scripts", {})
    if script not in scripts:
        print(f"[verification-lane-coverage] '{script}' is not registered")
        return 3
    del scripts[script]
    doc["scripts"] = dict(sorted(scripts.items()))
    dispositions_path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[verification-lane-coverage] unregistered: {script} (reason recorded: {reason.strip()})")
    return 0


def cmd_register(
    root: Path,
    dispositions_path: Path,
    script: str,
    disposition: str,
    reason: str,
    owner: str,
    review_by: str,
) -> int:
    """Register one currently-unreferenced script's disposition.

    The registry is the third wire-or-retire path: a dead script that a batch
    has not yet wired to a lane or retired is recorded here with an owner, a
    reason and a review date, so the *unregistered* count stays at zero and a
    new orphan cannot appear unnoticed.  Registration never relaxes the raw
    ratchet -- ``max_scripts_unreferenced_anywhere`` still only shrinks.

    Two invariants keep the registry honest:

    * a script that is still referenced anywhere is refused (registering live
      surface would create an immediately stale entry, turning the registry
      into a permanent allowlist), and
    * the disposition must come from the closed vocabulary, so classifying
      debt is an explicit argument rather than free text.
    """
    if not _require_reason(reason):
        return 2
    if not (disposition or "").strip():
        print("[verification-lane-coverage] --disposition is required with --register-script")
        return 2
    if disposition not in SCRIPT_DISPOSITION_VOCABULARY:
        print(
            f"[verification-lane-coverage] unknown disposition '{disposition}'; "
            "add it to SCRIPT_DISPOSITION_VOCABULARY in review first"
        )
        return 2
    if not (owner or "").strip() or not (review_by or "").strip():
        print("[verification-lane-coverage] --owner and --review-by are required")
        return 2

    result = measure(root, DEFAULT_EXEMPTIONS, dispositions_path)
    dead = set(result["scripts_unreferenced_anywhere"])
    if script not in dead:
        print(
            f"[verification-lane-coverage] refusing to register '{script}': it is "
            "not an unreferenced script under scripts/ (live or already retired)"
        )
        return 3
    if not (root / script).is_file():
        print(f"[verification-lane-coverage] '{script}' is not a file")
        return 3

    doc = {"schema_version": "verification-lane-dispositions/v1", "targets": {}, "scripts": {}}
    if dispositions_path.exists():
        doc = json.loads(dispositions_path.read_text(encoding="utf-8"))
    scripts = doc.setdefault("scripts", {})
    existing = scripts.get(script)
    if existing and existing.get("disposition") != disposition:
        print(
            f"[verification-lane-coverage] '{script}' already registered as "
            f"'{existing.get('disposition')}'; refusing to silently reclassify"
        )
        return 3
    scripts[script] = {
        "disposition": disposition,
        "owner": owner.strip(),
        "review_by": review_by.strip(),
        "reason": reason.strip(),
    }
    doc["scripts"] = dict(sorted(scripts.items()))
    dispositions_path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[verification-lane-coverage] registered: {script} as {disposition}")
    return 0


def cmd_retire(root: Path, dispositions_path: Path, script: str, reason: str) -> int:
    """Park one unreferenced script under ``scripts/retired/`` (governed action).

    Retirement is the only way dead surface leaves the raw count: the file is
    moved (history preserved) instead of deleted, recorded in
    ``scripts/retired/retirements.json`` for the audit trail, and its registered
    disposition is removed so ``--check`` never sees a stale entry.  A script
    that is still referenced anywhere is refused.
    """
    if not _require_reason(reason):
        return 2
    result = measure(root, DEFAULT_EXEMPTIONS, dispositions_path)
    return _retire_one(root, dispositions_path, script, reason, set(result["scripts_unreferenced_anywhere"]))


def cmd_retire_all(root: Path, dispositions_path: Path, reason: str) -> int:
    """Park every currently-unreferenced script (one measurement, one batch)."""
    if not _require_reason(reason):
        return 2
    result = measure(root, DEFAULT_EXEMPTIONS, dispositions_path)
    dead = sorted(result["scripts_unreferenced_anywhere"])
    if not dead:
        print("[verification-lane-coverage] nothing to retire: no unreferenced scripts")
        return 0
    # A registered disposition of RETAINED means the owner decided the file is
    # dead-but-required (e.g. a package marker); a batch sweep must not override
    # that decision.  Only the bulk path skips it; --retire SCRIPT is explicit.
    registered: dict = {}
    if dispositions_path.exists():
        registered = json.loads(dispositions_path.read_text(encoding="utf-8")).get("scripts") or {}
    retained = [
        s for s in dead
        if (registered.get(s) or {}).get("disposition") in RETAINED_SCRIPT_DISPOSITIONS
    ]
    for script in retained:
        print(f"[verification-lane-coverage] retained (not retired): {script}")
    targets = [s for s in dead if s not in set(retained)]
    failures = 0
    for script in targets:
        failures += _retire_one(root, dispositions_path, script, reason, set(dead)) != 0
    print(
        f"[verification-lane-coverage] retire-all: {len(targets) - failures}/{len(targets)} "
        f"parked, {len(retained)} retained"
    )
    return 1 if failures else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", metavar="PATH", help="write the full measurement as JSON")
    parser.add_argument("--summary", action="store_true", help="print the human summary")
    parser.add_argument("--check", action="store_true", help="fail when the surface grew past the baseline")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--dispositions", default=str(DEFAULT_DISPOSITIONS))
    parser.add_argument("--list-zero-reference", action="store_true",
                        help="print every zero-reference target, one per line")
    parser.add_argument("--list-unreferenced-scripts", action="store_true",
                        help="print every never-referenced script, one per line")
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="deliberately rewrite the baseline (reviewed governance action)",
    )
    parser.add_argument(
        "--register-script",
        metavar="SCRIPT",
        help="register one unreferenced script's disposition (governed action)",
    )
    parser.add_argument(
        "--register-batch",
        metavar="PATH",
        help="register a reviewed JSON manifest of {script, disposition, reason, owner, review_by}",
    )
    parser.add_argument(
        "--disposition",
        help="disposition value for --register-script (closed vocabulary)",
    )
    parser.add_argument(
        "--owner",
        help="owning team for --register-script (required)",
    )
    parser.add_argument(
        "--review-by",
        help="ISO date by which the registered disposition must be revisited",
    )
    parser.add_argument(
        "--unregister-script",
        metavar="SCRIPT",
        help="remove a script registration that a wiring change made stale",
    )
    parser.add_argument(
        "--record-missing-assets",
        action="store_true",
        help="record the measured absent recipe paths under the absent_assets register",
    )
    parser.add_argument(
        "--retire",
        metavar="SCRIPT",
        help="park one unreferenced script under scripts/retired/ (governed action)",
    )
    parser.add_argument(
        "--reason",
        help="audit-trail reason for --retire (required)",
    )
    parser.add_argument(
        "--retire-all",
        action="store_true",
        help="park every currently-unreferenced script under scripts/retired/",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()

    if args.unregister_script:
        return cmd_unregister_script(
            root, Path(args.dispositions), args.unregister_script, args.reason
        )
    if args.record_missing_assets:
        return cmd_record_missing_assets(
            root, Path(args.dispositions), args.reason, args.owner, args.review_by
        )
    if args.register_batch:
        return cmd_register_batch(root, Path(args.dispositions), Path(args.register_batch))
    if args.register_script:
        return cmd_register(
            root,
            Path(args.dispositions),
            args.register_script,
            args.disposition,
            args.reason,
            args.owner,
            args.review_by,
        )
    if args.retire:
        return cmd_retire(root, Path(args.dispositions), args.retire, args.reason)
    if args.retire_all:
        return cmd_retire_all(root, Path(args.dispositions), args.reason)

    result = measure(root, DEFAULT_EXEMPTIONS, Path(args.dispositions))

    if args.list_zero_reference:
        for name in result["targets_zero_reference"]:
            print(name)
        return 0
    if args.list_unreferenced_scripts:
        for name in result["scripts_unreferenced_anywhere"]:
            print(name)
        return 0

    if args.write_baseline:
        Path(args.baseline).write_text(
            json.dumps(baseline_payload(result), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[verification-lane-coverage] baseline rewritten: {args.baseline}")
    if args.json:
        Path(args.json).write_text(
            json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    if args.summary or not (args.check or args.json):
        print(render_summary(result))

    if args.check:
        baseline_path = Path(args.baseline)
        if not baseline_path.exists():
            print(f"[verification-lane-coverage] DENY baseline missing: {baseline_path}", file=sys.stderr)
            return 2
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        regressions = compare(result, baseline)
        if regressions:
            print("[verification-lane-coverage] DENY verification surface grew:", file=sys.stderr)
            for item in regressions:
                print(f"  - {item}", file=sys.stderr)
            print(
                "  Shrink the surface, or deliberately rewrite the baseline in a reviewed batch.",
                file=sys.stderr,
            )
            return 2
        print(
            "[verification-lane-coverage] PASS surface within the frozen baseline "
            f"(review_by {baseline.get('review_by', 'n/a')})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
