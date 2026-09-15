#!/usr/bin/env python3
from pathlib import Path
import re
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]
X2MANY = ROOT / "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue"
ONE2MANY_CELL = ROOT / "frontend/apps/web/src/components/template/One2ManyCellEditor.vue"
VIEW_RELATION = ROOT / "frontend/apps/web/src/components/view/ViewRelationalRenderer.vue"


def x2many_command_ownership_errors(source: str) -> list[str]:
    template = re.sub(r"<!--[\s\S]*?-->", "", source.split("<script", 1)[0])
    class Buttons(HTMLParser):
        def __init__(self):
            super().__init__()
            self.calls = []

        def handle_starttag(self, tag, attrs):
            if tag == "scbutton":
                self.calls.append(dict(attrs))

    parser = Buttons()
    parser.feed(template)
    buttons = re.findall(r"<ScButton\b[\s\S]*?</ScButton>", template)
    disclosures = [button for button in buttons if 'class="o2m-readonly-value-trigger"' in button]
    disclosure_attrs = [attrs for attrs in parser.calls if attrs.get("class") == "o2m-readonly-value-trigger"]
    failures = []
    if len(parser.calls) - len(disclosure_attrs) != 9:
        failures.append("X2Many must retain exactly 9 governed commands alongside readonly disclosure")
    if len(disclosures) != 1 or len(disclosure_attrs) != 1:
        return failures + ["X2Many must retain exactly one readonly value disclosure"]
    button = disclosures[0]
    popovers = re.findall(r"<ScPopover\b[\s\S]*?</ScPopover>", template)
    owners = [popover for popover in popovers if button in popover]
    required = ('type="button"', 'appearance="structured-content"', 'variant="ghost"',
                ':title="readonlyCellValue(row[column.name])"',
                ':aria-label="`查看完整${column.label}：${readonlyCellValue(row[column.name])}`"',
                '>{{ readonlyCellValue(row[column.name]) }}</ScButton>')
    if (len(owners) != 1
            or 'v-if="readonlyCellCanExpand(column, row[column.name])"' not in owners[0]
            or 'trigger="click"' not in owners[0]
            or '<template #trigger>' not in owners[0]
            or any(marker not in button for marker in required)
            or set(disclosure_attrs[0]) - {"type", "class", "appearance", "variant", "size", ":title", ":aria-label"}):
        failures.append("readonly value disclosure must only reveal its canonical cell value through the popover")
    return failures


def validate(
    x2many: str | None = None,
    view_relation: str | None = None,
    one2many_cell: str | None = None,
) -> list[str]:
    x2m = x2many if x2many is not None else X2MANY.read_text(encoding="utf-8")
    view = view_relation if view_relation is not None else VIEW_RELATION.read_text(encoding="utf-8")
    cell = one2many_cell if one2many_cell is not None else ONE2MANY_CELL.read_text(encoding="utf-8")
    failures: list[str] = []
    x2many_actions = (
        '<slot name="collection-actions" />',
        '<ScButton\n          v-if="adapter.one2manyCanCreate(field.name)"',
        '<ScButton\n              v-if="adapter.one2manyCanOpenRow(field.name, row._row)"',
        '<ScButton\n              v-if="adapter.one2manyCanUnlink(field.name)"\n              class="o2m-row-remove"',
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
        '<button\n          v-if="adapter.one2manyCanCreate(field.name)"',
        '<button class="relational-add"',
        '<button class="relational-edit"',
        '<button class="relational-delete"',
        '<button class="relational-save"',
        '<button class="relational-cancel"',
    )
    if any(marker in x2m or marker in view for marker in forbidden):
        failures.append("relational surface retains a generic legacy command")
    if "isSettlementIntroduceField" in x2m or "SettlementIntroduceDialog" in x2m:
        failures.append("shared X2Many surface retains a business-specific collection action")
    forbidden_variant_overrides = (
        ".chip-btn {",
        ".ghost {",
        ".relational-add,",
        ".relational-delete {",
        ".relational-save {",
    )
    if any(marker in x2m or marker in view for marker in forbidden_variant_overrides):
        failures.append("relational surface overrides governed ScButton variant presentation")
    if ':disabled="saving" @click="cancelEdit"' in view:
        failures.append("relational cancel changed the existing transaction settlement boundary")
    stateful_relation_controls = (
        'v-for="att in adapter.selectedRelationOptions(field.name)"',
        'ProfessionalManyToManySelect',
    )
    for marker in stateful_relation_controls:
        if marker not in x2m:
            failures.append(f"X2Many lost stateful governed relation control {marker}")
    if any(marker in source for source in (x2m, cell) for marker in ('<button', '<input', '<select')):
        failures.append("X2Many retains a raw interactive control outside the primitive adapter")
    readonly_attachment_markers = (
        ':data-control-state="field.readonly ? \'readonly\' : \'editable\'"',
        'v-if="!field.readonly"\n            variant="ghost"',
        'v-else-if="field.readonly"\n        class="attachment-empty"',
        'v-if="!field.readonly"\n        :key="uploadTick"',
        'if (field.readonly) return;',
    )
    for marker in readonly_attachment_markers:
        if marker not in x2m:
            failures.append(f"readonly attachment authority is incomplete: {marker}")
    failures.extend(x2many_command_ownership_errors(x2m))
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
    print("[frontend_relational_action_primitives_guard] PASS x2many_commands=9 readonly_disclosures=1 delegated_slots=1 cell_editor=governed view_relation=6 raw_controls=0 readonly_attachments=fail_closed")
