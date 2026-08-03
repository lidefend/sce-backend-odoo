import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(SCRIPT_DIR, "..", "..", "..", "..");
const artifact = (...parts) => path.join(ROOT_DIR, "artifacts", "playwright", ...parts);
const OUTPUT_PATH = artifact("system-user-experience-full-browser", "summary.json");
const VISUAL_REPORT_PATH = process.env.USER_VISIBLE_SURFACE_REPORT || "/tmp/user_page_visual_coverage.json";

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

const count = (value) => Array.isArray(value) ? value.length : 0;

async function main() {
  const [configSummary, configReport, shellReport, visualReport, formReport] = await Promise.all([
    readJson(artifact("config-workbench-operation", "summary.json")),
    readJson(artifact("config-workbench-operation", "report.json")),
    readJson(artifact("system-user-experience-shell", "report.json")),
    readJson(VISUAL_REPORT_PATH),
    readJson(artifact("business-form-user-perspective", "report.json")),
  ]);

  const configOk = configSummary.ok === true
    && configSummary.assertion === "64/64"
    && configSummary.journeys === "10/10"
    && configSummary.actions === "19/19"
    && configSummary.screenshots === "9/9"
    && configSummary.delivery === "delivery_ready"
    && configSummary.professional === "professional_ready"
    && configSummary.consoleErrors === 0
    && configSummary.requestFailed === 0
    && configReport.ok === true;
  const shellOk = shellReport.ok === true
    && shellReport.caseCount >= 5
    && count(shellReport.failures) === 0
    && count(shellReport.consoleErrors) === 0
    && count(shellReport.requestFailed) === 0;
  const visualSummary = visualReport.summary || {};
  const visualOk = Number(visualSummary.totalDiscovered || 0) > 0
    && visualSummary.totalScanned === visualSummary.totalDiscovered
    && visualSummary.actionOk === visualSummary.totalDiscovered
    && Number(visualSummary.actionFailed || 0) === 0
    && Number(visualSummary.consoleErrorCount || 0) === 0
    && count(visualReport.actionResults) === visualSummary.totalDiscovered
    && count(visualReport.actionFailures) === 0
    && count(visualReport.consoleErrors) === 0;
  const formResults = Array.isArray(formReport.results) ? formReport.results : [];
  const formOk = formReport.ok === true
    && formResults.length >= 20
    && formResults.every((row) => row?.ok === true)
    && count(formReport.errors) === 0
    && count(formReport.consoleErrors) === 0;

  const gates = {
    config_workbench: { ok: configOk },
    shell: { ok: shellOk, caseCount: shellReport.caseCount },
    visible_surface: {
      ok: visualOk,
      discovered: visualSummary.totalDiscovered,
      scanned: visualSummary.totalScanned,
      failures: visualSummary.actionFailed,
      consoleErrors: visualSummary.consoleErrorCount,
    },
    business_form_user_perspective: { ok: formOk, caseCount: formResults.length },
  };
  const payload = { ok: Object.values(gates).every((gate) => gate.ok), reportPath: OUTPUT_PATH, gates };

  await fs.mkdir(path.dirname(OUTPUT_PATH), { recursive: true });
  await fs.writeFile(OUTPUT_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  if (!payload.ok) throw Object.assign(new Error("system user experience full browser summary is not ok"), { details: gates });
  console.log(JSON.stringify(payload, null, 2));
}

main().catch((err) => {
  console.error(JSON.stringify({
    ok: false,
    message: err instanceof Error ? err.message : String(err),
    details: err?.details || {},
  }, null, 2));
  process.exit(1);
});
