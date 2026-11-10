from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify import frontend_rich_text_guard as guard


class FrontendRichTextGuardTest(unittest.TestCase):
    OWNER = (
        '<template><div v-html="html" data-semantic-component="ScRichText" '
        ':data-policy="policy" /></template>\n'
        "import { sanitizeReadonlyHtml } from './a'; "
        "import { sanitizeRestrictedHtml } from './b';\n"
    )

    def make_root(self, files: dict[str, str]) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "frontend/apps/web/src").mkdir(parents=True)
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def baseline_files(self) -> dict[str, str]:
        files = {guard.OWNER: self.OWNER}
        for relative, count in guard.CONSUMERS.items():
            files[relative] = "<template>" + "<ScRichText />" * count + "</template>"
        return files

    def test_current_contract_shape_passes(self) -> None:
        self.assertEqual(guard.inspect(self.make_root(self.baseline_files()))["errors"], [])

    def test_naked_v_html_fails(self) -> None:
        files = self.baseline_files()
        files["frontend/apps/web/src/Naked.vue"] = '<template><div v-html="html" /></template>'
        errors = guard.inspect(self.make_root(files))["errors"]
        self.assertTrue(any("naked v-html outside ScRichText" in error for error in errors))

    def test_external_html_v_html_is_detected(self) -> None:
        files = self.baseline_files()
        files["frontend/apps/web/src/template.html"] = '<div v-html="html"></div>'
        errors = guard.inspect(self.make_root(files))["errors"]
        self.assertTrue(any("naked v-html outside ScRichText" in error for error in errors))

    def test_missing_policy_branch_fails(self) -> None:
        files = self.baseline_files()
        files[guard.OWNER] = self.OWNER.replace("sanitizeRestrictedHtml", "unusedSanitizer")
        errors = guard.inspect(self.make_root(files))["errors"]
        self.assertTrue(any("sanitizer contract" in error for error in errors))

    def test_consumer_count_drift_fails(self) -> None:
        files = self.baseline_files()
        relative = next(iter(guard.CONSUMERS))
        files[relative] = "<template></template>"
        errors = guard.inspect(self.make_root(files))["errors"]
        self.assertTrue(any("consumer count mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
