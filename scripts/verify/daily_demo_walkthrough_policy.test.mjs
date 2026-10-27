import assert from 'node:assert/strict';
import { permitsWalkthroughWrite as allows } from './daily_demo_walkthrough_policy.mjs';
const plan = {model:'sc.labor.worker',key:'DEMO-WALK-20261026-WORKER01',keyField:'name',actions:[{method:'action_enter'}]};
const req = (intent, params) => ({intent,params:{model:plan.model,...params}});
const create = req('api.data',{op:'create',vals:{name:plan.key}});
assert(allows(create,plan));
assert(!allows(create,plan,10));
assert(!allows(req('api.data',{op:'create',vals:{name:'seed'}}),plan));
assert(!allows(req('api.data',{op:'create',vals:{name:plan.key,state:'done'}}),plan));
assert(!allows({...create,params:{...create.params,model:'res.users'}},plan));
assert(allows(req('api.data',{op:'write',ids:[10],vals:{note:'walkthrough'}}),plan,10));
assert(!allows(req('api.data',{op:'write',ids:[10,11],vals:{note:'walkthrough'}}),plan,10));
assert(!allows(req('api.data',{op:'write',ids:[11],vals:{note:'walkthrough'}}),plan,10));
assert(!allows(req('api.data',{op:'write',ids:[10],vals:{state:'done'}}),plan,10));
assert(!allows(req('api.data',{op:'unlink',ids:[10]}),plan,10));
assert(allows(req('execute_button',{res_id:10,button:{type:'object',name:'action_enter'}}),plan,10));
assert(!allows(req('execute_button',{res_id:11,button:{type:'object',name:'action_enter'}}),plan,10));
assert(!allows(req('execute_button',{res_id:10,button:{type:'object',name:'action_delete'}}),plan,10));
assert(!allows(req('api.onchange',{res_id:11}),plan,10));
assert(!allows(req('api.data',{op:'write',ids:[10],values:{note:'safe'},vals:{state:'done'}}),plan,10));
assert(!allows(req('api.data.write',{id:10,values:{note:'safe'},vals:{state:'done'}}),plan,10));
for(const carrier of ['payload','params','data','args']) {
  assert(!allows(req('api.data',{op:'write',ids:[10],[carrier]:{vals:{state:'done'}}}),plan,10));
}
assert(!allows(req('api.data',{op:'create',vals:{name:plan.key},context:{default_state:'done'}}),plan));
assert(!allows({...create,context:{default_state:'done'}},plan));
assert(!allows(req('api.data',{op:'create',vals:{name:plan.key},context:{default_line_ids:[[1,42,{note:'changed'}]]}}),plan));
for(const command of [[1,42,{note:'changed'}],[2,42,0],[3,42,0],[4,42,0],[6,0,[42]]]) {
  assert(!allows(req('api.data',{op:'write',ids:[10],vals:{line_ids:[command]}}),plan,10));
}
const children={...plan,newChildFields:['line_ids']};
assert(allows(req('api.data',{op:'write',ids:[10],vals:{line_ids:[[0,0,{name:'new child'}]]}}),children,10));
assert(!allows(req('api.data',{op:'write',ids:[10],vals:{line_ids:[[1,42,{name:'existing child'}]]}}),children,10));
assert(!allows(req('api.data',{op:'write',ids:[10],vals:{line_ids:[[0,0,{state:'done'}]]}}),children,10));
assert(!allows(req('api.data',{op:'create',vals:{name:plan.key},context:{default_state:'done'}}),{...plan,defaultValues:{default_state:'done'}}));
const emptyAttachments={...plan,emptyRelationFields:['attachment_ids']};
assert(allows(req('api.data',{op:'create',vals:{name:plan.key,attachment_ids:[[6,0,[]]]}}),emptyAttachments));
assert(!allows(req('api.data',{op:'create',vals:{name:plan.key,attachment_ids:[[6,0,[42]]]}}),emptyAttachments));
assert(!allows(req('api.data',{op:'write',ids:[10],vals:{attachment_ids:[[6,0,[]]]}}),emptyAttachments,10));
console.log('35 bounded request-containment assertions passed');

const {validateWalkthroughResume:resume}=await import('./daily_demo_walkthrough_policy.mjs');
const root={runtime:{source_revision:'sha'},plan,recordId:10,responses:[{intent:'api.data',params:create.params,http:200,payload:{ok:true,data:{id:10}}}]};
const latest={...root,responses:[{intent:'execute_button',params:{button:{name:'action_enter'}},payload:{ok:true}}]};
const exitPlan={...plan,actions:[{method:'action_exit'}]};
assert.equal(resume([latest,root],exitPlan,'sha'),10);
assert.throws(()=>resume([latest,root],plan,'sha'),/replay/);
assert.throws(()=>resume([{...latest,pendingMutation:{}},root],exitPlan,'sha'),/Uncertain/);
assert.throws(()=>resume([latest,{...root,recordId:11}],exitPlan,'sha'),/identity/);
assert.throws(()=>resume([latest],exitPlan,'sha'),/creation/);
assert.throws(()=>resume([latest,root],exitPlan,'other'),/identity/);
console.log('resume lineage: 6 assertions PASS');

const approvalPlan={approvalOnly:true,model:'sc.general.contract',key:'DEMO-DELIVERY-20261026-UI01',actions:[{method:'validate_tier'}]};
const approve={intent:'execute_button',params:{model:approvalPlan.model,res_id:7,button:{type:'object',name:'validate_tier'}}};
assert(allows(approve,approvalPlan,7));
assert(!allows(approve,approvalPlan,6));
assert(!allows({...approve,params:{...approve.params,button:{type:'object',name:'action_signed'}}},approvalPlan,7));
assert(!allows({intent:'api.data',params:{model:approvalPlan.model,op:'write',ids:[7],vals:{note:'x'}}},approvalPlan,7));
assert(!allows(approve,{...approvalPlan,key:'old'},7));
console.log('approval-only containment: 5 assertions PASS');

const {validateContractRelayResume:relay}=await import('./daily_demo_walkthrough_policy.mjs');
const seats=[['a',1,'validate_tier'],['b',2,'validate_tier']];
const done={login:'a',method:'validate_tier',actionSucceeded:true,responses:[{...approve,http:200,payload:{ok:true}}]};
const failed={login:'b',method:'validate_tier',responses:[]};
const relayProof={recordId:7,key:approvalPlan.key,runtime:{source_revision:'sha'},status:'STOPPED_NOT_ACCEPTED',actors:[done,failed]};
assert.equal(relay(relayProof,7,approvalPlan.key,'sha',seats),1);
assert.throws(()=>relay({...relayProof,pendingMutation:{}},7,approvalPlan.key,'sha',seats));
assert.throws(()=>relay({...relayProof,actors:[done,{...failed,responses:[approve]}]},7,approvalPlan.key,'sha',seats));
assert.throws(()=>relay({...relayProof,actors:[{...done,login:'b'},failed]},7,approvalPlan.key,'sha',seats));
assert.throws(()=>relay({...relayProof,actors:[{...done,responses:[]},failed]},7,approvalPlan.key,'sha',seats));
console.log('contract relay checkpoint: 5 assertions PASS');
