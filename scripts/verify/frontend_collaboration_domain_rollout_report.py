#!/usr/bin/env python3
"""Create deterministic checked-in collaboration rollout evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _load_shared_reporter():
    shared_path = Path(__file__).with_name("frontend_project_domain_rollout_report.py")
    spec = importlib.util.spec_from_file_location(
        "frontend_project_domain_rollout_report_shared", shared_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"shared domain rollout reporter is unavailable: {shared_path}")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    return shared


_SHARED = _load_shared_reporter()


def normalized_snapshot(payload):
    snapshot = _SHARED.normalized_snapshot(payload)
    runtime = payload.get("form_contract_runtime")
    if isinstance(runtime, dict):
        snapshot["formContractRuntime"] = {
            "actionXmlid": runtime.get("action_xmlid"),
            "viewXmlid": runtime.get("view_xmlid"),
            "selectedContractXmlid": runtime.get("selected_contract_xmlid"),
            "presentationMode": runtime.get("presentation_mode"),
            "effectiveRenderProfile": runtime.get("effective_render_profile"),
            "formStructureAuthority": runtime.get("form_structure_authority"),
        }
    return snapshot


def markdown(snapshot, title):
    rendered = _SHARED.markdown(snapshot, title).rstrip()
    runtime = snapshot.get("formContractRuntime")
    if not isinstance(runtime, dict):
        return rendered + "\n"
    lines = [
        "",
        "## Exact form Contract V2 runtime",
        "",
        f"- action: `{runtime.get('actionXmlid')}`",
        f"- resolved form view: `{runtime.get('viewXmlid')}`",
        f"- selected contract: `{runtime.get('selectedContractXmlid')}`",
        f"- presentation mode: `{runtime.get('presentationMode')}`",
        f"- effective render profile: `{runtime.get('effectiveRenderProfile')}`",
        f"- form structure authority: `{runtime.get('formStructureAuthority')}`",
        "",
    ]
    return rendered + "\n" + "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    snapshot = normalized_snapshot(payload)
    Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_output).write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(args.markdown_output).write_text(
        markdown(snapshot, "Collaboration Domain Frontend Rollout v1"),
        encoding="utf-8",
    )
    print(json.dumps({"status": snapshot["status"], "actions": len(snapshot["actions"])}))
    return 0 if snapshot["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
