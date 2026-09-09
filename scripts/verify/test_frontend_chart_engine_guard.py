from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify.frontend_chart_engine_guard import validate


class FrontendChartEngineGuardTest(unittest.TestCase):
    def make_root(self, source: str) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        package = root / "frontend/apps/web/package.json"
        package.parent.mkdir(parents=True)
        package.write_text(json.dumps({"dependencies": {"echarts": "6.1.0"}}), encoding="utf-8")
        installed = root / "frontend/node_modules/.pnpm/echarts@6.1.0/node_modules/echarts/package.json"
        installed.parent.mkdir(parents=True)
        installed.write_text(json.dumps({"exports": {"./core": "./core.js", "./charts": "./charts.js", "./components": "./components.js", "./renderers": "./renderers.js", "./features": "./features.js"}}), encoding="utf-8")
        component = root / "frontend/apps/web/src/Chart.vue"
        component.parent.mkdir(parents=True)
        component.write_text(source, encoding="utf-8")
        return root

    def test_dynamic_official_subpaths_with_canvas_renderer_pass(self) -> None:
        root = self.make_root("const modules = Promise.all([import('echarts/core'), import('echarts/charts'), import('echarts/components'), import('echarts/renderers')]); renderers.CanvasRenderer;")
        self.assertEqual(validate(root), [])

    def test_full_bundle_import_fails(self) -> None:
        self.assertTrue(any("full echarts import" in failure for failure in validate(self.make_root("import('echarts')"))))

    def test_unapproved_subpath_fails(self) -> None:
        self.assertTrue(any("not an approved public entrypoint" in failure for failure in validate(self.make_root("import('echarts/lib/echarts')"))))

    def test_svg_renderer_fails_for_dynamic_import_too(self) -> None:
        root = self.make_root("import('echarts/renderers'); renderers.CanvasRenderer; renderers.SVGRenderer;")
        self.assertTrue(any("SVGRenderer" in failure for failure in validate(root)))


if __name__ == "__main__":
    unittest.main()
