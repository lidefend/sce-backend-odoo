# -*- coding: utf-8 -*-
"""Authoritative mapping from registered native tree classes to semantics."""

NATIVE_COLLECTION_PRESENTATION_SEMANTICS = {
    "smart_hierarchy_browser": "hierarchy_browser",
    "smart_hierarchy_planner": "hierarchy_planner",
    "smart_hierarchical_worksheet": "hierarchical_worksheet",
}


def native_collection_presentation(js_class):
    semantic = NATIVE_COLLECTION_PRESENTATION_SEMANTICS.get(
        str(js_class or "").strip()
    )
    if not semantic:
        return None
    return {
        "semantic": semantic,
        "source": "native_view_derived",
    }
