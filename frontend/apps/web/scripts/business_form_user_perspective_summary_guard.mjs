import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(SCRIPT_DIR, "..", "..", "..", "..");
const ARTIFACT_ROOT = path.join(ROOT_DIR, "artifacts", "playwright", "business-form-user-perspective");
const REPORT_PATH = path.join(ARTIFACT_ROOT, "report.json");
const MIN_CASE_COUNT = 20;

function fail(message, details = {}) {
  const error = new Error(message);
  error.details = details;
  throw error;
}

async function readJson(filePath) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch (err) {
    fail(`cannot read JSON artifact: ${filePath}`, { error: err instanceof Error ? err.message : String(err) });
  }
}

async function isFile(filePath) {
  if (!filePath) return false;
  return fs.stat(filePath).then((stat) => stat.isFile()).catch(() => false);
}

async function main() {
  const report = await readJson(REPORT_PATH);
  const results = Array.isArray(report.results) ? report.results : [];
  const declaredEntryAssertions = Array.isArray(report.declaredEntryAssertions) ? report.declaredEntryAssertions : [];
  const failures = results.filter((row) => row?.ok !== true);
  const screenshotMissing = [];
  for (const row of results) {
    if (!await isFile(row?.screenshotPath)) screenshotMissing.push(row);
  }
  const leaked = results.filter((row) => Array.isArray(row?.leaked) && row.leaked.length > 0);
  const missing = results.filter((row) => Array.isArray(row?.missing) && row.missing.length > 0);
  const undeclared = results.filter((row) => Array.isArray(row?.undeclared) && row.undeclared.length > 0);
  // Consolidated codes cannot capture a create contract for the retired model: the
  // capability is delivered by a declared unified handling entry. They are instead
  // required to consume the carrier's delivered action contract, proven by a
  // non-empty declared baseline action set.
  const contractNotConsumed = results.filter(
    (row) => row?.kind !== "consolidated" && row?.contractCaptured !== true,
  );
  const consolidatedNoDeclaredActions = results.filter(
    (row) => row?.kind === "consolidated" && !(Array.isArray(row?.declaredBaselineVisible) && row.declaredBaselineVisible.length),
  );
  // Locked declaration consumption: a field the delivered contract declares
  // visible+editable for this profile, whose own and every ancestor `invisible`
  // expression resolves false, must be rendered. Once the ground truth reads the
  // unsaved-record sentinel correctly (see createIdentityKinds) this is a hard
  // gate rather than evidence: a field that is declared present but missing from
  // the surface is a real declaration/behaviour split, not a tolerable drift.
  const declaredVisibleNotRendered = results
    .filter((row) => Array.isArray(row?.declaredVisibleNotRendered) && row.declaredVisibleNotRendered.length > 0)
    .map((row) => ({ code: row.code, fields: row.declaredVisibleNotRendered }));
  // Consolidated codes are delivered through a declared unified handling entry, so
  // the standalone create journey cannot exist. Their result must still carry the
  // retired standalone identity and prove it is absent from the governed
  // declaration; a consolidation that silently drifts back in must fail closed.
  const consolidated = results.filter((row) => row?.kind === "consolidated");
  const consolidatedUnbound = consolidated.filter(
    (row) => !String(row?.retired || "").includes("|") || row?.retiredAbsentFromDeclaration !== true,
  );
  const retiredNotAbsent = results.filter(
    (row) => String(row?.retired || "").includes("|") && row?.retiredAbsentFromDeclaration !== true,
  );
  const undeclaredEntry = results.filter((row) => !String(row?.entry || "").includes("|"));
  // A create-profile contract must describe an unsaved record (no id, or Odoo's
  // `NewId_0x...` sentinel). A persisted id means every declaration evaluated
  // against these values is answering a different record, so fail closed.
  const persistedCreateIdentity = results.filter((row) => row?.createRecordIdKind === "persisted");
  const createIdentityKinds = [...new Set(results.filter((row) => row?.kind !== "consolidated").map((row) => String(row?.createRecordIdKind || "<missing>")))].sort();
  // Anti-vacuity: the visible+editable declaration gate only proves anything when
  // a create case actually declares visible editable fields. A run that reported
  // none would satisfy the gate trivially, so it fails closed instead.
  const noDeclaredEditableField = results.filter(
    (row) => row?.kind !== "consolidated" && !(Array.isArray(row?.declaredVisibleEditable) && row.declaredVisibleEditable.length),
  );
  const declarationMismatch = declaredEntryAssertions.filter((row) => row?.ok !== true);
  const consoleErrors = Array.isArray(report.consoleErrors) ? report.consoleErrors : [];

  if (report.ok !== true) fail("business form user perspective report is not ok", { ok: report.ok });
  if (results.length < MIN_CASE_COUNT) fail("business form user perspective case count is too low", { actual: results.length, expected: MIN_CASE_COUNT });
  if (declaredEntryAssertions.length < 1) fail("business form user perspective declared-entry assertions are missing", { actual: declaredEntryAssertions.length });
  if (!Number(report.declaredEntryCount || 0)) fail("business form user perspective did not consume the governed declaration", { declaredEntryCount: report.declaredEntryCount });
  if (undeclaredEntry.length) fail("business form user perspective case is not bound to a declared entry identity", { undeclaredEntry });
  if (createIdentityKinds.some((kind) => kind === "<missing>")) fail("business form user perspective create case did not report its record identity kind", { createIdentityKinds });
  if (persistedCreateIdentity.length) fail("business form user perspective create contract is bound to a persisted record", { persistedCreateIdentity });
  if (noDeclaredEditableField.length) fail("business form user perspective declared no visible editable field to gate", { noDeclaredEditableField });
  if (failures.length) fail("business form user perspective has failed cases", { failures });
  if (consolidatedUnbound.length) fail("business form user perspective consolidated case is not bound to its retired standalone identity", { consolidatedUnbound });
  if (retiredNotAbsent.length) fail("business form user perspective retired standalone entry is still declared", { retiredNotAbsent });
  if (declarationMismatch.length) fail("business form user perspective declared-entry assertion failed", { declarationMismatch });
  if (missing.length) fail("business form user perspective has missing user-facing sections", { missing });
  if (declaredVisibleNotRendered.length) fail("business form user perspective did not render a declared visible editable field", { declaredVisibleNotRendered });
  if (undeclared.length) fail("business form user perspective rendered fields outside the delivered contract", { undeclared });
  if (contractNotConsumed.length) fail("business form user perspective did not consume the delivered create contract", { contractNotConsumed });
  if (consolidatedNoDeclaredActions.length) fail("business form user perspective consolidated case did not consume the delivered carrier action contract", { consolidatedNoDeclaredActions });
  if (leaked.length) fail("business form user perspective leaked forbidden technical/source text", { leaked });
  if (screenshotMissing.length) fail("business form user perspective screenshot evidence missing", { screenshotMissing });
  if (consoleErrors.length) fail("business form user perspective has console errors", { consoleErrors });

  console.log(JSON.stringify({
    ok: true,
    reportPath: REPORT_PATH,
    caseCount: results.length,
    declaredEntryCount: report.declaredEntryCount,
    declaredEntryAssertions: declaredEntryAssertions.length,
    failures: failures.length,
    missing: missing.length,
    undeclared: undeclared.length,
    declaredVisibleNotRendered,
    createIdentityKinds,
    declaredEditableCases: results.filter((row) => row?.kind !== "consolidated" && Array.isArray(row?.declaredVisibleEditable) && row.declaredVisibleEditable.length).length,
    consolidated: consolidated.length,
    consolidatedUnbound: consolidatedUnbound.length,
    leaked: leaked.length,
    consoleErrors: consoleErrors.length,
  }, null, 2));
}

main().catch((err) => {
  console.error(JSON.stringify({
    ok: false,
    message: err instanceof Error ? err.message : String(err),
    details: err?.details || {},
  }, null, 2));
  process.exit(1);
});
