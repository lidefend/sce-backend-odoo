#!/usr/bin/env node
// Backend exact-instance contract prerequisite for frontend acceptance tools.
//
// The governed contract export (make contract.export_all) is request-construction
// and semantic-regression input only: it strips instance-custody fields and seals
// sha256(contract minus meta), so definition/generation/authority sit outside the
// seal. The complete runtime contract must come from the live ui.contract.v2 read.
// This module consumes that live receipt (acceptance.backend_contract_receipt.v1)
// and fails closed on any missing, stale or mismatched prerequisite.
import fs from 'node:fs';
import { createHash } from 'node:crypto';

export const RECEIPT_SCHEMA = 'acceptance.backend_contract_receipt.v1';
export const DEFAULT_RECEIPT_PATH = 'artifacts/backend/dev_acceptance_release_probe.json';
export const REQUIRED_INTENT = 'ui.contract.v2';

const sha256 = value => createHash('sha256').update(value).digest('hex');

export class CanonicalJsonUnsupported extends Error {}

// Mirrors smart_core.core.contract_lifecycle.canonical_json:
// sort_keys=True, separators=(",", ":"), ensure_ascii=False.
// Python renders floats (1.0 -> "1.0", 1e-05) and ints beyond 2**53 with reprs
// JavaScript cannot reproduce, so this refuses that domain instead of silently
// producing a different digest. Compare with stableJson() when order-insensitive
// structural equality is needed rather than the seal protocol.
export function canonicalJson(value) {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new CanonicalJsonUnsupported('non-finite number');
    if (!Number.isInteger(value)) throw new CanonicalJsonUnsupported(`floating point value ${value}`);
    if (!Number.isSafeInteger(value)) throw new CanonicalJsonUnsupported(`integer beyond 2**53: ${value}`);
    return String(value);
  }
  if (typeof value === 'string') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (typeof value === 'object') {
    const keys = Object.keys(value).filter(key => value[key] !== undefined).sort();
    return `{${keys.map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  throw new CanonicalJsonUnsupported(`unsupported type ${typeof value}`);
}

// Order-insensitive structural equality for request comparison. Uses native
// JSON number rendering, so every JSON value is comparable; never used for the seal.
export function stableJson(value) {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
  if (typeof value === 'object') {
    const keys = Object.keys(value).filter(key => value[key] !== undefined).sort();
    return `{${keys.map(key => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value) ?? 'null';
}

// sha256 over the sealed semantic payload (contract minus meta). Returns '' when
// the contract leaves the mirrored domain, so a caller can never treat an
// unverifiable payload as matching.
export function semanticSha256(contract) {
  if (!contract || typeof contract !== 'object' || Array.isArray(contract)) return '';
  const payload = { ...contract };
  delete payload.meta;
  try {
    return sha256(canonicalJson(payload));
  } catch (error) {
    return '';
  }
}

function positiveInt(value) {
  return Number.isSafeInteger(value) && value > 0 ? value : 0;
}

function text(value) {
  return typeof value === 'string' ? value.trim() : '';
}

export function readContractReceipt(file) {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    return { receipt: null, error: `contract_receipt_unavailable:${error?.code || 'read_error'}` };
  }
  // Accept either the bare receipt or the governed probe report that embeds it.
  const receipt = parsed && typeof parsed === 'object' && parsed.contract && typeof parsed.contract === 'object'
    ? parsed.contract : parsed;
  return { receipt, error: '' };
}

function lifecycleOf(contract) {
  const meta = contract && typeof contract.meta === 'object' && contract.meta ? contract.meta : {};
  return meta.lifecycle && typeof meta.lifecycle === 'object' ? meta.lifecycle : {};
}

// Fail-closed prerequisite evaluation. Returns the approved contract binding the
// caller must execute, or { ok: false, code, detail } identifying the exact gap.
export function contractPrerequisite({ receipt, expectedSha = '', database = '', login = '', roleCode = '', companyName = '' } = {}) {
  const fail = (code, detail = {}) => ({ ok: false, code, detail });
  if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) return fail('contract_receipt_missing');
  if (text(receipt.schema) !== RECEIPT_SCHEMA) return fail('contract_receipt_schema_unknown', { schema: receipt.schema });
  if (receipt.enabled === false) return fail('contract_receipt_disabled');
  if (text(receipt.status) !== 'PASS') return fail('contract_receipt_not_pass', { status: receipt.status });
  if (Array.isArray(receipt.errors) && receipt.errors.length) return fail('contract_receipt_errors', { errors: receipt.errors });

  const required = Array.isArray(receipt.required_checks) ? receipt.required_checks : [];
  const executed = Array.isArray(receipt.executed_checks) ? receipt.executed_checks : [];
  const notRun = Array.isArray(receipt.not_run_checks) ? receipt.not_run_checks : [];
  const checks = receipt.checks && typeof receipt.checks === 'object' ? receipt.checks : {};
  if (!required.length) return fail('contract_receipt_required_checks_missing');
  if (notRun.length) return fail('contract_receipt_checks_not_run', { not_run: notRun });
  if (!executed.length) return fail('contract_receipt_checks_not_executed');
  const failed = required.filter(name => checks[name] !== true);
  if (failed.length) return fail('contract_receipt_checks_failed', { failed });

  const identity = receipt.identity && typeof receipt.identity === 'object' ? receipt.identity : {};
  const servedSha = text(identity.served_sha);
  const receiptExpectedSha = text(identity.expected_sha);
  if (!/^[0-9a-f]{40}$/.test(servedSha) || servedSha !== receiptExpectedSha) {
    return fail('contract_receipt_identity_unbound', { served_sha: servedSha, expected_sha: receiptExpectedSha });
  }
  if (!/^[0-9a-f]{40}$/.test(text(expectedSha))) return fail('contract_receipt_required_sha_missing');
  if (servedSha !== text(expectedSha)) return fail('contract_receipt_stale', { served_sha: servedSha, required_sha: text(expectedSha) });
  const receiptDatabase = text(receipt.request && typeof receipt.request === 'object' ? receipt.request.database : '');
  if (text(database) && receiptDatabase && receiptDatabase !== text(database)) {
    return fail('contract_receipt_database_mismatch', { receipt: receiptDatabase, runtime: text(database) });
  }
  if (text(login) && text(identity.login) !== text(login)) return fail('contract_receipt_login_mismatch', { receipt: text(identity.login), runtime: text(login) });
  if (text(roleCode) && text(identity.role_code) !== text(roleCode)) return fail('contract_receipt_role_mismatch', { receipt: text(identity.role_code), runtime: text(roleCode) });
  if (text(companyName) && text(identity.company_name) !== text(companyName)) return fail('contract_receipt_company_mismatch', { receipt: text(identity.company_name), runtime: text(companyName) });

  const approvedSha = text(receipt.approved_semantic_sha256);
  const recomputedSha = text(receipt.recomputed_semantic_sha256);
  if (!/^[0-9a-f]{64}$/.test(approvedSha) || approvedSha !== recomputedSha) {
    return fail('contract_receipt_semantics_unverified', { approved: approvedSha, recomputed: recomputedSha });
  }
  const asset = receipt.schema_asset && typeof receipt.schema_asset === 'object' ? receipt.schema_asset : {};
  if (!/^[0-9a-f]{64}$/.test(text(asset.sha256)) || text(asset.sha256) !== text(asset.declared_schema_sha256)) {
    return fail('contract_receipt_schema_digest_unbound', { asset: text(asset.sha256), declared: text(asset.declared_schema_sha256) });
  }
  if (Array.isArray(asset.formal_schema_errors) && asset.formal_schema_errors.length) {
    return fail('contract_receipt_schema_invalid', { errors: asset.formal_schema_errors });
  }
  const custody = receipt.custody && typeof receipt.custody === 'object' ? receipt.custody : {};
  if (!/^[0-9a-f]{64}$/.test(text(custody.response_sha256))) return fail('contract_receipt_custody_missing');

  const resolution = receipt.resolution && typeof receipt.resolution === 'object' ? receipt.resolution : {};
  const request = receipt.request && typeof receipt.request === 'object' ? receipt.request : {};
  const params = request.params && typeof request.params === 'object' ? request.params : {};
  const requestContext = request.context && typeof request.context === 'object' && !Array.isArray(request.context) ? request.context : {};
  const model = text(resolution.model);
  const recordId = positiveInt(resolution.record_id);
  const actionId = positiveInt(resolution.action_id);
  const menuId = positiveInt(resolution.menu_id);
  const stableIdentifier = text(resolution.stable_identifier);
  const viewType = text(params.view_type);
  if (text(request.intent) !== REQUIRED_INTENT) return fail('contract_receipt_intent_unexpected', { intent: request.intent });
  if (!text(requestContext.lang) || !text(requestContext.tz)) {
    // The sealed digest is a function of the request context (the projection is
    // localized), so a receipt that does not record it cannot be replayed verbatim.
    return fail('contract_receipt_request_context_missing', { lang: text(requestContext.lang), tz: text(requestContext.tz) });
  }
  if (!model || !recordId || !actionId || !menuId || !stableIdentifier) {
    return fail('contract_receipt_resolution_incomplete', { model, record_id: recordId, action_id: actionId, menu_id: menuId, stable_identifier: stableIdentifier });
  }
  if (positiveInt(params.record_id) !== recordId || positiveInt(params.action_id) !== actionId || positiveInt(params.menu_id) !== menuId || text(params.model) !== model) {
    return fail('contract_receipt_request_target_mismatch', { params });
  }
  if (!viewType) return fail('contract_receipt_view_type_missing');
  const snapshotLifecycle = lifecycleOf(receipt.snapshot);
  const snapshotIntegrity = snapshotLifecycle.integrity && typeof snapshotLifecycle.integrity === 'object' ? snapshotLifecycle.integrity : {};
  if (text(snapshotIntegrity.contractSha256) !== approvedSha) {
    return fail('contract_receipt_snapshot_unsealed', { snapshot: text(snapshotIntegrity.contractSha256), approved: approvedSha });
  }
  const snapshotDefinition = snapshotLifecycle.definition && typeof snapshotLifecycle.definition === 'object' ? snapshotLifecycle.definition : {};
  const snapshotAuthority = snapshotLifecycle.authority && typeof snapshotLifecycle.authority === 'object' ? snapshotLifecycle.authority : {};
  if (!Object.keys(snapshotAuthority).length) return fail('contract_receipt_authority_missing');

  return {
    ok: true,
    approved: {
      model, record_id: recordId, action_id: actionId, menu_id: menuId, view_type: viewType,
      stable_identifier: stableIdentifier,
      route: `/a/${actionId}?menu_id=${menuId}`,
    },
    approvedRequest: { intent: text(request.intent), params, context: requestContext },
    approvedSemanticSha256: approvedSha,
    schemaSha256: text(asset.sha256),
    authority: snapshotAuthority,
    definition: {
      schemaId: text(snapshotDefinition.schemaId),
      schemaVersion: text(snapshotDefinition.schemaVersion),
      schemaSha256: text(snapshotDefinition.schemaSha256),
    },
    identity: { served_sha: servedSha, login: text(identity.login), role_code: text(identity.role_code), company_name: text(identity.company_name), uid: identity.uid },
  };
}

export function assertContractPrerequisite(options = {}) {
  // Throws so callers cannot continue to DOM assertions without the prerequisite.
  if (!options.receipt) throw new Error(`contract prerequisite failed: ${options.loadError || 'contract_receipt_missing'}`);
  const verdict = contractPrerequisite(options);
  if (!verdict.ok) throw new Error(`contract prerequisite failed: ${verdict.code} ${JSON.stringify(verdict.detail)}`);
  return verdict;
}

function sortedUnique(values) {
  return [...new Set((Array.isArray(values) ? values : []).filter(value => typeof value === 'string'))].sort();
}

// Compares the observed live ui.contract.v2 envelope against the approved contract
// on identity, schema/authority and the backend-sealed semantic digest.
export function observedContractBinding({ envelope, receiptRequest = {}, approved, requestParams = {} } = {}) {
  const fail = (code, detail = {}) => ({ ok: false, code, detail });
  const data = envelope && typeof envelope.data === 'object' && envelope.data ? envelope.data : {};
  if (envelope?.ok !== true) return fail('observed_envelope_not_ok', { ok: envelope?.ok });
  const lifecycle = lifecycleOf(data);
  const integrity = lifecycle.integrity && typeof lifecycle.integrity === 'object' ? lifecycle.integrity : {};
  const definition = lifecycle.definition && typeof lifecycle.definition === 'object' ? lifecycle.definition : {};
  const authority = lifecycle.authority && typeof lifecycle.authority === 'object' ? lifecycle.authority : {};
  const pageInfo = data.pageInfo && typeof data.pageInfo === 'object' ? data.pageInfo : {};
  const mainData = data.dataContract && typeof data.dataContract === 'object' ? data.dataContract.mainData : null;
  const observedDigest = text(integrity.contractSha256);
  if (!observedDigest) return fail('observed_contract_unsealed');
  if (text(definition.schemaSha256) !== text(approved.schemaSha256)) {
    return fail('observed_schema_digest_mismatch', { observed: text(definition.schemaSha256), approved: text(approved.schemaSha256) });
  }
  if (text(definition.schemaId) !== text(approved.definition?.schemaId) || text(definition.schemaVersion) !== text(approved.definition?.schemaVersion)) {
    return fail('observed_schema_identity_mismatch', { observed: definition, approved: approved.definition });
  }
  const declared = sortedUnique(approved.authority?.authorities);
  const observed = sortedUnique(authority.authorities);
  if (!declared.length || !observed.length || JSON.stringify(declared) !== JSON.stringify(observed)) {
    return fail('observed_authority_mismatch', { observed, approved: declared });
  }
  if (text(pageInfo.model) !== text(approved.approved?.model) || text(pageInfo.viewType) !== text(approved.approved?.view_type)) {
    return fail('observed_page_identity_mismatch', { model: pageInfo.model, view_type: pageInfo.viewType });
  }
  if (positiveInt(mainData?.id) !== positiveInt(approved.approved?.record_id)) {
    return fail('observed_record_identity_mismatch', { observed: positiveInt(mainData?.id), approved: positiveInt(approved.approved?.record_id) });
  }
  for (const key of ['record_id', 'action_id', 'menu_id']) {
    if (positiveInt(requestParams?.[key]) !== positiveInt(approved.approved?.[key])) {
      return fail('observed_request_target_mismatch', { key, observed: positiveInt(requestParams?.[key]), approved: positiveInt(approved.approved?.[key]) });
    }
  }
  // The approved request must be reproducible under the live actor: a replay of the
  // declared request has to carry the same backend-sealed semantic digest.
  const approvedParams = receiptRequest && typeof receiptRequest === 'object' ? receiptRequest : {};
  const approvedKeys = Object.keys(approvedParams).sort();
  const observedKeys = Object.keys(requestParams || {}).sort();
  const extraParams = observedKeys.filter(key => !approvedKeys.includes(key));
  const missingParams = approvedKeys.filter(key => !observedKeys.includes(key));
  const conflictingParams = approvedKeys.filter(key => observedKeys.includes(key)
    && stableJson(requestParams[key]) !== stableJson(approvedParams[key]));
  if (conflictingParams.length) {
    return fail('observed_request_conflict', { conflicting_params: conflictingParams });
  }
  const exact = !extraParams.length && !missingParams.length
    && approvedKeys.every(key => stableJson(requestParams[key]) === stableJson(approvedParams[key]));
  const sameAsApproved = observedDigest === text(approved.approvedSemanticSha256);
  // The executed contract must reproduce the approved seal whether or not the
  // request is identical: an equal request shape alone is never sufficient, and a
  // wider/narrower request is only acceptable while the sealed semantics match.
  if (!sameAsApproved) {
    return fail('observed_semantics_diverged', { observed: observedDigest, approved: text(approved.approvedSemanticSha256) });
  }
  return { ok: true, observedSemanticSha256: observedDigest, approvedSemanticSha256: text(approved.approvedSemanticSha256),
    request_scope: exact ? 'approved_request_exact' : 'wider_or_narrower_request_semantically_equal',
    exact_approved_request: exact, same_as_approved: sameAsApproved,
    extra_request_params: extraParams, missing_request_params: missingParams, conflicting_request_params: [] };
}
