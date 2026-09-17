#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = {
    "frontend/apps/web/src/views/LoginView.vue": (
        'class="login-masthead"',
        'class="brand-visual"',
        "pageText('brand_name', config.appBrand.name)",
        "grid-template-areas: 'auth brand'",
        'v-if="!dbInputDisabled"',
        '<ScIcon name="user"',
        '<ScIcon name="lock"',
    ),
    "frontend/apps/web/src/components/design-system/ScCard.vue": (
        "| 'fact' |",
        "fact: { padding: '0' }",
        "[data-appearance='fact']",
        "| 'task-section' |",
        "[data-appearance='task-section']",
    ),
    "frontend/apps/web/src/components/template/FormSection.vue": (
        ":appearance=\"preferReadonlyFacts ? 'fact' : 'form-section'\"",
    ),
    "frontend/apps/web/src/pages/contractForm/ObjectTaskPage.vue": (
        'appearance="task-section"',
        "grid-auto-rows: max-content",
        "align-content: start",
    ),
    "frontend/apps/web/src/pages/contractForm/CanonicalFormNodeRenderer.vue": (
        "fields.value.every((field) => field.readonly)",
        ':prefer-readonly-facts="readonlyFactLayout"',
        "canonical-form-node--readonly-fact",
        "@media (max-width: 480px)",
        ".canonical-form-node--container:not(.canonical-form-node--readonly-fact)",
    ),
    "frontend/apps/web/src/pages/contractForm/canonicalFormRenderState.ts": (
        "applyCanonicalFormValidation",
        "validationFieldErrors[field.fieldCode]",
    ),
    "frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts": (
        "invalid: field.invalid",
        "errorText: field.errorText || undefined",
    ),
    "frontend/apps/web/src/pages/ContractFormPage.vue": (
        "const suppressPageHeaderTitle = computed(() => false)",
        ':title="pageDisplayTitle"',
    ),
    "frontend/apps/web/src/pages/ListPage.vue": (
        'data-semantic-component="ListPage"',
    ),
    "frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue": (
        'class="toolbar-total"',
        "grid-template-areas: 'view search total sort primary'",
    ),
    "frontend/apps/web/src/components/product-list/CollectionRowCell.css": (
        "text-overflow: ellipsis",
        "white-space: nowrap",
    ),
    "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue": (
        "grid-template-columns: minmax(72px, max-content) minmax(0, 1fr)",
        ".o2m-readonly-row:last-child",
    ),
    "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue": (
        "grid-auto-rows: max-content",
        "align-content: start",
    ),
    "frontend/apps/web/src/layouts/AppShell.css": (
        "max-height: 100%",
        "max-block-size: 100%",
        ".shell :deep(.sidebar--scroll)",
        "overflow: hidden",
    ),
    "frontend/apps/web/src/layouts/AppShell.vue": (
        "workspacePanelMode === 'catalog'",
        "平台应用",
        "workspacePanelMode === 'navigation'",
    ),
}
FORBIDDEN_BY_SOURCE = {
    "frontend/apps/web/src/pages/contractForm/canonicalFormRenderState.ts": (
        "message.includes(field.label)",
    ),
    "frontend/apps/web/src/pages/ListPage.vue": (
        "ScPageHeader",
        "ProductPageHeader",
    ),
}
FORBIDDEN_PRODUCT_HINTS = (
    "payment.request",
    "project.project",
    "action_id=",
    "menu_id=",
)

PAGE_HEADER_TITLE_SOURCE = "frontend/apps/web/src/pages/ContractFormPage.vue"
_BOOLEAN_TOKENS = ("&&", "||", "!", "(", ")", "true", "false")


class _BooleanExpression:
    """Minimal evaluator for the boolean binding of one template attribute."""

    def __init__(self, expression: str, variables: dict[str, bool]) -> None:
        tokens = re.findall(r"&&|\|\||!|\(|\)|[A-Za-z_][A-Za-z0-9_]*", expression)
        if "".join(tokens) != re.sub(r"\s+", "", expression):
            raise ValueError(f"unsupported syntax in {expression!r}")
        for token in tokens:
            if token in _BOOLEAN_TOKENS or token in variables:
                continue
            raise ValueError(f"unknown identifier {token!r} in {expression!r}")
        self.tokens = tokens
        self.variables = variables
        self.index = 0

    def parse(self) -> bool:
        value = self._or()
        if self.index != len(self.tokens):
            raise ValueError(f"trailing tokens in {self.tokens}")
        return value

    def _peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _or(self) -> bool:
        value = self._and()
        while self._peek() == "||":
            self.index += 1
            value = self._and() or value
        return value

    def _and(self) -> bool:
        value = self._unary()
        while self._peek() == "&&":
            self.index += 1
            value = self._unary() and value
        return value

    def _unary(self) -> bool:
        token = self._peek()
        if token == "!":
            self.index += 1
            return not self._unary()
        if token == "(":
            self.index += 1
            value = self._or()
            if self._peek() != ")":
                raise ValueError("unbalanced parentheses in hide-title binding")
            self.index += 1
            return value
        if token in ("true", "false"):
            self.index += 1
            return token == "true"
        if token in self.variables:
            self.index += 1
            return bool(self.variables[token])
        raise ValueError(f"unexpected token {token!r} in hide-title binding")


def _page_header_title_failures(text: str) -> list[str]:
    """Behaviour model for the record page's authoritative title.

    The guard evaluates the real ``:hide-title`` binding under both page states
    instead of matching a literal string: a record page must never hide its
    authoritative title, and a configuration preview must always show it so the
    administrator can identify the page being configured.
    """
    failures: list[str] = []
    binding = re.search(r':hide-title="([^"]*)"', text)
    if not binding:
        return [f"page-pattern parity requirement missing: {PAGE_HEADER_TITLE_SOURCE}: :hide-title binding"]
    default = re.search(r"const suppressPageHeaderTitle = computed\(\(\) => (true|false)\)", text)
    if not default:
        return [f"page-pattern parity requirement missing: {PAGE_HEADER_TITLE_SOURCE}: suppressPageHeaderTitle default"]
    suppress = default.group(1) == "true"
    states = (
        ("record page", False, suppress),
        ("configuration preview", True, suppress),
        # A preview must keep the authoritative title even when suppression is
        # requested, otherwise the administrator cannot identify the page.
        ("configuration preview", True, True),
    )
    for surface, preview, flag in states:
        requested = "requested suppression" if flag else "declared default"
        try:
            hidden = _BooleanExpression(binding.group(1), {
                "suppressPageHeaderTitle": flag, "isConfigurationPreview": preview,
            }).parse()
        except ValueError as error:
            failures.append(f"page-pattern parity: unusable :hide-title binding for {surface} ({requested}): {PAGE_HEADER_TITLE_SOURCE}: {error}")
            continue
        if hidden:
            failures.append(f"page-pattern parity: the {surface} must not hide its authoritative title ({requested}): {PAGE_HEADER_TITLE_SOURCE}")
    return failures


def validate(read_text=lambda source: (ROOT / source).read_text(encoding="utf-8")) -> list[str]:
    failures: list[str] = []
    for source, requirements in REQUIREMENTS.items():
        text = read_text(source)
        if source == PAGE_HEADER_TITLE_SOURCE:
            failures.extend(_page_header_title_failures(text))
        for requirement in requirements:
            if requirement not in text:
                failures.append(f"page-pattern parity requirement missing: {source}: {requirement}")
        for forbidden in FORBIDDEN_PRODUCT_HINTS:
            if forbidden in text:
                failures.append(f"page-pattern parity contains product-specific routing hint: {source}: {forbidden}")
        for forbidden in FORBIDDEN_BY_SOURCE.get(source, ()):
            if forbidden in text:
                failures.append(f"page-pattern parity contains duplicate heading owner: {source}: {forbidden}")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("[frontend_page_pattern_reference_parity_guard] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"[frontend_page_pattern_reference_parity_guard] PASS surfaces={len(REQUIREMENTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
