"""Reuse the reviewed API-02R login flow; password stays in hidden input, token in a process pipe."""
import getpass,json,subprocess,sys,urllib.request,datetime
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
sys.path.insert(0,str(ROOT/'scripts/verify'))
from python_http_smoke_utils import build_intent_url,assert_entry_request,extract_login_token,_request_json
password=getpass.getpass('Demo password (hidden): ')
url=build_intent_url('http://1.95.85.92:18081/t/demo')
payload={'intent':'login','params':{'login':'wutao','password':password,'contract_mode':'default'}}
headers={'Content-Type':'application/json','X-Anonymous-Intent':'1','x-tenant':'default'}
assert_entry_request(url,payload,headers)
status,body,_=_request_json(urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method='POST'),retries=1)
token=extract_login_token(body)
if not token:raise SystemExit('Authentication failed')
del password,payload,body
payload={'intent':'chatter.timeline','params':{'model':'project.project','res_id':15,'offset':0,'include_audit':True,'context':{'company_id':1}},'context':{'company_id':1}}
status,body,_=_request_json(urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'x-tenant':'default'},method='POST'),retries=1)
del token
items=body.get('data',{}).get('items',[])
projection={'task':'FEPC-09','purpose':'Fill previously omitted message author/body fields only; no new records or pagination','time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request':payload,'http_status':status,'application_ok':body.get('ok'),'messages':[{'key':x.get('key'),'typeLabel':x.get('typeLabel'),'body':x.get('body'),'at':x.get('at'),'author_name':x.get('message',{}).get('author_name')} for x in items if x.get('type')=='message']}
(OUT/'message-author-evidence.json').write_text(json.dumps(projection,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'http_status':status,'application_ok':body.get('ok'),'message_count':len(projection['messages'])}))
