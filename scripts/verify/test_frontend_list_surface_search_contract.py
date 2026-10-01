"""Contract lock for the released list-surface search probe.

The list-surface structure probe must drive the controls the product declares
(``toolbar-search-submit`` inside the declared ``collection-search-control`` and
the declared ``ScEmptyState`` empty contract) instead of reproducing interactions
that the primitive consumes. This test fails when either side drops a declared
hook, so the probe converges instead of accumulating per-symptom selector patches.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / 'scripts/verify/frontend_list_surface_structure_browser.mjs'
TOOLBAR = ROOT / 'frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue'
EMPTY_STATE = ROOT / 'frontend/apps/web/src/components/design-system/ScEmptyState.vue'
HEADER = ROOT / 'frontend/apps/web/src/components/product-list/ProductListHeader.vue'
LIST_PAGE = ROOT / 'frontend/apps/web/src/pages/ListPage.vue'

EMPTY_CONTRACT = '[data-semantic-component="ScEmptyState"][data-state="empty"]'
CONTENT_CONTRACT = '[data-collection-presentation="table"]'


def validate_search_probe(probe, toolbar, empty_state, header, list_page):
    """Reject a probe that assumes interactions or product hooks that are not declared."""
    assert "press('Enter')" not in probe, 'the list search must submit through the declared control'
    assert 't-input__inner' not in probe, 'the probe must not bind to primitive internals'
    assert 'sc-table-shell' not in probe, 'the probe must not bind to a stylesheet-only class'
    assert 'toolbar-search-submit' in probe, 'the declared collection search submit control is required'
    assert 'collection-search-control' in probe, 'the declared collection search control is required'
    assert 'product-list-header__search button[type="submit"]' in probe, 'the declared header search submit control is required'
    assert "closest('.collection-search-control, .product-list-header__search')" in probe, 'the declared search control box is the usability measurement'
    assert EMPTY_CONTRACT in probe, 'the probe must wait on the declared empty contract'
    assert CONTENT_CONTRACT in probe, 'the probe must resolve the first business content by its declared presentation contract'
    assert 'toolbar-search-submit' in toolbar, 'ActionSurfaceToolbar must declare the collection search submit control'
    assert 'collection-search-control' in toolbar, 'ActionSurfaceToolbar must declare the collection search control'
    assert 'product-list-header__search' in header, 'ProductListHeader must declare the fallback search form'
    assert 'type="submit"' in header, 'ProductListHeader must declare the fallback search submit control'
    assert 'data-semantic-component="ScEmptyState"' in empty_state, 'ScEmptyState must declare its semantic component'
    assert 'data-state="empty"' in empty_state, 'ScEmptyState must declare the empty state contract'
    assert 'data-collection-presentation="table"' in list_page, 'ListPage must declare the table presentation contract'


class ListSurfaceSearchContractTest(unittest.TestCase):
    def setUp(self):
        self.probe = PROBE.read_text()
        self.toolbar = TOOLBAR.read_text()
        self.empty_state = EMPTY_STATE.read_text()
        self.header = HEADER.read_text()
        self.list_page = LIST_PAGE.read_text()
        self.declared = (self.probe, self.toolbar, self.empty_state, self.header, self.list_page)

    def test_released_probe_declares_the_contract(self):
        self.assertIsNone(validate_search_probe(*self.declared))

    def test_key_press_submission_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(*(self.probe + "\nawait input.press('Enter');\n", *self.declared[1:]))

    def test_primitive_internal_binding_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(*(self.probe + "\nconst x = '.t-input__inner';\n", *self.declared[1:]))

    def test_missing_declared_submit_control_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(*(self.probe.replace('toolbar-search-submit', 'toolbar-search'), *self.declared[1:]))

    def test_missing_declared_empty_contract_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(self.probe, self.toolbar, self.empty_state.replace('data-state="empty"', ''), self.header, self.list_page)

    def test_product_dropping_the_submit_hook_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(self.probe, self.toolbar.replace('toolbar-search-submit', 'toolbar-search'), self.empty_state, self.header, self.list_page)

    def test_stylesheet_only_content_class_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(*(self.probe.replace(CONTENT_CONTRACT, '.table > .sc-table-shell'), *self.declared[1:]))

    def test_raw_primitive_box_measurement_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(*(self.probe.replace("closest('.collection-search-control, .product-list-header__search')", ''), *self.declared[1:]))

    def test_product_dropping_the_presentation_contract_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_search_probe(self.probe, self.toolbar, self.empty_state, self.header, self.list_page.replace('data-collection-presentation="table"', ''))


if __name__ == '__main__':
    unittest.main()
