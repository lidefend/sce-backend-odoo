"""Contract lock for the released list-surface search probe.

The list-surface structure probe must drive the controls the product declares
(``toolbar-search-submit`` inside the declared ``collection-search-control`` and
the declared ``ScEmptyState`` empty contract) instead of reproducing interactions
that the primitive consumes. This test fails when either side drops a declared
hook, so the probe converges instead of accumulating per-symptom selector patches.
"""
from pathlib import Path
import importlib.util
import json
import unittest
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / 'scripts/verify/frontend_list_surface_structure_browser.mjs'
TOOLBAR = ROOT / 'frontend/apps/web/src/components/action/ActionSurfaceToolbar.vue'
EMPTY_STATE = ROOT / 'frontend/apps/web/src/components/design-system/ScEmptyState.vue'
HEADER = ROOT / 'frontend/apps/web/src/components/product-list/ProductListHeader.vue'
LIST_PAGE = ROOT / 'frontend/apps/web/src/pages/ListPage.vue'
FRONTEND_MAKE = ROOT / 'make/frontend.mk'
CONTRACT_LIFECYCLE = ROOT / 'addons/smart_core/core/contract_lifecycle.py'

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


def load_contract_lifecycle():
    spec = importlib.util.spec_from_file_location('contract_lifecycle', CONTRACT_LIFECYCLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_acceptance_contract_consumption(probe, frontend_make):
    """The probe must consume the backend-approved contract before it asserts anything."""
    assert 'assertContractPrerequisite(' in probe, 'the probe must require the backend exact-instance contract receipt'
    gate_at = probe.index('assertContractPrerequisite(')
    # Match the call sites, not the function definitions: a definition that appears
    # earlier in the file would otherwise satisfy the ordering assertion while the
    # real call drifted above the gate.
    for later in ('await login(page, navigation)', 'await findPopulatedList(page, navigation)', 'await captureState(page'):
        assert probe.index(later) > gate_at, f'{later} must run after the contract prerequisite gate, not before'
    assert 'readContractReceipt(' in probe, 'the probe must read the declared receipt rather than invent an approval'
    assert 'observedContractBinding(' in probe, 'the probe must bind the executed response to the approved contract'
    assert 'page.locator(`[data-record-key="${approvedRecordId}"]`)' in probe, 'the approved record must be opened by its declared row identity'
    assert 'approved_contract_binding' in probe, 'the record walk must report the approved-contract binding step'
    assert 'SC_ACCEPTANCE_REQUIRE_CONTRACT=1' in frontend_make, 'the governed list browser lane must require the contract receipt'
    assert 'SC_ACCEPTANCE_CONTRACT_RECEIPT' in frontend_make, 'the governed list browser lane must pass the contract receipt'
    assert 'SC_ACCEPTANCE_REQUIRED_SHA' in frontend_make, 'the governed list browser lane must bind the required served revision'
    # The declared instance receipt names one exact runtime; the daily profile
    # resolves a different declared environment, so it must not be bound to that
    # receipt implicitly nor silently skip it when it is explicitly required.
    assert "DAILY || ['1', 'true', 'yes']" not in probe, 'the daily profile must not implicitly require the acceptance-instance receipt'
    assert 'SC_ACCEPTANCE_REQUIRE_CONTRACT="$(SC_ACCEPTANCE_REQUIRE_CONTRACT)"' in frontend_make, 'the daily lane must pass the contract requirement explicitly'
    assert 'not_required_for_profile' in probe, 'the probe must report why a profile is not contract-bound'


class AcceptanceContractConsumptionTest(unittest.TestCase):
    """Lock that the browser consumes the backend contract, not a selector string."""

    def test_probe_consumes_the_approved_contract_before_any_assertion(self):
        validate_acceptance_contract_consumption(PROBE.read_text(), FRONTEND_MAKE.read_text())

    def test_semantic_seal_parity_between_backend_and_frontend(self):
        lifecycle = load_contract_lifecycle()
        fixture = {
            'pageInfo': {'model': 'payment.request', 'viewType': 'form'},
            'fields': [{'name': 'amount_total', 'type': 'monetary'}, {'name': '公司', 'type': 'char'}],
            'statusContract': {'globalStatus': {'modelRights': {'write': True}, 'effectiveRenderProfile': 'readonly'}},
            'counts': [1, 2, 3],
            'meta': {'lifecycle': {'runtime': {'requestId': 'request.1'}}},
        }
        expected = lifecycle.payload_sha256(lifecycle.contract_semantic_payload(fixture))
        program = (
            "import { semanticSha256 } from './scripts/verify/lib/acceptance_contract_receipt.mjs';"
            f"process.stdout.write(semanticSha256({json.dumps(fixture, ensure_ascii=False)}));"
        )
        result = subprocess.run(['node', '--input-type=module', '-e', program], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)

    def test_semantic_seal_refuses_payloads_outside_the_mirrored_domain(self):
        """Python renders floats/bigints; the JS mirror must refuse rather than diverge."""
        lifecycle = load_contract_lifecycle()
        fixture = {'meta': {}, 'ratio': 0.5, 'tiny': 1e-05, 'big': 2 ** 53}
        backend_expected = lifecycle.payload_sha256(lifecycle.contract_semantic_payload(fixture))
        self.assertTrue(backend_expected)
        program = (
            "import { semanticSha256 } from './scripts/verify/lib/acceptance_contract_receipt.mjs';"
            f"process.stdout.write(semanticSha256({json.dumps(fixture, ensure_ascii=False)}));"
        )
        result = subprocess.run(['node', '--input-type=module', '-e', program], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '', 'an unmirrorable payload must not yield a comparable digest')
        self.assertNotEqual(result.stdout.strip(), backend_expected)


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
const workspace = {sections:[{key:'todo',count:1}]};
const summary = {intent:'my.work.summary',params:{product_workspace:true,page:1,sort_by:'priority',sort_dir:'desc'},response:{ok:true,data:{product_workspace:workspace}}};
assert(dailyHomeSummaryMatches(summary));
// The workspace home consumes the my.work.summary contract and must not carry its
// own product fetch scale (PR #621 removed the frontend-held 12/4/12 envelope
// defaults; the product_workspace projection ignores limit/limit_each/page_size).
for (const key of ['limit','limit_each','page_size']) assert(!dailyHomeSummaryMatches({...summary,params:{...summary.params,[key]:12}}),key);
assert(!dailyHomeSummaryMatches({...summary,params:{...summary.params,product_workspace:false}}));
assert(!dailyHomeSummaryMatches({...summary,params:{...summary.params,page:2}}));
assert(!dailyHomeSummaryMatches({...summary,params:{...summary.params,sort_by:'id'}}));
assert(!dailyHomeSummaryMatches({...summary,response:{ok:false,data:{product_workspace:workspace}}}));
// The projected workspace must actually be built, not just acknowledged.
assert(!dailyHomeSummaryMatches({...summary,response:{ok:true,data:{product_workspace:{sections:[]}}}}));
assert(!dailyHomeSummaryMatches({...summary,response:{ok:true,data:{}}}));
assert.equal([summary].slice(1).filter(dailyHomeSummaryMatches).length,0);
const expected = {model:'payment.request',recordId:4,actionId:8,menuId:9};
const contract = {intent:'ui.contract.v2',params:{record_id:4,action_id:8,menu_id:9},response:{ok:true,data:{pageInfo:{model:'payment.request',viewType:'form'},dataContract:{mainData:{id:4}}}}};
assert(dailyDetailContractMatches(contract,expected));
for (const key of ['model','recordId','actionId','menuId']) assert(!dailyDetailContractMatches(contract,{...expected,[key]:'wrong'}));
assert(!dailyDetailContractMatches({...contract,response:{ok:false,data:contract.response.data}},expected));

"""
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_record_probe_helpers(self, assertions):
        source = self.probe.split('function dailyActorContext(')[1].split('let browser,')[0]
        result = subprocess.run(['node', '-e', "const assert = require('node:assert/strict');\nfunction dailyActorContext(" + source + assertions], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_record_renderer_profiles_and_identity_execute_real_helpers(self):
        self.run_record_probe_helpers("""
const expected={model:'res.partner',recordId:42,actionId:8,menuId:9,path:'/r/res.partner/42'};
const contract={pageInfo:{model:'res.partner',viewType:'form'},dataContract:{mainData:{id:42}},statusContract:{globalStatus:{effectiveRenderProfile:'readonly'}}};
const declaration=dailyRecordPresentation(contract,expected);
const observed={model:'res.partner',record:'42',action:'8',menu:'9',driverCount:1,patternCount:1,driverErrorCount:0,profile:'readonly',cards:2,detailAdopted:'true',detailCards:2};
assert(dailyRecordDomMatches(observed,declaration,expected));
for(const [key,value] of Object.entries({model:'wrong',record:'43',action:'7',menu:'10',driverCount:0,patternCount:2,driverErrorCount:1,profile:'edit',cards:0,detailCards:0})) assert(!dailyRecordDomMatches({...observed,[key]:value},declaration,expected),key);
assert(dailyRecordDomMatches({...observed,detailAdopted:'false',detailCards:0},declaration,expected));
assert.throws(()=>dailyRecordPresentation({...contract,statusContract:{globalStatus:{effectiveRenderProfile:'edit'}}},expected),/readonly route/);
assert.throws(()=>dailyRecordPresentation({...contract,dataContract:{mainData:{id:43}}},expected),/identity/);
assert.throws(()=>dailyRecordPresentation({...contract,statusContract:{globalStatus:{effectiveRenderProfile:'unknown'}}},expected),/unsupported/);
for(const profile of ['edit','readonly']) {
  const resolved=dailyRecordPresentation({...contract,statusContract:{globalStatus:{effectiveRenderProfile:profile}}},{...expected,path:'/f/res.partner/42'});
  assert.equal(resolved.profile,profile);
  assert(dailyRecordDomMatches({...observed,profile},resolved,expected));
}
const created=dailyRecordPresentation({...contract,dataContract:{mainData:{}},statusContract:{globalStatus:{effectiveRenderProfile:'create'}}},{...expected,recordId:0,path:'/f/res.partner/new'});
assert.equal(created.record,'new');assert.equal(created.profile,'create');
assert.throws(()=>dailyRecordPresentation(contract,{...expected,recordId:0,path:'/f/res.partner/new'}),/profile/);
assert.throws(()=>dailyRecordPresentation({...contract,statusContract:{globalStatus:{effectiveRenderProfile:'create'}}},expected),/profile/);
""")

    def test_actual_bootstrap_actor_and_captured_contract_references(self):
        self.run_record_probe_helpers("""
const init={user:{id:16},role_surface:{role_codes:['pm','cost']},record_context:{company_id:3},auth:{role:'ignored-config-role'}};
assert.deepEqual(dailyActorContext(init),{source:'captured_system_init',user_id:16,role_codes:['pm','cost'],company_id:3});
assert.deepEqual(dailyActorContext({auth:{role:'admin'},login:'x'}),{source:'captured_system_init',user_id:null,role_codes:[],company_id:null});
const row={intent:'ui.contract.v2',response:{ok:true,data:{meta:{contract_version:'2.0'}},meta:{trace_id:'trace-test'}}};
assert.deepEqual(dailyContractEvidenceRef([{},row],row),{response_index:1,intent:'ui.contract.v2',trace_id:'trace-test',contract_version:'2.0'});
assert.throws(()=>dailyContractEvidenceRef([],row),/not captured/);
""")
        self.assertIn('dailyActorContext(navigation.payload())', self.probe)
        self.assertIn('contract_evidence_ref: contractEvidenceRef', self.probe)

    def test_record_checks_require_each_viewport_and_each_executed_step(self):
        self.run_record_probe_helpers("""
const viewports=[{key:'1440'},{key:'390'}];
const steps=['declared_entry_route','exact_record_contract','approved_contract_binding','declared_renderer','return_to_source'];
const checks=viewports.flatMap(viewport=>steps.map(check=>({viewport:viewport.key,check,passed:true})));
const expected=viewports.flatMap(viewport=>steps.map(check=>`${viewport.key}:${check}`));
assert.deepEqual(dailyRecordCheckSummary(checks,viewports),{passed:10,total:10,complete:true,expected});
assert(!dailyRecordCheckSummary([],viewports).complete);
assert(!dailyRecordCheckSummary(checks.slice(0,9),viewports).complete);
assert(!dailyRecordCheckSummary([...checks,checks[0]],viewports).complete);
assert(!dailyRecordCheckSummary(checks.map((row,i)=>i===2?{...row,passed:false}:row),viewports).complete);
assert(!dailyRecordCheckSummary(checks.map(row=>({...row,viewport:'1440'})),viewports).complete);
assert(!dailyRecordCheckSummary([],[]).complete);
""")
        self.assertIn('(!DAILY || recordSummary.complete)', self.probe)

    def test_daily_record_summary_follows_the_contract_gate_shape(self):
        self.run_record_probe_helpers("""
const viewports=[{key:'1440'},{key:'390'}];
const dailySteps=['declared_entry_route','exact_record_contract','declared_renderer','return_to_source'];
const dailyChecks=viewports.flatMap(viewport=>dailySteps.map(check=>({viewport:viewport.key,check,passed:true})));
const dailyExpected=viewports.flatMap(viewport=>dailySteps.map(check=>`${viewport.key}:${check}`));
assert.deepEqual(dailyRecordCheckSummary(dailyChecks,viewports,'not_required_for_profile'),{passed:8,total:8,complete:true,expected:dailyExpected});
assert(!dailyRecordCheckSummary(dailyChecks,viewports).complete);
const acceptedSteps=[...dailySteps.slice(0,2),'approved_contract_binding',...dailySteps.slice(2)];
const acceptedChecks=viewports.flatMap(viewport=>acceptedSteps.map(check=>({viewport:viewport.key,check,passed:true})));
const acceptedExpected=viewports.flatMap(viewport=>acceptedSteps.map(check=>`${viewport.key}:${check}`));
assert.deepEqual(dailyRecordCheckSummary(acceptedChecks,viewports,'accepted'),{passed:10,total:10,complete:true,expected:acceptedExpected});
assert(!dailyRecordCheckSummary(acceptedChecks,viewports,'not_required_for_profile').complete);
assert(!dailyRecordCheckSummary([...dailyChecks,dailyChecks[0]],viewports,'not_required_for_profile').complete);
assert(!dailyRecordCheckSummary(dailyChecks.map((row,i)=>i===1?{...row,passed:false}:row),viewports,'not_required_for_profile').complete);
assert(!dailyRecordCheckSummary(dailyChecks.map(row=>({...row,viewport:'1440'})),viewports,'not_required_for_profile').complete);
assert.deepEqual(dailyRecordCheckSummary(dailyChecks,viewports,'not_evaluated'),{passed:8,total:8,complete:true,expected:dailyExpected});
""")
        self.assertIn('dailyRecordCheckSummary(recordChecks, VIEWPORTS, contractGate.status, DAILY_OBSERVATION_SCOPE)', self.probe)

    def test_daily_record_summary_covers_the_workbench_and_form_profile_scopes(self):
        # The workbench and form-profile scopes execute different bodies, so the
        # expected shape must follow the scope: a workbench run has no record
        # walk at all and a form-profile run asserts the declared create/edit
        # entries instead of the row-opened record walk.
        self.run_record_probe_helpers("""
const viewports=[{key:'1440'},{key:'390'}];
const workbench=dailyRecordCheckSummary([],viewports,'not_required_for_profile','workbench-only');
assert.equal(workbench.total,0);assert(workbench.complete);
assert(!dailyRecordCheckSummary([{viewport:'1440',check:'x',passed:true}],viewports,'not_required_for_profile','workbench-only').complete);
const steps=['declared_create_entry','create_contract','create_renderer','declared_edit_entry','edit_contract','edit_renderer'];
const checks=viewports.flatMap(viewport=>steps.map(check=>({viewport:viewport.key,check,passed:true})));
const summary=dailyRecordCheckSummary(checks,viewports,'not_required_for_profile','form-profiles');
assert.equal(summary.passed,12);assert.equal(summary.total,12);assert(summary.complete);
assert(!dailyRecordCheckSummary(checks.slice(0,11),viewports,'not_required_for_profile','form-profiles').complete);
const notApplicable=checks.map(row=>row.check==='create_renderer'?{...row,passed:false,not_applicable:true,reason:'create authority not declared'}:row);
assert(dailyRecordCheckSummary(notApplicable,viewports,'not_required_for_profile','form-profiles').complete);
const recordSteps=['declared_entry_route','exact_record_contract','declared_renderer','return_to_source'];
const recordChecks=viewports.flatMap(viewport=>recordSteps.map(check=>({viewport:viewport.key,check,passed:true})));
assert(!dailyRecordCheckSummary(recordChecks,viewports,'not_required_for_profile','form-profiles').complete);
assert(!dailyRecordCheckSummary([],viewports,'not_required_for_profile','form-profiles').complete);
""")
        self.assertIn('stepsByScope[scope] || recordSteps', self.probe)
        self.assertIn('if (FORM_PROFILES_ONLY) {', self.probe)
        self.assertIn('dailyCreateContractMatches', self.probe)
        self.assertIn('dailyCreateDomMatches', self.probe)

    def test_record_renderer_probe_is_bound_to_shipped_component_markers(self):
        page = (ROOT / 'frontend/apps/web/src/pages/ContractFormPage.vue').read_text()
        host = (ROOT / 'frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue').read_text()
        self.assertIn('<ContractFormDriverHost v-if="!showCurrentFormFieldConfigScope"', page)
        self.assertIn('<ContractFormNativeCanvas v-else-if="!boundFormDesignerSnapshot"', page)
        for marker in ['data-form-model', 'data-form-record', 'data-form-action-id', 'data-form-menu-id', 'data-detail-composition-adopted']:
            self.assertIn(marker, page)
        self.assertIn(':data-contract-form-driver="renderKit"', host)
        self.assertIn(':render-profile="renderModel.identity.mode"', host)
        for pattern in ['WorkspaceFormPattern', 'TaskFormPattern']:
            component = (ROOT / f'frontend/apps/web/src/components/product-page-patterns/{pattern}.vue').read_text()
            self.assertIn(':data-render-profile="model.renderProfile"', component)
            self.assertIn('data-product-page-pattern=', component)
        self.assertNotIn("page.locator('[data-form-canvas]')", self.probe)
        self.assertIn('dailyRecordDomMatches(presentation, declaration, expectedDetail)', self.probe)

    def test_failed_intent_diagnostic_keeps_only_safe_identity_and_error(self):
        self.run_record_probe_helpers("""
const request={intent:'file.download',params:{id:15,model:'ir.attachment',res_id:42,action_id:8,record_id:42,op:'read',password:'fixture-password',context:{secret:'private'},body:'business body'}};
const result=safeFailedResponse(404,'https://daily.test/api/v1/intent?token=hidden',request,{error:{code:404,reason_code:'NOT_FOUND',message:'missing fixture-password',data:{body:'private'}},meta:{trace_id:'trace-1'}},['fixture-password']);
assert.equal(result.intent,'file.download');assert.equal(result.id,15);assert.equal(result.res_id,42);assert.equal(result.error.reason_code,'NOT_FOUND');assert.equal(result.error.trace_id,'trace-1');
const serialized=JSON.stringify(result);for(const value of ['fixture-password','business body','private','hidden'])assert(!serialized.includes(value));
assert.equal(result.error.message,'missing [redacted]');
assert.deepEqual(safeFailedResponse(403,'https://daily.test/api/v1/intent',{intent:'login',params:{model:'private',id:15,login:'private',password:'private'}},{}),{status:403,url:'https://daily.test/api/v1/intent',intent:'login'});
assert.equal(safeFailedResponse(404,'https://daily.test/api/v1/intent',{intent:'chatter.timeline',params:{res_id:42,model:'res.partner'}},{}).res_id,42);
assert.equal(safeFailedResponse(500,'https://daily.test/assets/a?token=secret',request,{}).url,'https://daily.test/assets/a');
""")

    def test_detail_only_does_not_claim_list_checks_and_failure_retains_rows(self):
        self.assertIn("['all', 'record-only', 'detail-only', 'workbench-only', 'form-profiles']", self.probe)
        self.assertLess(self.probe.index('const rows = [];'), self.probe.index('try {\n  if (DAILY)'))
        self.assertIn("const LIST_MATRIX_SKIPPED = WORKBENCH_ONLY || FORM_PROFILES_ONLY "
                      "|| (DAILY && DAILY_OBSERVATION_SCOPE === 'detail-only');", self.probe)
        # Declared at module scope: the failure handler reads it, so a later declaration
        # would raise a TDZ ReferenceError and mask the real failure.
        self.assertLess(self.probe.index('const LIST_MATRIX_SKIPPED'),
                        self.probe.index('list_execution: LIST_MATRIX_SKIPPED ?'))
        self.assertIn('for (const viewport of LIST_MATRIX_SKIPPED ? [] : VIEWPORTS)', self.probe)
        self.assertIn('const aggregateChecks = LIST_MATRIX_SKIPPED ? {} :', self.probe)
        self.assertIn("list_execution: LIST_MATRIX_SKIPPED ? 'not_run' : 'completed'", self.probe)
        self.assertIn('screenshot, rows, acceptance_scope: acceptanceScope, actor_context: actorContext, record_checks: recordChecks', self.probe)
        self.assertIn('LIST_MATRIX_SKIPPED ? null : await productionComponentProof', self.probe)
        self.assertIn('LIST_MATRIX_SKIPPED ? [] : await negativeProofs', self.probe)

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
        # The rejection rule matches the primitive class name itself, so the
        # negative fixture spells it without the CSS dot: the fixture tests the
        # rule, it does not couple to the vendor selector.
        with self.assertRaises(AssertionError):
            validate_search_probe(*(self.probe + "\nconst x = 't-input__inner';\n", *self.declared[1:]))

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
