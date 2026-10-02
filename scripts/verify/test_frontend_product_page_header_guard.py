import unittest
from unittest.mock import patch

from scripts.verify.frontend_product_page_header_guard import _strip_comments, validate


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

    def test_action_semantic_normalization_is_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "contractFormHeaderCanonicalActions.ts":
                return value.replace("normalizeActionSemantics", "removedSemanticNormalization")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "canonical header action floorplan rendering misses normalizeActionSemantics",
                validate(),
            )

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
                    "font: var(--sc-font-body-medium);\n  box-sizing: border-box;\n  display: grid;\n  align-items: center;\n  width: 100%;\n  max-width: 100%;\n  min-width: 0;",
                    "font-size: 12px;\n  max-width: none;\n  min-width: auto;",
                    1,
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("native readonly body font token and shrinkable slot" in item for item in validate()))

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

    def test_contract_test_wiring_rejects_a_failure_swallowing_suffix(self):
        """`<step> || true` 会让步骤**执行但失败不再传播**——必须与伪命令同等对待。"""
        real = Path.read_text

        def swallowed(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs || true",
                )
            return value

        with patch("pathlib.Path.read_text", swallowed):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_rejects_a_short_circuited_step(self):
        """`false && <step>` 让步骤**永不执行**，却仍让首 token 与参数同时在场。"""
        real = Path.read_text

        def short_circuited(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@false && node /tmp/product-page-header-adapter-contract-test.mjs",
                )
            return value

        with patch("pathlib.Path.read_text", short_circuited):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_accepts_a_plain_redirection(self):
        """`2>&1`／`>/dev/null` 是重定向而不是链式分隔符：不得因此假失败。"""
        real = Path.read_text

        def redirected(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs 2>&1",
                )
            return value

        with patch("pathlib.Path.read_text", redirected):
            self.assertEqual(validate(), [])

    def test_contract_test_wiring_rejects_a_redirect_tight_against_the_separator(self):
        """`>/dev/null|| true` 把分隔符**紧贴**在重定向后：剥离重定向时吞掉分隔符会让失败不再传播。"""
        real = Path.read_text
        for suffix, note in (
            (" >/dev/null|| true", "no-space ||"),
            (" 2>/dev/null; echo ok", "no-space ;"),
            (" >/dev/null&&false", "no-space &&"),
            (" >/dev/null|true", "no-space |"),
        ):
            def squeezed(path, *args, **kwargs):
                value = real(path, *args, **kwargs)
                if path.name == "frontend.mk":
                    return value.replace(
                        "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                        "\t@node /tmp/product-page-header-adapter-contract-test.mjs" + suffix,
                    )
                return value

            with patch("pathlib.Path.read_text", squeezed):
                failures = validate()
            self.assertTrue(
                any("node execution step missing or disabled" in item for item in failures),
                f"{note}: {failures}",
            )

    def test_contract_test_wiring_rejects_a_backgrounded_step(self):
        """`<step> &` 后台化后 shell 立刻以 0 退出：步骤的失败不再传播，必须与 `|| true` 同等对待。"""
        real = Path.read_text

        def backgrounded(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs &",
                )
            return value

        with patch("pathlib.Path.read_text", backgrounded):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_contract_test_wiring_rejects_a_continued_line_suffix(self):
        """Make 会把以 `\\` 结尾的行与下一行拼成同一条 shell 命令：续行修饰不得对门禁不可见。"""
        real = Path.read_text

        def continued(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs \\\n\t\t|| true",
                )
            return value

        with patch("pathlib.Path.read_text", continued):
            failures = validate()
        self.assertTrue(any("node execution step missing or disabled" in item for item in failures), failures)

    def test_gate_hook_cannot_be_hidden_in_a_trailing_comment(self):
        """把 unit 目标从真实前置里删掉、只留在行尾 `#` 注释中：子串判定会 PASS，token 判定必须失败。"""
        real = Path.read_text

        def commented(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "verify.frontend.quick.gate: verify.frontend.official_icon.unit",
                    "verify.frontend.quick.gate: verify.frontend.official_icon.unit # was verify.frontend.product_page_header.unit",
                ).replace(
                    " verify.frontend.navigation_shell.unit verify.frontend.product_page_header.unit",
                    " verify.frontend.navigation_shell.unit",
                )
            return value

        with patch("pathlib.Path.read_text", commented):
            failures = validate()
        self.assertTrue(
            any("gate hook itself can be silently detached" in item for item in failures),
            failures,
        )

    def test_attrs_bound_through_a_v_bind_modifier_is_rejected(self):
        """`v-bind.prop=`／`v-bind.camel=`／`v-bind.attr=` 与 `v-bind=` 是同一个整对象展开通道。"""
        real = Path.read_text
        for modifier in (".prop", ".camel", ".attr"):
            def bound(path, *args, **kwargs):
                value = real(path, *args, **kwargs)
                if path.name == "ScPageHeader.vue":
                    return value.replace(
                        ':presentation-mode="collectionMode"',
                        f':presentation-mode="collectionMode" v-bind{modifier}="attrs"',
                    )
                return value

            with patch("pathlib.Path.read_text", bound):
                failures = validate()
            self.assertTrue(any("useAttrs()" in item for item in failures), f"{modifier}: {failures}")

    def test_rcdata_element_content_is_not_a_comment(self):
        """`textarea`／`title` 是 RCDATA：其中的 `<!--` 是文本，不得把其后真实模板吞成注释。"""
        text = '<textarea><!--</textarea>\n<ProductPageHeader v-bind="attrs" />'
        self.assertIn('v-bind="attrs"', _strip_comments(text))

    def test_attrs_bound_through_a_plain_identifier_is_rejected(self):
        """`const attrs = useAttrs()` 之外，`v-bind="attrs"` 本身也是兜底转发通道。"""
        real = Path.read_text

        def bound(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(
                    ':presentation-mode="collectionMode"',
                    ':presentation-mode="collectionMode" v-bind="attrs"',
                )
            return value

        with patch("pathlib.Path.read_text", bound):
            failures = validate()
        self.assertTrue(
            any("useAttrs()" in item for item in failures),
            failures,
        )

    def test_a_plain_string_mentioning_attrs_is_not_a_fallback(self):
        """合法文案（`'no attrs here'`）不得被误判成兜底转发。"""
        real = Path.read_text

        def commented(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ScPageHeader.vue":
                return value.replace(
                    "const collectionMode = resolveProductPageHeaderFixedMode('design-system');",
                    "const collectionMode = resolveProductPageHeaderFixedMode('design-system');\n"
                    "const _note = 'no attrs here';",
                )
            return value

        with patch("pathlib.Path.read_text", commented):
            self.assertEqual(validate(), [])

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

    def test_make_ignore_error_prefix_on_a_guarded_step_is_rejected(self):
        """`@-esbuild …`／`-@node …`：shell 形状完全正常，但 Make 会忽略该步骤的失败。"""
        real = Path.read_text

        def prefixed(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                    "\t@-frontend/apps/web/node_modules/.bin/esbuild frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                ).replace(
                    "\t@node /tmp/product-page-header-adapter-contract-test.mjs",
                    "\t-@node /tmp/product-page-header-adapter-contract-test.mjs",
                )
            return value

        with patch("pathlib.Path.read_text", prefixed):
            failures = validate()
        self.assertTrue(
            any("ignore-error prefix" in item for item in failures),
            failures,
        )

    def test_make_ignore_special_target_is_rejected(self):
        """`.IGNORE:` 让全部 recipe 的失败不再让 make 失败，且不改任何 recipe 行。"""
        real = Path.read_text

        def ignored(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value + "\n.IGNORE:\n"
            return value

        with patch("pathlib.Path.read_text", ignored):
            failures = validate()
        self.assertTrue(
            any(".IGNORE special target" in item for item in failures),
            failures,
        )

    def test_makeflags_ignore_errors_is_rejected(self):
        """`MAKEFLAGS += -i` 等价于给整棵 make 加 `-i`，同样不改 recipe 行。"""
        real = Path.read_text

        def flag(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value + "\nMAKEFLAGS += -i\n"
            return value

        with patch("pathlib.Path.read_text", flag):
            failures = validate()
        self.assertTrue(
            any("sets MAKEFLAGS -i" in item for item in failures),
            failures,
        )

    def test_included_makefile_must_not_redefine_the_wired_target(self):
        """Make 取同一目标的**最后一份** recipe：在 `include` 的片段里重定义可整条替换被测 recipe。"""
        real = Path.read_text

        def overriding(path, *args, **kwargs):
            if path.name == "frontend_override.mk":
                return "verify.frontend.product_page_header.unit:\n\t@echo overridden\n"
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value + "\ninclude make/frontend_override.mk\n"
            return value

        with patch("pathlib.Path.read_text", overriding):
            failures = validate()
        self.assertTrue(
            any("must be defined exactly once" in item for item in failures),
            failures,
        )

    def _with_fragment_include(self, include_stmt, fragment_body, mutate=None):
        """在 `make/frontend.mk` 末尾 include 一个片段（片段内容由参数给出），返回 `validate()` 的失败列表。"""
        real = Path.read_text

        def altered(path, *args, **kwargs):
            if path.name == "_inj_frag.mk":
                return fragment_body
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                if mutate is not None:
                    value = mutate(value)
                return value + "\n" + include_stmt + "\n"
            return value

        with patch("pathlib.Path.read_text", altered):
            return validate()

    def test_sinclude_must_not_hide_a_redefinition(self):
        """`sinclude` 是 GNU `-include` 的正式同义词，同样是**静态可解析**的 include 拼写。"""
        failures = self._with_fragment_include(
            "sinclude make/_inj_frag.mk",
            "verify.frontend.product_page_header.unit:\n\t@echo overridden\n",
        )
        self.assertTrue(any("must be defined exactly once" in item for item in failures), failures)

    def test_continued_include_line_must_not_hide_a_redefinition(self):
        """`include \\` ＋换行是 Make 的续行：只按物理行匹配就会漏掉整条 include。"""
        failures = self._with_fragment_include(
            "include \\\nmake/_inj_frag.mk",
            "verify.frontend.product_page_header.unit:\n\t@echo overridden\n",
        )
        self.assertTrue(any("must be defined exactly once" in item for item in failures), failures)

    def test_quoted_include_path_must_not_hide_a_redefinition(self):
        failures = self._with_fragment_include(
            'include "make/_inj_frag.mk"',
            "verify.frontend.product_page_header.unit:\n\t@echo overridden\n",
        )
        self.assertTrue(any("must be defined exactly once" in item for item in failures), failures)

    def test_variable_target_name_must_not_shadow_the_guarded_target(self):
        """`$(VAR):` 目标名静态不可知，按失败关闭方向处理（要求显式登记）。"""
        failures = self._with_fragment_include(
            "include make/_inj_frag.mk",
            "_HT := verify.frontend.product_page_header.unit\n$(_HT):\n\t@echo overridden\n",
        )
        self.assertTrue(any("non-literal target" in item for item in failures), failures)

    def test_redefined_shell_must_be_rejected(self):
        """片段把 `SHELL` 指到恒返回 0 的程序：recipe 一字未改，失败却不再传播。"""
        failures = self._with_fragment_include("include make/_inj_frag.mk", "SHELL := /bin/true\n")
        self.assertTrue(any("SHELL is redefined" in item for item in failures), failures)

    def test_oneshell_must_be_rejected(self):
        """`.ONESHELL:` 让整条 recipe 共用一个 shell、只看最后一行的状态。"""
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "\t@python3 scripts/verify/frontend_product_page_header_guard.py",
                    "\t@python3 scripts/verify/frontend_product_page_header_guard.py\n\t@true",
                ) + "\n.ONESHELL:\n"
            return value

        with patch("pathlib.Path.read_text", altered):
            failures = validate()
        self.assertTrue(any(".ONESHELL" in item for item in failures), failures)

    def test_prefixed_makeflags_forms_must_be_rejected(self):
        """`override`／`export` 前缀与续行都不改变 `MAKEFLAGS += -i` 的语义。"""
        real = Path.read_text

        def flag(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value + "\noverride MAKEFLAGS += -i\nexport MAKEFLAGS := -i\nMAKEFLAGS += \\\n-i\n"
            return value

        with patch("pathlib.Path.read_text", flag):
            failures = validate()
        self.assertGreaterEqual(
            sum(1 for item in failures if "sets MAKEFLAGS" in item),
            3,
            failures,
        )

    def test_harmless_included_fragment_is_still_legal(self):
        """反向锁定：`sinclude` 一个只声明无关变量的片段不得假失败。"""
        self.assertEqual(self._with_fragment_include("sinclude make/_inj_frag.mk", "OTHER_AXIS := 1\n"), [])


    def test_eval_wrapped_directives_must_be_rejected(self):
        """`$(eval SHELL := …)` / `$(eval MAKEFLAGS += -i)`：行首匹配看不见被包裹的指令内容。"""
        for body in ("$(eval SHELL := /bin/true)\n", "$(eval MAKEFLAGS += -i)\n", "$(eval .ONESHELL:)\n"):
            failures = self._with_fragment_include("include make/_inj_frag.mk", body)
            self.assertTrue(
                any("$(eval" in item for item in failures),
                (body, failures),
            )

    def test_define_wrapped_directives_must_be_rejected(self):
        """`define SHELL … endef`：多行体的值静态不可枚举，按失败关闭处理。"""
        failures = self._with_fragment_include(
            "include make/_inj_frag.mk", "define SHELL\n/bin/true\nendef\n"
        )
        self.assertTrue(any("define/endef" in item for item in failures), failures)

    def test_variable_carried_makeflags_must_be_rejected(self):
        """`IGN := -i` ＋ `MAKEFLAGS += $(IGN)`：直接赋值形态匹配不到，但展开结果才是真相。"""
        failures = self._with_fragment_include(
            "include make/_inj_frag.mk", "IGN := -i\nMAKEFLAGS += $(IGN)\n"
        )
        self.assertTrue(any("through a variable" in item for item in failures), failures)

    def test_variable_carried_shell_must_be_rejected(self):
        failures = self._with_fragment_include(
            "include make/_inj_frag.mk", "MY_SHELL := /bin/true\nSHELL := $(MY_SHELL)\n"
        )
        self.assertTrue(any("through a variable" in item for item in failures), failures)

    def test_recipe_line_environment_assignment_is_not_a_make_directive(self):
        """反向锁定：`\tSHELL=/bin/bash cmd` 只是给一条命令设环境变量，不得当作 make 级重定义。"""
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value + "\n_tmp.recipe.probe:\n\tSHELL=/bin/bash run-other\n"
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertEqual(validate(), [])

    def test_posix_and_export_shell_without_assignment_are_legal(self):
        """反向锁定：`.POSIX:` 与 `export SHELL`（无赋值）不是失败传播通道。"""
        failures = self._with_fragment_include("include make/_inj_frag.mk", ".POSIX:\nexport SHELL\n")
        self.assertEqual(failures, [])


from pathlib import Path

if __name__ == "__main__":
    unittest.main()
