import unittest
from unittest.mock import patch

from scripts.verify.frontend_product_page_header_guard import validate


class ProductPageHeaderGuardTest(unittest.TestCase):
    def test_repository_contract_passes(self):
        self.assertEqual(validate(), [])

    def test_configuration_preview_must_disable_status_writes(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ContractFormPage.vue":
                return value.replace(
                    ':status-interactive="!isConfigurationPreview && nativeStatusbar.visible && !nativeStatusbar.readonly"',
                    ':status-interactive="nativeStatusbar.visible && !nativeStatusbar.readonly"',
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("status-interactive" in item for item in validate()))

    def test_adapter_must_single_source_its_fixed_presentation_mode(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(':presentation-mode="collectionMode"', 'presentation-mode="collection"')
            return value

        with patch("pathlib.Path.read_text", altered):
            failures = validate()
        self.assertIn(
            "header adapter hardcodes presentation mode instead of the entry registry: components/design-system/ScPageHeader.vue",
            failures,
        )

        def unbound(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(":presentation-mode=\"collectionMode\"", "presentation-mode=\"collection\"").replace(
                    "const collectionMode = resolveProductPageHeaderFixedMode('design-system');", ""
                )
            return value

        with patch("pathlib.Path.read_text", unbound):
            failures = validate()
        self.assertTrue(any("single-source its fixed presentation mode" in item for item in failures), failures)

    def test_adapter_must_not_bind_presentation_mode_to_a_literal(self):
        real = Path.read_text

        def literal(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(':presentation-mode="collectionMode"', ":presentation-mode=\"'collection'\"")
            return value

        with patch("pathlib.Path.read_text", literal):
            failures = validate()
        self.assertTrue(any("binds presentation mode to a literal" in item for item in failures), failures)

    def test_adapter_must_not_forward_unregistered_axes_through_attrs(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(':presentation-mode="collectionMode"', ':presentation-mode="collectionMode" v-bind="$attrs"')
            return value

        with patch("pathlib.Path.read_text", altered):
            failures = validate()
        self.assertTrue(any("must not forward unregistered axes through $attrs" in item for item in failures), failures)

    def test_authority_must_not_forward_unregistered_axes_through_attrs(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ProductPageHeader.vue":
                return value.replace("data-product-page-header", 'data-product-page-header v-bind="$attrs"')
            return value

        with patch("pathlib.Path.read_text", altered):
            failures = validate()
        self.assertIn("ProductPageHeader must not forward unregistered axes through $attrs/useAttrs()/attrs", failures)

    def test_contract_test_must_stay_a_quick_gate_prerequisite(self):
        real = Path.read_text

        def unhooked(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return "\n".join(
                    line.replace(" verify.frontend.product_page_header.unit", "")
                    if line.startswith("verify.frontend.quick.gate:") else line
                    for line in value.splitlines()
                )
            return value

        with patch("pathlib.Path.read_text", unhooked):
            failures = validate()
        self.assertTrue(any("gate hook itself can be silently detached" in item for item in failures), failures)

    def test_authority_marker_removal_is_reported(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ProductPageHeader.vue":
                return value.replace("data-render-profile", "data-removed-render-profile")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("data-render-profile" in item for item in validate()))

    def test_registry_must_declare_axes_and_direct_consumers(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "productPageHeaderAdapters.ts":
                return value.replace("PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS", "DIRECT_CONSUMERS")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn("header entry registry does not declare axes and direct consumers", validate())

    def test_registry_must_name_every_entry_path(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "productPageHeaderAdapters.ts":
                return value.replace("'components/template/PageHeader.vue'", "'components/template/RemovedPageHeader.vue'")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn("header entry registry misses entry path: components/template/PageHeader.vue", validate())

    def test_missing_contract_test_file_is_reported(self):
        real_exists = Path.exists

        def missing(path):
            if path.name == "product_page_header_adapter_contract_test.ts":
                return False
            return real_exists(path)

        with patch("pathlib.Path.exists", missing):
            failures = validate()
        self.assertIn("header entry contract test is missing", failures)

    def test_adapter_fixed_mode_constant_must_come_from_its_own_entry(self):
        real = Path.read_text

        def drifted(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(
                    "resolveProductPageHeaderFixedMode('design-system')",
                    "resolveProductPageHeaderFixedMode('page')",
                )
            return value

        with patch("pathlib.Path.read_text", drifted):
            failures = validate()
        self.assertTrue(any("single-source its fixed presentation mode" in item for item in failures), failures)

    def test_contract_test_wiring_must_not_be_commented_out(self):
        real = Path.read_text

        def commented(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                    "\t#@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                )
            return value

        with patch("pathlib.Path.read_text", commented):
            failures = validate()
        self.assertTrue(
            any("not wired into verify.frontend.product_page_header.unit" in item for item in failures),
            failures,
        )

    def test_contract_test_wiring_target_must_not_be_duplicated(self):
        real = Path.read_text

        def duplicated(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value + "\nverify.frontend.product_page_header.unit:\n\t@echo detached\n"
            return value

        with patch("pathlib.Path.read_text", duplicated):
            failures = validate()
        self.assertTrue(
            any("must be defined exactly once" in item for item in failures),
            failures,
        )

    def test_contract_test_wiring_esbuild_line_must_be_a_real_invocation(self):
        real = Path.read_text

        def faked(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                    "\t@echo esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                )
            return value

        with patch("pathlib.Path.read_text", faked):
            failures = validate()
        self.assertTrue(
            any("esbuild bundle step missing or disabled" in item for item in failures),
            failures,
        )

    def test_contract_test_node_step_must_not_be_commented_out(self):
        real = Path.read_text

        def commented(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t#@node /tmp/product-page-header-adapter-contract-test.mjs",
                )
            return value

        with patch("pathlib.Path.read_text", commented):
            failures = validate()
        self.assertTrue(
            any("not wired into verify.frontend.product_page_header.unit" in item for item in failures),
            failures,
        )

    def test_entry_contract_test_must_stay_wired(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                    "frontend/apps/web/scripts/removed_contract_test.ts",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            failures = validate()
        self.assertTrue(any("not wired into verify.frontend.product_page_header.unit" in item for item in failures), failures)

    def test_missing_semantic_marker_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            return value.replace("data-product-page-header", "data-removed") if path.name == "ProductPageHeader.vue" else value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("data-product-page-header" in item for item in validate()))

    def test_floorplan_decision_mode_rendering_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "contractFormHeaderCanonicalActions.ts":
                return value.replace("input.floorplan?.decisionMode", "input.floorplan?.removedDecisionMode")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "canonical header action floorplan rendering misses input.floorplan?.decisionMode",
                validate(),
            )

    def test_mobile_identity_cannot_retain_desktop_flex_basis(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ProductPageHeader.vue":
                return value.replace(
                    ".product-page-header__identity{flex:0 1 auto;min-width:0}",
                    ".product-page-header__identity{min-width:0}",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "ProductPageHeader mobile identity retains a desktop flex basis",
                validate(),
            )

    def test_page_title_cannot_restore_detached_literals(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ProductPageHeader.vue":
                return value.replace(
                    "font-size:var(--sc-product-text-title); font-weight:var(--sc-pattern-page-header-title-weight)",
                    "font-size:22px; font-weight:700",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "ProductPageHeader restores detached title typography literals",
                validate(),
            )

    def test_tdesign_body_typography_bridge_is_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "theme.css" and path.parent.name == "tdesign":
                return value.replace(
                    "--td-font-size-body-medium: var(--sc-product-text-body);",
                    "--td-font-size-body-medium: 12px;",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("TDesign body-size bridge" in item for item in validate()))

    def test_native_readonly_body_typography_stays_in_shrinkable_slot(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "FormSection.vue":
                return value.replace(
                    "max-width: 100%;\n  min-width: 0;\n  font-size: var(--sc-product-text-body);",
                    "max-width: none;\n  min-width: auto;\n  font-size: 12px;",
                    1,
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("native readonly body token and shrinkable slot" in item for item in validate()))

    def test_mobile_exit_action_cannot_be_inverted(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ContractFormProductHeader.vue":
                return value.replace(
                    "...(mobileActionAuthority.value.keys.includes('back:form.back') ? [{ value: 'builtin:back', label: props.backLabel",
                    "...(props.showBack === false ? [{ value: 'builtin:back', label: props.backLabel",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "contract header mobile action settlement can hide the only exit action",
                validate(),
            )

    def test_contract_test_wiring_esbuild_cannot_be_an_echo_of_the_real_command(self):
        real = Path.read_text

        def echoed(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                    "\t@echo frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts --bundle",
                )
            return value

        with patch("pathlib.Path.read_text", echoed):
            failures = validate()
        self.assertTrue(any("esbuild bundle step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_node_cannot_be_an_echo_of_the_real_command(self):
        real = Path.read_text

        def echoed(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@echo node /tmp/product-page-header-adapter-contract-test.mjs",
                )
            return value

        with patch("pathlib.Path.read_text", echoed):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_unittest_cannot_be_an_echo_of_the_real_command(self):
        real = Path.read_text

        def echoed(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@python3 -m unittest scripts/verify/test_frontend_product_page_header_guard.py",
                    "\t@echo python3 -m unittest scripts/verify/test_frontend_product_page_header_guard.py",
                )
            return value

        with patch("pathlib.Path.read_text", echoed):
            failures = validate()
        self.assertTrue(
            any("guard unit test or guard script step missing or disabled" in item for item in failures),
            failures,
        )

    def test_contract_test_wiring_rejects_a_filename_smuggled_into_a_recipe_comment(self):
        real = Path.read_text

        def smuggled(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@node --version # product-page-header-adapter-contract-test",
                )
            return value

        with patch("pathlib.Path.read_text", smuggled):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_rejects_an_esbuild_filename_smuggled_into_a_recipe_comment(self):
        real = Path.read_text

        def smuggled(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                    "\t@true # frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts --bundle",
                )
            return value

        with patch("pathlib.Path.read_text", smuggled):
            failures = validate()
        self.assertTrue(any("esbuild bundle step missing or disabled" in item for item in failures), failures)

    def test_comment_decoy_cannot_hide_unregistered_attrs_forwarding(self):
        real = Path.read_text

        def decoy(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(
                    ':presentation-mode="collectionMode"',
                    '{{ \'/*\' }}v-bind="$attrs"{{ \'*/\' }} :presentation-mode="collectionMode"',
                )
            return value

        with patch("pathlib.Path.read_text", decoy):
            failures = validate()
        self.assertIn(
            "header adapter must not forward unregistered axes through $attrs/useAttrs()/attrs: components/design-system/ScPageHeader.vue",
            failures,
        )

    def test_comment_decoy_cannot_hide_a_hardcoded_presentation_mode(self):
        real = Path.read_text

        def decoy(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(
                    ':presentation-mode="collectionMode"',
                    '{{ \'/*\' }}presentation-mode="collection"{{ \'*/\' }}',
                )
            return value

        with patch("pathlib.Path.read_text", decoy):
            failures = validate()
        self.assertTrue(any("hardcodes presentation mode" in item for item in failures), failures)

    def test_contract_test_wiring_rejects_a_shell_chained_node_decoy(self):
        real = Path.read_text

        def chained(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@node --version; echo product-page-header-adapter-contract-test",
                )
            return value

        with patch("pathlib.Path.read_text", chained):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_rejects_a_shell_chained_unittest_decoy(self):
        real = Path.read_text

        def chained(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@python3 -m unittest scripts/verify/test_frontend_product_page_header_guard.py",
                    "\t@python3 -c 'pass'; echo unittest test_frontend_product_page_header_guard.py",
                )
            return value

        with patch("pathlib.Path.read_text", chained):
            failures = validate()
        self.assertTrue(
            any("guard unit test or guard script step missing or disabled" in item for item in failures),
            failures,
        )

    def test_use_attrs_fallback_is_rejected_in_an_adapter(self):
        real = Path.read_text

        def fallback(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(
                    ':presentation-mode="collectionMode"',
                    ':presentation-mode="collectionMode" v-bind="forwardedAttrs"',
                ).replace(
                    "import ProductPageHeader from '../product-page-header/ProductPageHeader.vue';",
                    "import ProductPageHeader from '../product-page-header/ProductPageHeader.vue';\nimport { useAttrs } from 'vue';\nconst forwardedAttrs = useAttrs();",
                )
            return value

        with patch("pathlib.Path.read_text", fallback):
            failures = validate()
        self.assertTrue(any("useAttrs()" in item for item in failures), failures)

    def test_contract_test_wiring_rejects_a_noop_flag_before_the_real_argument(self):
        real = Path.read_text

        def noop(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@node --version /tmp/product-page-header-adapter-contract-test.mjs",
                )
            return value

        with patch("pathlib.Path.read_text", noop):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_rejects_a_unittest_help_invocation(self):
        real = Path.read_text

        def help_only(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@python3 -m unittest scripts/verify/test_frontend_product_page_header_guard.py",
                    "\t@python3 -m unittest --help scripts/verify/test_frontend_product_page_header_guard.py",
                )
            return value

        with patch("pathlib.Path.read_text", help_only):
            failures = validate()
        self.assertTrue(
            any("guard unit test or guard script step missing or disabled" in item for item in failures),
            failures,
        )

    def test_contract_test_wiring_rejects_an_esbuild_version_probe(self):
        real = Path.read_text

        def probe(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                    "\t@frontend/apps/web/node_modules/.bin/esbuild --version frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                )
            return value

        with patch("pathlib.Path.read_text", probe):
            failures = validate()
        self.assertTrue(any("esbuild bundle step missing or disabled" in item for item in failures), failures)

    def test_content_heading_authority_is_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "index.ts" and path.parent.name == "router":
                return value.replace(
                    "name: 'api-key-management', component:",
                    "name: 'api-key-management', pageHeadingOwnerRemoved: true, component:",
                ).replace(
                    "meta: { layout: 'shell', pageHeadingOwner: 'content' } },\n    { path: '/a/:actionId'",
                    "meta: { layout: 'shell' } },\n    { path: '/a/:actionId'",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "page-header route does not declare content heading authority: api-key-management",
                validate(),
            )

    def test_low_code_query_cannot_override_content_heading_authority(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "AppShell.vue":
                return value.replace(
                    "const contentOwnsPageHeading",
                    "const formDesignerKeepsHeadline = BUSINESS_CONFIG_MODES.lowCode;\nconst contentOwnsPageHeading",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "AppShell must not override content heading authority for low-code form routes",
                validate(),
            )

    def test_workspace_aliases_must_share_content_heading_authority(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "index.ts" and path.parent.name == "router":
                return "\n".join(
                    line.replace(", pageHeadingOwner: 'content'", "")
                    if "name: 'scene-home'" in line else line
                    for line in value.splitlines()
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "page-header route does not declare content heading authority: scene-home",
                validate(),
            )


from pathlib import Path

if __name__ == "__main__":
    unittest.main()
