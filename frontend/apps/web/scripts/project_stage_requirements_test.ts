import assert from 'node:assert/strict';
import { decodeStageRequirements } from '../src/api/projectStageRequirements';
import { buildContractFormActions } from '../src/pages/contractForm/contractActionPresentation';
import { buildFormActionExecutionPlan } from '../src/pages/contractForm/actionExecutionPlan';
const payload = {title:'Requirements',project:{id:17,name:'A'},stage:{value:'done',label:'Done'},labels:{project:'Project',stage:'Stage',required:'Required',optional:'Optional',done:'Done',pending:'Pending',empty:'Empty',back:'Back'},items:[{title:'Check',required:true,done:false}],return_path:'/r/project.project/17'};
let count=0;
assert.equal(decodeStageRequirements(payload,17).items.length,1);count++;
assert.deepEqual(decodeStageRequirements({...payload,items:[]},17).items,[]);count++;
for(const invalid of [{...payload,project:{id:18,name:'B'}},{...payload,items:null},{...payload,items:[{title:'X',required:'yes',done:false}]},{...payload,labels:{}},{...payload,return_path:'//external.test'},{...payload,stage:{value:'done'}}]){assert.throws(()=>decodeStageRequirements(invalid,17));count++;}
const actions=buildContractFormActions({model:'project.project',recordId:17,renderProfile:'edit',sceneReadyActions:[],v2ButtonStatus:{stage:{visible:true,disabled:false,backendIdentity:"stage-binding"}},v2ActionRuleList:[{actionId:'action.stage',actionKey:'action_view_stage_requirements',label:'Requirements',triggerType:'click',sourceWidgetId:'stage',button:{},intent:'open',target:{url:'/project-stage-requirements/17',target:'self'},backendIdentity:'stage-binding',allowed:true,enabled:true,disabled:false,entitlementEvaluated:true,authorizationAllowed:true,presentation:{tier:'primary'},actionSafety:{classification:'safe',requires_confirm:false,reason_code:'SAFE_NAVIGATION_ACTION'}}]});
assert.equal(actions.length,1);count++;
const plan=buildFormActionExecutionPlan({action:actions[0],modelName:'project.project',recordId:17});
assert.equal(plan.kind,'open_url');count++;
if(plan.kind==='open_url'){assert.equal(plan.url,'/project-stage-requirements/17');count++;}
console.log(`project stage requirements: ${count} assertions passed`);
