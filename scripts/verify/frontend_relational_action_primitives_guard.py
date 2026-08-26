#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
X2MANY = ROOT / "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue"
VIEW_RELATION = ROOT / "frontend/apps/web/src/components/view/ViewRelationalRenderer.vue"


def validate(x2many: str | None = None, view_relation: str | None = None) -> list[str]:
    x2m = x2many if x2many is not None else X2MANY.read_text(encoding="utf-8")
    view = view_relation if view_relation is not None else VIEW_RELATION.read_text(encoding="utf-8")
    failures: list[str] = []
    x2many_actions = (
        '<ScButton\n              v-if="adapter.relationCreateMode(field.name) === \'page\'"',
        '<ScButton\n        v-if="adapter.one2manyCanCreate(field.name)"',
        '<ScButton\n          class="ghost o2m-row-remove"',
        'v-for="row in adapter.removedOne2manyRows(field.name)"',
        '>上一页</ScButton>',
        '>下一页</ScButton>',
    )
    for marker in x2many_actions:
        if marker not in x2m:
            failures.append(f"X2Many governed command missing {marker}")
    view_actions = (
        '<ScButton v-if="canEdit" class="relational-add"',
        '<ScButton class="relational-link"',
        '<ScButton class="relational-edit"',
        '<ScButton class="relational-delete" type="button" variant="danger"',
        '<ScButton class="relational-save" type="button" variant="primary" :loading="saving"',
        '<ScButton class="relational-cancel"',
        '<ScInput v-model="draftName"',
    )
    for marker in view_actions:
        if marker not in view:
            failures.append(f"View relational governed control missing {marker}")
    forbidden = (
        '<button\n              v-if="adapter.relationCreateMode(field.name)',
        '<button\n        v-if="adapter.one2manyCanCreate(field.name)"',
        '<button class="relational-add"',
        '<button class="relational-edit"',
        '<button class="relational-delete"',
        '<button class="relational-save"',
        '<button class="relational-cancel"',
    )
    if any(marker in x2m or marker in view for marker in forbidden):
        failures.append("relational surface retains a generic legacy command")
    stateful_native = (
        'v-for="option in adapter.selectedRelationOptions(field.name)"',
        'v-for="option in adapter.filteredRelationOptions(field.name).slice(0, 8)"',
    )
    for marker in stateful_native:
        if marker not in x2m:
            failures.append(f"X2Many lost stateful native relation control {marker}")
    if x2m.count("<ScButton") != 6:
        failures.append(f"X2Many expected 6 governed commands, found {x2m.count('<ScButton')}")
    if view.count("<ScButton") != 6:
        failures.append(f"View relational expected 6 governed commands, found {view.count('<ScButton')}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_relational_action_primitives_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_relational_action_primitives_guard] PASS x2many=6 view_relation=6")
