"""Bounded read-only HTTP/test transaction prerequisites. Never print credentials."""
import inspect
import hashlib
import json
import os

from odoo import sql_db
from odoo.modules.registry import Registry
from odoo.addons.smart_core.security.namespace_resolver import (
    _config, SHARED_SECRET_PARAM, SHARED_SECRET_ENV, ROUTE_VERSION_PARAM, ROUTE_VERSION_ENV,
)

assert env.cr.dbname == 'sc_dev_demo'
env.cr.rollback()
env.cr.execute('SET TRANSACTION READ ONLY')
try:
    namespace = env['sc.platform.namespace'].sudo().search([('database_name', '=', env.cr.dbname)])
    secret = os.getenv('SC_JWT_SECRET') or os.getenv('JWT_SECRET') or env['ir.config_parameter'].sudo().get_param('sc.jwt.secret') or ''
    print('AUTH01_HTTP_PREREQUISITES=' + json.dumps({
        'database': env.cr.dbname, 'namespace_count': len(namespace),
        'suite_alias_count': env['sc.platform.namespace.alias'].sudo().search_count([('alias', '=', 'suite-entry')]),
        'config_fingerprint': hashlib.sha256(json.dumps([
            _config(env, SHARED_SECRET_PARAM, SHARED_SECRET_ENV),
            _config(env, ROUTE_VERSION_PARAM, ROUTE_VERSION_ENV), secret,
        ]).encode()).hexdigest(),
        'active_alias_count': sum(bool(row.primary_alias) and row.lifecycle_state == 'active' for row in namespace),
        'entry_secret_present': bool(_config(env, SHARED_SECRET_PARAM, SHARED_SECRET_ENV)),
        'route_version_present': bool(_config(env, ROUTE_VERSION_PARAM, ROUTE_VERSION_ENV)),
        'jwt_secret_minimum_length_met': len(secret.encode()) >= 32,
    }))
    print('AUTH01_REGISTRY_CURSOR_SOURCE=' + inspect.getsource(Registry.cursor))
    print('AUTH01_TEST_CURSOR_COMMIT_SOURCE=' + inspect.getsource(sql_db.TestCursor.commit))
finally:
    env.cr.rollback()
