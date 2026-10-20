import fs from "node:fs/promises";
import path from "node:path";
import { launchChromium } from "../../../../scripts/verify/playwright_runtime.mjs";

const BASE_URL = String(
  process.env.FRONTEND_URL || process.env.WORKFLOW_CONTRACT_FRONTEND_URL || "http://127.0.0.1:18081"
).replace(/\/+$/, "");
const DB_NAME = String(process.env.DB_NAME || "sc_dev_demo").trim();
const LOGIN = String(process.env.E2E_LOGIN || "wutao").trim();
const PASSWORD = String(process.env.E2E_PASSWORD || "scdevpass").trim();
const ARTIFACT_DIR = path.resolve(
  process.cwd(),
  process.env.ARTIFACTS_DIR || "artifacts/playwright/product-configuration-capability"
);
const REPORT_PATH = path.join(ARTIFACT_DIR, "report.json");
const HOME_BLOCKS = [
  "today_actions",
  "risks",
  "my_objects",
  "quick_actions",
  "recent",
  "capability_map",
];

const report = {
  schema: "product.configuration.capability.browser.v1",
  pass: false,
  generated_at: new Date().toISOString(),
  runtime: { base_url: BASE_URL, database: DB_NAME, login: LOGIN },
  assertions: [],
  screenshots: [],
  contract_evidence: {},
  errors: [],
  failed_requests: [],
};

function check(condition, message, details = {}) {
  report.assertions.push({ pass: Boolean(condition), message, ...details });
  if (!condition) throw new Error(`${message}: ${JSON.stringify(details)}`);
}

async function screenshot(page, name) {
  const file = path.join(ARTIFACT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  report.screenshots.push({ name, file, url: page.url() });
}

async function login(page) {
  await page.goto(`${BASE_URL}/t/demo/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  const inputs = page.locator("input");
  await inputs.nth(0).fill(LOGIN);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForFunction(() => !window.location.pathname.includes("/login"), null, { timeout: 60000 });
  await page.locator(".layout-shell").waitFor({ timeout: 60000 });
}

async function waitForBlock(page, key) {
  const locator = page.locator(`[data-login-home-block="${key}"]`);
  await locator.waitFor({ state: "visible", timeout: 60000 });
  await page.waitForFunction(
    (blockKey) => {
      const node = document.querySelector(`[data-login-home-block="${blockKey}"]`);
      const state = node?.getAttribute("data-state") || "";
      return state !== "loading";
    },
    key,
    { timeout: 60000 }
  );
  return locator;
}

const browser = await launchChromium({ headless: true });
try {
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: "zh-CN" });
  const page = await context.newPage();
  page.on("console", (message) => {
    if (message.type() === "error" && !/favicon|ResizeObserver/i.test(message.text())) {
      report.errors.push({ type: "console", text: message.text(), url: page.url() });
    }
  });
  page.on("pageerror", (error) => report.errors.push({ type: "pageerror", text: error.message, url: page.url() }));
  page.on("response", (response) => {
    if (response.status() >= 400) {
      report.failed_requests.push({ status: response.status(), url: response.url() });
    }
  });
  page.on("response", async (response) => {
    if (!response.url().includes("/api/v1/intent") || response.status() !== 200) return;
    try {
      const requestBody = response.request().postDataJSON();
      if (requestBody?.intent !== "system.init") return;
      const payload = await response.json();
      const data = payload?.data && typeof payload.data === "object" ? payload.data : {};
      const collections = {};
      for (const [key, value] of Object.entries(data)) {
        if (!Array.isArray(value) || !value.length || key === "capabilities" || key === "scenes") continue;
        collections[key] = {
          count: value.length,
          samples: value.slice(0, 3).map((row) => String(row?.title || row?.name || row?.label || row?.record_name || row?.id || "")),
        };
      }
      report.contract_evidence.system_init_collections = collections;
      const extFacts = data?.ext_facts && typeof data.ext_facts === "object" ? data.ext_facts : {};
      const extCollections = {};
      for (const [moduleKey, moduleFacts] of Object.entries(extFacts)) {
        if (!moduleFacts || typeof moduleFacts !== "object") continue;
        const moduleCollections = {};
        const named = moduleFacts.workspace_collections && typeof moduleFacts.workspace_collections === "object"
          ? moduleFacts.workspace_collections
          : {};
        for (const [key, value] of Object.entries(named)) {
          if (!Array.isArray(value) || !value.length) continue;
          moduleCollections[key] = {
            count: value.length,
            samples: value.slice(0, 3).map((row) => String(row?.title || row?.name || row?.label || row?.record_name || row?.id || "")),
          };
        }
        extCollections[moduleKey] = moduleCollections;
      }
      report.contract_evidence.ext_facts_collections = extCollections;
      const home = payload?.data?.workspace_home || payload?.workspace_home || payload?.data?.result?.workspace_home;
      if (!home) return;
      report.contract_evidence.workspace_home = {
        today_actions: (Array.isArray(home.today_actions) ? home.today_actions : []).map((row) => String(row?.title || "")),
        my_objects: (Array.isArray(home.my_objects) ? home.my_objects : []).map((row) => ({
          kind: String(row?.kind || ""),
          title: String(row?.title || ""),
          model: String(row?.model || ""),
          record_id: Number(row?.record_id || 0),
          route: String(row?.route || ""),
        })),
        risk_actions: (Array.isArray(home?.risk?.actions) ? home.risk.actions : []).map((row) => String(row?.title || "")),
        scene_groups: (Array.isArray(home.scene_groups) ? home.scene_groups : []).map((row) => ({
          title: String(row?.title || ""),
          group_key: String(row?.group_key || ""),
          group_label: String(row?.group_label || ""),
          route: String(row?.route || ""),
        })),
        group_overview: (Array.isArray(home.group_overview) ? home.group_overview : []).map((row) => String(row?.label || row?.key || "")),
      };
    } catch {
      // Contract evidence is supplementary; assertion failures stay authoritative.
    }
  });

  await login(page);
  await page.goto(`${BASE_URL}/t/demo/`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator("[data-role-home]").waitFor({ timeout: 60000 });

  for (const key of HOME_BLOCKS) {
    const block = await waitForBlock(page, key);
    check((await block.count()) === 1, `home block ${key} is rendered once`);
    const text = (await block.innerText()).trim();
    check(text.length > 0, `home block ${key} has visible content`);
    const state = await block.getAttribute("data-state");
    check(Boolean(state), `home block ${key} declares its state`, { state });
    report.contract_evidence[`block_${key}`] = { state, text: text.slice(0, 1200) };
    if (key === "risks" || key === "my_objects") {
      check(["ready", "empty"].includes(String(state)), `home block ${key} is ready or intentionally empty`, { state });
    }
  }
  await screenshot(page, "01-home-six-blocks");
  const objectItems = page.locator('[data-login-home-block="my_objects"] [data-object-model]');
  const objectRows = await objectItems.evaluateAll((nodes) => nodes.map((node) => ({
    kind: node.getAttribute("data-object-kind") || "",
    model: node.getAttribute("data-object-model") || "",
    recordId: Number(node.getAttribute("data-object-record-id") || 0),
    route: node.getAttribute("data-object-route") || "",
  })));
  const allowedObjectModels = new Set(["project.project", "construction.contract", "payment.request"]);
  check(objectRows.length > 0, "my objects renders record-backed rows", { objectRows });
  check(
    objectRows.every((row) => allowedObjectModels.has(row.model) && row.recordId > 0),
    "my objects only renders declared project, contract or payment records",
    { objectRows }
  );
  check(
    objectRows.every((row) => row.route.startsWith("/r/")),
    "my objects exposes record routes",
    { objectRows }
  );
  const firstObjectRoute = objectRows[0]?.route;
  await page.goto(`${BASE_URL}/t/demo${firstObjectRoute}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator(".layout-shell").waitFor({ timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 60000 });
  check(page.url().includes(firstObjectRoute), "first business object opens its record route", { url: page.url(), route: firstObjectRoute });
  const recordErrors = await page.locator(
    '[data-semantic-component="ScInlineState"][data-state="error"], [data-semantic-component="ScErrorState"]'
  ).count();
  check(recordErrors === 0, "first business object record renders without an error state", { recordErrors });
  await screenshot(page, "02-first-business-object");
  await page.goto(`${BASE_URL}/t/demo/`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator("[data-role-home]").waitFor({ timeout: 60000 });
  for (const key of HOME_BLOCKS) {
    const block = page.locator(`[data-login-home-block="${key}"]`);
    await block.screenshot({ path: path.join(ARTIFACT_DIR, `home-block-${key}.png`) });
    report.screenshots.push({ name: `home-block-${key}`, file: path.join(ARTIFACT_DIR, `home-block-${key}.png`), url: page.url() });
  }

  await page.goto(`${BASE_URL}/t/demo/admin/business-config`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator('[data-product-capability-cards="v1"]').waitFor({ timeout: 60000 });
  await page.waitForFunction(
    () => document.querySelectorAll("[data-capability-card]").length === 8,
    null,
    { timeout: 60000 }
  );
  const cardKeys = await page.locator("[data-capability-card]").evaluateAll((nodes) => (
    nodes.map((node) => node.getAttribute("data-capability-card")).filter(Boolean)
  ));
  check(cardKeys.length === 8, "configuration workbench renders eight cards", { cardKeys });
  await screenshot(page, "02-configuration-workbench");

  await page.goto(`${BASE_URL}/t/demo/admin/system-parameters`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator('[data-semantic-component="SystemParameterCatalogView"]').waitFor({ timeout: 60000 });
  await page.locator("[data-parameter-key]").first().waitFor({ timeout: 60000 });
  const parameterCategories = await page.locator("[data-parameter-category]").count();
  const parameters = await page.locator("[data-parameter-key]").count();
  check(parameterCategories >= 6, "system parameter catalog renders six categories", { parameterCategories });
  check(parameters > 0, "system parameter catalog renders parameters", { parameters });
  await screenshot(page, "03-system-parameter-catalog");

  await page.goto(`${BASE_URL}/t/demo/my-capabilities`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator('[data-semantic-component="MyCapabilitiesView"]').waitFor({ timeout: 60000 });
  await page.locator("[data-capability-key]").first().waitFor({ timeout: 60000 });
  const capabilities = await page.locator("[data-capability-key]").count();
  check(capabilities > 0, "my capabilities renders declared capabilities", { capabilities });
  await screenshot(page, "04-my-capabilities");

  check(report.errors.length === 0, "browser console and page errors are zero", { errors: report.errors });
  check(report.failed_requests.length === 0, "browser failed requests are zero", { failed_requests: report.failed_requests });
  report.pass = true;
} catch (error) {
  report.error = String(error?.stack || error?.message || error);
} finally {
  await browser.close().catch(() => {});
  await fs.mkdir(ARTIFACT_DIR, { recursive: true });
  await fs.writeFile(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf-8");
}

if (!report.pass) {
  console.error(`[product_configuration_capability_browser] FAIL ${report.error || "unknown error"}`);
  process.exit(1);
}
console.log(`[product_configuration_capability_browser] PASS blocks=${HOME_BLOCKS.length} assertions=${report.assertions.length}`);
