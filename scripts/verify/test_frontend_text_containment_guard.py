from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify import frontend_text_containment_guard as guard


class FrontendTextContainmentGuardTest(unittest.TestCase):
    def make_root(
        self,
        *,
        important: bool = False,
        governed_important: bool = False,
        bad_fallback: bool = False,
        wrong_clamp: bool = False,
    ) -> Path:
        root = Path(tempfile.mkdtemp())
        web = root / "frontend/apps/web/src"
        files = {
            "frontend/apps/web/src/components/Structural.css": ".chip{white-space: nowrap;text-overflow: ellipsis}",
            "frontend/apps/web/src/components/Info.css": ".value{white-space: nowrap;text-overflow: ellipsis}",
            "frontend/apps/web/src/components/Info.vue": '<template><span title="full">{{ }}</span></template>',
            guard.MY_WORK: ".work-card h3{-webkit-line-clamp: 2;}.work-card h3{-webkit-line-clamp: 4;}",
        }
        if important:
            files["frontend/apps/web/src/components/Structural.css"] += ".bad{color:red !important}"
        if governed_important:
            files["frontend/apps/web/src/styles/accessibility.css"] = (
                "@media (prefers-reduced-motion: reduce) {"
                "*{animation-duration:0.01ms !important;animation-iteration-count:1 !important;"
                "transition-duration:0.01ms !important;scroll-behavior:auto !important;}"
            )
        if wrong_clamp:
            files[guard.MY_WORK] = ".work-card h3{-webkit-line-clamp: 2;}"
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        allowlist = root / "docs/architecture/text_containment_allowlist.json"
        allowlist.parent.mkdir(parents=True)
        owner = "frontend/apps/web/src/components/Missing.vue" if bad_fallback else "frontend/apps/web/src/components/Info.vue"
        policy = {
            "importantOverrides": [{
                "file": "frontend/apps/web/src/styles/accessibility.css",
                "max": 4,
                "reason": "governed reduced-motion floor",
            }],
            "structuralOverlapExceptions": [{
                "file": "frontend/apps/web/src/components/Structural.css",
                "reason": "structural",
            }],
            "informationOverlapFiles": [{
                "styleLocation": "frontend/apps/web/src/components/Info.css",
                "fallbackOwner": owner,
                "fallback": "title",
            }],
            "policy": {
                "businessTitleMaxLines": 2,
                "recordIdentityTemporaryMaxLines": 4,
            },
        }
        allowlist.write_text(json.dumps(policy), encoding="utf-8")
        return root

    def test_registered_overlap_and_zero_important_pass(self) -> None:
        result = guard.inspect(self.make_root())
        self.assertEqual(result["errors"], [])

    def test_important_fails(self) -> None:
        errors = guard.inspect(self.make_root(important=True))["errors"]
        self.assertTrue(any("!important" in error for error in errors))

    def test_governed_reduced_motion_important_passes(self) -> None:
        result = guard.inspect(self.make_root(governed_important=True))
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["important"], 4)

    def test_missing_fallback_owner_fails(self) -> None:
        errors = guard.inspect(self.make_root(bad_fallback=True))["errors"]
        self.assertTrue(any("fallback owner is missing" in error for error in errors))

    def test_clamp_policy_drift_fails(self) -> None:
        errors = guard.inspect(self.make_root(wrong_clamp=True))["errors"]
        self.assertTrue(any("temporary record identity clamp" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
