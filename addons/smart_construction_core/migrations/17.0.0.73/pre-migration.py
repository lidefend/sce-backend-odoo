"""Preserve the product-owned AR/AP projection table during RC6.1 upgrade."""

import importlib.util
from pathlib import Path


def _load_lifecycle_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "models"
        / "projection_relation_lifecycle.py"
    )
    spec = importlib.util.spec_from_file_location(
        "smart_construction_core_projection_relation_lifecycle", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def migrate(cr, installed_version):
    del installed_version
    lifecycle = _load_lifecycle_module()
    lifecycle.ensure_ar_ap_project_summary_provider(cr)
