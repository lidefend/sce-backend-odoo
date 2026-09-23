"""Read-only exact-object public exposure audit. Never emits matching secret values."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/ci'))
import secret_scan
import personal_data_scan


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.PIPE)


def audit(candidate, refs):
    if len(candidate) != 40 or any(c not in '0123456789abcdef' for c in candidate):
        raise ValueError('full candidate SHA required')
    remote = sorted({line.split()[0] for line in refs.splitlines() if line.strip()})
    if not remote: raise ValueError('empty remote ref observation')
    for sha in [candidate, *remote]:
        git('cat-file', '-e', sha+'^{commit}')  # Missing objects fail closed.
    commits = git('rev-list', '--reverse', candidate, '--not', *remote).decode().splitlines()
    objects = git('rev-list', '--objects', '--no-object-names', candidate, '--not', *remote).decode().splitlines()
    metadata = subprocess.check_output(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'], input=('\n'.join(objects)+'\n').encode(),cwd=ROOT).decode() if objects else ''
    blobs = {line.split()[0]:int(line.split()[2]) for line in metadata.splitlines() if line.split()[1]=='blob'}
    paths = {sha:set() for sha in blobs}
    head_paths = set()
    for rev in dict.fromkeys([candidate,*commits]):
        for entry in git('ls-tree','-rz',rev).split(b'\0'):
            if not entry: continue
            meta,path=entry.split(b'\t',1); fields=meta.split()
            name=path.decode('utf-8','surrogateescape')
            if rev==candidate: head_paths.add(name)
            sha=fields[2].decode()
            if sha in paths: paths[sha].add(name)
    known,_,catalog=secret_scan.load_legacy_catalog()
    normal_ids={e["id"] for e in catalog["fingerprints"]+catalog["confirmed_history_fingerprints"] if e.get("disposition")=="NORMAL_TEXT"}
    exceptions=personal_data_scan.load_false_positives()
    content=[];findings=[];personal=[];restricted=[];unparsed=[];normal_text=[];customer_refs=[]
    commit_content=[]
    for commit in commits:
        data=git("cat-file","commit",commit)
        hits={f.rule for line in data.decode("utf-8",errors="replace").splitlines() for f in secret_scan.scan_line(line)}
        if hits: findings.append({"commit":commit,"paths":[],"rules":sorted(hits)})
        commit_content.append({"commit":commit,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)})
    for sha,size in blobs.items():
        data=git('cat-file','blob',sha)
        if len(data)!=size: raise ValueError('blob size mismatch')
        names=sorted(paths[sha])
        try: text=data.decode('utf-8');binary='\x00' in text
        except UnicodeDecodeError: text=data.decode('latin1');binary=True
        # Scan every byte-bearing object irrespective of extension or deletion.
        hits=set()
        for line in text.splitlines(): hits.update(f.rule for f in secret_scan.scan_line(line))
        for f in secret_scan.scan_legacy_text(text,sha,known):
            if f.fingerprint_id in normal_ids:
                normal_text.append({'blob':sha,'paths':names,'catalog_id':f.fingerprint_id,'disposition':'NORMAL_TEXT'})
            else: hits.add('known_legacy_credential:'+f.fingerprint_id)
        if re.search(r'baosheng|宝盛|保胜',text,re.I):
            customer_refs.append({'blob':sha,'paths':names,'classification':'named_customer_reference_requires_public_authorization_review','public_authorization':'not_established'})
        if hits:findings.append({'blob':sha,'paths':names,'rules':sorted(hits),'classification':'requires_secret_triage_no_values_recorded'})
        for name in names:
            for f in personal_data_scan.scan_text(text,name,sha):
                key=(f.rule_id,f.path,f.blob_id,f.classification)
                if key not in exceptions: personal.append({'blob':sha,**f.public_metadata()})
        restricted_names=[n for n in names if any(x in n.lower() for x in ['customer_addons/','baosheng','宝盛','保胜','legacy-source','legacy_source'])]
        if restricted_names:
            restricted.append({'blob':sha,'paths':restricted_names,'owner':'customer/project owner; exact rights not established','public_authorization':'not_found_in_available_evidence'})
        if binary:unparsed.append({'blob':sha,'paths':names,'reason':'raw-byte secret scan performed; binary/archive semantics require content-specific review'})
        content.append({'blob':sha,'sha256':hashlib.sha256(data).hexdigest(),'bytes':size,'paths':names,'paths_absent_at_candidate':[n for n in names if n not in head_paths],'binary':binary})
    return {'candidate':candidate,'remote_refs_sha256':hashlib.sha256(refs.encode()).hexdigest(),'remote_refs':refs.splitlines(),'new_commits':commits,'new_blob_count':len(blobs),'new_contents':content,'commit_contents':commit_content,'normal_text_catalog_matches':normal_text,'customer_reference_review':customer_refs,'scanner_source_sha256':digest_source(),'secret_findings':findings,'personal_data_findings':personal,'restricted_asset_candidates':restricted,'binary_review_pending':unparsed,'secret_values_recorded':False,'scope':'all novel reachable blobs including intermediate/deleted versions and all novel commit metadata; no size or suffix skips','publication':'blocked' if findings or personal or restricted or unparsed or customer_refs else 'content_patterns_clear_authorization_still_required'}


def digest_source():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/"scripts/ci/secret_scan.py",ROOT/"scripts/ci/personal_data_scan.py",ROOT/"config/security/legacy_credential_fingerprints.json",ROOT/"scripts/ci/personal_data_false_positives.json"]}


def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--refs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit(a.candidate,a.refs.read_text());a.output.write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in result.items() if k in ['candidate','new_commits','new_blob_count','secret_findings','personal_data_findings','restricted_asset_candidates','binary_review_pending','publication']}))

if __name__=='__main__': main()
