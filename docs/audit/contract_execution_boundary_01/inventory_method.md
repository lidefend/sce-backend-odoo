# E1 源码清单重现方法

在基线 `0d17e91e7190e1a293e4e6ac969c39738a87218f` 或源码未变化的文档候选上，将下方代码保存到仓库内临时 `.cjs` 文件并从根目录执行 `node <file>`。使用仓库已经安装的 TypeScript；不安装依赖、不访问服务或数据库。输出位于同目录的 e1_source_inventory.json。

这是只读源码盘点方法，不是生产工具或验证门禁。扫描所有跟踪的 web src/packages TS/JS/Vue script；不解析 Vue template，不推断动态回调的实际运行事实。模块闭包是保守近似。

```javascript
// Read-only source inventory. Run from repository root with installed frontend TypeScript.
const fs=require('fs'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const ts=require(require.resolve('typescript',{paths:[path.resolve('frontend/apps/web')]}));
const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
const tracked=cp.execFileSync('git',['ls-files'],{encoding:'utf8'}).trim().split('\n');
const files=tracked.filter(p=>/^frontend\/(apps\/web\/src|packages)\//.test(p)&&/\.(ts|tsx|js|vue)$/.test(p));
const sourceSet=new Set(files), calls=[], imports=[], intents=[], manifest=[], diagnostics=[];
const transport=new Set(['intentRequest','intentRequestRaw','apiRequest','apiRequestRaw','apiRequestRawUncoalesced','fetch','sendBeacon','XMLHttpRequest','WebSocket','EventSource']);
const apiNames=new Set();
for(const p of files.filter(p=>p.startsWith('frontend/apps/web/src/api/'))){
 const s=fs.readFileSync(p,'utf8'); for(const m of s.matchAll(/export\s+(?:async\s+)?function\s+(\w+)/g))apiNames.add(m[1]);
}
function resolve(from,spec){if(!spec.startsWith('.'))return null;const p=path.posix.normalize(path.posix.join(path.posix.dirname(from),spec));return [p,p+'.ts',p+'.tsx',p+'.js',p+'.vue',p+'/index.ts'].find(p=>sourceSet.has(p))||null;}
for(const p of files){
 const original=fs.readFileSync(p,'utf8');manifest.push({path:p,sha256:sha(original)});
 let code=original;
 if(p.endsWith('.vue')){let chars=original.split('').map(c=>c==='\n'?'\n':' ');for(const m of original.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\s*>/g)){const start=m.index+m[0].indexOf('>')+1;for(let i=0;i<m[1].length;i++)chars[start+i]=m[1][i];}code=chars.join('');}
 const sf=ts.createSourceFile(p,code,ts.ScriptTarget.Latest,true,p.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
 for(const d of sf.parseDiagnostics)diagnostics.push({path:p,start:d.start,message:ts.flattenDiagnosticMessageText(d.messageText,' ')});
 const bindings=new Map();
 for(const node of sf.statements){
  if(!ts.isImportDeclaration(node)||!ts.isStringLiteral(node.moduleSpecifier))continue;
  const spec=node.moduleSpecifier.text,resolved=resolve(p,spec),cl=node.importClause;
  const names=[];if(cl?.name)names.push([cl.name.text,'default']);
  if(cl?.namedBindings){if(ts.isNamedImports(cl.namedBindings))for(const e of cl.namedBindings.elements)names.push([e.name.text,e.propertyName?.text||e.name.text]);else names.push([cl.namedBindings.name.text,'*']);}
  for(const [local,exported]of names)bindings.set(local,{spec,resolved,exported});
  imports.push({from:p,spec,resolved,type_only:!!cl?.isTypeOnly});
 }
 function visit(n){
  if(ts.isPropertyAssignment(n)&&n.name.getText(sf).replace(/['"]/g,'')==='intent'){
   intents.push({path:p,line:sf.getLineAndCharacterOfPosition(n.getStart(sf)).line+1,value:ts.isStringLiteral(n.initializer)?n.initializer.text:null,dynamic:!ts.isStringLiteral(n.initializer)});
  }
  if(ts.isCallExpression(n)||ts.isNewExpression(n)){
   const e=n.expression,leaf=ts.isIdentifier(e)?e.text:ts.isPropertyAccessExpression(e)?e.name.text:null;
   const b=leaf?bindings.get(leaf):null;
   const alias=b?.exported;
   let kind=transport.has(alias||leaf)?'transport_named_call':b?.resolved?.startsWith('frontend/apps/web/src/api/')?'api_import_call':apiNames.has(leaf)?'api_name_callback_candidate':['executeSceneMutation','loadActionContractV2','loadModelContractV2'].includes(leaf)?'contract_runtime_call':null;
   if(!kind && e.getText(sf).length<180 && [...transport,...apiNames].some(x=>new RegExp('\\b'+x+'\\b').test(e.getText(sf))))kind='indirect_api_expression_candidate';
   if(kind){let owner=n.parent;while(owner&&!ts.isFunctionLike(owner))owner=owner.parent;
    calls.push({path:p,line:sf.getLineAndCharacterOfPosition(n.getStart(sf)).line+1,callee:e.getText(sf),kind,import_source:b?.resolved||b?.spec||null,owner:owner?.name?.getText(sf)||'<callback-or-module>',execution_proven:false});}
  }
  ts.forEachChild(n,visit);
 }visit(sf);
}
const affected=new Set(calls.map(x=>x.path));let change=true;while(change){change=false;for(const i of imports)if(i.resolved&&affected.has(i.resolved)&&!i.type_only&&!affected.has(i.from)){affected.add(i.from);change=true;}}
const backend=tracked.filter(p=>p.startsWith('addons/smart_core/')&&/\.(py)$/.test(p)&&/(handlers\/|controllers\/intent|core\/(intent|scene_ready|unified_page_contract)|utils\/.*(cache|idempotency))/.test(p)).map(p=>({path:p,sha256:sha(fs.readFileSync(p))}));
const result={baseline:cp.execFileSync('git',['rev-parse','origin/main'],{encoding:'utf8'}).trim(),status:'STATIC_INVENTORY_NOT_RUNTIME_PROOF',method:'TypeScript AST of all tracked web src and package TS/JS/Vue scripts; API names and relative module import reverse closure. Backend manifest is authority entrypoint inventory, not AST reachability.',limitations:['Vue template expressions are not AST-parsed; injected callbacks, runtime-generated intents, namespace aliases and external packages require manual tracing.','Module reverse closure is an overapproximation, not proof of execution or HTTP count.','Literal intent assignments include declarations; they are not necessarily request sites.','No browser or server execution; removable requests and performance benefit are NOT_VERIFIED.'],summary:{frontend_files:files.length,backend_authority_files:backend.length,request_candidate_sites:calls.length,literal_intent_declarations:intents.filter(x=>!x.dynamic).length,dynamic_intent_declarations:intents.filter(x=>x.dynamic).length,request_reachable_module_candidates:affected.size,parse_diagnostics:diagnostics.length},files:manifest,backend_authority_files:backend,request_candidate_sites:calls,intent_declarations:intents,imports,request_reachable_modules:[...affected].sort(),parse_diagnostics:diagnostics};
fs.writeFileSync('docs/audit/contract_execution_boundary_01/e1_source_inventory.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result.summary));
```
