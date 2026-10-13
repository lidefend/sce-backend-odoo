#!/usr/bin/env python3
"""Fail when a list-surface claim is bound to evidence that does not support it.

The page-pattern ledgers bind a conclusion to a concrete observation, e.g.
``... gates 108/108 list-surface checks ...``. A claim is only proof when the
cited artifact is *archived* under a recorded identity and when its recorded
gate counts equal the claimed ones.

This was a real defect: ``collection.header-actions`` and
``collection.toolbar-surface`` cited ``.runtime/final-acceptance/list-surface-structure.json``
as ``316/316 gated``, but that mutable path had since been overwritten by a
payment.request create/edit run whose document records ``records 12/12`` and
``gated 0/0``. The ledger therefore asserted list-surface coverage that no
artifact supported — and the guard itself depended on a machine-local file that
may not exist at all on another checkout.

Both problems are fixed at once by binding claims to a tracked, hash-verified
evidence archive (``.../rendering-detail/evidence-archive/manifest.v1.json``):

* a claim must cite an artifact the archive records;
* when a local copy exists its sha256 must match the archived identity, so a
  path that was overwritten by another run stops proving the claim;
* when no local copy exists the archived identity still adjudicates the claim,
  so the guard is machine-independent;
* the archived schema and gate counts must support the claimed ``X/Y``.

Restore the content of archived artifacts with
``make evidence.archive.fetch ARCHIVE_ROOT=<dir>``; the guard never requires it.

Rules, all mechanical:

* every ``X/Y gated`` claim must name at least one artifact path;
* that path must be archived with ``schema == frontend_list_surface_structure_browser.v1``;
* the archived evidence must gate the list surface (``gated.total > 0``);
* the archived ``gated`` counts must equal the claimed ``X/Y``.

Exit code 0 means every gated claim in the scanned index is bound to an archived
identity that supports it.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "docs" / "frontend_productization" / "rendering-detail"
ARCHIVE_RELATIVE = "docs/frontend_productization/rendering-detail/evidence-archive/manifest.v1.json"
ARCHIVE_SCHEMA = "frontend_evidence_archive.v1"
SURFACE_SCHEMA = "frontend_list_surface_structure_browser.v1"
PATH_RE = re.compile(r"(?:\.runtime|artifacts)/[A-Za-z0-9_./@-]*\.[A-Za-z0-9]{1,6}")
# Both observed phrasings: "316/316 gated" and "gates 316/316 checks".
CLAIM_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s+(?:gated|checks)")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class BindingError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _strings(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def index_documents(directory: Path | None = None) -> list[Path]:
    base = directory or INDEX_DIR
    if not base.exists():
        raise BindingError(f"{base} does not exist")
    return sorted(path for path in base.iterdir() if path.suffix in (".json", ".md"))


def document_strings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return list(_strings(json.loads(text)))
    return text.splitlines()


def load_archive() -> tuple[dict[str, dict], list[str]]:
    """Return ``{artifact: entry}`` plus any integrity problems in the archive."""
    target = ROOT / ARCHIVE_RELATIVE
    problems: list[str] = []
    if not target.is_file():
        raise BindingError(f"{ARCHIVE_RELATIVE} is missing: claims cannot be bound to any evidence identity")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BindingError(f"{ARCHIVE_RELATIVE} is not valid JSON: {exc}") from exc
    if payload.get("schema") != ARCHIVE_SCHEMA:
        raise BindingError(f"{ARCHIVE_RELATIVE}: unexpected schema {payload.get('schema')!r}")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise BindingError(f"{ARCHIVE_RELATIVE}: no archived entries")
    archive: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append(f"archive entry is not an object: {entry!r}")
            continue
        artifact = str(entry.get("artifact") or "")
        if not artifact:
            problems.append("archive entry names no artifact")
            continue
        if artifact in archive:
            problems.append(f"archive declares {artifact} more than once")
            continue
        hash_value = str(entry.get("sha256") or "")
        if not SHA256_RE.match(hash_value):
            problems.append(f"archive entry {artifact} declares no valid sha256")
        if entry.get("schema") != SURFACE_SCHEMA:
            problems.append(f"archive entry {artifact} does not declare {SURFACE_SCHEMA}")
        archive[artifact] = entry
    return archive, problems


def audit_string(document: Path, text: str, archive: dict[str, dict]) -> list[str]:
    claim = CLAIM_RE.search(text)
    if not claim:
        return []
    claimed_passed, claimed_total = int(claim.group(1)), int(claim.group(2))
    references = sorted({match.group(0) for match in PATH_RE.finditer(text)})
    if not references:
        return [f"{document.name}: a gated claim names no artifact path: {claim.group(0)}"]
    problems: list[str] = []
    bound: list[tuple[str, dict]] = []
    for reference in references:
        entry = archive.get(reference)
        if entry is None:
            continue
        local = ROOT / reference
        if local.is_file():
            actual = sha256(local)
            if actual != entry["sha256"]:
                problems.append(
                    f"{document.name}: {reference} was overwritten after archiving "
                    f"(sha256 {actual[:16]} != archived {str(entry['sha256'])[:16]}); a mutable path "
                    f"cannot prove {claim.group(0)}"
                )
                continue
        bound.append((reference, entry))
    if not bound:
        if problems:
            return problems
        return [
            f"{document.name}: the claim {claim.group(0)!r} cites no artifact bound to an archived "
            f"identity: {references}"
        ]
    for reference, entry in bound:
        gated = entry.get("gated") or {}
        passed = int(gated.get("passed") or 0)
        total = int(gated.get("total") or 0)
        if total <= 0:
            problems.append(
                f"{document.name}: {reference} is cited for {claim.group(0)} but gates nothing "
                f"(gated {passed}/{total}); it is not list-surface evidence"
            )
            continue
        if (passed, total) != (claimed_passed, claimed_total):
            problems.append(
                f"{document.name}: the claim {claim.group(0)} does not match the archived {reference} "
                f"(archive records gated {passed}/{total})"
            )
    return problems


def audit(directory: Path | None = None) -> list[str]:
    archive, problems = load_archive()
    for document in index_documents(directory):
        for text in document_strings(document):
            problems.extend(audit_string(document, text, archive))
    return problems


def main(argv: list[str] | None = None) -> int:
    target = Path(argv[0]) if argv else None
    problems = audit(target)
    if problems:
        for problem in problems:
            print(f"[list-surface-evidence] DENY {problem}", file=sys.stderr)
        return 2
    print("[list-surface-evidence] OK every gated claim is bound to an archived evidence identity")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except BindingError as exc:
        print(f"[list-surface-evidence] DENY {exc}", file=sys.stderr)
        raise SystemExit(2)
