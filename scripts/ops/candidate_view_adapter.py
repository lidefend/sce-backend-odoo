"""P4 candidate-view admission and bounded transaction protocol.

The CLI is offline. There is deliberately no runtime driver registered until a
clone/recovery receipt provider has been independently reviewed. JSON can never
install a driver or grant write authority. No shell, credentials or DB connector.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import UUID
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'docs/ops/iterations/fe-presentation-convergence-01/payment-list-create/payment-list-create-07-scope-contract.json'
SOURCE = 'addons/smart_construction_core/views/support/user_confirmed_formal_list_views.xml'
XMLID = 'smart_construction_core.view_payment_request_formal_payment_apply_tree'
SHA = re.compile(r'[0-9a-f]{40}')
DIGEST = re.compile(r'[0-9a-f]{64}')
# No current clone has an approved runtime/recovery integration. This is code
# authority, not a request flag or import path controlled by the caller.
RUNTIME_DRIVERS = {}


class Refused(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Refused(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def exact(obj, keys, label):
    require(isinstance(obj, dict) and set(obj) == set(keys.split()), label + ': missing/unknown fields')


def full(value, regex, label):
    require(isinstance(value, str) and regex.fullmatch(value), label + ': invalid identity')


def positive(value, label):
    require(type(value) is int and value > 0, label + ': invalid ID')


def uuid(value):
    try:
        require(isinstance(value, str) and str(UUID(value)) == value, 'invalid UUID')
    except (ValueError, AttributeError):
        raise Refused('invalid UUID') from None


def parse_xml(raw):
    require(isinstance(raw, bytes) and b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw, 'unsafe XML')
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        raise Refused('invalid XML') from None


def tree_shape(node):
    return [node.tag, sorted(node.attrib.items()), (node.text or '').strip(),
            (node.tail or '').strip(), [tree_shape(child) for child in node]]


def read_candidate(repo, sha, path):
    # Fixed tracked source only; no checkout and no execution of candidate code.
    full(sha, SHA, 'candidate SHA')
    require(path == SOURCE, 'source path outside scope')
    result = subprocess.run(['git', '-C', str(repo), 'show', sha + ':' + path],
                            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, 'candidate source unavailable')
    return result.stdout


def validate_request(req):
    exact(req, 'schema candidate snapshot target view effects', 'request')
    require(req['schema'] == 'candidate_view_request.v1', 'unsupported request version')
    c = req['candidate']
    exact(c, 'sha image frontend_sha256 xml_sha256', 'candidate')
    full(c['sha'], SHA, 'candidate SHA')
    require(isinstance(c['image'], str) and re.fullmatch(
        r'ghcr\.io/lidefend/sce-product@sha256:[0-9a-f]{64}', c['image']), 'immutable image required')
    for key in ('frontend_sha256', 'xml_sha256'):
        full(c[key], DIGEST, key)
    s = req['snapshot']
    exact(s, 'source_database source_uuid source_sha database_sha256 filestore_sha256 manifest_sha256', 'snapshot')
    require(isinstance(s['source_database'], str) and re.fullmatch(r'[a-z][a-z0-9_]+', s['source_database']), 'invalid source database')
    uuid(s['source_uuid']); full(s['source_sha'], SHA, 'snapshot source SHA')
    for key in ('database_sha256', 'filestore_sha256', 'manifest_sha256'):
        full(s[key], DIGEST, key)
    t = req['target']
    exact(t, 'registration_id database uuid runtime_sha image frontend_sha256', 'target')
    require(isinstance(t['registration_id'], str) and re.fullmatch(r'candidate-view-[a-z0-9-]+', t['registration_id']), 'invalid registration')
    require(isinstance(t['database'], str) and re.fullmatch(r'sc_candidate_view_[a-z0-9_]+', t['database']), 'not a disposable candidate database')
    uuid(t['uuid'])
    require(t['uuid'] != s['source_uuid'] and t['database'] != s['source_database'], 'source/target identity collision')
    require((t['runtime_sha'], t['image'], t['frontend_sha256']) == (c['sha'], c['image'], c['frontend_sha256']), 'candidate/runtime identity mismatch')
    v = req['view']
    exact(v, 'xmlid id original_arch original_sha256 expected_after_state_sha256', 'view')
    require(v['xmlid'] == XMLID, 'view outside scope'); positive(v['id'], 'view')
    require(isinstance(v['original_arch'], str), 'original arch required')
    full(v['original_sha256'], DIGEST, 'original arch hash')
    require(digest(v['original_arch'].encode()) == v['original_sha256'], 'original arch hash mismatch')
    full(v['expected_after_state_sha256'], DIGEST, 'expected post-state')
    exact(req['effects'], 'before_state_sha256 recovery_receipt_sha256', 'effects')
    for value in req['effects'].values():
        full(value, DIGEST, 'effects digest')


def build_plan(req, raw):
    validate_request(req)
    require(digest(raw) == req['candidate']['xml_sha256'], 'candidate XML digest mismatch')
    root = parse_xml(raw)
    rows = [r for r in root.iter('record') if r.get('id') == XMLID.split('.')[1]]
    require(len(rows) == 1 and rows[0].get('model') == 'ir.ui.view', 'missing/ambiguous source occurrence')
    fields = rows[0].findall("field[@name='arch']")
    require(len(fields) == 1 and len(fields[0]) == 1, 'ambiguous source arch')
    new = fields[0][0]
    require(new.tag == 'tree' and all(new.get(k) == v for k, v in
        {'create':'true', 'edit':'false', 'delete':'false'}.items()), 'invalid candidate list capability')
    old = parse_xml(req['view']['original_arch'].encode())
    require(old.tag == 'tree' and old.get('create') == 'false', 'unexpected original declaration')
    old.set('create', 'true')
    require(tree_shape(old) == tree_shape(new), 'change exceeds create attribute')
    arch = ET.tostring(new, encoding='unicode')
    return {'schema':'candidate_view_plan.v1', 'request':req,
            'request_sha256':canonical_hash(req), 'arch':arch, 'arch_sha256':digest(arch.encode()),
            'status':'offline_plan_only', 'write_authorized':False}


def execute(plan, driver):
    """Internal protocol for a future trusted driver, tested with an in-memory port.

    Driver must lock exclusive disposable resources, re-read identities, use ORM
    (including its normal side effects), and produce complete state witnesses.
    Not a public driver injection or a live database implementation.
    """
    req = plan['request']
    validate_request(req)
    require(plan == build_plan(req, driver.source_bytes()), 'plan/source mismatch')
    require(plan['request_sha256'] == canonical_hash(req), 'plan changed')
    require(plan['arch_sha256'] == digest(plan['arch'].encode()), 'plan arch changed')
    # Revalidate actual leaf; hash supplied by a caller is never authority.
    old = parse_xml(req['view']['original_arch'].encode()); old.set('create', 'true')
    require(tree_shape(old) == tree_shape(parse_xml(plan['arch'].encode())), 'plan exceeds scope')
    with driver.exclusive():
        require(driver.registration() == req['target'], 'unregistered/drifted target')
        require(driver.recovery_binding() == {'request_sha256':plan['request_sha256'],
            'receipt_sha256':req['effects']['recovery_receipt_sha256']}, 'recovery not proven for exact scope')
        before = driver.snapshot()
        exact(before, 'target snapshot view_matches view_arch arch_prev view_metadata queue assets cache_state business_digest other_views_digest form_binding', 'state witness')
        require(canonical_hash(before) == req['effects']['before_state_sha256'], 'pre-write drift')
        require(before['target'] == req['target'] and before['snapshot'] == req['snapshot'], 'runtime/source mismatch')
        require(before['view_matches'] == [req['view']['id']], 'view identity not unique')
        require(before['view_arch'] == req['view']['original_arch'], 'original arch drift')
        try:
            driver.orm_write(req['view']['id'], {'arch_db':plan['arch']})
            after = driver.snapshot()
            exact(after, 'target snapshot view_matches view_arch arch_prev view_metadata queue assets cache_state business_digest other_views_digest form_binding', 'post-state witness')
            require(after['target'] == before['target'] and after['snapshot'] == before['snapshot'], 'identity changed')
            require(after['business_digest'] == before['business_digest'], 'business data changed')
            require(after['other_views_digest'] == before['other_views_digest'], 'non-target view changed')
            require(after['form_binding'] == before['form_binding'], 'form/context changed')
            require(after['view_matches'] == before['view_matches'] and after['view_arch'] == plan['arch'], 'view readback mismatch')
            require(canonical_hash(after) == req['view']['expected_after_state_sha256'], 'side-effect scope exceeded')
            driver.commit()
        except BaseException:
            driver.rollback()
            driver.quarantine()  # rollback does not restore process caches
            raise
        return {'schema':'candidate_view_result.v1', 'request_sha256':plan['request_sha256'],
                'candidate':req['candidate'], 'snapshot':req['snapshot'], 'target':req['target'],
                'view':{'xmlid':XMLID, 'id':req['view']['id'], 'before_sha256':req['view']['original_sha256'],
                        'after_sha256':plan['arch_sha256']}, 'before':before, 'after':after,
                'browser_acceptance':'not_run', 'business_save':'not_authorized'}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('plan', 'apply'))
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--repository', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        req = json.loads(args.request.read_text())
        validate_request(req)
        scope = json.loads(CONTRACT.read_text())
        require(scope.get('schema') == 'candidate_view_scope.v1' and
                scope.get('source_path') == SOURCE and scope.get('xmlid') == XMLID, 'scope contract mismatch')
        require(scope.get('registered_targets') == [] and scope.get('runtime_driver_supported') is False,
                'scope contract cannot enable runtime driver')
        raw = read_candidate(args.repository, req['candidate']['sha'], SOURCE)
        plan = build_plan(req, raw)
        if args.action == 'apply':
            # Never accept a caller-provided driver, receipt boolean or arbitrary
            # Python module. No remote commands are reachable in this release.
            require(req['target']['registration_id'] in RUNTIME_DRIVERS,
                    'runtime_driver_not_supported: no approved clone/recovery provider; zero writes')
            raise Refused('runtime execution requires separate reviewed integration')
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
        return 0
    except (Refused, ValueError, OSError) as error:
        print(json.dumps({'status':'refused', 'reason':str(error), 'write_attempted':False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
