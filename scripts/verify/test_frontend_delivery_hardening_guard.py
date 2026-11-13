#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import xml.etree.ElementTree as ET
import re
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]



class AuthenticatedIntentProbeTest(unittest.TestCase):
    def test_request_identity_and_failures(self):
        program = r"""
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { bindAuthenticatedIntent, successfulIntentData, authenticateBrowserProbe, assertEntryRequest, fillLoginCredentials } from './scripts/verify/frontend_authenticated_intent.mjs';
const response = (id=7, status=200, body={data:{user:{id,login:'probe'}}}, headers={authorization:'Bearer test-only'}) => ({
 status:()=>status, json:async()=>body,
 request:()=>({method:()=> 'POST',url:()=> 'https://example.test/t/demo/api/v1/intent',
 allHeaders:async()=>({...headers,'content-length':'99'}),
 postData:()=>JSON.stringify({intent:'system.init',context:{company_id:3},params:{}})})
});
const request = await bindAuthenticatedIntent(response(),7);
let sent;
const context={request:{post:async(url,options)=>{sent={url,...options};return response();}}};
await request(context,'system.init',{});
assert.equal(sent.url,'https://example.test/t/demo/api/v1/intent');
assert.equal(sent.headers.authorization,'Bearer test-only');
assert.equal(sent.headers['content-length'],undefined);
assert.equal(sent.headers['X-Odoo-DB'],undefined);
assert.deepEqual(sent.data.context,{company_id:3});
await request(context,'payment.request.available_actions',{id:19});
assert.deepEqual(sent.data.params,{id:19});
await assert.rejects(bindAuthenticatedIntent(response(8),7),/principal mismatch/);
await assert.rejects(bindAuthenticatedIntent(response(7,200,undefined,{}),7),/request missing/);
for (const [status,body] of [[401,{}],[409,{}],[200,{ok:false}],[200,{error:{code:403}}],[200,{code:500}]]) {
 assert.throws(()=>successfulIntentData(status,body,'probe'),/request rejected/);
 await assert.rejects(request({request:{post:async()=>response(7,status,body)}},'system.init',{}),/request rejected/);
}
await assert.rejects(request({request:{post:async()=>response(8)}},'system.init',{}),/principal mismatch/);
let failedTransportCalls=0;
await assert.rejects(request({request:{post:async()=>{
 failedTransportCalls+=1;
 throw new Error('Bearer secret');
}}},'system.init',{}),
 error=>/^system\.init: authenticated probe transport failed \(Error\)$/.test(error.message)
   && !error.message.includes('secret'));
assert.equal(failedTransportCalls,2);
let retryCalls=0;
const recovered=await request({request:{post:async()=>{
 retryCalls+=1;
 if(retryCalls===1) throw Object.assign(new Error('Bearer secret'),{code:'ECONNRESET'});
 return response();
}}},'system.init',{});
assert.equal(retryCalls,2);
assert.equal(recovered.status,200);
let nonStartupCalls=0;
await assert.rejects(request({request:{post:async()=>{
 nonStartupCalls+=1;
 throw Object.assign(new Error('Bearer secret'),{code:'ECONNRESET'});
}}},'payment.request.available_actions',{}),
 error=>/^payment\.request\.available_actions: authenticated probe transport failed \(ECONNRESET\)$/
   .test(error.message) && !error.message.includes('secret'));
assert.equal(nonStartupCalls,1);
const next = await bindAuthenticatedIntent(response(8),8);
await next({request:{post:async()=>response(8)}},'system.init',{});
// The shared login binder must observe fast responses emitted by the click,
// reject the wrong actor, and never include the error body/password in failures.
async function authenticate(body, status=200, login='probe') {
  const page=new EventEmitter();
  const emit=resp=>page.emit('response',resp);
  try { return await authenticateBrowserProbe(page,'probe',async()=>{
    emit({url:()=> 'https://example.test/t/demo/api/v1/intent', status:()=>status,
      request:()=>({method:()=> 'POST',postData:()=>JSON.stringify({intent:'login',params:{login}})})});
    emit({...response(7,200,body), url:()=> 'https://example.test/t/demo/api/v1/intent'});
  }); } finally { assert.equal(page.listenerCount('response'),0); }
}
const authenticated=await authenticate({data:{user:{id:7,login:'probe'}}});
await authenticated(context,'system.init',{});
await assert.rejects(authenticate({data:{user:{id:7}}},200,'other'),/requested login mismatch/);
await assert.rejects(authenticate({ok:false,error:{message:'password-secret'}},401),
 error=>error.message==='login: intent request rejected (HTTP 401)' && !error.message.includes('password-secret'));
await assert.rejects(bindAuthenticatedIntent(response(7,200,undefined,{authorization:'Bearer test','x-odoo-db':'old'}),7),/database routing is forbidden/);
for (const params of [{db:''}, {database:null}, {context:{db:false}}, {context:{database:0}}]) {
  let calls=0;
  await assert.rejects(request({request:{post:async()=>{calls++;return response();}}},'probe',params), /database routing is forbidden/);
  assert.equal(calls,0);
}
for (const [url,headers,payload] of [
 ['https://example.test/api/v1/intent?database=',{},{}],
 ['https://example.test/api/v1/intent',{'X-Odoo-DB-Locked':''},{}],
 ['https://example.test/api/v1/intent',{}, {db:null}],
 ['https://example.test/api/v1/intent',{}, {context:{database:''}}],
]) assert.throws(()=>assertEntryRequest(url,headers,payload),/database routing is forbidden/);
const failedSubmitPage = new EventEmitter();
await assert.rejects(authenticateBrowserProbe(failedSubmitPage, 'probe', async () => { throw new Error('submit failed'); }), /submit failed/);
assert.equal(failedSubmitPage.listenerCount('response'), 0);
// Remount clears only the password on the first attempt. Both fields must stick.
let attempts = 0, now = 0, values = {}, alwaysLosePassword = false;
const realNow = Date.now;
const form = {
 locator: selector => { const field = selector.includes('username') ? 'username' : 'password'; return {
  first() { return this; },
  async fill(value) { if (field === 'username') attempts++; values[field] = value; },
  async inputValue() { return values[field] || ''; },
 }; },
 async waitForTimeout(ms) { now += ms; if (attempts === 1 || alwaysLosePassword) values.password = ''; },
};
try {
 Date.now = () => now;
 await fillLoginCredentials(form, 'probe', 'synthetic-only', 2000);
 assert.equal(attempts, 2);
 alwaysLosePassword = true;
 await assert.rejects(fillLoginCredentials(form, 'probe', 'synthetic-only', 500),
   error => error.message === 'login form did not stabilize within timeout');
} finally { Date.now = realNow; }
console.log('authenticated probe boundaries PASS');
"""
        subprocess.run(['node', '--input-type=module', '-e', program], cwd=ROOT, check=True)


class RuntimePerformanceSampleTest(unittest.TestCase):
    def test_measurement_preserves_real_boundary_and_redacts_payloads(self):
        program = r"""
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { measureRuntimeSample, startupTiming } from './scripts/verify/frontend_runtime_performance_sample.mjs';
assert.deepEqual(startupTiming({total_ms:10,timings_ms:{assembly:8,token:'secret',invalid:-1},
 subtimings_ms:{capabilities:{query:3,secret:'private'}},payload:'private'}),
 {total_ms:10,timings_ms:{assembly:8},subtimings_ms:{capabilities:{query:3}}});
assert.equal(startupTiming(null),null);
assert.equal(startupTiming({total_ms:-1}).total_ms,null);
const page = new EventEmitter();
const request = (intent, profile=true) => ({url:()=>'/api/v1/intent',
 postData:()=>JSON.stringify({intent,params:{password:'never-export'}}),
 timing:()=>({responseEnd:5}),response:async()=>({status:()=>200,finished:async()=>null,
 json:async()=>({meta:profile?{startup_profile:{total_ms:3,timings_ms:{build:2}}}:{},data:{private:'never-export'}})})});
const sample=await measureRuntimeSample(page,async()=>{
 page.emit('request',request('system.init'));page.emit('request',request('api.data'));
 await new Promise(resolve=>setTimeout(resolve,15));
},{index:1});
assert.equal(sample.requests.length,1);
assert.equal(sample.requests[0].startup_profile.total_ms,3);
assert.equal(sample.requests[0].diagnostic,'captured');
assert.ok(sample.total_ms>=10);
assert.ok(!JSON.stringify(sample).includes('never-export'));
assert.equal(page.listenerCount('request'),0);
const missing=await measureRuntimeSample(page,async()=>page.emit('request',request('system.init',false)),{});
assert.equal(missing.requests[0].startup_profile,null);
assert.equal(missing.requests[0].diagnostic,'startup_profile_missing');
await assert.rejects(measureRuntimeSample(page,async()=>{throw new Error('original failure')},{}),/original failure/);
assert.equal(page.listenerCount('request'),0);
console.log('runtime sample assertions PASS');
"""
        subprocess.run(['node', '--input-type=module', '-e', program], cwd=ROOT, check=True)


class MyWorkPerformanceNavigationTest(unittest.TestCase):
    def test_my_work_timing_uses_the_rendered_role_home_action(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("async function openMyWorkFromRoleHome(page)", source)
        self.assertIn(
            "roleHome.getByRole('button', { name: '查看全部', exact: true })",
            source,
        )
        performance = source.split("let performanceRole = FINANCE_LOGIN;", 1)[1].split(
            "const formSamples = [];", 1
        )[0]
        self.assertNotIn("navigateSpa(page, '/my-work'", performance)
        self.assertIn("openMyWorkFromRoleHome(page)", performance)

    def test_retained_detail_timing_stays_in_the_warmed_spa_document(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("async function returnToMyWorkInRetainedDocument(page)", source)
        performance = source.split("let performanceRole = FINANCE_LOGIN;", 1)[1].split(
            "const formSamples = [];", 1
        )[0]
        sample_loop = performance.split("for (let i = 0; i < PERF_RUNS; i += 1) {", 1)[1].split(
            "if (name.endsWith('_detail'))", 1
        )[0]
        my_work_branch, detail_branch = sample_loop.split("} else {", 1)
        self.assertIn("page.goto", my_work_branch)
        self.assertNotIn("page.goto", detail_branch)
        self.assertIn("returnToMyWorkInRetainedDocument(page)", detail_branch)


class MissingRecordResponseTest(unittest.TestCase):
    def test_only_matching_contract_record_absence_is_expected(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text()
        function = source.split("function isExpectedMissingRecordResponse(row, expected) {", 1)[1].split("\nfunction capture", 1)[0]
        program = "const accepts = function(row, expected) {" + function + r"""
const assert = require('node:assert/strict');
const expected = {recordId: 73, actionId: 8};
const valid = {status:404,intent:'ui.contract.v2',op:'action_open',reason_code:'RECORD_NOT_FOUND',res_id:73,action_id:8};
assert.equal(accepts(valid,expected),true);
for (const patch of [{status:409},{status:403},{status:500},{reason_code:'CONFIG_TARGET_STALE'},
 {reason_code:undefined},{op:'model'},{intent:'api.data'},{res_id:74},{action_id:9}]) {
 assert.equal(accepts({...valid,...patch},expected),false,JSON.stringify(patch));
}
"""
        subprocess.run(["node", "-e", program], cwd=ROOT, check=True)


class PaymentCreateFailureEvidenceTest(unittest.TestCase):
    def test_control_diagnostic_distinguishes_hidden_readonly_and_editable_without_values(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text()
        function = source.split("function paymentCreateControlDiagnostic(surface) {", 1)[1].split("\nasync function openPaymentCreateFromList", 1)[0]
        program = "const diagnose = function(surface) {" + function + "\n" + r'''
const node = (attrs = {}, shown = true) => ({
  getAttribute: (key) => attrs[key] ?? null,
  getBoundingClientRect: () => ({ width: shown ? 100 : 0, height: 20 }),
});
globalThis.window = { getComputedStyle: () => ({ display: 'block', visibility: 'visible' }) };
const field = (state, input) => ({
  ...node(), tagName: 'DIV',
  querySelectorAll: (selector) => selector === 'input' ? (input ? [input] : []) : [node({ 'data-control-state': state })],
});
const fields = [field('readonly', null), field('editable', {...node({type:'number'}, false), disabled:false, readOnly:false}), field('editable', {...node({type:'number'}), disabled:false, readOnly:false})];
for (const field of fields) for (const input of field.querySelectorAll('input')) Object.defineProperty(input, 'value', { get() { throw new Error('must not read input values'); } });
const surface = { ...node({'data-state':'ready'}), querySelectorAll: (selector) => selector.includes('ContractFormProductHeader') ? [node({'data-state':'create'})] : fields };
process.stdout.write(JSON.stringify(diagnose(surface)));
'''
        result = subprocess.run(["node", "-e", program], cwd=ROOT, text=True, capture_output=True, check=True)
        diagnostic = json.loads(result.stdout)
        self.assertEqual(diagnostic["formState"], "ready")
        self.assertEqual(diagnostic["headerStates"], ["create"])
        fields = diagnostic["amountFields"]
        self.assertEqual(fields[0]["controls"][0]["state"], "readonly")
        self.assertEqual(fields[0]["inputs"], [])
        self.assertFalse(fields[1]["inputs"][0]["visible"])
        self.assertTrue(fields[2]["inputs"][0]["visible"])

    def test_failure_evidence_is_uploaded_and_input_requirement_is_preserved(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text()
        workflow = (ROOT / ".github/workflows/frontend_release_gate.yml").read_text()
        self.assertIn('paymentCreateSurface.locator(\'[data-field-name="amount"] input\').waitFor', source)
        for suffix in ("payment-create-failure.json", "failure.json", "screenshots/failure.png"):
            self.assertIn("artifacts/frontend-delivery-hardening/" + suffix, workflow)


class NewModelSpecificCssTest(unittest.TestCase):
    """The hardening rule is about selectors that are new to the product.

    Re-organizing a rule that had a shared selector list prints the surviving
    selector as an added diff line, so deciding novelty from the diff shape
    alone reported a pre-existing selector as newly added model-specific CSS.
    The rule must keep deciding novelty against the base revision while still
    failing on a selector the base revision does not have.
    """

    def test_novelty_is_decided_against_the_base_revision(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_guard.py").read_text(encoding="utf-8")

        self.assertIn('["git", "show", f"origin/main:{path}"]', source)
        self.assertIn('re.escape(selector) + r"(?![\\w-])"', source)
        self.assertNotIn('"model-specific CSS": r"', source)


TOGGLE_PATTERN = re.compile(
    r"<ScButton\b(?=[^>]*\baria-controls=\"primary-sidebar\")"
    r"(?=[^>]*:aria-expanded=\"sidebarVisible\")[^>]*>",
    re.DOTALL,
)


class AppShellSidebarSemanticsTest(unittest.TestCase):
    def test_unified_visibility_state_controls_the_named_region(self):
        source = """
        <ScButton aria-controls="primary-sidebar"
                  :aria-expanded="sidebarVisible"></ScButton>
        """
        self.assertIsNotNone(TOGGLE_PATTERN.search(source))

    def test_old_desktop_only_state_is_rejected(self):
        source = """
        <ScButton aria-controls="primary-sidebar"
                  :aria-expanded="!sidebarHidden"></ScButton>
        """
        self.assertIsNone(TOGGLE_PATTERN.search(source))

    def test_unrelated_aria_expanded_marker_is_rejected(self):
        source = """
        <ScButton aria-controls="other-panel"
                  :aria-expanded="sidebarVisible"></ScButton>
        """
        self.assertIsNone(TOGGLE_PATTERN.search(source))


class ContractFormCacheOwnershipTest(unittest.TestCase):
    def test_route_wrapper_leaves_cache_identity_to_app_shell(self):
        source = """
        <template><ContractFormPage /></template>
        <script setup lang="ts">
        import ContractFormPage from './ContractFormPage.vue';
        </script>
        """
        self.assertIn("<ContractFormPage />", source)
        self.assertNotIn(':key="routeIdentity"', source)
        self.assertNotIn("useRoute()", source)

    def test_global_route_derived_inner_key_is_rejected(self):
        source = """
        <template><ContractFormPage :key="routeIdentity" /></template>
        <script setup lang="ts">
        const route = useRoute();
        </script>
        """
        self.assertIn(':key="routeIdentity"', source)
        self.assertIn("useRoute()", source)

    def test_cache_identity_is_scoped_to_the_authenticated_actor(self):
        app = (ROOT / "frontend/apps/web/src/App.vue").read_text(encoding="utf-8")
        helper = (ROOT / "frontend/apps/web/src/app/activityPageCacheIdentity.ts").read_text(encoding="utf-8")
        self.assertIn("resolveActivityCacheKey({", app)
        self.assertIn("retainedActivityActorId.value", app)
        self.assertIn(
            "activity:user:${positiveInteger(actorUserId)}:${routeKey}:${epoch}",
            helper,
        )

    def test_logout_does_not_create_an_anonymous_record_cache_key(self):
        source = "if (userId > 0) retainedActivityActorId.value = userId;"
        self.assertNotIn("retainedActivityActorId.value = 0", source)

    def test_scope_switch_leaves_record_before_context_mutation(self):
        source = "const previousRoute = await leaveScopeSensitiveRoute();"
        self.assertIn("await leaveScopeSensitiveRoute()", source)

    def test_auxiliary_load_stops_after_page_deactivation(self):
        source = "if (!isComponentActive.value || reloadToken !== activeReloadToken) return;"
        self.assertIn("!isComponentActive.value", source)

    def test_auxiliary_preload_only_hydrates_selected_create_defaults(self):
        source = """
        if (!recordId.value) {
          await hydrateSelectedRelationOptions();
        }
        """
        self.assertNotIn("loadRelationOptions()", source)
        self.assertLess(source.index("if (!recordId.value)"), source.index("hydrateSelectedRelationOptions()"))

    def test_one2many_hydration_honors_relation_read_contract(self):
        source = """
        const entry = relationEntry(formFields()[name]);
        if (entry?.canRead === false) return;
        await readContractFormRecord();
        """
        self.assertLess(source.index("canRead === false"), source.index("readContractFormRecord()"))

    def test_v2_contract_client_builds_the_normalized_store_directly(self):
        source = """
        const response = await intentRequestRaw({ intent: 'ui.contract.v2', params });
        const snapshot = decodeContractV2Snapshot(response.data);
        return { snapshot, store: createContractV2Store(snapshot) };
        """
        self.assertIn("decodeContractV2Snapshot(response.data)", source)
        self.assertIn("createContractV2Store(snapshot)", source)
        self.assertNotIn("adaptUnifiedPageContractV2Raw", source)

    def test_v2_create_contract_cache_is_context_scoped_and_store_safe(self):
        source = """
        const key = [session.sessionDb, session.token, currentContextEpoch(), JSON.stringify(params)].join('|');
        if (renderProfile === 'create' && !recordId) return restoreCachedResult(cached.result);
        function restoreCachedResult(result) {
          const snapshot = cloneJson(result.snapshot);
          return { snapshot, store: createContractV2Store(snapshot) };
        }
        """
        self.assertIn("currentContextEpoch()", source)
        self.assertIn("renderProfile === 'create'", source)
        self.assertIn("createContractV2Store(snapshot)", source)
        self.assertNotIn("adaptUnifiedPageContractV2Raw", source)

    def test_inactive_action_page_ignores_record_context_events(self):
        source = """
        function handleRecordContextChanged(): void {
          if (!isComponentActive.value) return;
          refreshForRecordContextChange();
        }
        """
        self.assertLess(source.index("!isComponentActive.value"), source.index("refreshForRecordContextChange()"))

    def test_later_functional_failure_preserves_isolated_performance_pass(self):
        source = "if (performanceReport.result !== 'PASS') performanceReport.result = 'FAIL';"
        self.assertIn("result !== 'PASS'", source)

    def test_browser_matrix_rejects_persisted_relation_candidate_preload(self):
        source = "noEagerCandidateSurfaces.has(surface.name)"
        self.assertIn("noEagerCandidateSurfaces", source)

    def test_browser_contract_target_uses_released_ten_center_entry(self):
        # The binding must be checked through its declared constants rather than a
        # literal source spelling, so the guard locks the released entry and the
        # declared action pair instead of one line's formatting.
        path = ROOT / "scripts/verify/frontend_delivery_hardening_runtime_ids.py"
        text = path.read_text(encoding="utf-8")
        module = ast.parse(text)

        def module_constant(name):
            for node in module.body:
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == name
                ):
                    return node.value
            return None

        menu_value = module_constant("CONTRACT_MENU_XMLID")
        action_value = module_constant("CONTRACT_ACTION_XMLID")
        self.assertIsInstance(menu_value, ast.Constant)
        self.assertEqual(
            menu_value.value, "smart_construction_core.menu_sc_p1_daily_contract"
        )
        self.assertIsInstance(action_value, ast.Constant)
        self.assertEqual(
            action_value.value, "smart_construction_core.action_sc_general_contract"
        )

        resolve_targets = next(
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "resolve_targets"
        )
        payload = next(
            node.value
            for node in resolve_targets.body
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Dict)
            and any(
                isinstance(target, ast.Name) and target.id == "payload"
                for target in node.targets
            )
        )
        contract_binding = next(
            value
            for key, value in zip(payload.keys, payload.values)
            if isinstance(key, ast.Constant) and key.value == "contract"
        )
        self.assertIsInstance(contract_binding, ast.Call)
        self.assertIsInstance(contract_binding.func, ast.Name)
        self.assertEqual(contract_binding.func.id, "target")
        self.assertIsInstance(contract_binding.args[0], ast.Name)
        self.assertEqual(contract_binding.args[0].id, "CONTRACT_MENU_XMLID")
        declared_action = next(
            (
                keyword.value
                for keyword in contract_binding.keywords
                if keyword.arg == "declared_action_xmlid"
            ),
            None,
        )
        self.assertIsInstance(declared_action, ast.Name)
        self.assertEqual(declared_action.id, "CONTRACT_ACTION_XMLID")
        self.assertNotIn("menu_sc_construction_contract", text)

    def test_browser_payment_target_uses_role_owned_hardening_fixture(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_runtime_ids.py").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a"',
            source,
        )
        self.assertNotIn(
            '"payment_request": target("smart_construction_core.menu_sc_user_payment_apply", '
            '"smart_construction_acceptance_fixture.fe_request_a_001")',
            source,
        )

    def test_acceptance_payment_execution_uses_its_project_company(self):
        source = (
            ROOT
            / "addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py"
        ).read_text(encoding="utf-8")

        self.assertRegex(
            source,
            re.compile(
                r'def _execution\(.*?"project_id": project\.id,\s*'
                r'"company_id": project\.company_id\.id,',
                re.DOTALL,
            ),
        )

    def test_confirmation_dialog_probe_tracks_safe_cancel_autofocus(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "dialog.getByRole('button', { name: '取消', exact: true })",
            source,
        )
        self.assertNotIn(
            "dialog.getByRole('button', { name: '确认提交' }).evaluate",
            source,
        )

    def test_company_isolation_probe_waits_for_scoped_final_company_item(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text(
            encoding="utf-8"
        )

        self.assertIn("const initiatedSection = page.locator", source)
        self.assertIn("filter({ hasText: 'FE-C-PR-001' }).waitFor", source)
        self.assertIn("initiatedSection.locator('.work-card').filter({ hasText: journeyName })", source)
        self.assertIn("FINAL_COMPANY_MY_WORK J11", source)
        self.assertIn("final My Work request did not use company B context", source)
        self.assertIn("final My Work response did not use company B scope", source)

    def test_relation_candidate_probe_waits_for_prior_surface_quiet(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text(
            encoding="utf-8"
        )

        self.assertIn("async function relationCandidateCountAfterQuiet(", source)
        responsive = source.split("const noEagerCandidateSurfaces", 1)[1].split(
            "if (SKIP_PERF)", 1
        )[0]
        baseline = "await relationCandidateCountAfterQuiet(page, runtime, 'construction.contract')"
        self.assertIn(baseline, responsive)
        self.assertLess(
            responsive.index(baseline),
            responsive.index("await page.goto(`${BASE_URL}${surface.route}`"),
        )

    def test_form_open_performance_starts_from_settled_list(self):
        source = (ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs").read_text(
            encoding="utf-8"
        )

        self.assertIn('data-collection-state="ok"', source)
        self.assertIn('data-collection-state="empty"', source)
        performance = source.split("const formSamples = [];", 1)[1].split(
            "const switchSamples = [];", 1
        )[0]
        self.assertEqual(
            performance.count("navigateSpa(page, listRoute(TARGETS.payment_request), READY_ACTION_LIST_SELECTOR)"),
            2,
        )
        self.assertNotIn("[data-list-status]:visible", performance)


MODULE = ROOT / 'addons/smart_construction_core'


def native_group_graph():
    graph = {}
    for filename in ('sc_capability_groups.xml', 'sc_role_groups.xml'):
        for row in ET.parse(MODULE / 'security' / filename).findall('.//record[@model="res.groups"]'):
            key = row.attrib['id']
            key = key if '.' in key else 'smart_construction_core.' + key
            edges = graph.setdefault(key, set())
            for field in row.findall('./field[@name="implied_ids"]'):
                expression = re.sub(r"ref\(['\"]([^'\"]+)['\"]\)", lambda m: repr(m.group(1)), field.attrib['eval'])
                for command in ast.literal_eval(expression):
                    if command[0] == 6:
                        edges.clear()
                        edges.update(command[2])
                    elif command[0] == 4:
                        edges.add(command[1])
                    elif command[0] == 3:
                        edges.discard(command[1])
                    elif command[0] == 5:
                        edges.clear()
                    else:
                        raise AssertionError(f'unhandled group command: {command}')
    return graph


class SettlementComplianceVisibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = native_group_graph()
        with (MODULE / 'security/ir.model.access.csv').open() as stream:
            cls.readers = {row['group_id:id'] for row in csv.DictReader(stream)
                           if row['model_id:id'] == 'model_payment_request' and row['perm_read'] == '1'}
        root = ET.parse(MODULE / 'views/core/settlement_views.xml')
        cls.states = root.findall('.//field[@name="compliance_state"]')
        cls.messages = root.findall('.//field[@name="compliance_message"]')

    def closure(self, group):
        result, pending = set(), [group]
        while pending:
            key = pending.pop()
            if key not in result:
                result.add(key)
                pending.extend(self.graph.get(key, ()))
        return result

    def test_all_consumers_and_dependency_use_identical_native_groups(self):
        self.assertEqual(len(self.states), 1)
        self.assertEqual(len(self.messages), 3)
        expected = set(self.states[0].attrib.get('groups', '').split(','))
        self.assertNotIn('', expected)
        for field in self.messages:
            self.assertEqual(set(field.attrib.get('groups', '').split(',')), expected)
            self.assertIn('compliance_state', field.attrib['modifiers'])

    def test_group_closure_matches_payment_read_authority(self):
        visibility = set(self.states[0].attrib.get('groups', '').split(','))
        for group in self.graph.keys() | self.readers:
            with self.subTest(group=group):
                effective = self.closure(group)
                self.assertEqual(bool(effective & visibility), bool(effective & self.readers))

    def test_project_manager_without_finance_does_not_receive_predicate(self):
        effective = self.closure('smart_construction_core.group_sc_role_project_manager')
        self.assertFalse(effective & self.readers)
        for field in self.states + self.messages:
            self.assertFalse(effective & set(field.attrib.get('groups', '').split(',')))

    def test_finance_and_combined_roles_keep_matching_indicators(self):
        for group in ('group_sc_cap_finance_read', 'group_sc_cap_finance_user', 'group_sc_cap_finance_manager'):
            effective = self.closure('smart_construction_core.' + group)
            for extra in (set(), self.closure('smart_construction_core.group_sc_role_project_manager')):
                for field in self.states + self.messages:
                    self.assertTrue((effective | extra) & set(field.attrib.get('groups', '').split(',')))



if __name__ == "__main__":
    unittest.main()
