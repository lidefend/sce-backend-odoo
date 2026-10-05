import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

function requiredEnv(name, aliases = []) {
  for (const key of [name, ...aliases]) {
    const value = String(process.env[key] || "").trim();
    if (value) return value;
  }
  throw new Error(`missing required environment variable: ${[name, ...aliases].join(" or ")}`);
}

function findCachedChromiumExecutable() {
  const explicit = process.env.CHROMIUM_EXECUTABLE_PATH || process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || "";
  if (explicit && fsSync.existsSync(explicit)) return explicit;
  const cacheRoot = path.join(process.env.HOME || "", ".cache", "ms-playwright");
  if (!cacheRoot || !fsSync.existsSync(cacheRoot)) return "";
  return fsSync.readdirSync(cacheRoot)
    .filter((name) => name.startsWith("chromium_headless_shell-") || name.startsWith("chromium-"))
    .sort()
    .reverse()
    .flatMap((name) => [
      path.join(cacheRoot, name, "chrome-headless-shell-linux64", "chrome-headless-shell"),
      path.join(cacheRoot, name, "chrome-linux64", "chrome"),
    ])
    .find((item) => fsSync.existsSync(item)) || "";
}

const BASE_URL = requiredEnv("BASE_URL", ["WORKFLOW_CONTRACT_FRONTEND_URL"]);
const DB_NAME = requiredEnv("DB_NAME", ["DB"]);
const LOGIN = requiredEnv("E2E_LOGIN", ["LOGIN"]);
const PASSWORD = requiredEnv("E2E_PASSWORD", ["PASSWORD"]);
const ROOT_DIR = process.env.REPO_ROOT || process.cwd();
const WALK_REPORT = process.env.WALK_REPORT || path.join(ROOT_DIR, "artifacts/backend/daily_acceptance_route_walk_1440_light.json");
const OUT = process.env.OUT || path.join(ROOT_DIR, "artifacts/backend/daily_acceptance_template_coverage.json");
const SHOT_DIR = process.env.SHOT_DIR || path.join(ROOT_DIR, "artifacts/backend/daily_acceptance_template_shots");
const ALLOW_WRITE = String(process.env.ALLOW_WRITE || "0") === "1";
const WRITE_MODEL = String(process.env.WRITE_MODEL || "").trim();
const WRITE_NAME_FIELD = String(process.env.WRITE_NAME_FIELD || "name").trim();
const PROBE_LIMIT = Number(process.env.TEMPLATE_PROBE_LIMIT || 30);
const EXCLUSIONS = new Set(String(process.env.TEMPLATE_EXCLUSIONS || "").split(",").map((item) => item.trim()).filter(Boolean));
const ERROR_TEXT_RE = /render error|contract not renderable|missing required nav|页面加载失败|系统异常|加载异常|发生异常|Traceback|Cannot read/i;

const DECLARED_TEMPLATES = [
  "home",
  "collection_table",
  "collection_card",
  "readonly_form",
  "create_edit_form",
  "relation_dialog",
  "one2many",
  "collaboration",
  "designer",
  "loading",
  "empty",
  "error_forbidden",
];
// Covered by separate governed entries, referenced by this acceptance rather than duplicated here.
const EXTERNAL_TEMPLATES = {
  collaboration: "contract form collaboration panel (covered by relation/form walk evidence)",
  designer: "make verify.business_config.config_workbench_operation_acceptance",
};

function normalize(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

async function main() {
  await fs.mkdir(SHOT_DIR, { recursive: true });
  const report = JSON.parse(await fs.readFile(WALK_REPORT, "utf8"));
  const actionResults = Array.isArray(report.actionResults) ? report.actionResults : [];
  const formResults = Array.isArray(report.formResults) ? report.formResults : [];
  const entries = actionResults.filter((row) => row && row.actionId && row.ok !== false);
  const forms = formResults.filter((row) => row && !row.skipped && row.ok !== false && row.model && row.recordId);

  const executablePath = findCachedChromiumExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: "zh-CN" });
  const page = await context.newPage();
  const consoleErrors = [];
  const httpFailures = [];
  const requestFailures = [];
  let currentCheck = "";
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push({ check: currentCheck, text: msg.text().slice(0, 400) });
  });
  page.on("pageerror", (err) => consoleErrors.push({ check: currentCheck, text: err.message.slice(0, 400) }));
  page.on("response", (response) => {
    if (response.status() >= 400) {
      httpFailures.push({ check: currentCheck, status: response.status(), url: response.url().slice(0, 250) });
    }
  });
  page.on("requestfailed", (request) => {
    const failure = request.failure()?.errorText || "";
    if (failure.includes("net::ERR_ABORTED")) return;
    requestFailures.push({ check: currentCheck, url: request.url().slice(0, 250), failure });
  });

  const login = async () => {
    await page.goto(`${BASE_URL}/login?db=${encodeURIComponent(DB_NAME)}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    const inputs = page.locator("input");
    await inputs.nth(0).fill(LOGIN);
    await page.locator('input[type="password"]').first().fill(PASSWORD);
    if (await inputs.count() >= 3) {
      const dbInput = inputs.nth(2);
      if (await dbInput.isEnabled().catch(() => false)) await dbInput.fill(DB_NAME);
    }
    await page.locator('button[type="submit"]').first().click();
    await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 60000 });
    await page.waitForTimeout(600);
  };

  const token = async () => page.evaluate(() => {
    const key = Object.keys(sessionStorage).find((item) => item.startsWith("sc_auth_token")) || "";
    return key ? sessionStorage.getItem(key) : "";
  });

  const intent = async (authToken, intentName, params = {}) => page.evaluate(async ({ authToken, intentName, params, dbName }) => {
    const res = await fetch(`/api/v1/intent?db=${encodeURIComponent(dbName)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Odoo-DB": dbName, Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ intent: intentName, params, meta: { startup_chain_bypass: true } }),
    });
    const body = await res.json();
    if (!res.ok || body.ok === false) throw new Error(JSON.stringify(body.error || body).slice(0, 500));
    return body.data || body;
  }, { authToken, intentName, params, dbName: DB_NAME });

  const settle = async () => {
    await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(700);
  };
  const bodyText = async () => page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  const overflowPx = async () => page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - window.innerWidth - 2)).catch(() => 0);
  const shot = async (name) => { await page.screenshot({ path: path.join(SHOT_DIR, `${name}.png`), fullPage: false }).catch(() => {}); };

  const results = [];
  const runCheck = async (template, fn) => {
    currentCheck = template;
    const before = { console: consoleErrors.length, http: httpFailures.length, request: requestFailures.length };
    const detail = { route: "", notes: [] };
    let status = "ok";
    let message = "";
    try {
      if (EXTERNAL_TEMPLATES[template] && !EXCLUSIONS.has(template)) {
        status = "external";
        message = EXTERNAL_TEMPLATES[template];
      } else {
        await fn(detail);
      }
      await shot(template);
    } catch (error) {
      status = EXCLUSIONS.has(template) ? "excluded" : "fail";
      message = error instanceof Error ? error.message : String(error);
    }
    detail.overflowPx = await overflowPx();
    detail.consoleErrorDelta = consoleErrors.length - before.console;
    detail.httpFailureDelta = httpFailures.length - before.http;
    detail.requestFailureDelta = requestFailures.length - before.request;
    detail.httpStatuses = httpFailures.slice(before.http).map((row) => row.status);
    results.push({ template, status, message, ...detail });
  };

  await login();
  const authToken = await token();
  if (!authToken) throw new Error("login token missing");

  const tableEntry = entries.find((row) => row.model && row.model !== "") || entries[0];
  const formTarget = forms.find((row) => row.model === tableEntry?.model) || forms[0];

  await runCheck("home", async (detail) => {
    await page.goto(`${BASE_URL}/?db=${encodeURIComponent(DB_NAME)}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await settle();
    detail.route = "/";
    const marker = page.locator('[data-product-page-mode="dashboard"], .home-page').first();
    await marker.waitFor({ state: "visible", timeout: 20000 });
    const text = await bodyText();
    if (ERROR_TEXT_RE.test(text)) throw new Error(`home rendered error text: ${text.slice(0, 200)}`);
    detail.notes.push("dashboard shell visible");
  });

  await runCheck("collection_table", async (detail) => {
    if (!tableEntry) throw new Error("no list entry discovered in walk report");
    const route = `/a/${tableEntry.actionId}?db=${encodeURIComponent(DB_NAME)}${tableEntry.menuId ? `&menu_id=${tableEntry.menuId}` : ""}`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await settle();
    detail.route = route;
    await page.locator('[data-product-page-mode="list"]').first().waitFor({ state: "visible", timeout: 30000 });
    const headerCount = await page.locator("th").count().catch(() => 0);
    const emptyVisible = await page.locator(".sc-empty, [data-semantic-component='ScEmptyState']").count().catch(() => 0);
    if (headerCount === 0 && emptyVisible === 0) throw new Error("collection table has neither headers nor empty state");
    detail.notes.push(`headers=${headerCount} empty=${emptyVisible}`);
    const selectAll = page.locator('thead input[type="checkbox"]').first();
    const rowBoxes = page.locator('tbody input[type="checkbox"]');
    const rowCount = await rowBoxes.count().catch(() => 0);
    if (rowCount > 0) {
      if (!(await selectAll.count())) throw new Error("row selection present but no header select-all control");
      await selectAll.check({ force: true }).catch(async () => { await selectAll.click({ force: true }); });
      await page.waitForTimeout(500);
      const checked = await page.locator('tbody input[type="checkbox"]:checked').count().catch(() => 0);
      if (checked === 0) throw new Error("select-all did not check any row selection control");
      detail.notes.push(`selection checked=${checked}/${rowCount}`);
      await selectAll.uncheck({ force: true }).catch(() => {});
    } else {
      detail.notes.push("no data rows; selection control verified by contract only");
    }
  });

  await runCheck("collection_card", async (detail) => {
    if (!tableEntry) throw new Error("no list entry discovered in walk report");
    const route = `/a/${tableEntry.actionId}?db=${encodeURIComponent(DB_NAME)}${tableEntry.menuId ? `&menu_id=${tableEntry.menuId}` : ""}&view_mode=kanban`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await settle();
    detail.route = route;
    const lane = page.locator('[data-semantic-component="CollectionKanbanLane"], .collection-kanban-lane').first();
    const empty = page.locator(".sc-empty, [data-semantic-component='ScEmptyState']").first();
    const visible = (await lane.count().catch(() => 0)) > 0 || (await empty.count().catch(() => 0)) > 0;
    if (!visible) throw new Error("kanban surface not rendered for view_mode=kanban");
    detail.notes.push("kanban lane or empty-state rendered");
  });

  await runCheck("readonly_form", async (detail) => {
    if (!formTarget) throw new Error("no form target discovered in walk report");
    const route = `/r/${formTarget.model}/${formTarget.recordId}?db=${encodeURIComponent(DB_NAME)}${formTarget.actionId ? `&action_id=${formTarget.actionId}` : ""}${formTarget.menuId ? `&menu_id=${formTarget.menuId}` : ""}`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await settle();
    detail.route = route;
    await page.locator(".template-layout-shell, [data-product-page-mode='form']").first().waitFor({ state: "visible", timeout: 30000 });
    const text = await bodyText();
    if (ERROR_TEXT_RE.test(text)) throw new Error("readonly form rendered error text");
    detail.notes.push(`model=${formTarget.model} record=${formTarget.recordId}`);
  });

  await runCheck("create_edit_form", async (detail) => {
    if (!tableEntry) throw new Error("no list entry discovered in walk report");
    const route = `/a/${tableEntry.actionId}?db=${encodeURIComponent(DB_NAME)}${tableEntry.menuId ? `&menu_id=${tableEntry.menuId}` : ""}`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await settle();
    detail.route = route;
    const createButton = page.locator(".action-toolbar button").filter({ hasText: /新建|创建|新增/ }).first();
    await createButton.waitFor({ state: "visible", timeout: 15000 });
    await createButton.click();
    await page.waitForTimeout(1200);
    const formMarker = page.locator(".template-layout-shell, [data-product-page-mode='form']").first();
    await formMarker.waitFor({ state: "visible", timeout: 30000 });
    const outlineCount = await page.locator(".native-business-outline-item").count().catch(() => 0);
    const inputCount = await page.locator("input:not([type=hidden]), textarea, select").count().catch(() => 0);
    if (outlineCount === 0 && inputCount === 0) throw new Error("create form opened without any field surface");
    detail.notes.push(`outline=${outlineCount} inputs=${inputCount}`);
    const cancel = page.locator("button").filter({ hasText: /取消|返回|放弃/ }).first();
    if (await cancel.count()) {
      await cancel.click().catch(() => {});
      await page.waitForTimeout(800);
    }
    if (WRITE_MODEL && !ALLOW_WRITE) throw new Error("write model supplied but ALLOW_WRITE is not enabled");
  });

  await runCheck("one2many", async (detail) => {
    let found = "";
    for (const form of forms.slice(0, PROBE_LIMIT)) {
      const route = `/r/${form.model}/${form.recordId}?db=${encodeURIComponent(DB_NAME)}${form.actionId ? `&action_id=${form.actionId}` : ""}${form.menuId ? `&menu_id=${form.menuId}` : ""}`;
      await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
      await settle();
      const editor = page.locator('[data-semantic-component="One2ManyCellEditor"], .o2m-cell-editor, .relation-editor').first();
      if (await editor.count().catch(() => 0)) { found = route; detail.notes.push(`o2m editor on ${form.model}`); break; }
    }
    if (!found) throw new Error(`no one2many/many2many editor found across ${Math.min(forms.length, PROBE_LIMIT)} forms`);
    detail.route = found;
  });

  await runCheck("empty", async (detail) => {
    let found = "";
    for (const entry of entries.slice(0, PROBE_LIMIT)) {
      if (!entry.model) continue;
      let rows = null;
      try {
        const list = await intent(authToken, "api.data", { op: "list", model: entry.model, fields: ["id"], limit: 1, context: {} });
        rows = (list.rows || list.records || list.data || []).length;
      } catch { continue; }
      if (rows === 0) {
        const route = `/a/${entry.actionId}?db=${encodeURIComponent(DB_NAME)}${entry.menuId ? `&menu_id=${entry.menuId}` : ""}`;
        await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
        await settle();
        const empty = page.locator(".sc-empty, [data-semantic-component='ScEmptyState']").first();
        if (await empty.count().catch(() => 0)) { found = route; detail.notes.push(`empty state on ${entry.model}`); break; }
      }
    }
    if (!found) throw new Error("no model with zero rows produced a rendered empty state");
    detail.route = found;
  });

  await runCheck("error_forbidden", async (detail) => {
    if (!formTarget) throw new Error("no form target for forbidden probe");
    const route = `/r/${formTarget.model}/999999999?db=${encodeURIComponent(DB_NAME)}${formTarget.actionId ? `&action_id=${formTarget.actionId}` : ""}${formTarget.menuId ? `&menu_id=${formTarget.menuId}` : ""}`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await settle();
    detail.route = route;
    const text = await bodyText();
    if (ERROR_TEXT_RE.test(text)) throw new Error("forbidden/not-found route rendered a raw traceback or render error");
    const presented = /无权限|没有权限|权限不足|禁止访问|记录不存在|不存在|未找到|Not Found|Forbidden/i.test(text)
      || (await page.locator(".sc-empty, [data-semantic-component='ScEmptyState'], .status-panel").count().catch(() => 0)) > 0
      || page.url().includes("/a/");
    if (!presented) throw new Error("forbidden/not-found route produced no user-facing presentation");
    detail.notes.push("forbidden/not-found presented as a user-facing state");
  });

  await runCheck("loading", async (detail) => {
    if (!tableEntry) throw new Error("no list entry for loading probe");
    const route = `/a/${tableEntry.actionId}?db=${encodeURIComponent(DB_NAME)}${tableEntry.menuId ? `&menu_id=${tableEntry.menuId}` : ""}`;
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await settle();
    await page.waitForTimeout(1500);
    detail.route = route;
    const busy = await page.locator('[aria-busy="true"]').count().catch(() => 0);
    if (busy > 0) throw new Error(`page stayed busy after settle (aria-busy=${busy})`);
    detail.notes.push("no lingering busy state after settle");
  });

  if (ALLOW_WRITE && WRITE_MODEL) {
    await runCheck("write_cycle", async (detail) => {
      const label = `UI-ACCEPT-${Date.now()}`;
      const created = await intent(authToken, "api.data", { op: "create", model: WRITE_MODEL, vals: { [WRITE_NAME_FIELD]: label }, context: {} });
      const recordId = Number(created?.id || created?.record_id || 0);
      if (!recordId) throw new Error("write cycle create returned no id");
      detail.notes.push(`created ${WRITE_MODEL} id=${recordId}`);
      const search = await intent(authToken, "api.data", { op: "list", model: WRITE_MODEL, fields: ["id"], domain: [[WRITE_NAME_FIELD, "=", label]], limit: 5, context: {} });
      const found = (search.rows || search.records || search.data || []).map((row) => Number(row.id)).includes(recordId);
      if (!found) throw new Error("created record not readable back");
      const unlinked = await intent(authToken, "api.data.unlink", { model: WRITE_MODEL, ids: [recordId], context: {} });
      void unlinked;
      const after = await intent(authToken, "api.data", { op: "list", model: WRITE_MODEL, fields: ["id"], domain: [[WRITE_NAME_FIELD, "=", label]], limit: 5, context: {} });
      const leftover = (after.rows || after.records || after.data || []).length;
      if (leftover !== 0) throw new Error("write cycle cleanup did not remove the acceptance record");
      detail.notes.push("create-read-unlink-verify cycle passed");
    });
  }

  await browser.close();

  const statuses = Object.fromEntries(DECLARED_TEMPLATES.map((name) => [name, results.find((row) => row.template === name)?.status || "missing"]));
  const failing = results.filter((row) => ["fail", "missing"].includes(row.status));
  const coverage = DECLARED_TEMPLATES.map((name) => ({
    template: name,
    status: statuses[name],
    covered: ["ok", "external", "excluded"].includes(statuses[name]),
  }));
  const payload = {
    schema: "sce.user_template_coverage_acceptance.v1",
    meta: {
      baseUrl: BASE_URL,
      database: DB_NAME,
      login: LOGIN,
      walkReport: WALK_REPORT,
      generatedAt: new Date().toISOString(),
      allowWrite: ALLOW_WRITE,
      writeModel: WRITE_MODEL,
      exclusions: [...EXCLUSIONS],
    },
    coverage,
    results,
    consoleErrors: consoleErrors.slice(0, 100),
    httpFailures: httpFailures.slice(0, 100),
    requestFailures: requestFailures.slice(0, 100),
    summary: {
      declared: DECLARED_TEMPLATES.length,
      covered: coverage.filter((row) => row.covered).length,
      failing: failing.length,
      consoleErrorCount: consoleErrors.length,
      httpFailureCount: httpFailures.length,
      requestFailureCount: requestFailures.length,
    },
  };
  await fs.writeFile(OUT, JSON.stringify(payload, null, 2));
  console.log(JSON.stringify({ out: OUT, coverage, summary: payload.summary, results: results.map((row) => ({ template: row.template, status: row.status, message: row.message })) }, null, 2));
  if (failing.length) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
