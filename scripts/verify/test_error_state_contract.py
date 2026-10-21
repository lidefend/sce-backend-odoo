"""Execute the P0 declaration against the generic TS consumer, with mutations."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('error_state_contract', ROOT / 'addons/smart_core/core/error_state_contract.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ErrorStateContractTest(unittest.TestCase):
    def test_public_declaration_is_independent_and_has_unique_selectors(self):
        first = module.build_error_state_contract()
        second = module.build_error_state_contract()
        statuses = [code for row in first['states'] for code in row['statuses']]
        self.assertEqual(len(statuses), len(set(statuses)))
        self.assertIn(first['default_kind'], [row['kind'] for row in first['states']])
        first['states'][0]['title'] = 'changed'
        self.assertNotEqual(first, second)

    def test_component_render_and_recovery_clicks(self):
        subprocess.run(['node', 'scripts/verify/error_state_component_test.cjs'], cwd=ROOT,
                       input=json.dumps(module.build_error_state_contract()), text=True, check=True)

    def test_consumer_uses_changed_declarations_and_rejects_missing_contract(self):
        program = r'''
const fs = require('node:fs');
const assert = require('node:assert/strict');
const ts = require('./frontend/apps/web/node_modules/typescript');
const vm = require('node:vm');
const cache = {};
function load(path) {
 if(cache[path]) return cache[path];
 const source=fs.readFileSync(path,'utf8');
 const module={exports:{}};
 const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const requireLocal=name=>load('frontend/apps/web/src/app/contract/contractGap.ts');
 vm.runInNewContext('(function(require,module,exports){'+code+'\n})',{})(requireLocal,module,module.exports);
 return cache[path]=module.exports;
}
const {resolveProductErrorState,requireErrorStateContract}=load('frontend/apps/web/src/app/productErrorState.ts');
const contract=JSON.parse(fs.readFileSync(0,'utf8'));
for(const row of contract.states) for(const status of row.statuses) {
 assert.equal(resolveProductErrorState({status},contract).kind,row.kind);
}
const changed=structuredClone(contract);
const missing=changed.states.find(row=>row.statuses.includes(404));
missing.title='Renamed by declaration';missing.action.label='Declared return';missing.action.path='/my-work';
const result=resolveProductErrorState({status:404,message:'token=secret'},changed);
assert.equal(result.title,missing.title);assert.equal(result.action.path,'/my-work');
assert.equal(result.action.label,'Declared return');assert.ok(!result.message.includes('secret'));
for(const invalid of [null,{}, {...contract,states:[]}, {...contract,default_kind:'absent'}]) {
 assert.throws(()=>requireErrorStateContract(invalid),error=>error.name==='ContractGapError');
}
const duplicate=structuredClone(contract); duplicate.states[1].statuses.push(401);
assert.throws(()=>requireErrorStateContract(duplicate),error=>error.name==='ContractGapError');
for(const path of ['https://evil.test','//evil.test','/\\evil.test']) {
 const bad=structuredClone(contract);bad.states[0].action.path=path;
 assert.throws(()=>requireErrorStateContract(bad),error=>error.name==='ContractGapError');
}
console.log('error-state declaration/consumer mutations PASS');
'''
        subprocess.run(['node', '-e', program], cwd=ROOT,
                       input=json.dumps(module.build_error_state_contract()), text=True, check=True)


if __name__ == '__main__':
    unittest.main()
