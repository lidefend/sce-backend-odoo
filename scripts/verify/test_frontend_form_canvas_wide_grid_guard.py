import contextlib
import io
from pathlib import Path
import re
import runpy
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / 'scripts/verify/frontend_form_canvas_wide_grid_guard.py'


class ReadonlyGridGuardTests(unittest.TestCase):
    def run_guard(self, mutate=lambda value: value, target='/components/template/FormSection.vue', rewriter=None):
        original = Path.read_text
        def rewrite_readonly(value):
            return re.sub(r'(?m)^\.readonly-value\s*\{([^{}]*)\}', lambda match: '.readonly-value {' + mutate(match.group(1)) + '}', value, count=1)
        rewrite = rewriter or rewrite_readonly
        def read(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if str(path).endswith(target):
                return rewrite(value)
            return value
        with patch.object(Path, 'read_text', read), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(GUARD))

    def test_current(self):
        self.run_guard()

    def test_order_and_font_are_not_layout_authority(self):
        self.run_guard(lambda body: '\n  width: 100%;' + body.replace('\n  width: 100%;', ''))

    def test_missing_width_fails(self):
        with self.assertRaisesRegex(SystemExit, 'readonly value declaration.*width'):
            self.run_guard(lambda body: body.replace('\n  width: 100%;', ''))

    def test_wrong_width_fails(self):
        with self.assertRaisesRegex(SystemExit, 'readonly value declaration.*width'):
            self.run_guard(lambda body: body.replace('\n  width: 100%;', '\n  width: 50%;'))

    def test_neighbor_declaration_cannot_supply_width(self):
        with self.assertRaisesRegex(SystemExit, 'readonly value declaration.*width'):
            self.run_guard(lambda body: body.replace('\n  width: 100%;', '') + '}\n.neighbor { width: 100%;')

    def test_declared_span_unit_is_fail_closed(self):
        with self.assertRaisesRegex(SystemExit, 'layout span unit'):
            self.run_guard(
                target='/components/template/layoutSpan.ts',
                rewriter=lambda value: value.replace('return 24;', 'return 20;', 1),
            )

    def test_renderer_must_consume_the_declared_span_module(self):
        with self.assertRaisesRegex(SystemExit, 'declared layout span unit'):
            self.run_guard(
                target='/components/template/NativeFormTreeRenderer.vue',
                rewriter=lambda value: value.replace("from './layoutSpan'", "from './layoutSpanX'", 1),
            )

    def test_low_code_width_class_is_not_a_renderer_vocabulary(self):
        with self.assertRaisesRegex(SystemExit, 're-derives a field width'):
            self.run_guard(
                rewriter=lambda value: value.replace(
                    ".field[data-field-span='8'] {",
                    ".field--compact {\n  grid-column: span 8;\n}\n\n.field[data-field-span='8'] {",
                    1,
                ),
            )

    def test_medium_band_attribute_must_match_the_binding(self):
        with self.assertRaisesRegex(SystemExit, 'responsive field grid contract'):
            self.run_guard(
                rewriter=lambda value: value.replace("data-field-band='full'", "data-span-band='full'", 1),
            )

    def test_schema_builder_must_carry_the_declared_span(self):
        with self.assertRaisesRegex(SystemExit, 'declared span'):
            self.run_guard(
                target='/pages/contractForm/useRecordFormFieldSchemas.ts',
                rewriter=lambda value: value.replace('resolveSpan:(field)=>(field as LayoutNode).span', 'resolveSpan:(_field)=>12', 1),
            )

    def test_declared_facets_must_have_one_authority(self):
        target = '/addons/smart_core/handlers/ui_contract_v2_projection.py'
        for rewrite in (
            lambda value: value.replace('"field--compact": 8', '"field--compact": 9', 1),
            lambda value: value.replace('"field--half": 12,', '', 1),
        ):
            with self.assertRaisesRegex(SystemExit, 'declared layout facets resolve by two authorities'):
                self.run_guard(target=target, rewriter=rewrite)

    def test_renderer_facet_table_must_mirror_the_projection(self):
        target = '/pages/contractForm/fieldUtils.ts'
        for rewrite in (
            lambda value: value.replace("['compact', 8]", "['compact', 9]", 1),
            lambda value: value.replace("    ['wide', 16],\n", "", 1),
            lambda value: value.replace('function declaredFieldSizeSpans(): Map<string, number> {', 'function renamedFacetSpans(): Map<string, number> {', 1),
        ):
            with self.assertRaisesRegex(SystemExit, 'declared layout facets resolve by two authorities'):
                self.run_guard(target=target, rewriter=rewrite)
