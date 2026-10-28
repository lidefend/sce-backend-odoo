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
(OUT/'authentication-status.json').write_text(json.dumps({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'http_status':status,'application_ok':body.get('ok'),'user_id':body.get('data',{}).get('user',{}).get('id'),'secrets_persisted':False},indent=2)+'\n')
del password,payload,body
if not token:raise SystemExit('Authentication blocked; safe status saved')
r=subprocess.run(['node',str(OUT/'probe.mjs')],input=json.dumps({'token':token}),text=True,capture_output=True)
del token
print(r.stdout)
if r.returncode:print('Browser probe failed; safe partial measurements retained')
raise SystemExit(r.returncode)
