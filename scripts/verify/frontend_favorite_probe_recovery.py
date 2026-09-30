"""One-off recovery of the intercepted-request probe, never a general cleanup tool."""
import json

EXPECTED = dict(id=8, name='仅检查表单，不保存', user_id=30,
                model_id='payment.request', action_id=775,
                create_date='2026-09-30 11:11:30.981759', is_default=False)


def validate_target(database, row):
    if database != 'sc_frontend_acceptance' or row != EXPECTED:
        raise RuntimeError('DENY: exact probe object/database mismatch')


def recover(env):
    if env.cr.dbname != 'sc_frontend_acceptance':
        raise RuntimeError('DENY: wrong database')
    user = env['res.users'].sudo().browse(30).exists()
    if not user or user.login != 'fixture_role_finance':
        raise RuntimeError('DENY: fixture actor mismatch')
    record = env['ir.filters'].sudo().browse(EXPECTED['id']).exists()
    if not record:
        print(json.dumps({'status': 'already_absent', 'id': EXPECTED['id']}))
        return
    row = dict(id=record.id, name=record.name, user_id=record.user_id.id,
               model_id=record.model_id, action_id=record.action_id.id,
               create_date=str(record.create_date), is_default=record.is_default)
    print(json.dumps({'before': row}, ensure_ascii=False))
    validate_target(env.cr.dbname, row)
    record.unlink()
    assert not env['ir.filters'].sudo().browse(EXPECTED['id']).exists()
    env.cr.commit()
    env.invalidate_all()
    assert not env['ir.filters'].sudo().browse(EXPECTED['id']).exists()
    print(json.dumps({'status': 'restored', 'id': EXPECTED['id'], 'remaining': 0}))


if 'env' in globals():
    recover(env)
