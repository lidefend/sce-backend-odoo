"""Contract lock for the released list-surface search probe.

The list-surface structure probe must drive the controls the product declares
(``toolbar-search-submit`` inside the declared ``collection-search-control`` and
the declared ``ScEmptyState`` empty contract) instead of reproducing interactions
that the primitive consumes. This test fails when either side drops a declared
hook, so the probe converges instead of accumulating per-symptom selector patches.
"""
from pathlib import Path
import unittest
import subprocess


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

    def test_daily_read_boundary_executes_real_predicate(self):
        source = self.probe.split('function dailyReadonlyRequest(')[1].split('let browser,')[0]
        program = """const assert = require('node:assert/strict');
const build = require('./frontend/apps/web/node_modules/esbuild').buildSync;
const code = build({stdin:{contents:"export * from './app/runtime/recordEntryContract'; export * from './app/routeQuery'; export * from './app/resolvers/sceneRegistry';",resolveDir:process.cwd()+'/frontend/apps/web/src',loader:'ts'},bundle:true,platform:'node',format:'cjs',define:{'import.meta.env.DEV':'false'},write:false}).outputFiles[0].text;
const mod={exports:{}};new Function('module','exports','require',code)(mod,mod.exports,require);const dailyRuntime=mod.exports;
function dailyReadonlyRequest(""" + source + "\n"
        program += """
for (const intent of ['login','system.init','ui.contract','ui.contract.v2','load_contract','route.authority.validate','my.work.summary','chatter.timeline','chatter.followers.list']) assert(dailyReadonlyRequest('POST','/api/v1/intent',{intent}));
for (const op of ['list','read','search_read','default_get']) assert(dailyReadonlyRequest('POST','/api/v1/intent',{intent:'api.data',params:{op}}));
for (const op of ['create','write','unlink']) assert(!dailyReadonlyRequest('POST','/api/v1/intent',{intent:'api.data',params:{op}}));
for (const intent of ['execute_button','file.upload','chatter.post','search.favorite.set','unknown']) assert(!dailyReadonlyRequest('POST','/api/v1/intent',{intent}));
assert(!dailyReadonlyRequest('POST','/api/v1/intent',{intent:'api.data',params:{op:'list',payload:{op:'write'}}}));
assert(!dailyReadonlyRequest('POST','/api/v1/intent',{intent:'api.data',op:'unlink',params:{op:'read'}}));
assert(dailyReadonlyRequest('POST','/api/v1/intent',{intent:'api.data',params:{op:'read',context:{lang:'zh_CN'}}}));
assert(!dailyReadonlyRequest('POST','/web/dataset/call_kw',{}));
assert(!dailyReadonlyRequest('DELETE','/api/v1/intent',{}));
const declared = {scene_ready_contract:{scenes:[{scene:{key:'projects.list',title:'Projects'},page:{route:'/s/projects.list'}}]},role_surface:{landing_path:'/s/projects.list',landing_scene_key:'projects.list'},default_route:{route:'/',scene_key:'workspace.home'}};
assert.equal(dailyDeclaredLanding(declared).route,'/s/projects.list');
assert(!dailyLandingMatches('https://daily.test/',dailyDeclaredLanding(declared),'https://daily.test'));
assert(dailyLandingMatches('https://daily.test/s/projects.list',dailyDeclaredLanding(declared),'https://daily.test'));
assert.equal(dailyDeclaredLanding({role_surface:{landing_scene_key:'workspace.home'}}).route,'/');
assert.equal(dailyDeclaredLanding({default_route:declared.default_route}).route,'/');
assert(dailyLandingMatches('https://daily.test/s/projects.list?menu_id=291',{route:'/s/projects.list?menu_id=291',scene_key:'projects.list'},'https://daily.test'));
assert(!dailyLandingMatches('https://daily.test/',{route:'/s/projects.list'},'https://daily.test'));
assert(!dailyLandingMatches('https://daily.test/',null,'https://daily.test'));
assert(!dailyLandingMatches('https://other.test/s/projects.list',{route:'/s/projects.list'},'https://daily.test'));
assert.equal(dailyDeclaredLanding({role_surface:{landing_path:'/s/unpublished'},default_route:{route:'/'}}).route,'/');
assert.equal(dailyDeclaredLanding({default_route:{route:'/a/99'}}).route,'/');
assert.equal(dailyDeclaredLanding({role_surface:{landing_path:'/workbench'}}).route,'/');
const list = {pageInfo:{model:'payment.request'},actionContract:{actionRuleList:[{sourceWidgetId:'page.row',target:{view_type:'form'}}]},statusContract:{globalStatus:{modelRights:{write:true}}}};
const sourceEntry = {actionId:8,menuId:9};
assert.equal(dailyRecordEntry(list,{id:4},sourceEntry).path,'/f/payment.request/4');
list.statusContract.globalStatus.modelRights.write=false;
assert.equal(dailyRecordEntry(list,{id:4},sourceEntry).path,'/r/payment.request/4');
list.actionContract.actionRuleList[0].target={record_entry:{model:'payment.request',record_id:'${id}',entry_intent:'explicit_readonly',model_write_authority:true}};
assert.equal(dailyRecordEntry(list,{id:4},sourceEntry).path,'/r/payment.request/4');
assert.throws(()=>dailyRecordEntry({...list,actionContract:{actionRuleList:[]}},{id:4},sourceEntry),/no declared row opener/);
const summary = {intent:'my.work.summary',params:{product_workspace:true,limit:12,limit_each:4,page_size:12,page:1,sort_by:'priority',sort_dir:'desc'},response:{ok:true}};
assert(dailyHomeSummaryMatches(summary));
assert(!dailyHomeSummaryMatches({...summary,params:{...summary.params,product_workspace:false}}));
assert.equal([summary].slice(1).filter(dailyHomeSummaryMatches).length,0);
const expected = {model:'payment.request',recordId:4,actionId:8,menuId:9};
const contract = {intent:'ui.contract.v2',params:{record_id:4,action_id:8,menu_id:9},response:{ok:true,data:{pageInfo:{model:'payment.request',viewType:'form'},dataContract:{mainData:{id:4}}}}};
assert(dailyDetailContractMatches(contract,expected));
for (const key of ['model','recordId','actionId','menuId']) assert(!dailyDetailContractMatches(contract,{...expected,[key]:'wrong'}));
assert(!dailyDetailContractMatches({...contract,response:{ok:false,data:contract.response.data}},expected));

"""
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_daily_identity_precedes_login_and_failure_is_reported(self):
        self.assertLess(self.probe.index('servedIdentity = await verifyServedIdentity'), self.probe.index('  await login(page, navigation);'))
        self.assertIn('servedIdentity.servedDatabase !== DATABASE', self.probe)
        self.assertIn("mode: 'shared-read'", self.probe)
        self.assertIn('await lease?.release()', self.probe)
        self.assertIn("failure: String(error?.message || error)", self.probe)
        self.assertIn('runtime.denied_requests.length', self.probe)
        self.assertIn('DAILY ? acceptance.login', self.probe)
        self.assertIn('DAILY ? acceptance.password', self.probe)

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
