import unittest

from scripts.verify.frontend_professional_component_registry_guard import ROOT, validate


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


if __name__ == "__main__":
    unittest.main()
