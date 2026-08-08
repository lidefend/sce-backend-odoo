#!/usr/bin/env python3
"""Activate a verified production restore as a persistent, no-egress clone."""
from __future__ import annotations
import argparse, json, os, re, subprocess, time
from pathlib import Path
RESTORE_ID=re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$"); SHA=re.compile(r"^[0-9a-f]{40}$"); IMAGE=re.compile(r"^sha256:[0-9a-f]{64}$")
CONFIRMATION="ACTIVATE_ISOLATED_PRODUCTION_ACCEPTANCE_CLONE"
class CloneRuntimeError(RuntimeError): pass
def run(args,check=True):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False)
 if check and r.returncode: raise CloneRuntimeError((r.stderr.strip().splitlines() or ["command failed"])[-1][:300])
 return r.stdout.strip()
def activate(restore_id,customer_sha,image,port):
 if os.environ.get("CONFIRM_PRODUCTION_ACCEPTANCE_CLONE_RUNTIME")!=CONFIRMATION: raise CloneRuntimeError("exact acceptance clone activation confirmation is required")
 if not RESTORE_ID.fullmatch(restore_id) or not SHA.fullmatch(customer_sha): raise CloneRuntimeError("invalid immutable clone identity")
 if not IMAGE.fullmatch(image) or not 18095<=port<=18120: raise CloneRuntimeError("invalid immutable image or loopback port")
 report=json.loads(Path(f"/data/backups/sc_production/restore-rehearsals/{restore_id}.json").read_text())
 if report.get("status")!="PASS" or report.get("production_database_connected") is not False: raise CloneRuntimeError("verified isolated restore report is required")
 resources=report.get("resources") or {}; db_container,network,filestore=(resources.get(k) for k in ("db_container","network","filestore_volume"))
 if any(not str(v).startswith(restore_id) for v in (db_container,network,filestore)): raise CloneRuntimeError("restore resources escaped the isolated namespace")
 customer_root=Path(f"/opt/sce/customer-addons/acceptance/{customer_sha}")
 if not (customer_root/"sce_customer_baosheng/__manifest__.py").is_file(): raise CloneRuntimeError("immutable customer addon is unavailable")
 rows=run(["docker","inspect",db_container,"--format","{{range .Config.Env}}{{println .}}{{end}}"])
 password=next((r.split("=",1)[1] for r in rows.splitlines() if r.startswith("POSTGRES_PASSWORD=")),"")
 if not password: raise CloneRuntimeError("isolated database credential is unavailable")
 database=f"r10e_{restore_id}"; runtime_root=Path(f"/data/backups/sc_production/acceptance-runtimes/{restore_id}"); runtime_root.mkdir(mode=0o700,parents=True,exist_ok=False)
 config=runtime_root/"odoo.conf"; config.write_text("[options]\naddons_path = /mnt/product-addons,/mnt/customer-addons,/usr/lib/python3/dist-packages/odoo/addons\n"+f"db_host = {db_container}\ndb_port = 5432\ndb_user = odoo\ndb_password = {password}\ndbfilter = ^{database}$\nlist_db = False\nworkers = 0\nmax_cron_threads = 0\nsmtp_server = 127.0.0.1\n"); config.chmod(0o640)
 container=f"{restore_id}_acceptance_odoo"
 run(["docker","run","-d","--name",container,"--network",network,"--publish",f"127.0.0.1:{port}:8069","--group-add","0","--label","sc.production-acceptance-clone=true","-v",f"{filestore}:/var/lib/odoo/filestore","-v",f"{customer_root}:/mnt/customer-addons:ro","-v",f"{config}:/etc/odoo/odoo.conf:ro","--entrypoint","odoo",image,"-c","/etc/odoo/odoo.conf","-d",database])
 for _ in range(60):
  if run(["docker","inspect",container,"--format","{{.State.Running}}|{{.State.ExitCode}}"],False).startswith("true|"): return {"status":"PASS","database":database,"container":container,"loopback_port":port,"exact_dbfilter":True,"customer_sha":customer_sha,"external_egress":False}
  time.sleep(1)
 raise CloneRuntimeError("acceptance clone did not remain running")
def main():
 p=argparse.ArgumentParser(); p.add_argument("--restore-id",required=True); p.add_argument("--customer-sha",required=True); p.add_argument("--image",required=True); p.add_argument("--port",required=True,type=int); a=p.parse_args(); print(json.dumps(activate(a.restore_id,a.customer_sha,a.image,a.port),sort_keys=True))
if __name__=="__main__": main()
