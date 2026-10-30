import assert from 'node:assert';
import { contextOperationAllowed, parseOdooDictLiteral } from '../src/app/actionViewContextPolicy';

// Python dict literal
assert.strictEqual(contextOperationAllowed("{'create': False, 'edit': False, 'delete': False}", 'create'), false);
assert.strictEqual(contextOperationAllowed("{'create': True}", 'create'), true);
// JSON
assert.strictEqual(contextOperationAllowed('{"create": false}', 'create'), false);
// False / 0 / "false"
assert.strictEqual(contextOperationAllowed("{'create': 0}", 'create'), false);
assert.strictEqual(contextOperationAllowed("{'create': 'false'}", 'create'), false);
assert.strictEqual(contextOperationAllowed("{'create': 'False'}", 'create'), false);
// quoted strings with an escaped single quote
assert.strictEqual(contextOperationAllowed(String.raw`{'note': 'it\'s ok', 'create': False}`, 'create'), false);
// nested context: top-level operation flag is authoritative, nested value does not affect it
assert.strictEqual(contextOperationAllowed("{'context': {'create': False}}", 'create'), true);
// malformed context fails closed (must not render a declared read-only operation)
assert.strictEqual(contextOperationAllowed("{'create': False", 'create'), false);
assert.strictEqual(contextOperationAllowed("not a dict", 'create'), false);
// ordinary action without explicit restrictions
assert.strictEqual(contextOperationAllowed('', 'create'), true);
assert.strictEqual(contextOperationAllowed(undefined, 'create'), true);
assert.strictEqual(contextOperationAllowed("{'edit': False}", 'create'), true);

// parseOdooDictLiteral contract
assert.deepStrictEqual(parseOdooDictLiteral("{'a': True, 'b': None}"), { a: true, b: null });
assert.deepStrictEqual(parseOdooDictLiteral(''), {});
assert.strictEqual(parseOdooDictLiteral('{broken'), null);
assert.strictEqual(parseOdooDictLiteral('[]'), null);

console.log('action_view_context_policy_test PASS');
