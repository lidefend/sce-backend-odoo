import fs from "node:fs/promises";

const REPORT_PATH = process.env.USER_VISIBLE_SURFACE_REPORT || "/tmp/user_page_visual_coverage.json";

function fail(message, details = {}) {
  const error = new Error(message);
  error.details = details;
  throw error;
}

async function main() {
  const report = JSON.parse(await fs.readFile(REPORT_PATH, "utf8"));
  const summary = report?.summary || {};
  const actionResults = Array.isArray(report?.actionResults) ? report.actionResults : [];
  const actionFailures = actionResults.filter((row) => row?.ok !== true);
  const consoleErrors = Array.isArray(report?.consoleErrors) ? report.consoleErrors : [];

  const discovered = Number(summary.totalDiscovered || 0);
  const scanned = Number(summary.totalScanned || 0);
  const actionOk = Number(summary.actionOk || 0);
  const reportedFailures = Number(summary.actionFailed || 0);

  if (discovered <= 0) fail("visible surface discovery returned no pages", { summary });
  if (scanned !== discovered) fail("visible surface scan is incomplete", { discovered, scanned });
  if (actionResults.length !== discovered) fail("visible surface result count does not match discovery", {
    discovered,
    results: actionResults.length,
  });
  if (actionOk !== discovered || reportedFailures || actionFailures.length) {
    fail("visible surface scan has failed pages", { summary, actionFailures });
  }
  if (Number(summary.consoleErrorCount || 0) || consoleErrors.length) {
    fail("visible surface scan has console errors", { summary, consoleErrors });
  }

  console.log(JSON.stringify({
    ok: true,
    reportPath: REPORT_PATH,
    discovered,
    scanned,
    actionOk,
    actionFailed: 0,
    consoleErrors: 0,
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
