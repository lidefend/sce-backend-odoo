#!/usr/bin/env python3
"""Create deterministic checked-in project-domain rollout evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalized_snapshot(payload: dict[str, object]) -> dict[str, object]:
    actions = []
    for row in payload.get("actions", []):
        actions.append(
            {
                "menuXmlid": row["menu_xmlid"],
                "menuName": row["menu_name"],
                "actionXmlid": row["action_xmlid"],
                "actionName": row["action_name"],
                "model": row["model"],
                "viewMode": row["view_mode"],
                "authority": {
                    "semantics": row["authority"]["semantics"],
                    "menuChain": [
                        {
                            "menuXmlid": layer["menu_xmlid"],
                            "groups": sorted(layer["groups"]),
                        }
                        for layer in row["authority"]["menu_chain"]
                    ],
                    "actionGroups": sorted(row["authority"]["action_groups"]),
                },
                "surfaces": [
                    {
                        "viewType": view["view_type"],
                        "viewXmlid": view["view_xmlid"],
                        "jsClass": view["js_class"],
                        "semantic": view["semantic"],
                        "readiness": view["readiness"],
                        "reason": view["reason"],
                    }
                    for view in row["views"]
                ],
            }
        )
    actions.sort(key=lambda row: (row["menuXmlid"], row["actionXmlid"]))
    return {
        "schemaVersion": payload["schemaVersion"],
        "status": payload["status"],
        "domain": payload["domain"],
        "rootMenuXmlid": payload["root_menu_xmlid"],
        "ownerModule": payload["owner_module"],
        "excludedScopes": ["demo_addons", "external_customer_addons", "user_specific_visibility"],
        "summary": payload["summary"],
        "actions": actions,
        "gaps": payload["gaps"],
    }


def markdown(snapshot: dict[str, object]) -> str:
    summary = snapshot["summary"]
    lines = [
        "# Project Domain Frontend Rollout v1",
        "",
        "This report covers the repository formal-product runtime baseline for the project center.",
        "Demo, customer overlays, and user-specific visibility are deliberately excluded.",
        "",
        "## Summary",
        "",
        f"- status: `{snapshot['status']}`",
        f"- formal actions: `{summary['action_count']}`",
        f"- models: `{summary['model_count']}`",
        f"- ready collection surfaces: `{summary['ready_surface_count']}`",
        f"- readable fallbacks: `{summary['readable_fallback_count']}`",
        f"- structural forms: `{summary['structural_form_count']}`",
        f"- fail-closed surfaces: `{summary['fail_closed_count']}`",
        f"- gaps: `{summary['gap_count']}`",
        "",
        "## Formal entries",
        "",
        "| Menu | Action | Model | Views | Layered authority |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in snapshot["actions"]:
        surfaces = ", ".join(
            f"{item['viewType']}:{item['semantic']}:{item['readiness']}"
            for item in row["surfaces"]
        )
        lines.append(
            "| `{}` | `{}` | `{}` | {} | {} |".format(
                row["menuXmlid"],
                row["actionXmlid"],
                row["model"],
                surfaces,
                " → ".join(
                    "`{}`:[{}]".format(
                        layer["menuXmlid"],
                        ", ".join(f"`{group}`" for group in layer["groups"]) or "public",
                    )
                    for layer in row["authority"]["menuChain"]
                )
                + " → action:[{}]".format(
                    ", ".join(f"`{group}`" for group in row["authority"]["actionGroups"])
                    or "MISSING"
                ),
            )
        )
    lines.extend(["", "## Gap classification", ""])
    if snapshot["gaps"]:
        lines.extend(
            f"- `{item['action_xmlid']}`: `{item['reason']}`"
            for item in snapshot["gaps"]
        )
    else:
        lines.append("No P0/P1 frontend rollout gaps were detected for the formal project-center entries.")
    lines.extend(
        [
            "",
            "## Acceptance routing",
            "",
            "- Primary journey: project ledger opens through its formal action/menu and preserves workspace form authority.",
            "- Security counterexample: a project-read user cannot gain manager-only project lifecycle authority.",
            "- Any future unregistered `smart_*` view class fails this audit closed.",
            "",
        ]
    )
    return "\n".join(lines)


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
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.markdown_output).write_text(markdown(snapshot), encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "actions": len(snapshot["actions"])}, ensure_ascii=False))
    return 0 if snapshot["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
