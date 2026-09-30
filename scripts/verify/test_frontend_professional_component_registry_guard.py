import unittest

from scripts.verify.frontend_professional_component_registry_guard import (
    ROOT,
    SEMANTIC_MARKERS,
    condition_is_live,
    regex_can_start,
    validate,
)


class ProfessionalComponentRegistryGuardTest(unittest.TestCase):
    def test_repository_passes(self):
        self.assertEqual(validate(), [])

    def test_missing_presenter_resolution_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("contractFormPresenter.ts"):
                return value.replace("resolveContractProfessionalComponent({", "bypassRegistry({")
            return value

        self.assertTrue(any("Presenter" in failure for failure in validate(source)))

    def test_missing_dom_marker_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace("data-component-readiness", "data-readiness-removed")
            return value

        self.assertTrue(any("data-component-readiness" in failure for failure in validate(source)))

    def test_removed_renderer_branch_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "componentRenderer === 'ProfessionalBusinessValueControl'",
                    "componentRenderer === 'RemovedRenderer'",
                )
            return value

        self.assertTrue(any("ProfessionalBusinessValueControl" in failure for failure in validate(source)))

    def test_missing_fail_closed_branch_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace("data-field-fail-closed", "data-field-fail-open")
            return value

        self.assertTrue(any("fail closed" in failure for failure in validate(source)))

    def test_missing_renderer_union_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("PROFESSIONAL_COMPONENT_RENDERERS = Object.freeze([", "RENDERER_NAMES = (")
            return value

        self.assertTrue(any("closed renderer union" in failure for failure in validate(source)))

    def test_comment_only_renderer_mention_fails(self):
        """A comment must not be able to stand in for a renderer branch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "componentRenderer === 'ProfessionalBusinessValueControl'",
                    "componentRenderer === 'RemovedRenderer'",
                ) + "\n// renderer branch: 'ProfessionalBusinessValueControl'\n"
            return value

        self.assertTrue(any("ProfessionalBusinessValueControl" in failure for failure in validate(source)))

    def test_plain_string_renderer_mention_fails(self):
        """A plain string literal is not a renderer dispatch either."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "componentRenderer === 'ProfessionalBusinessValueControl'",
                    "componentRenderer === 'RemovedRenderer'",
                ) + "\nconst rendererProbe = 'ProfessionalBusinessValueControl';\n"
            return value

        self.assertTrue(any("ProfessionalBusinessValueControl" in failure for failure in validate(source)))

    def test_ghost_renderer_with_commented_branch_fails(self):
        """A union member no branch dispatches fails even when prose names it."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostRenderer',\n  'FormSectionField',")
            if path.endswith("FormSection.vue"):
                return value + "\n<!-- GhostRenderer -->\n// GhostRenderer\n"
            return value

        self.assertTrue(any("GhostRenderer" in failure for failure in validate(source)))

    def test_unbound_fail_closed_marker_fails(self):
        """The fail-closed marker must stay bound to the unregistered-renderer predicate."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace('v-if="declaresUnknownComponentRenderer(field)"', 'v-if="false"')
            return value

        self.assertTrue(any("fail-closed branch" in failure for failure in validate(source)))

    def test_imported_constant_dispatch_fails(self):
        """Registered over-strict surface: dispatch is matched by literal renderer name."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "componentRenderer === 'ProfessionalBusinessValueControl'",
                    "componentRenderer === PROFESSIONAL_BUSINESS_VALUE_CONTROL",
                )
            return value

        self.assertTrue(any("ProfessionalBusinessValueControl" in failure for failure in validate(source)))


    def test_string_literal_dispatch_fails(self):
        """A quoted sentence is not a branch, even when it spells the comparison."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostControl',\n  'FormSectionField',")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "componentRenderer === 'ProfessionalBusinessValueControl'",
                    "componentRenderer === 'RemovedRenderer'",
                ) + '\nconst _ghost = "componentRenderer === \'GhostControl\'";\n'
            return value

        failures = validate(source)
        self.assertTrue(any("GhostControl" in failure for failure in failures))
        self.assertTrue(any("ProfessionalBusinessValueControl" in failure for failure in failures))

    def test_template_body_text_dispatch_fails(self):
        """Markup text is not a branch either; only the script can dispatch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostControl',\n  'FormSectionField',")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "</template>",
                    "<span hidden>componentRenderer === 'GhostControl'</span>\n</template>",
                    1,
                )
            return value

        self.assertTrue(any("GhostControl" in failure for failure in validate(source)))

    def test_hardcoded_predicate_set_fails(self):
        """The predicate must read the closed union, not a copy of it."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS)",
                    "new Set<string>(['FormSectionField'])",
                )
            return value

        self.assertTrue(
            any("closed renderer union" in failure for failure in validate(source))
        )

    def test_predicate_set_widened_inline_fails(self):
        """Naming the union while adding a name of its own still drifts."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS)",
                    "new Set<string>([...PROFESSIONAL_COMPONENT_RENDERERS, 'GhostRenderer'])",
                )
            return value

        self.assertTrue(any("spreads past" in failure for failure in validate(source)))

    def test_trimmed_predicate_fails(self):
        """The predicate reads the value the producer writes, without trimming."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const renderer = field.componentRenderer;",
                    "const renderer = String(field.componentRenderer || '').trim();",
                )
            return value

        self.assertTrue(any("trims the renderer" in failure for failure in validate(source)))

    def test_marker_removed_from_template_fails(self):
        """The marker has to be bound in the template, not quoted somewhere."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    ":data-field-fail-closed=\"String(field.componentRenderer || '')\"",
                    "",
                )
            return value

        self.assertTrue(any("does not fail closed" in failure for failure in validate(source)))

    def test_spaced_and_renamed_binding_passes(self):
        """Registered tolerance: the binding is matched by shape, not by exact text."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    'v-if="declaresUnknownComponentRenderer(field)"',
                    'v-if = "declaresUnknownComponentRenderer(node)"',
                )
            return value

        self.assertEqual(validate(source), [])


    def test_regex_literal_dispatch_fails(self):
        """A regular expression is a literal too; it cannot dispatch a renderer."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostRegex',\n  'FormSectionField',")
            if path.endswith("paymentSettlementDetailCollectionModel.ts"):
                return value + "\nexport const PROBE = /componentRenderer === 'GhostRegex'/;\n"
            return value

        self.assertTrue(any("GhostRegex" in failure for failure in validate(source)))

    def test_semantic_marker_in_comment_fails(self):
        """The semantic markers are attributes, not words that may sit in prose."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    ':data-component-key="field.componentKey || undefined"',
                    "",
                ) + "\n// data-component-key\n"
            return value

        self.assertTrue(any("data-component-key" in failure for failure in validate(source)))

    def test_predicate_set_concat_fails(self):
        """Extending the union by call still widens the predicate's set."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS)",
                    "new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS.concat(EXTRA_RENDERERS))",
                )
            return value

        self.assertTrue(any("closed renderer union" in failure for failure in validate(source)))

    def test_predicate_set_spread_past_union_fails(self):
        """Spreading past the union names it and still leaves the union behind."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS)",
                    "new Set<string>([...PROFESSIONAL_COMPONENT_RENDERERS, ...EXTRA_RENDERERS])",
                )
            return value

        self.assertTrue(any("spreads past" in failure for failure in validate(source)))

    def test_predicate_set_reassigned_fails(self):
        """A set that is rebound after it is built is not the union any more."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const knownComponentRenderers: ReadonlySet<string> = new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS);",
                    "let knownComponentRenderers: ReadonlySet<string> = new Set<string>(PROFESSIONAL_COMPONENT_RENDERERS);\n"
                    "knownComponentRenderers = new Set<string>([...PROFESSIONAL_COMPONENT_RENDERERS, 'GhostRebind']);",
                )
            return value

        self.assertTrue(
            any("not a constant" in failure or "is reassigned" in failure for failure in validate(source))
        )

    def test_comment_markers_inside_strings_pass(self):
        """Registered tolerance: a marker inside a string must not swallow a branch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    'const probeUrl = "https://example.test/a//b";\n'
                    'const probeBlock = "/* not a comment */";\n'
                    "const slots = useSlots();",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_regex_with_quotes_passes(self):
        """Registered tolerance: quotes inside a regular expression are not a branch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "const probeQuotes = /['\"]/;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])


    def test_control_statement_regex_dispatch_fails(self):
        """A pattern after `if (...)` is still a pattern, not a branch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostRx',\n  'FormSectionField',")
            if path.endswith("paymentSettlementDetailCollectionModel.ts"):
                return value + "\nif (_probe) /componentRenderer === 'GhostRx'/.test(_probe);\n"
            return value

        self.assertTrue(any("GhostRx" in failure for failure in validate(source)))

    def test_control_statement_regex_passes(self):
        """Registered tolerance: a pattern after a control statement is code."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "if (_probe) /['\"]/.test(_probe);\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_marker_as_script_string_fails(self):
        """A marker quoted in the script is not the attribute the field carries."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    ':data-component-key="field.componentKey || undefined"',
                    "",
                ) + '\nconst _fake = "data-component-key";\n'
            return value

        self.assertTrue(any("data-component-key" in failure for failure in validate(source)))

    def test_fail_closed_marker_as_script_string_fails(self):
        """Quoting the fail-closed attribute does not bind it either."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    ":data-field-fail-closed=\"String(field.componentRenderer || '')\"",
                    "",
                ) + '\nconst _fakeMarker = ":data-field-fail-closed=";\n'
            return value

        self.assertTrue(any("does not fail closed" in failure for failure in validate(source)))

    def test_predicate_set_mutated_fails(self):
        """A set that is widened at run time is not the union any more."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "(knownComponentRenderers as Set<string>).add('GhostMutated');\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("is mutated" in failure for failure in validate(source)))


    def test_byte_order_mark_after_control_statement_fails(self):
        """The blank the JavaScript lexer skips is not always Python's blank."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostBlank',\n  'FormSectionField',")
            if path.endswith("paymentSettlementDetailCollectionModel.ts"):
                return value + "\nif (_probe)\ufeff/componentRenderer === 'GhostBlank'/.test(_probe);\n"
            return value

        self.assertTrue(any("GhostBlank" in failure for failure in validate(source)))

    def test_apostrophe_in_template_passes(self):
        """Registered tolerance: prose punctuation is not a string in a template."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace('role="alert"', 'role="alert" title="don\'t"', 1)
            return value

        self.assertEqual(validate(source), [])

    def test_apostrophe_in_template_body_text_passes(self):
        """Prose punctuation in markup text must not swallow the script imports."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    'class="template-form-section-hint">{{ hint }}',
                    'class="template-form-section-hint">don\'t {{ hint }}',
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_fail_closed_marker_as_style_selector_fails(self):
        """A selector in the style block does not bind the marker on a field."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                value = value.replace(
                    ":data-field-fail-closed=\"String(field.componentRenderer || '')\"",
                    "",
                )
                return value.replace(
                    ".field-fail-closed {",
                    '.field-fail-closed[data-field-fail-closed="x"] {',
                    1,
                )
            return value

        self.assertTrue(any("does not fail closed" in failure for failure in validate(source)))

    def test_predicate_set_assigned_over_fails(self):
        """Assigning a new set into the same name is still a widening."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "Object.assign(knownComponentRenderers, ['GhostAssigned']);\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("is mutated" in failure for failure in validate(source)))

    def test_method_call_division_passes(self):
        """Registered tolerance: a method named like a control word is not one."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "const probeRatio = promise.catch(handler) / 2;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])


    def test_for_await_regex_dispatch_fails(self):
        """`for await (...)` is a control statement too, so its `/` opens a pattern."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostAwait',\n  'FormSectionField',")
            if path.endswith("paymentSettlementDetailCollectionModel.ts"):
                return value + "\nfor await (const entry of stream) /componentRenderer === 'GhostAwait'/.test(entry);\n"
            return value

        self.assertTrue(any("GhostAwait" in failure for failure in validate(source)))

    def test_predicate_set_referenced_elsewhere_fails(self):
        """A set named anywhere but its declaration and test can be widened there."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "knownComponentRenderers\n  .add('GhostWidened');\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("referenced beyond" in failure for failure in validate(source)))

    def test_postfix_increment_division_passes(self):
        """Registered tolerance: `hits++ / 2` divides, it does not open a pattern."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "let probeHits = 0;\nprobeHits++ / 2;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_script_string_cannot_forge_the_template_half_fails(self):
        """A `<template>` quoted in the script is not the section's markup half."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return (
                    value.replace('v-if="declaresUnknownComponentRenderer(field)"', 'v-if="false"')
                    .replace(':data-field-fail-closed="String(field.componentRenderer || \'\')"', "")
                    .replace(
                        "</script>",
                        'const _forged = \'<template>x v-if="declaresUnknownComponentRenderer(x)" '
                        ':data-field-fail-closed="y"></template>\';\n</script>',
                        1,
                    )
                )
            return value

        failures = validate(source)
        self.assertTrue(any("fail closed" in failure for failure in failures))
        self.assertTrue(any("fail-closed branch" in failure for failure in failures))

    def test_marker_quoted_in_an_attribute_value_fails(self):
        """A marker written inside an attribute value is text, not an attribute."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                forgery = ':title="' + "'" + ':data-component-key=' + "'" + '"'
                return value.replace(
                    ':data-component-key="field.componentKey || undefined"',
                    forgery,
                    1,
                )
            return value

        self.assertTrue(any("data-component-key" in failure for failure in validate(source)))

    def test_marker_moved_off_the_field_iterator_fails(self):
        """A semantic marker only counts on the element that iterates the fields."""

        inner = '    <template v-if="showHead && $slots.action" #actions><slot name="action" /></template>'
        tail = '\n          :data-contract-adapter="field.contractAdapter || undefined"'

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                moved = value.replace(tail, "", 1)
                assert moved != value
                return moved.replace(
                    inner,
                    inner + '\n    <p :data-contract-adapter="field.contractAdapter || undefined">probe</p>',
                    1,
                )
            return value

        self.assertTrue(
            any("field iterator" in failure for failure in validate(source))
        )

    def test_fail_closed_trio_split_across_elements_fails(self):
        """The predicate call, the marker and the visible alert role share one element."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace('                role="alert"\n', "", 1).replace(
                    '    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>',
                    '    <p role="alert" class="template-form-section-hint">{{ hint }}</p>',
                    1,
                )
            return value

        self.assertTrue(any("alert role on one element" in failure for failure in validate(source)))

    def test_single_quoted_branch_attribute_passes(self):
        """Registered tolerance: a branch attribute may be quoted either way."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    'v-else-if="usesProfessionalBusinessValue(field)"',
                    "v-else-if='usesProfessionalBusinessValue(field)'",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_indirect_eval_rebinding_fails(self):
        """`(0, eval)` reaches the compiler just as `eval(` does."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "(0, eval)('globalThis.Boolean = () => false');\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("rebinds the global eval" in failure for failure in validate(source)))

    def test_branch_element_that_is_not_imported_fails(self):
        """Only an element the script imports can render a registered renderer."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostTag',\n  'FormSectionField',").replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostTag')",
                    1,
                )
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '<q v-if="hint"',
                    '<q v-if="false"',
                ).replace(
                    '    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>',
                    '    <ghostTag v-if="ghostBranch(field)" class="template-form-section-hint">{{ hint }}</ghostTag>',
                    1,
                ).replace(
                    "const slots = useSlots();",
                    "function ghostBranch(field: FormSectionFieldSchema): boolean {\n"
                    "  return field.componentRenderer === 'GhostTag';\n"
                    "}\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("GhostTag" in failure for failure in validate(source)))

    def test_postfix_increment_before_a_predicate_passes(self):
        """Registered tolerance: `hits++ / 2` must not swallow the renderer branches."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "function declaresUnknownComponentRenderer(",
                    "let probeHits = 0;\nconst probeRatio = probeHits++ / 1;\nfunction declaresUnknownComponentRenderer(",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_renderer_laundered_through_a_cast_fails(self):
        """A registration may not name a renderer through a cast."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', "
                    "'GhostControl' as unknown as ProfessionalComponentRenderer)",
                    1,
                )
            return value

        failures = validate(source)
        self.assertTrue(any("bare union member" in failure for failure in failures))
        self.assertTrue(any("unknown-typed cast" in failure for failure in failures))

    def test_registration_naming_an_unlisted_renderer_fails(self):
        """A registration is a renderer call site, not just an entry in the union."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostUnlisted')",
                    1,
                )
            return value

        self.assertTrue(
            any("does not name the registered renderer" in failure for failure in validate(source))
        )

    def test_registration_outside_the_closed_list_fails(self):
        """Registering past the closed list must not add an unchecked renderer."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace(
                    "] as const;",
                    "] as const;\nregistration('sc.extra.ghost', 'ghost', ['char']);",
                    1,
                )
            return value

        self.assertTrue(
            any("outside its closed registration list" in failure for failure in validate(source))
        )

    def test_field_type_mapping_renderer_fails(self):
        """The mapping the factory builds is a renderer call site as well."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace(
                    "'ProfessionalBaseFieldControl'] as [string, ProfessionalComponentRenderer]",
                    "'GhostMapped'] as [string, ProfessionalComponentRenderer]",
                    1,
                )
            return value

        self.assertTrue(
            any("does not name the mapped renderer" in failure for failure in validate(source))
        )

    def test_builtin_prototype_reach_fails(self):
        """Patching a builtin prototype is what would disarm the predicate at load time."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "Set.prototype.has = () => true;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("builtin prototype" in failure for failure in validate(source)))

    def test_doubled_operator_is_a_division_not_a_pattern(self):
        """`hits++ / 2` divides; only a single operator lets a pattern start."""

        self.assertFalse(regex_can_start(list("hits++ / 2;"), 7))
        self.assertFalse(regex_can_start(list("hits-- / 2;"), 7))
        self.assertFalse(regex_can_start(list("base ** 2 / 3;"), 10))
        self.assertTrue(regex_can_start(list("if (x) /re/.test(y);"), 7))
        self.assertTrue(regex_can_start(list("return /re/.test(y);"), 7))
        self.assertFalse(regex_can_start(list("obj.method() / 2;"), 13))

    def test_commented_template_cannot_stand_in_for_the_markup_half_fails(self):
        """A `<template>` written inside a comment is not the section's markup half."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return (
                    "<!-- <template><i v-if=\"declaresUnknownComponentRenderer(f)\" "
                    ':data-field-fail-closed="z" /></template> -->\n'
                ) + value.replace(
                    'v-if="declaresUnknownComponentRenderer(field)"', 'v-if="false"'
                ).replace(':data-field-fail-closed="String(field.componentRenderer || \'\')"', "")
            return value

        failures = validate(source)
        self.assertTrue(any("fail closed" in failure for failure in failures))
        self.assertTrue(any("fail-closed branch" in failure for failure in failures))

    def test_script_word_in_a_template_comment_passes(self):
        """Registered tolerance: the word `<script>` in prose is not a script block."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>',
                    '    <!-- see the <script> block below -->\n'
                    '    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>',
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_script_word_in_an_attribute_value_passes(self):
        """Registered tolerance: `<script>` quoted in an attribute is not a block either."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>',
                    '    <p title="<script> is a tag" class="template-form-section-hint">{{ hint }}</p>',
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_comment_between_callee_and_paren_fails(self):
        """A registration cannot hide from the check behind a comment."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration /*pad*/ ('sc.input.text', 'text', ['char'], 'ready', 'GhostPadded')",
                    1,
                )
            return value

        self.assertTrue(any("GhostPadded" in failure for failure in validate(source)))

    def test_prototype_reached_through_reflection_fails(self):
        """The predicate cannot be disarmed by reaching a prototype indirectly."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "Object.getPrototypeOf(new Set<string>()).has = () => true;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("builtin prototype" in failure for failure in validate(source)))

    def test_branch_in_an_unimported_module_fails(self):
        """A branch counts only where the section can reach it."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostElsewhere',\n  'FormSectionField',").replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostElsewhere')",
                    1,
                )
            if path.endswith("components/template/PageHeader.vue"):
                return value.replace(
                    "</script>",
                    "const never = (componentRenderer: string) => componentRenderer === 'GhostElsewhere';\n"
                    "void never;\n</script>",
                    1,
                )
            return value

        self.assertTrue(any("GhostElsewhere" in failure for failure in validate(source)))

    def test_renderer_renamed_end_to_end_on_a_section_branch_passes(self):
        """Registered tolerance: a renderer renamed in registry, import, tag and helper."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith(("professionalComponentRegistry.ts", "FormSection.vue")):
                return value.replace("ProfessionalBaseFieldControl", "ReachedBranch")
            return value

        self.assertEqual(validate(source), [])

    def test_renderer_renamed_end_to_end_on_a_module_branch_passes(self):
        """Registered tolerance: the same rename where an imported module dispatches."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith(
                (
                    "professionalComponentRegistry.ts",
                    "FormSection.vue",
                    "paymentSettlementDetailCollectionModel.ts",
                )
            ):
                return value.replace("PaymentSettlementDetailCollectionControl", "ReachedBranch")
            return value

        self.assertEqual(validate(source), [])

    def test_renamed_import_still_reaches_the_module_branch_passes(self):
        """A branch is reached under its bound name and found under its export."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "import { isPaymentSettlementDetailCollectionField } from "
                    "'../professional-fields/paymentSettlementDetailCollectionModel';",
                    "import { isPaymentSettlementDetailCollectionField as isPsdcField } from "
                    "'../professional-fields/paymentSettlementDetailCollectionModel';",
                    1,
                ).replace(
                    "return isPaymentSettlementDetailCollectionField(field);",
                    "return isPsdcField(field);",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_arrow_declared_branch_helper_fails(self):
        """Registered over-strict surface: a branch helper is read as a declaration."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostArrow',\n  'FormSectionField',").replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostArrow')",
                    1,
                )
            if path.endswith("FormSection.vue"):
                return value.replace(
                    'v-else-if="usesProfessionalBusinessValue(field)"',
                    'v-else-if="arrowBranch(field)"',
                    1,
                ).replace(
                    "const slots = useSlots();",
                    "const arrowBranch = (field: FormSectionFieldSchema) => "
                    "field.componentRenderer === 'GhostArrow';\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("GhostArrow" in failure for failure in validate(source)))

    def test_dead_arrow_in_an_imported_module_fails(self):
        """Importing a module is not enough: only a function the section reaches."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostDeadBranch',\n  'FormSectionField',").replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostDeadBranch')",
                    1,
                )
            if path.endswith("paymentSettlementDetailCollectionModel.ts"):
                return value + (
                    "\nconst reached = (componentRenderer: string) => componentRenderer === 'GhostDeadBranch';\n"
                    "void reached;\n"
                )
            return value

        self.assertTrue(any("GhostDeadBranch" in failure for failure in validate(source)))

    def test_dead_arrow_in_the_section_script_fails(self):
        """A comparison no template branch names is not a renderer branch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostDeadBranch',\n  'FormSectionField',").replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostDeadBranch')",
                    1,
                )
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "const __audit = (componentRenderer: string) => componentRenderer === 'GhostDeadBranch';\n"
                    "void __audit;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("GhostDeadBranch" in failure for failure in validate(source)))

    def test_dispatch_parked_in_a_helper_no_element_renders_fails(self):
        """A comparison only a helper no branch element renders holds is not a branch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostElsewhere',\n  'FormSectionField',").replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostElsewhere')",
                    1,
                )
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "function isLegacyComplexField(field: FormSectionFieldSchema) {",
                    "function isLegacyComplexField(field: FormSectionFieldSchema) {\n"
                    "  if (field.componentRenderer === 'GhostElsewhere') return false;",
                    1,
                )
            return value

        self.assertTrue(any("GhostElsewhere" in failure for failure in validate(source)))

    def test_global_rebinding_in_the_section_fails(self):
        """Rebinding a global the predicate reads would disarm it at load time."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "(globalThis as unknown as { Boolean: unknown }).Boolean = () => false;\n"
                    "const slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("rebinds the global" in failure for failure in validate(source)))

    def test_shadowing_the_predicate_set_constructor_fails(self):
        """A class of the same name puts another `.has` behind the predicate."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "class Set<T> { has(_value: T): boolean { return true; } }\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("rebinds the global Set" in failure for failure in validate(source)))

    def test_import_binding_a_predicate_global_fails(self):
        """An import that binds `Boolean` disarms the predicate just as well."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "import { Boolean } from '../../utils/booleanish';\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("rebinds the global Boolean" in failure for failure in validate(source)))

    def test_commented_import_cannot_forge_a_reached_module_fails(self):
        """Only a real import names a module the section can reach."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace("  'FormSectionField',", "  'GhostElsewhere',\n  'FormSectionField',").replace(
                    "registration('sc.input.text', 'text', ['char'])",
                    "registration('sc.input.text', 'text', ['char'], 'ready', 'GhostElsewhere')",
                    1,
                )
            if path.endswith("paymentSettlementIntroduceModel.ts"):
                return value + (
                    "\nexport function isPaymentSettlementDetailCollectionField(componentRenderer: string): boolean {\n"
                    "  return componentRenderer === 'GhostElsewhere';\n"
                    "}\n"
                )
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "const slots = useSlots();\n"
                    "// import { isPaymentSettlementDetailCollectionField } from "
                    "'../professional-fields/paymentSettlementIntroduceModel';\n",
                    1,
                )
            return value

        self.assertTrue(any("GhostElsewhere" in failure for failure in validate(source)))

    def test_registration_call_named_in_a_string_passes(self):
        """A sentence that spells a registration call is not a registration."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalComponentRegistry.ts"):
                return value.replace(
                    "const REGISTRATIONS = [",
                    'const _doc = "throws when registration( is called outside the list";\n'
                    "const REGISTRATIONS = [",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_angle_bracket_text_is_not_a_tag_fails(self):
        """`<1` opens no element, so a marker written after it is markup text."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '          :data-component-key="field.componentKey || undefined"\n', "", 1
                ).replace(
                    '    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>',
                    '    <p class="template-form-section-hint"><1 :data-component-key= x></p>',
                    1,
                )
            return value

        self.assertTrue(any("data-component-key" in failure for failure in validate(source)))

    def test_marker_as_body_text_fails(self):
        """A marker must be an attribute name inside a tag, not markup text."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '          :data-component-key="field.componentKey || undefined"\n', "", 1
                ).replace(
                    '    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>',
                    '    <p class="template-form-section-hint">:data-component-key=</p>',
                    1,
                )
            return value

        self.assertTrue(any("data-component-key" in failure for failure in validate(source)))

    def test_kebab_case_branch_element_passes(self):
        """Vue resolves a kebab-case tag to the imported component, so it dispatches."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "<ProfessionalDetailCollectionControl",
                    "<professional-detail-collection-control",
                    1,
                ).replace(
                    "</ProfessionalDetailCollectionControl>",
                    "</professional-detail-collection-control>",
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def test_fail_closed_branch_on_a_dead_tag_fails(self):
        """A shape parked in a constant-false subtree reaches no field render."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                value = value.replace(
                    '                v-if="declaresUnknownComponentRenderer(field)"',
                    '                v-if="false"',
                    1,
                )
                return value.replace(
                    '          <div class="field-label-row">',
                    '          <template v-if="false"><q v-if="declaresUnknownComponentRenderer(field)" role="alert"\n'
                    "             :data-field-fail-closed=\"String(field.componentRenderer || '')\" /></template>\n"
                    '          <div class="field-label-row">',
                    1,
                )
            return value

        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_fail_closed_branch_outside_the_field_iterator_fails(self):
        """The alert has to sit where the field itself is rendered."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                value = value.replace(
                    '                class="field-fail-closed"\n                role="alert"',
                    '                class="field-fail-closed"\n                role="presentation"',
                    1,
                )
                return value.replace(
                    '      <template v-if="displayFields.length">',
                    '      <div v-if="declaresUnknownComponentRenderer(field)" role="alert"\n'
                    "           :data-field-fail-closed=\"String(field.componentRenderer || '')\" />\n"
                    '      <template v-if="displayFields.length">',
                    1,
                )
            return value

        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_dispatch_name_only_a_dead_duplicate_renders_fails(self):
        """A dead copy of the element must not stand in for the rendered one."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                value = value.replace(
                    "              <ProfessionalBusinessValueControl\n"
                    '                v-else-if="usesProfessionalBusinessValue(field)"',
                    "              <div\n                class=\"dead-slot\"\n"
                    '                v-else-if="usesProfessionalBusinessValue(field)"',
                    1,
                )
                return value.replace(
                    '          <div class="field-label-row">',
                    '          <template v-if="false"><ProfessionalBusinessValueControl\n'
                    '             v-if="usesProfessionalBusinessValue(field)" :field="field" /></template>\n'
                    '          <div class="field-label-row">',
                    1,
                )
            return value

        self.assertTrue(any("not rendered by the field iterator" in failure for failure in validate(source)))

    def test_renderer_branch_outside_the_field_iterator_fails(self):
        """A render call outside the field list renders no field."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                value = value.replace(
                    "              <ProfessionalBusinessValueControl\n",
                    "              <div\n",
                    1,
                )
                return value.replace(
                    '      <template v-if="displayFields.length">',
                    '      <ProfessionalBusinessValueControl v-if="usesProfessionalBusinessValue(field)" :field="field" />\n'
                    '      <template v-if="displayFields.length">',
                    1,
                )
            return value

        self.assertTrue(any("not rendered by the field iterator" in failure for failure in validate(source)))

    def _markers_without_the_field_iterator(self):
        value = (ROOT / "frontend/apps/web/src/components/template/FormSection.vue").read_text(encoding="utf-8")
        for marker in SEMANTIC_MARKERS:
            line = f'          :{marker}="field.'
            start = value.index(line)
            value = value[:start] + value[value.index("\n", start) + 1:]
        return value

    def test_semantic_markers_moved_to_a_dead_iterator_fail(self):
        """The markers have to ride the element that renders the field list."""

        replace = (
            '      <template v-if="displayFields.length">',
            '      <template v-if="displayFields.length">\n'
            '        <template v-if="false"><span v-for="(entry, idx) in []" :key="idx" '
            + " ".join(f':{marker}="entry"' for marker in SEMANTIC_MARKERS)
            + ">{{ entry }}</span></template>",
        )

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return self._markers_without_the_field_iterator().replace(*replace, 1)
            return value

        self.assertTrue(any("renders no field list" in failure for failure in validate(source)))

    def test_semantic_markers_on_a_literal_iterator_fail(self):
        """An empty literal is not the field list the markers have to ride."""

        replace = (
            '      <template v-if="displayFields.length">',
            '      <template v-if="displayFields.length">\n'
            '        <span v-for="(entry, idx) in []" :key="idx" '
            + " ".join(f':{marker}="entry"' for marker in SEMANTIC_MARKERS)
            + ">{{ entry }}</span>",
        )

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return self._markers_without_the_field_iterator().replace(*replace, 1)
            return value

        self.assertTrue(any("renders no field list" in failure for failure in validate(source)))

    def test_constructor_reach_fails(self):
        """A constructor reached off a value compiles code that disarms the predicate."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "const revive = (({} as Record<string, unknown>).toString as unknown as "
                    "{ constructor: (source: string) => () => void }).constructor;\n"
                    "revive('globalThis.Boolean = () => false')();\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_document_default_view_reach_fails(self):
        """`document.defaultView` is another name for the global object."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "const globalView = document.defaultView as unknown as Record<string, unknown>;\n"
                    "globalView['Boolean'] = () => false;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_computed_global_key_reach_fails(self):
        """A global name as a string key reaches the global the predicate reads."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "const bag = {} as Record<string, unknown>;\n"
                    "bag['constructor'] = () => false;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_dynamic_import_reach_fails(self):
        """A module loaded at run time runs outside the audited script text."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "void import('./formSection.mapper');\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_fail_closed_branch_hidden_by_v_show_fails(self):
        """A visible alert role on an element bound never to show is not fail-closed."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '                class="field-fail-closed"\n                role="alert"',
                    '                class="field-fail-closed"\n                v-show="false"\n                role="alert"',
                    1,
                )
            return value

        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_fail_closed_branch_hidden_attribute_fails(self):
        """The `hidden` attribute hides the alert however its branch resolves."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '                class="field-fail-closed"\n                role="alert"',
                    '                class="field-fail-closed"\n                hidden\n                role="alert"',
                    1,
                )
            return value

        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_fail_closed_trio_in_a_computed_false_template_fails(self):
        """A condition written as an expression is still a constant to the render."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                value = value.replace('                role="alert"', '                role="presentation"', 1)
                return value.replace(
                    '          <div class="field-label-row">',
                    '          <template v-if="Boolean(false)"><q v-if="declaresUnknownComponentRenderer(field)"\n'
                    "             role=\"alert\" :data-field-fail-closed=\"String(field.componentRenderer || '')\" /></template>\n"
                    '          <div class="field-label-row">',
                    1,
                )
            return value

        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_dispatch_in_a_computed_false_template_fails(self):
        """A dead duplicate under a computed condition dispatches nothing."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                value = value.replace(
                    "              <ProfessionalBusinessValueControl\n"
                    '                v-else-if="usesProfessionalBusinessValue(field)"',
                    "              <div\n                class=\"dead-slot\"\n"
                    '                v-else-if="usesProfessionalBusinessValue(field)"',
                    1,
                )
                return value.replace(
                    '          <div class="field-label-row">',
                    '          <template v-if="Boolean(false)"><ProfessionalBusinessValueControl\n'
                    '             v-if="usesProfessionalBusinessValue(field)" :field="field" /></template>\n'
                    '          <div class="field-label-row">',
                    1,
                )
            return value

        self.assertTrue(any("not rendered by the field iterator" in failure for failure in validate(source)))

    def test_semantic_markers_on_an_ancestor_iterator_fail(self):
        """The markers ride the field list, not a loop that wraps it."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                for marker in SEMANTIC_MARKERS:
                    line = f'          :{marker}="field.'
                    start = value.index(line)
                    value = value[:start] + value[value.index("\n", start) + 1:]
                return value.replace(
                    '      <template v-if="displayFields.length">',
                    '      <template v-if="displayFields.length">\n'
                    '        <div v-for="once in onceList" :key="once" '
                    + " ".join(f':{marker}="once"' for marker in SEMANTIC_MARKERS)
                    + ">",
                    1,
                )
            return value

        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_computed_string_key_reach_fails(self):
        """A template-literal key reaches the same property as a quoted one."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "(frames as unknown as Record<string, unknown>)[`Boolean`] = () => false;\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_concatenated_string_key_reach_fails(self):
        """A key concatenated out of literals is still a string key."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "(globalThis as unknown as Record<string, unknown>)['Boole' + 'an'] = () => false;\n"
                    "const slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_timer_string_reach_fails(self):
        """A timer handed a string compiles it, exactly as `eval` does."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "const slots = useSlots();",
                    "setTimeout('globalThis.Boolean = () => false', 0);\nconst slots = useSlots();",
                    1,
                )
            return value

        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_v_for_of_alias_passes(self):
        """`v-for=\"x of list\"` iterates the same list as `in`."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    'v-for="(field, index) in displayFields"',
                    'v-for="(field, index) of displayFields"',
                    1,
                )
            return value

        self.assertEqual(validate(source), [])

    def _with_script_line(self, line):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace("const slots = useSlots();", line + "\nconst slots = useSlots();", 1)
            return value

        return source

    def _with_fail_closed_attribute(self, attribute):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '                class="field-fail-closed"\n                role="alert"',
                    '                class="field-fail-closed"\n                ' + attribute + '\n                role="alert"',
                    1,
                )
            return value

        return source

    def test_string_key_held_in_a_name_reaches_the_global_fails(self):
        """A key the script keeps in a name reaches the property the key spells."""

        source = self._with_script_line(
            "const dKey = 'default' + 'View';\n"
            "const bKey = 'Bool' + 'ean';\n"
            "const view = (document as unknown as Record<string, Record<string, unknown>>)[dKey];\n"
            "view[bKey] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_every_key_of_a_chain_is_read_fails(self):
        """`value[first][second]` is two accesses, and the second one counts too."""

        source = self._with_script_line(
            "const fKey = 'fil' + 'ter';\n"
            "const cKey = 'con' + 'structor';\n"
            "const revive = (([] as unknown) as Record<string, Record<string, unknown>>)[fKey][cKey] "
            "as unknown as (source: string) => () => void;\n"
            "revive('globalThis.Boolean = () => false')();"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_string_key_picked_out_of_a_list_fails(self):
        """A key picked out of a list of strings is a string key the reading cannot spell out."""

        source = self._with_script_line(
            "const parts = ['con', 'structor'];\n"
            "const cKey = parts[0];\n"
            "const revive = ({} as Record<string, Record<string, unknown>>)[cKey];\n"
            "void revive;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_string_key_outside_the_global_family_passes(self):
        """A key the script holds as a string that names nothing global is not a reach."""

        source = self._with_script_line(
            "const keyName = 'labels';\n"
            "const bag: Record<string, unknown> = {};\n"
            "bag[keyName] = 1;"
        )
        self.assertEqual(validate(source), [])

    def test_global_written_through_object_assign_fails(self):
        """`Object.assign(host, ...)` puts a new value behind a global name at load time."""

        source = self._with_script_line(
            "Object.assign(frames as unknown as Record<string, unknown>, { Boolean: () => false });"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_every_name_of_the_global_object_is_a_host_fails(self):
        """The browser names the global object `parent`, `top`, and `opener` as well."""

        for alias in ("parent", "top", "opener", "frames"):
            with self.subTest(alias=alias):
                source = self._with_script_line(f"const host = {alias};\nvoid host;")
                self.assertTrue(
                    any("rebinds the global" in failure for failure in validate(source)),
                    f"{alias} is a name for the global object",
                )

    def test_property_named_like_a_host_is_not_a_host_passes(self):
        """`rect.top` is a value, not the window, so a property name is not a host."""

        source = self._with_script_line(
            "const rectTop = (rect as DOMRect).top + (rect as DOMRect).height / 2;\nvoid rectTop;"
        )
        self.assertEqual(validate(source), [])

    def test_escaped_host_spelling_reaches_the_same_named_fails(self):
        """An identifier written with an escape is the identifier it resolves to."""

        source = self._with_script_line(
            "const host = gl\\u006FbalThis as unknown as Record<string, unknown>;\nhost.Boolean = () => false;"
        )
        self.assertTrue(any("rebinds the global" in failure for failure in validate(source)))

    def test_style_bound_as_an_object_hides_the_branch_fails(self):
        """`display: none` in a bound style object hides the alert as plainly as a literal one."""

        source = self._with_fail_closed_attribute(" :style=\"{ display: 'none' }\"")
        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_style_declaration_casing_hides_the_branch_fails(self):
        """A browser reads a style declaration whatever its casing."""

        source = self._with_fail_closed_attribute('style="Display: none"')
        self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_style_that_still_shows_the_branch_passes(self):
        """A `style` binding that hides nothing is not a hidden alert."""

        source = self._with_fail_closed_attribute(" :style=\"{ color: 'red', opacity: 1 }\"")
        self.assertEqual(validate(source), [])

    def test_literal_true_condition_is_live(self):
        """`v-if="true"` renders, so it is not one of the constants that render nothing."""

        for value in ("true", "1", "'x'", "true === true", "Boolean(true)"):
            with self.subTest(value=value):
                self.assertTrue(condition_is_live(value))
        for value in ("false", "0", "''", "!true", "1 === 2", "Boolean(false)", "null", "undefined", "NaN"):
            with self.subTest(value=value):
                self.assertFalse(condition_is_live(value))
        self.assertTrue(condition_is_live("field.visible"))
        self.assertTrue(condition_is_live("displayFields.length"))

    def test_optional_chaining_key_reaches_the_global_fails(self):
        """`value?.[key]` reads the same property as `value[key]`."""

        source = self._with_script_line(
            "const cKey = 'con' + 'structor';\n"
            "const maker = ({} as Record<string, unknown>);\n"
            "maker?.[cKey] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_later_binding_does_not_hide_the_reach_fails(self):
        """Every binding of a name counts, not the last one the text holds."""

        source = self._with_script_line(
            "let cKey = 'constructor';\n"
            "const revive = ({} as Record<string, Record<string, unknown>>)[cKey];\n"
            "void revive;\n"
            "cKey = 'unused';"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_parenthesised_key_reaches_the_global_fails(self):
        """`('Boolean')` is the string `'Boolean'`."""

        source = self._with_script_line(
            "const gk = ('Boolean');\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[gk] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_key_concatenated_across_lines_reaches_the_global_fails(self):
        """An initializer that continues onto the next line is one expression."""

        source = self._with_script_line(
            "const gk = 'Bool' +\n  'ean';\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[gk] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_appended_key_reaches_the_global_fails(self):
        """`name += 'ean'` builds a string the text does not spell out."""

        source = self._with_script_line(
            "let gk = 'Bool';\n"
            "gk += 'ean';\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[gk] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_asserted_key_reaches_the_global_fails(self):
        """A key carrying a type assertion is the same key."""

        source = self._with_script_line(
            "const gk = 'Boolean';\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[gk as keyof typeof host] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_bare_style_value_hides_the_branch_fails(self):
        """An unquoted `style` value compiles to the declaration a quoted one does."""

        for attribute in ("style=display:none", "style=visibility:hidden"):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_number_accumulator_used_as_a_key_passes(self):
        """A name a script appends numbers to is not a string key."""

        source = self._with_script_line(
            "let total = 0;\n"
            "total += 1;\n"
            "const row: Record<string, unknown> = {};\n"
            "row[total] = true;"
        )
        self.assertEqual(validate(source), [])


    def test_key_wrapped_in_parentheses_on_the_access_reaches_the_global_fails(self):
        """`value[(key)]` reads the property the key spells, parentheses and all."""

        source = self._with_script_line(
            "const gk = 'Boolean';\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[(gk)] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_type_asserted_binding_reaches_the_global_fails(self):
        """`'Boolean' as const` is the string `'Boolean'`, so the binding is a string key."""

        for initializer in ("'Boolean' as const", "('Boolean' as const)", "'Boolean' satisfies string"):
            with self.subTest(initializer=initializer):
                source = self._with_script_line(
                    f"const gk = {initializer};\n"
                    "const host = ({} as Record<string, unknown>);\n"
                    "host[gk] = () => false;"
                )
                self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_asserted_key_on_the_access_reaches_the_global_fails(self):
        """`host[key!]` and `host[key satisfies string]` are the same access as `host[key]`."""

        for key in ("gk!", "gk satisfies string", "gk as unknown as string"):
            with self.subTest(key=key):
                source = self._with_script_line(
                    "const gk = 'Boolean';\n"
                    "const host = ({} as Record<string, unknown>);\n"
                    f"host[{key}] = () => false;"
                )
                self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_logical_assignment_binding_reaches_the_global_fails(self):
        """The `||=` family builds on the value the name already held, so the string is not spelled out."""

        for assignment in ("gk ||= 'constructor';", "gk ??= 'constructor';", "gk &&= 'constructor';"):
            with self.subTest(assignment=assignment):
                source = self._with_script_line(
                    "let gk;\n"
                    f"{assignment}\n"
                    "const revive = ({} as Record<string, Record<string, unknown>>)[gk];\n"
                    "void revive;"
                )
                self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_continuation_starting_with_an_operator_reaches_the_global_fails(self):
        """An initializer that continues on a line starting with `+` is one expression."""

        source = self._with_script_line(
            "const gk = 'con'\n  + 'structor';\n"
            "const revive = ({} as Record<string, Record<string, unknown>>)[gk];\n"
            "void revive;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_destructured_binding_reaches_the_global_fails(self):
        """A name destructured out of a value that spells strings is a string key the text cannot spell."""

        source = self._with_script_line(
            "const { hk, gk } = { hk: 'defaultView', gk: 'Boolean' };\n"
            "const host = ({} as Record<string, unknown>);\n"
            "void hk;\n"
            "host[gk] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_quoted_style_property_name_hides_the_branch_fails(self):
        """A declaration names its property with quotes or as a key, and hides the branch either way."""

        for attribute in (
            " :style=\"{ 'display': 'none' }\"",
            " :style=\"{ ['display']: 'none' }\"",
            " :style='{ \"display\": \"none\" }'",
            " :style=\"{ 'opacity': 0 }\"",
        ):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_style_text_inside_another_attribute_passes(self):
        """A `style=…` inside another attribute's value is text, not a declaration on the tag."""

        for attribute in (" :title=\"'style=display:none'\"", " :aria-description=\"`style=visibility:hidden`\""):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertEqual(validate(source), [])

    def test_quoted_style_property_that_still_shows_passes(self):
        """A quoted property name that hides nothing is not a hidden alert."""

        source = self._with_fail_closed_attribute(" :style=\"{ 'color': 'red' }\"")
        self.assertEqual(validate(source), [])

    def test_asserted_key_outside_the_global_family_passes(self):
        """A non-null asserted key the script holds as a string that names nothing global is not a reach."""

        source = self._with_script_line(
            "const gk = 'labels';\n"
            "const bag: Record<string, unknown> = {};\n"
            "bag[gk!] = 1;"
        )
        self.assertEqual(validate(source), [])

    def test_destructured_name_without_a_string_passes(self):
        """A name destructured out of a value that spells no string is not a string key."""

        source = self._with_script_line(
            "const { fields } = props;\n"
            "const bag: Record<string, unknown> = {};\n"
            "bag[fields] = 1;"
        )
        self.assertEqual(validate(source), [])


    def test_declaration_words_inside_another_value_pass(self):
        """`hidden`, `v-show=` and `style=` inside another attribute's value are that value's text."""

        for attribute in (
            " :title=\"'hidden'\"",
            " title=\"hidden\"",
            " :title=\"'v-show=false'\"",
            " title=\"style=display:none\"",
        ):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertEqual(validate(source), [])

    def test_declarations_written_on_the_tag_still_hide_the_branch_fails(self):
        """The same words on the tag are declarations, so the reading is not loosened."""

        for attribute in (" hidden", ' :v-show="false"', "style=display:none", ' style="visibility:hidden"'):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))


    def test_bound_hidden_attribute_hides_the_branch_fails(self):
        """`hidden` is a boolean attribute, so a bound value that can be truthy hides the element."""

        for attribute in (' :hidden="true"', ' v-bind:hidden="true"', ' :hidden="fieldHidden"'):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_hidden_attribute_casing_hides_the_branch_fails(self):
        """A browser reads an attribute name whatever its casing."""

        for attribute in (" HIDDEN", " Hidden", ' HIDDEN="hidden"'):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_bound_hidden_attribute_that_shows_passes(self):
        """`:hidden="false"` is a bound value that renders, so it is not a hidden alert."""

        source = self._with_fail_closed_attribute(' :hidden="false"')
        self.assertEqual(validate(source), [])

    def test_renamed_destructuring_reaches_the_global_fails(self):
        """`const { k: gk } = …` binds `gk`, and that name is the key."""

        source = self._with_script_line(
            "const { k: gk } = { k: 'constructor' };\n"
            "const revive = ({} as Record<string, Record<string, unknown>>)[gk];\n"
            "void revive;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_source_key_of_a_rename_is_not_a_binding_passes(self):
        """`const { gk: other } = …` binds `other`, so `gk` is not a string key here."""

        source = self._with_script_line(
            "const { gk: other } = { gk: 'Boolean' };\n"
            "void other;\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[gk] = 1;"
        )
        self.assertEqual(validate(source), [])

    def test_destructuring_of_a_value_without_strings_passes(self):
        """A pattern whose value spells nothing binds no string."""

        source = self._with_script_line(
            "const { k: gk } = props;\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[gk] = 1;"
        )
        self.assertEqual(validate(source), [])

    def test_rest_element_is_not_a_string_binding_passes(self):
        """A rest element binds an object rather than a string."""

        source = self._with_script_line(
            "const { ...rest } = { k: 'Boolean' };\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[rest] = 1;"
        )
        self.assertEqual(validate(source), [])

    def test_key_wrapped_literal_reaches_the_global_fails(self):
        """`('con' + 'structor')` in the brackets is the same key as the unparenthesised one."""

        source = self._with_script_line(
            "const host = ({} as Record<string, unknown>);\n"
            "host[('con' + 'structor')] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_angle_asserted_key_reaches_the_global_fails(self):
        """The older `<string>key` assertion is a wrapper around the same key."""

        source = self._with_script_line(
            "const gk = 'Boolean';\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[<string>gk] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_key_built_by_an_operator_reaches_the_global_fails(self):
        """`(first ?? 'x')` reads a name the script bound to a string, brackets or not."""

        source = self._with_script_line(
            "const gk = 'Boolean';\n"
            "const host = ({} as Record<string, unknown>);\n"
            "host[(gk ?? 'x')] = () => false;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_stacked_type_assertions_reach_the_global_fails(self):
        """Assertions stack, and the name still holds the string the text spells underneath."""

        for initializer in ("'Boolean' as unknown as string", "'Boolean' as unknown as any"):
            with self.subTest(initializer=initializer):
                source = self._with_script_line(
                    f"const gk = {initializer};\n"
                    "const host = ({} as Record<string, unknown>);\n"
                    "host[gk] = () => false;"
                )
                self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))

    def test_every_key_of_an_optional_chain_is_read_fails(self):
        """`value?.[first]?.[second]` is two accesses, and the second one counts too."""

        source = self._with_script_line(
            "const fKey = 'fil' + 'ter';\n"
            "const cKey = 'con' + 'structor';\n"
            "const revive = ([] as unknown as Record<string, Record<string, unknown>>)?.[fKey]?.[cKey];\n"
            "void revive;"
        )
        self.assertTrue(any("reaches the global object" in failure for failure in validate(source)))


    def test_attribute_set_the_template_does_not_name_hides_the_branch_fails(self):
        """`v-bind` as an object or a dynamic argument can hand the element a hiding attribute."""

        for attribute in (
            ' v-bind="{ hidden: true }"',
            ' v-bind="attrs"',
            ' v-bind:[k]="true"',
            ' :[k]="true"',
            " v-bind=\"{ style: { display: 'none' } }\"",
        ):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_named_attributes_still_show_the_branch_passes(self):
        """A `v-bind` that names its argument hands the element one attribute the template names."""

        for attribute in (' v-bind:title="\'x\'"', ' :class="\'a\'"', ' :data-field-fail-closed="\'x\'"'):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertEqual(validate(source), [])


    def _with_ancestor_attribute(self, attribute):
        """Adds an attribute to the element that wraps the fail-closed branch."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                anchor = '<div class="field-control-main">'
                return value.replace(anchor, anchor[:-1] + " " + attribute + ">", 1)
            return value

        return source

    def _with_field_row_attribute(self, attribute):
        """Adds an attribute to the element that loops over the fields."""

        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    '          :key="field.key"',
                    '          :key="field.key"\n          ' + attribute,
                    1,
                )
            return value

        return source

    def test_binding_modifier_spellings_hide_the_branch_fails(self):
        """A binding modifier rides before the `=`, and the declaration still hides."""

        for attribute in (
            ' :hidden.prop="true"',
            ' :hidden.attr="true"',
            ' :hidden.camel="true"',
            ' :hidden.attr="false"',
            ' v-bind:hidden.attr="true"',
            ' v-bind.prop="{ hidden: true }"',
            " :style.prop=\"'display:none'\"",
            " :style.attr=\"'display:none'\"",
            " :style.camel=\"{ display: 'none' }\"",
            " :style.prop=\"['display:none']\"",
            " :style.attr=\"['display:none']\"",
            " :style.prop=\"{ toString() { return 'display:none' } }\"",
            " :hidden.camel=\"''\"",
            " :hidden.camel=\"`false`\"",
            " :hidden=\"`false`\"",
            " :hidden.prop=\"''\"",
            " :hidden=\"('')\"",
            " :hidden.prop=\"('')\"",
            " :hidden.camel=\"(`false`)\"",
            " :hidden=\"(`false`)\"",
        ):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_modifier_that_does_not_hide_still_shows_the_branch_passes(self):
        """`.prop` sets the DOM property, and `.prop`/`.attr` coerce an object to text."""

        for attribute in (
            ' :hidden.prop="false"',
            ' :hidden.camel="false"',
            ' :hidden.attr="null"',
            ' :hidden.attr="(null)"',
            ' :hidden.prop.attr="false"',
            ' :hidden=""',
            ' :hidden="(false)"',
            ' :hidden.prop="(false)"',
            ' :hidden="(0)"',
            " :style=\"'color: red'\"",
            " v-bind:title.prop=\"'x'\"",
        ):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertEqual(validate(source), [])

    def test_object_handed_to_a_forced_style_fails_closed(self):
        """A browser coerces the object to `[object Object]`, and that is not read here.

        The value reaches `el.style` or `setAttribute` as text, and what a given
        literal coerces to is not decided from its source, so the spelling is
        refused rather than trusted: this is an over-rejection in the fail-closed
        direction and the contract records it.
        """

        for attribute in (" :style.prop=\"{ display: 'none' }\"", " :style.attr=\"{ display: 'none' }\""):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_style_text_built_from_literals_fails_closed(self):
        """A bound value that composes its text is refused, however it builds it.

        `['display' + ':none']`, `` `display:${'none'}` ``, a `join(':')` and a
        `concat`/`replace`/`String.fromCharCode` call all reach the sheet as
        surely as the text does, and which shapes build text is read from the
        residue with the comments and the literal contents blanked rather than
        from a list of the operator spellings seen so far.  A call is read the
        same way whatever its callee is called through - `obj['join'](…)` keeps
        its `(` when the key it names is blanked, and a comment between the
        callee and the `(` does not unmake it.  A value that composes its text,
        literal or not, is an over-rejection in the fail-closed direction and
        the contract records it.

        The text is read as the two readers read it before any of that: the
        compiler decodes the character references and the escapes a literal
        holds (`'display&#58;none'`, `'display:\\tnone'`), and a CSS reader
        drops the comments, so `'display:/*x*/none'` declares what it declares,
        and `opacity` hides at every spelling of zero (`'opacity:.0'`,
        `'opacity:00'`) while `visibility` hides at `collapse` too.
        """

        for attribute in (
            " :style.prop=\"['display' + ':none']\"",
            " :style.attr=\"['display' + ':none']\"",
            " :style=\"'display' + ':none'\"",
            " :style.prop=\"`display:${'none'}`\"",
            " :style.prop=\"['display','none'].join(':')\"",
            " :style.prop=\"['visibility:hid' + 'den']\"",
            " :style.prop=\"'display'.concat(':none')\"",
            " :style.attr=\"'visibility'.concat(':hidden')\"",
            " :style.prop=\"'display:nnone'.replace('nn','n')\"",
            " :style.prop=\"String.fromCharCode(100,105,115,112,108,97,121)\"",
            " :style=\"a + b\"",
            " :style.prop=\"'display:\\u006eone'\"",
            " :style=\"['display',':none']['join']('')\"",
            " :style=\"'display'['concat'](':none')\"",
            " :style=\"String['fromCharCode'](100,105,115,112,108,97,121)\"",
            " :style=\"'display:nnone'['replace']('nn','n')\"",
            " :style=\"['display',':none']/*c*/.join/*c*/('')\"",
            " :style=\"'display'/*a*/.concat/*b*/(':none')\"",
            " :style=\"rowStyle?.()\"",
            " :style=\"'display&#58;none'\"",
            " :style=\"'display&#x3A;none'\"",
            " :style=\"'&#100;isplay:none'\"",
            " :style=\"'display&#58none'\"",
            " :style=\"'visibility&#58;hidden'\"",
            " :style=\"'opacity:.0'\"",
            " :style=\"'opacity:00'\"",
            " :style=\"'visibility:collapse'\"",
            " :style=\"'display:/*x*/none'\"",
            " :style=\"'display:\\tnone'\"",
        ):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_style_text_that_declares_nothing_still_shows_the_branch_passes(self):
        """Markup keeps its declaration as text, and a bound value that builds none shows.

        `style="width: calc(100% - 4px)"` is markup rather than an expression,
        so a call written in it is a value the tag holds; a bound value whose
        own text declares no hiding style, and a value composed without any
        literal to build from, are left alone.
        """

        for attribute in (
            " :style=\"rowStyle\"",
            " :style=\"scope.row.cssText\"",
            " :style=\"'color: red'\"",
            " :style=\"{ width: 'calc(100% - 4px)' }\"",
            ' style="width: calc(100% - 4px)"',
            ' style="background: url(a.png)"',
            " :style=\"'a`b'\"",
            " :style=\"rowStyle /* the row decides */\"",
            " :style=\"'opacity: 0.5'\"",
            " :style=\"'color: &#58;'\"",
            " :style=\"'&unknownref;'\"",
            ' :hidden.attr="\\u006eull"',
        ):
            with self.subTest(attribute=attribute):
                source = self._with_fail_closed_attribute(attribute)
                self.assertEqual(validate(source), [])

    def test_hiding_attribute_on_an_ancestor_hides_the_branch_fails(self):
        """An element enclosing the alert hides it as surely as the alert's own tag."""

        for attribute in (
            "hidden",
            ':hidden="true"',
            ':hidden.attr="false"',
            ":hidden=\"('')\"",
            ':hidden.camel="(`false`)"',
            'v-bind="{ hidden: true }"',
            ":style=\"{ display: 'none' }\"",
            'style="display:none"',
            'v-show="false"',
        ):
            with self.subTest(container="wrapper", attribute=attribute):
                source = self._with_ancestor_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))
            with self.subTest(container="field-row", attribute=attribute):
                source = self._with_field_row_attribute(attribute)
                self.assertTrue(any("no field render reaches it" in failure for failure in validate(source)))

    def test_named_attribute_on_an_ancestor_still_shows_the_branch_passes(self):
        """An ancestor whose attribute set the template names hides nothing."""

        for attribute in ('data-ancestor="row"', ":class=\"'row'\""):
            with self.subTest(attribute=attribute):
                source = self._with_ancestor_attribute(attribute)
                self.assertEqual(validate(source), [])


if __name__ == "__main__":
    unittest.main()
