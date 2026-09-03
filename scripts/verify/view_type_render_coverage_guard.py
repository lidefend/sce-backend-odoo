#!/usr/bin/env python3
"""Validate executable view-type renderer coverage without source-text markers."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "frontend/apps/web/scripts/view_type_render_coverage_probe.ts"
ESBUILD = ROOT / "frontend/apps/web/node_modules/.bin/esbuild"
ACTION_VIEW = ROOT / "frontend/apps/web/src/views/ActionView.vue"
ACTIVITY_PAGE = ROOT / "frontend/apps/web/src/pages/ActivityPage.vue"
ANALYSIS_PAGE = ROOT / "frontend/apps/web/src/pages/AnalysisPage.vue"
SCHEMA = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
ANALYSIS_MODES = ("pivot", "graph")
FALLBACK_MODES = ("calendar", "gantt", "dashboard")
ACTIVITY_CARRIER = "ui.contract.v2.layoutContract.activityProfile"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def run_runtime_probe(root: Path = ROOT) -> dict[str, Any]:
    probe = root / PROBE.relative_to(ROOT)
    esbuild = root / ESBUILD.relative_to(ROOT)
    with tempfile.TemporaryDirectory(prefix="sc-view-type-coverage-") as directory:
        bundle = Path(directory) / "probe.mjs"
        subprocess.run(
            [str(esbuild), str(probe), "--bundle", "--platform=node", "--format=esm", f"--outfile={bundle}"],
            cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        completed = subprocess.run(
            ["node", str(bundle)], cwd=root, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("runtime probe must return an object")
    return payload


def validate_runtime_evidence(evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if evidence.get("scope") != "view_type_render_coverage":
        errors.append("runtime evidence scope mismatch")
    claims = _dict(evidence.get("deliveryClaims"))
    if claims != {"actionRouteProven": False, "browserDeliveryProven": False}:
        errors.append("coverage evidence must not claim action routes or browser delivery")

    registrations = _dict(evidence.get("registrations"))
    fallback = _dict(evidence.get("fallback"))
    analysis_profiles = _dict(evidence.get("analysisProfiles"))
    for mode in ANALYSIS_MODES:
        registration = _dict(registrations.get(mode))
        expected_registration = {
            "semantic": mode,
            "requestedRendererKey": f"core.{mode}",
            "activeRendererKey": f"core.{mode}",
            "status": "ready",
            "outlet": "standard",
            "reasonCode": "",
        }
        for key, expected in expected_registration.items():
            if registration.get(key) != expected:
                errors.append(f"{mode} registration {key} must be {expected!r}")
        profile_evidence = _dict(analysis_profiles.get(mode))
        profile = _dict(profile_evidence.get("profile"))
        model = _dict(profile_evidence.get("model"))
        authority = _dict(profile.get("sourceAuthority"))
        if authority.get("runtime_carrier") != f"ui.contract.v2.layoutContract.{mode}Profile":
            errors.append(f"{mode} normalized profile carrier is missing")
        if model.get("ok") is not True or model.get("reasonCode") != "":
            errors.append(f"{mode} dedicated resolver did not accept the governed carrier")
        if not _list(model.get("dimensions")) or not _list(model.get("rows")):
            errors.append(f"{mode} dedicated resolver did not consume dimensions and records")
    for mode in FALLBACK_MODES:
        registration = _dict(registrations.get(mode))
        expected_registration = {
            "semantic": mode,
            "requestedRendererKey": f"core.{mode}",
            "activeRendererKey": "core.readable_records",
            "status": "fallback",
            "outlet": "standard",
        }
        for key, expected in expected_registration.items():
            if registration.get(key) != expected:
                errors.append(f"{mode} registration {key} must be {expected!r}")
        if not str(registration.get("reasonCode") or "").strip():
            errors.append(f"{mode} fallback requires a reasonCode")

        mode_evidence = _dict(fallback.get(mode))
        presentation = _dict(mode_evidence.get("presentation"))
        descriptor = _dict(mode_evidence.get("descriptor"))
        page = _dict(mode_evidence.get("page"))
        if presentation.get("semantic") != mode:
            errors.append(f"{mode} projection semantic is not preserved")
        if descriptor.get("semantic") != mode or descriptor.get("viewMode") != mode:
            errors.append(f"{mode} executable resolver identity mismatch")
        if descriptor.get("activeRendererKey") != "core.readable_records" or descriptor.get("status") != "fallback":
            errors.append(f"{mode} executable resolver does not select readable fallback")
        if page.get("kind") != "advanced" or not _list(page.get("rows")):
            errors.append(f"{mode} readable record projection is not executable")

    activity_registration = _dict(registrations.get("activity"))
    expected_activity = {
        "semantic": "activity",
        "requestedRendererKey": "core.activity",
        "activeRendererKey": "core.activity",
        "status": "ready",
        "outlet": "standard",
        "reasonCode": "",
    }
    for key, expected in expected_activity.items():
        if activity_registration.get(key) != expected:
            errors.append(f"activity registration {key} must be {expected!r}")

    activity = _dict(evidence.get("activity"))
    if activity.get("decodedCarrier") != ACTIVITY_CARRIER:
        errors.append("activity decoder carrier is missing")
    if activity.get("storeCarrier") != ACTIVITY_CARRIER:
        errors.append("activity normalized store carrier is missing")
    model = _dict(activity.get("model"))
    if model.get("ok") is not True or model.get("reasonCode") != "":
        errors.append("activity dedicated resolver did not accept the governed carrier")
    if not _list(model.get("requestedFields")) or int(model.get("recordCount") or 0) < 1:
        errors.append("activity dedicated resolver did not consume fields and records")
    if activity.get("missingReasonCode") != "ACTIVITY_SOURCE_AUTHORITY_MISSING":
        errors.append("activity missing profile must fail closed")
    return errors


def validate_activity_schema(schema: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validator = Draft202012Validator(schema)
    payload = _dict(_dict(evidence.get("activity")).get("payload"))
    schema_errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    errors.extend(f"activity payload schema: {error.message}" for error in schema_errors)
    layout_schema = _dict(_dict(schema.get("$defs")).get("layoutContract"))
    activity_property = _dict(_dict(layout_schema.get("properties")).get("activityProfile"))
    if activity_property.get("$ref") != "#/$defs/activityProfile":
        errors.append("layoutContract.activityProfile schema carrier is not explicit")
    return errors


def _strip_js_comments_and_strings(source: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output.extend("  ")
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                output.extend("  ")
                index += 2
                state = "block_comment"
                continue
            if char in {"'", '"', "`"}:
                quote = char
                output.append("__STRING__")
                index += 1
                state = "string"
                continue
            output.append(char)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if char == "\n" else " ")
            index += 1
            if char == "\n":
                state = "code"
            continue
        if state == "block_comment":
            output.append("\n" if char == "\n" else " ")
            if char == "*" and next_char == "/":
                output.append(" ")
                index += 2
                state = "code"
            else:
                index += 1
            continue
        output.append("\n" if char == "\n" else " ")
        if char == "\\" and next_char:
            output.append("\n" if next_char == "\n" else " ")
            index += 2
        elif char == quote:
            index += 1
            state = "code"
        else:
            index += 1
    return "".join(output)


class _ActionViewTemplateParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.template_depth = 0
        self.seen_root_template = False
        self.stack: list[dict[str, bool]] = []
        self.activity_surface = False
        self.analysis_surface = False
        self.advanced_surface = False
        self.advanced_rows = False

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {str(key or "").lower(): str(value or "") for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = self._attrs(attrs)
        if tag == "template":
            if not self.seen_root_template:
                self.seen_root_template = True
                self.template_depth = 1
                self.stack.append({"advanced": False, "unreachable": False})
                return
            if self.template_depth:
                self.template_depth += 1
        if not self.template_depth:
            return
        ancestor_advanced = any(row["advanced"] for row in self.stack)
        ancestor_unreachable = any(row["unreachable"] for row in self.stack)
        condition = attributes.get("v-if", attributes.get("v-else-if", "")).strip().lower()
        unreachable = ancestor_unreachable or condition in {"false", "0", "null", "undefined"}
        classes = set(attributes.get("class", "").split())
        advanced = ancestor_advanced or (tag == "section" and "advanced-view" in classes and bool(attributes.get("v-else-if")))
        if tag == "activitypage" and not unreachable:
            expression = re.sub(r"\s+", "", attributes.get("v-else-if", ""))
            self.activity_surface = expression == "viewMode==='activity'" and attributes.get(":model") == "activitySurfaceModel"
        if tag == "analysispage" and not unreachable:
            expression = re.sub(r"\s+", "", attributes.get("v-else-if", ""))
            self.analysis_surface = expression == "viewMode==='pivot'||viewMode==='graph'" and attributes.get(":model") == "analysisSurfaceModel"
        if advanced and not ancestor_advanced and not unreachable:
            self.advanced_surface = True
        if tag == "article" and ancestor_advanced and not unreachable:
            loop = re.sub(r"\s+", "", attributes.get("v-for", ""))
            if "vm.content.advanced?.rows" in loop:
                self.advanced_rows = True
        self.stack.append({"advanced": advanced, "unreachable": unreachable})

    def handle_endtag(self, tag: str) -> None:
        if not self.template_depth:
            return
        if self.stack:
            self.stack.pop()
        if tag.lower() == "template":
            self.template_depth -= 1


def validate_action_view_structure(source: str, *, activity_page_exists: bool, analysis_page_exists: bool = True) -> list[str]:
    errors: list[str] = []
    parser = _ActionViewTemplateParser()
    parser.feed(source)
    if not parser.activity_surface:
        errors.append("ActionView has no reachable ActivityPage bound to activitySurfaceModel")
    if not parser.analysis_surface:
        errors.append("ActionView has no reachable AnalysisPage bound to analysisSurfaceModel")
    if not parser.advanced_surface or not parser.advanced_rows:
        errors.append("ActionView has no reachable readable advanced-record fallback surface")
    script_match = re.search(r"<script\b[^>]*>(.*?)</script>", source, flags=re.DOTALL | re.IGNORECASE)
    script = _strip_js_comments_and_strings(script_match.group(1) if script_match else "")
    if not re.search(r"^\s*import\s+ActivityPage\s+from\s+__STRING__\s*;?\s*$", script, flags=re.MULTILINE):
        errors.append("ActionView does not statically import ActivityPage")
    if not re.search(r"^\s*import\s+AnalysisPage\s+from\s+__STRING__\s*;?\s*$", script, flags=re.MULTILINE):
        errors.append("ActionView does not statically import AnalysisPage")
    if not activity_page_exists:
        errors.append("ActivityPage renderer file is missing")
    if not analysis_page_exists:
        errors.append("AnalysisPage renderer file is missing")
    return errors


def validate_current_architecture(root: Path = ROOT) -> list[str]:
    evidence = run_runtime_probe(root)
    schema = json.loads((root / SCHEMA.relative_to(ROOT)).read_text(encoding="utf-8"))
    action_view = (root / ACTION_VIEW.relative_to(ROOT)).read_text(encoding="utf-8")
    errors = validate_runtime_evidence(evidence)
    errors.extend(validate_activity_schema(schema, evidence))
    errors.extend(validate_action_view_structure(
        action_view,
        activity_page_exists=(root / ACTIVITY_PAGE.relative_to(ROOT)).is_file(),
        analysis_page_exists=(root / ANALYSIS_PAGE.relative_to(ROOT)).is_file(),
    ))
    return errors


def main() -> int:
    try:
        errors = validate_current_architecture()
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
        errors = [f"coverage evidence unavailable: {exc}"]
    if errors:
        print("[FAIL] view_type_render_coverage_guard")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[OK] view_type_render_coverage_guard")
    print("- analysis: pivot, graph -> governed profile resolver -> AnalysisPage")
    print("- fallback: calendar, gantt, dashboard -> core.readable_records")
    print("- activity: decoder -> normalized store -> core.activity resolver -> ActivityPage")
    print("- delivery_claims: action_route=false browser_delivery=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
