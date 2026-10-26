import assert from 'node:assert/strict';
import test from 'node:test';
import { permitsJournalSaveMutation } from './local_dev_journal_save_policy.mjs';
const allow = (request,state) => permitsJournalSaveMutation(request,state,{method:'POST',path:'/api/v1/intent'});
const state = { enabled: true, ready: true, ref: 'P4-JOURNAL-test', companyId: 1, journalId: 3, currencyId: 6,
  accounts: [49, 48], rowKeys: ['r1', 'r2'], createAttempted: false, createdId: null, cleanupVerified: false };
const create = { intent: 'api.data', params: { op: 'create', model: 'account.move', vals: { ref: state.ref, journal_id: 3,
  line_ids: [[0,0,{account_id:49,currency_id:6,debit:100,credit:0}], [0,0,{account_id:48,currency_id:6,debit:0,credit:100}]] } } };
test('only the balanced owned draft may be created', () => assert(allow(create,state)));
for (const [name, mutate] of [
 ['wrong marker', x => x.params.vals.ref = 'unowned'], ['other journal', x => x.params.vals.journal_id = 4],
 ['other company', x => x.params.vals.company_id = 2], ['posted', x => x.params.vals.state = 'posted'],
 ['unbalanced', x => x.params.vals.line_ids[1][2].credit = 99], ['existing row', x => x.params.vals.line_ids[0][0] = 1],
 ['unowned account', x => x.params.vals.line_ids[0][2].account_id = 99], ['lost currency', x => delete x.params.vals.line_ids[0][2].currency_id],
 ['sudo', x => x.params.sudo = true], ['write', x => x.params.op = 'write'],
]) test(`reject ${name}`, () => { const x=structuredClone(create); mutate(x); assert(!allow(x,state)); });
test('no retry or pre-ready create', () => { assert(!allow(create,{...state,createAttempted:true})); assert(!allow(create,{...state,ready:false})); });
test('cleanup requires verified exact created id', () => {
 const request={intent:'api.data.unlink',params:{model:'account.move',ids:[77]}};
 assert(!allow(request,state)); assert(!allow(request,{...state,createdId:77}));
 assert(allow(request,{...state,createdId:77,cleanupVerified:true}));
 assert(!allow(request,{...state,createdId:78,cleanupVerified:true}));
 assert(!allow({...request,params:{...request.params,ids:[77,78]}},{...state,createdId:77,cleanupVerified:true}));
});

for (const [name, mutate] of [
 ['extra root x2many', x => x.params.vals.invoice_line_ids = [[1,123,{name:'injected'}]]],
 ['extra row x2many', x => x.params.vals.line_ids[0][2].tax_ids = [[4,123]]],
 ['extra root field', x => x.params.vals.payment_id = 123],
 ['nested analytic write', x => x.params.vals.line_ids[0][2].analytic_distribution = {'123':100}],
 ['context default', x => x.params.context = {default_state:'posted'}],
 ['other context company', x => x.params.context = {company_id:2}],
 ['disable checks', x => x.params.context = {check_move_validity:false}],
 ['same account twice', x => x.params.vals.line_ids[1][2].account_id = 49],
]) test(`reject ${name}`, () => { const x=structuredClone(create); mutate(x); assert(!allow(x,state)); });
test('wrong transport refuses mutation', () => {
 assert(!permitsJournalSaveMutation(create,state,{method:'GET',path:'/api/v1/intent'}));
 assert(!permitsJournalSaveMutation(create,state,{method:'POST',path:'/api/other'}));
});
