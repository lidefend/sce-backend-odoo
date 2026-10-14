#!/usr/bin/env node
// Behaviour lock for the backend exact-instance contract prerequisite.
// Proves the frontend gate consumes the declared receipt and rejects every
// missing/stale/mismatched prerequisite before any DOM assertion runs.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  RECEIPT_SCHEMA, CanonicalJsonUnsupported, canonicalJson, semanticSha256, contractPrerequisite,
  assertContractPrerequisite, readContractReceipt, observedContractBinding,
} from './lib/acceptance_contract_receipt.mjs';

const SHA = 'a'.repeat(40);
const OTHER_SHA = 'e'.repeat(40);
const SEMANTIC = 'b'.repeat(64);
const SCHEMA = 'c'.repeat(64);
const CUSTODY = 'd'.repeat(64);
const AUTHORITIES = ['ir.model.access', 'ir.ui.menu', 'ir.ui.view', 'ui.contract'];

function genuineReceipt(overrides = {}) {
  const receipt = {
    schema: RECEIPT_SCHEMA,
    enabled: true,
    status: 'PASS',
    errors: [],
    required_checks: ['identity_deployed_sha', 'contract_schema_digest_bound'],
    executed_checks: ['identity_deployed_sha', 'contract_schema_digest_bound'],
    not_run_checks: [],
    checks: { identity_deployed_sha: true, contract_schema_digest_bound: true },
    identity: { served_sha: SHA, expected_sha: SHA, uid: 30, login: 'fixture_role_finance', role_code: 'finance', company_name: 'FE Company A' },
    approved_semantic_sha256: SEMANTIC,
    recomputed_semantic_sha256: SEMANTIC,
    schema_asset: { path: 'docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json', sha256: SCHEMA, declared_schema_sha256: SCHEMA, formal_schema_errors: [] },
    custody: { response_sha256: CUSTODY, response_bytes: 4096 },
    resolution: { model: 'payment.request', record_id: 1813, action_id: 775, menu_id: 545, stable_identifier: 'smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a', company_id: 8 },
    request: { intent: 'ui.contract.v2', database: 'sc_frontend_acceptance', http_status: 200,
      context: { lang: 'zh_CN', tz: 'Asia/Shanghai' },
      params: { op: 'model', model: 'payment.request', view_type: 'form', record_id: 1813, action_id: 775, menu_id: 545, delivery_profile: 'full', client_type: 'web_pc', accepted_contract_versions: ['2.0.x', '2.1.x', '2.2.x'], client_contract_capabilities: ['container_tree.v2'] } },
    snapshot: { meta: { lifecycle: { integrity: { contractSha256: SEMANTIC },
      definition: { schemaId: 'smart_core.unified_page_contract_v2', schemaVersion: '2.2.0', schemaSha256: SCHEMA },
      authority: { kind: 'unified_page_contract_v2', authorities: AUTHORITIES } } } },
  };
  return { ...receipt, ...overrides };
}

const CONTEXT = { expectedSha: SHA, database: 'sc_frontend_acceptance', login: 'fixture_role_finance', roleCode: 'finance', companyName: 'FE Company A' };
const accepted = contractPrerequisite({ receipt: genuineReceipt(), ...CONTEXT });
assert.equal(accepted.ok, true, 'a genuine receipt must be accepted');
assert.equal(accepted.approved.record_id, 1813);
assert.equal(accepted.approved.route, '/a/775?menu_id=545');
assert.equal(accepted.approved.stable_identifier, 'smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a');
assert.equal(accepted.schemaSha256, SCHEMA);
assert.deepEqual(accepted.approvedRequest.context, { lang: 'zh_CN', tz: 'Asia/Shanghai' });
assert.equal(accepted.identity.role_code, 'finance');
assert.deepEqual(accepted.authority.authorities, AUTHORITIES);
assert.equal(assertContractPrerequisite({ receipt: genuineReceipt(), ...CONTEXT }).ok, true);

// The approved identity comes from the receipt, never from a hard-coded record.
const moved = contractPrerequisite({ receipt: genuineReceipt({ resolution: { model: 'payment.request', record_id: 4242, action_id: 900, menu_id: 901, stable_identifier: 'demo.x' },
  request: { intent: 'ui.contract.v2', database: 'sc_frontend_acceptance', context: { lang: 'zh_CN', tz: 'Asia/Shanghai' }, params: { op: 'model', model: 'payment.request', view_type: 'form', record_id: 4242, action_id: 900, menu_id: 901 } } }), ...CONTEXT });
assert.equal(moved.ok, true);
assert.equal(moved.approved.record_id, 4242);
assert.equal(moved.approved.route, '/a/900?menu_id=901');

const rejected = (code, receipt, context = CONTEXT) => {
  const verdict = contractPrerequisite({ receipt, ...context });
  assert.equal(verdict.ok, false, `${code} must be rejected`);
  assert.equal(verdict.code, code, `expected ${code}, got ${verdict.code}`);
  assert.throws(() => assertContractPrerequisite({ receipt, ...context }), /contract prerequisite failed/, `${code} must stop the caller`);
};
rejected('contract_receipt_missing', null);
rejected('contract_receipt_schema_unknown', genuineReceipt({ schema: 'other.v1' }));
rejected('contract_receipt_disabled', genuineReceipt({ enabled: false, status: 'NOT_RUN' }));
rejected('contract_receipt_not_pass', genuineReceipt({ status: 'FAIL' }));
rejected('contract_receipt_errors', genuineReceipt({ errors: ['contract_schema_digest_not_bound'] }));
rejected('contract_receipt_required_checks_missing', genuineReceipt({ required_checks: [] }));
rejected('contract_receipt_checks_not_run', genuineReceipt({ not_run_checks: ['contract_formal_schema_valid'] }));
rejected('contract_receipt_checks_not_executed', genuineReceipt({ executed_checks: [] }));
rejected('contract_receipt_checks_failed', genuineReceipt({ checks: { identity_deployed_sha: true, contract_schema_digest_bound: false } }));
rejected('contract_receipt_identity_unbound', genuineReceipt({ identity: { served_sha: '', expected_sha: '' } }));
rejected('contract_receipt_required_sha_missing', genuineReceipt(), { ...CONTEXT, expectedSha: '' });
rejected('contract_receipt_stale', genuineReceipt({ identity: { served_sha: OTHER_SHA, expected_sha: OTHER_SHA, login: 'fixture_role_finance', role_code: 'finance', company_name: 'FE Company A' } }));
rejected('contract_receipt_database_mismatch', genuineReceipt(), { ...CONTEXT, database: 'sc_dev_demo' });
rejected('contract_receipt_login_mismatch', genuineReceipt(), { ...CONTEXT, login: 'fixture_role_project' });
rejected('contract_receipt_role_mismatch', genuineReceipt(), { ...CONTEXT, roleCode: 'project_manager' });
rejected('contract_receipt_company_mismatch', genuineReceipt(), { ...CONTEXT, companyName: 'FE Company B' });
rejected('contract_receipt_semantics_unverified', genuineReceipt({ recomputed_semantic_sha256: 'f'.repeat(64) }));
rejected('contract_receipt_semantics_unverified', genuineReceipt({ approved_semantic_sha256: '' }));
rejected('contract_receipt_schema_digest_unbound', genuineReceipt({ schema_asset: { path: 'x', sha256: SCHEMA, declared_schema_sha256: 'f'.repeat(64), formal_schema_errors: [] } }));
rejected('contract_receipt_schema_invalid', genuineReceipt({ schema_asset: { path: 'x', sha256: SCHEMA, declared_schema_sha256: SCHEMA, formal_schema_errors: ['$'] } }));
rejected('contract_receipt_custody_missing', genuineReceipt({ custody: {} }));
rejected('contract_receipt_intent_unexpected', genuineReceipt({ request: { intent: 'ui.contract', database: 'sc_frontend_acceptance', params: {} } }));
// A receipt that does not record the request context cannot be replayed verbatim:
// the sealed digest is a function of the localized projection.
rejected('contract_receipt_request_context_missing', genuineReceipt({ request: { ...genuineReceipt().request, context: {} } }));
rejected('contract_receipt_request_context_missing', genuineReceipt({ request: { ...genuineReceipt().request, context: { lang: 'zh_CN' } } }));
rejected('contract_receipt_resolution_incomplete', genuineReceipt({ resolution: { model: 'payment.request', action_id: 775, menu_id: 545 } }));
rejected('contract_receipt_request_target_mismatch', genuineReceipt({ resolution: { model: 'payment.request', record_id: 1813, action_id: 775, menu_id: 545, stable_identifier: 'demo.x' },
  request: { intent: 'ui.contract.v2', database: 'sc_frontend_acceptance', context: { lang: 'zh_CN', tz: 'Asia/Shanghai' }, params: { op: 'model', model: 'payment.request', view_type: 'form', record_id: 7777, action_id: 775, menu_id: 545 } } }));
rejected('contract_receipt_view_type_missing', genuineReceipt({ request: { intent: 'ui.contract.v2', database: 'sc_frontend_acceptance', context: { lang: 'zh_CN', tz: 'Asia/Shanghai' }, params: { op: 'model', model: 'payment.request', record_id: 1813, action_id: 775, menu_id: 545 } } }));
rejected('contract_receipt_snapshot_unsealed', genuineReceipt({ snapshot: { meta: { lifecycle: { integrity: { contractSha256: 'f'.repeat(64) }, authority: { authorities: AUTHORITIES } } } } }));
rejected('contract_receipt_authority_missing', genuineReceipt({ snapshot: { meta: { lifecycle: { integrity: { contractSha256: SEMANTIC }, definition: { schemaId: 'x', schemaVersion: '2.2.0' } } } } }));

// Receipt consumption: the probe report wrapper and the bare receipt are equivalent.
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'acceptance-receipt-'));
const bare = path.join(dir, 'bare.json');
const wrapped = path.join(dir, 'report.json');
fs.writeFileSync(bare, JSON.stringify(genuineReceipt()));
fs.writeFileSync(wrapped, JSON.stringify({ mode: 'dev_acceptance_release_probe', status: 'PASS', contract: genuineReceipt() }));
assert.equal(contractPrerequisite({ receipt: readContractReceipt(bare).receipt, ...CONTEXT }).ok, true);
assert.equal(contractPrerequisite({ receipt: readContractReceipt(wrapped).receipt, ...CONTEXT }).ok, true);
const missing = readContractReceipt(path.join(dir, 'absent.json'));
assert.equal(missing.receipt, null);
assert.match(missing.error, /contract_receipt_unavailable/);

const observedEnvelope = envelope => envelope;
const envelopeWith = ({ digest = SEMANTIC, schema = SCHEMA, authorities = AUTHORITIES, model = 'payment.request', viewType = 'form', id = 1813, ok = true } = {}) => ({
  ok, data: { pageInfo: { model, viewType }, dataContract: { mainData: { id } },
    meta: { lifecycle: { integrity: { contractSha256: digest }, definition: { schemaId: 'smart_core.unified_page_contract_v2', schemaVersion: '2.2.0', schemaSha256: schema }, authority: { authorities } } } },
});
const okBinding = observedContractBinding({
  envelope: observedEnvelope({ ok: true, data: { pageInfo: { model: 'payment.request', viewType: 'form' },
    dataContract: { mainData: { id: 1813 } },
    meta: { lifecycle: { integrity: { contractSha256: SEMANTIC }, definition: { schemaId: 'smart_core.unified_page_contract_v2', schemaVersion: '2.2.0', schemaSha256: SCHEMA }, authority: { kind: 'unified_page_contract_v2', authorities: [...AUTHORITIES].reverse() } } } } }),
  receiptRequest: accepted.approvedRequest.params,
  approved: accepted,
  requestParams: accepted.approvedRequest.params,
});
assert.equal(okBinding.ok, true, 'a matching live response must bind');
assert.equal(okBinding.exact_approved_request, true);
assert.equal(okBinding.same_as_approved, true);

const extraParamBinding = observedContractBinding({
  envelope: okBinding && { ok: true, data: { pageInfo: { model: 'payment.request', viewType: 'form' }, dataContract: { mainData: { id: 1813 } },
    meta: { lifecycle: { integrity: { contractSha256: SEMANTIC }, definition: { schemaId: 'smart_core.unified_page_contract_v2', schemaVersion: '2.2.0', schemaSha256: SCHEMA }, authority: { authorities: AUTHORITIES } } } } },
  receiptRequest: accepted.approvedRequest.params,
  approved: accepted,
  requestParams: { ...accepted.approvedRequest.params, render_profile: 'readonly' },
});
assert.equal(extraParamBinding.ok, true, 'a wider client request may still bind while the sealed semantics match the approved contract');
assert.equal(extraParamBinding.exact_approved_request, false);
assert.deepEqual(extraParamBinding.extra_request_params, ['render_profile']);

// A wider or narrower request never excuses a divergent seal: request-shape
// equality is only a hint, the backend-sealed semantic digest is the binding.
const widerDiverged = observedContractBinding({
  envelope: envelopeWith({ digest: 'f'.repeat(64) }),
  receiptRequest: accepted.approvedRequest.params,
  approved: accepted,
  requestParams: { ...accepted.approvedRequest.params, render_profile: 'readonly' },
});
assert.equal(widerDiverged.ok, false, 'a wider request with a divergent seal must be rejected');
assert.equal(widerDiverged.code, 'observed_semantics_diverged');
const { delivery_profile: _dropped, ...narrowerRequest } = accepted.approvedRequest.params;
const narrowerDiverged = observedContractBinding({
  envelope: envelopeWith({ digest: 'f'.repeat(64) }),
  receiptRequest: accepted.approvedRequest.params,
  approved: accepted,
  requestParams: narrowerRequest,
});
assert.equal(narrowerDiverged.ok, false, 'a narrower request with a divergent seal must be rejected');
assert.equal(narrowerDiverged.code, 'observed_semantics_diverged');

const bindingRejected = (code, envelope, requestParams = accepted.approvedRequest.params) => {
  const verdict = observedContractBinding({ envelope, receiptRequest: accepted.approvedRequest.params, approved: accepted, requestParams });
  assert.equal(verdict.ok, false, `${code} must be rejected`);
  assert.equal(verdict.code, code, `expected ${code}, got ${verdict.code}`);
};
bindingRejected('observed_envelope_not_ok', envelopeWith({ ok: false }));
bindingRejected('observed_contract_unsealed', envelopeWith({ digest: '' }));
bindingRejected('observed_schema_digest_mismatch', envelopeWith({ schema: 'f'.repeat(64) }));
bindingRejected('observed_authority_mismatch', envelopeWith({ authorities: ['ir.ui.view'] }));
bindingRejected('observed_page_identity_mismatch', envelopeWith({ model: 'res.partner' }));
bindingRejected('observed_record_identity_mismatch', envelopeWith({ id: 9999 }));
bindingRejected('observed_request_target_mismatch', envelopeWith(), { record_id: 9999 });
bindingRejected('observed_semantics_diverged', envelopeWith({ digest: 'f'.repeat(64) }));
bindingRejected('observed_request_conflict', envelopeWith(), { ...accepted.approvedRequest.params, delivery_profile: 'summary' });

// Protocol parity of the semantic seal (key order and meta are not part of it).
assert.equal(canonicalJson({ b: 1, a: [2, { d: 'x', c: null }] }), '{"a":[2,{"c":null,"d":"x"}],"b":1}');
assert.equal(canonicalJson({ zh: '施工合同' }), '{"zh":"施工合同"}');
assert.equal(semanticSha256({ meta: { lifecycle: { traceId: 'a' } }, page: 1 }), semanticSha256({ page: 1 }));
assert.notEqual(semanticSha256({ page: 1 }), semanticSha256({ page: 2 }));

// The JS mirror only covers the domain Python's canonical_json renders identically.
// Anything outside it must refuse to produce a digest instead of fabricating one.
assert.throws(() => canonicalJson({ ratio: 0.5 }), CanonicalJsonUnsupported);
assert.throws(() => canonicalJson({ big: 2 ** 53 }), CanonicalJsonUnsupported);
assert.throws(() => canonicalJson({ weird: Number.NaN }), CanonicalJsonUnsupported);
assert.equal(semanticSha256({ meta: {}, ratio: 0.5 }), '', 'an unsupported payload must not yield a comparable digest');
assert.notEqual(semanticSha256({ meta: {}, ratio: 0.5 }), SEMANTIC);

process.stdout.write('[acceptance_contract_receipt_test] PASS\n');

// local.dev reuses the same prerequisite, adding its resolved actor and target.
const { approvedTarget, formDeclaration } = await import('./local_dev_payment_request_floorplan_readonly.mjs');
const localTarget = { user: { id: 30, login: CONTEXT.login, company_name: CONTEXT.companyName },
  acceptance_authority: { role_code: CONTEXT.roleCode }, record: { id: 1813 }, action: { id: 775 }, menu: { id: 545 },
  contract_resolution: { targets: { payment_request: { model: 'payment.request' } } } };
let localCases = 0;
const acceptLocal = (receipt, target = localTarget) => approvedTarget({ receipt, target, sourceSha: SHA, database: CONTEXT.database });
assert.equal(acceptLocal(genuineReceipt()).ok, true); localCases++;
for (const receipt of [genuineReceipt({ status: 'FAIL' }), genuineReceipt({ identity: { ...genuineReceipt().identity, uid: 31 } }),
  genuineReceipt({ approved_semantic_sha256: '0'.repeat(64) }),
  genuineReceipt({ request: { ...genuineReceipt().request, database: 'other' } })]) {
  let launched = false;
  assert.throws(() => { acceptLocal(receipt); launched = true; });
  assert.equal(launched, false, 'approval failure must precede any browser launch'); localCases++;
}
assert.throws(() => acceptLocal(genuineReceipt(), { ...localTarget, record: { id: 9 } })); localCases++;
const nativeContract = { pageInfo: { model: 'payment.request', viewType: 'form' },
  statusContract: { globalStatus: { effectiveRenderProfile: 'readonly' } }, dataContract: { mainData: { id: 1813 } },
  formStructureContract: { structureAuthority: 'container_tree', presentationMode: 'task' } };
const expectedNative = { model: 'payment.request', record: 1813, routeMode: 'readonly' };
assert.equal(formDeclaration(nativeContract, expectedNative).bodyStructureAuthority, 'containerTree'); localCases++;
for (const contract of [{ ...nativeContract, formStructureContract: {} },
  { ...nativeContract, pageInfo: { model: 'other', viewType: 'form' } },
  { ...nativeContract, statusContract: { globalStatus: { effectiveRenderProfile: 'edit' } } }]) {
  assert.throws(() => formDeclaration(contract, expectedNative)); localCases++;
}
const shell = fs.readFileSync('scripts/verify/local_dev_payment_request_floorplan_readonly.sh', 'utf8');
assert.ok(shell.indexOf('--require-contract') < shell.indexOf('node "$ROOT_DIR/scripts/verify/local_dev_payment_request_floorplan_readonly.mjs"'));
assert.ok(shell.startsWith('#!/usr/bin/env bash\nset -euo pipefail'));
assert.ok(shell.includes("after.get('business_fingerprint') == before.get('business_fingerprint')"));
assert.ok(shell.includes("summary['pass'] = bool(summary.get('pass') is True and readback_ok and os.environ['BROWSER_STATUS'] == '0')")); localCases++;
console.log(`[local-dev-floorplan-prerequisite] PASS cases=${localCases}`);

const { consumptionCases } = await import('./local_dev_payment_request_floorplan_readonly.mjs');
const field = (id, name) => ({ widgetId: id, fieldCode: name, nativeLocator: `/form/${id}`, sourcePosition: 1, span: 6,
  componentConfig: { fieldType: 'text', nativeWidget: 'textarea' } });
const consumptionFixture = { layoutContract: { containerTree: [{ containerId: 'root', widgetList: [field('edit', 'note')],
  children: [{ containerId: 'hidden', widgetList: [field('dup1', 'duplicate'), field('dup2', 'duplicate')], children: [] }] }] },
  statusContract: { containerStatus: [{ containerId: 'root', visible: true }, { containerId: 'hidden', visible: false }],
    widgetStatus: [{ widgetId: 'edit', visible: true, readonly: false, auth: 'write' },
      { widgetId: 'dup1', visible: true, readonly: true, auth: 'read' },
      { widgetId: 'dup2', visible: true, readonly: true, auth: 'read' }] } };
const consumed = consumptionCases(consumptionFixture);
assert.deepEqual(consumed.selected.map(item => item.id), ['edit']);
assert.deepEqual(consumed.hidden.map(item => item.id), ['dup1', 'dup2']);
assert.ok(consumed.hidden.every(item => item.ownVisible && !item.ancestorsVisible));
assert.equal(consumed.selected[0].span, 6);
assert.throws(() => consumptionCases({ ...consumptionFixture, statusContract: { ...consumptionFixture.statusContract, containerStatus: [] } }));
assert.throws(() => consumptionCases({ ...consumptionFixture, statusContract: { ...consumptionFixture.statusContract, widgetStatus: [] } }));
const floorplanProbe = fs.readFileSync('scripts/verify/local_dev_payment_request_floorplan_readonly.mjs', 'utf8');
assert.ok(!floorplanProbe.includes("press('Enter')"));
assert.ok(floorplanProbe.includes('button.toolbar-search-submit:visible'));
console.log('[local-dev-consumption-declaration] PASS cases=8');

const { executionKeys } = await import('./local_dev_payment_request_floorplan_readonly.mjs');
const exactUnits = {check:'scope',identity:{uid:1},units:[{id:'entry_click'},{id:'edit:span:1440'}]};
const exactPlan = {schema:'evidence_scope.plan.v1',check:'scope',identity:{uid:1},affected:['edit:span:1440'],reusable:['entry_click'],blocked:[]};
assert.deepEqual([...executionKeys(exactUnits,exactPlan)],['edit:span:1440']);
assert.deepEqual([...executionKeys(exactUnits,{...exactPlan,affected:[],reusable:['entry_click','edit:span:1440']})],[]);
for (const patch of [{affected:['unknown']},{affected:['entry_click']},{blocked:['entry_click']},{identity:{uid:2}},{reusable:[]}]) {
  assert.throws(()=>executionKeys(exactUnits,{...exactPlan,...patch}));
}
assert.ok(floorplanProbe.includes("wants('entry_click')"));
assert.ok(floorplanProbe.includes('if (!wants(authKey) && !wants(spanKey) && !wants(guidanceKey)) continue'));
assert.ok(floorplanProbe.includes('affected scope was not fully executed'));
console.log('[local-dev-affected-executor] PASS cases=10');

const identityUnits = {...exactUnits, identity:{database:'sc_dev_demo',uid:1,company_id:2}};
assert.deepEqual([...executionKeys(identityUnits,{...exactPlan,identity:{company_id:2,uid:1,database:'sc_dev_demo'}})],['edit:span:1440']);
for (const identity of [{database:'sc_dev_demo',uid:1}, {database:'sc_dev_demo',uid:'1',company_id:2}, {database:'other',uid:1,company_id:2}, {database:'sc_dev_demo',uid:1,company_id:2,extra:true}]) {
  assert.throws(()=>executionKeys(identityUnits,{...exactPlan,identity}), /identity mismatch/);
}
console.log('[local-dev-plan-identity] PASS cases=5');

const { guidanceDeclaration } = await import('./local_dev_payment_request_floorplan_readonly.mjs');
const guidanceFixture = {layoutContract:{containerTree:[{name:'amount'}]},actionContract:{actionRuleList:[{button:{type:'object',name:'action_submit'},allowed:true,enabled:true,backendIdentity:'native.submit',presentation:{requires_confirmation:true,warning_message:'Native warning'}}]}};
assert.equal(guidanceDeclaration(guidanceFixture).message,'Native warning');
for (const change of [c=>c.layoutContract.containerTree.push({name:'legal_next_action_display'}),c=>c.actionContract.actionRuleList[0].enabled=false,c=>c.actionContract.actionRuleList[0].presentation.warning_message='',c=>c.actionContract.actionRuleList.push(c.actionContract.actionRuleList[0])]) {
  const fixture=structuredClone(guidanceFixture); change(fixture); assert.throws(()=>guidanceDeclaration(fixture));
}
console.log('[local-dev-native-guidance-declaration] PASS cases=5');
const { projectCreateDeclaration } = await import('./local_dev_payment_request_floorplan_readonly.mjs');
const projectEntry={model:'project.project',action_id:10,menu_id:11,view_id:12};
const projectFixture={pageInfo:{model:'project.project',viewType:'form'},formStructureContract:{presentationMode:'task',structureAuthority:'container_tree',sourceAuthority:{governance_source:{resolvedViewId:12}}},statusContract:{globalStatus:{effectiveRenderProfile:'create'},containerStatus:[{containerId:'root',visible:true}],widgetStatus:['name','initiation_date','manager_id'].map(field=>({widgetId:field,visible:true,required:true}))},layoutContract:{containerTree:[{containerId:'root',widgetList:['name','initiation_date','manager_id'].map(field=>({widgetId:field,fieldCode:field}))}]}};
assert.deepEqual(projectCreateDeclaration(projectFixture,projectEntry,{action_id:10,menu_id:11}).required.map(row=>row.field),['name','initiation_date','manager_id']);
for(const change of [c=>c.statusContract.globalStatus.effectiveRenderProfile='edit',c=>c.formStructureContract.sourceAuthority.governance_source.resolvedViewId=13,c=>c.statusContract.widgetStatus[0].required=false,c=>c.layoutContract.containerTree[0].widgetList.push({widgetId:'retired',fieldCode:'intake_next_action_display'})]) {
 const fixture=structuredClone(projectFixture);change(fixture);assert.throws(()=>projectCreateDeclaration(fixture,projectEntry,{action_id:10,menu_id:11}));
}
assert.throws(()=>projectCreateDeclaration(projectFixture,projectEntry,{action_id:99,menu_id:11}));
console.log('[local-dev-project-create-declaration] PASS cases=6');
