import { launchChromium } from "../../../../scripts/verify/playwright_runtime.mjs";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:18081";
const LOGIN = process.env.LOGIN || "admin";
const PASSWORD = process.env.PASSWORD || "admin";
const DB_NAME = process.env.DB_NAME || "";

function assert(condition, message, details = {}) {
  if (!condition) {
    const error = new Error(message);
    error.details = details;
    throw error;
  }
}

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.reload({ waitUntil: "domcontentloaded" });
  const inputs = page.locator("input.sc-input");
  await inputs.nth(0).fill(LOGIN);
  await inputs.nth(1).fill(PASSWORD);
  if (DB_NAME && await inputs.nth(2).isEditable()) {
    await inputs.nth(2).fill(DB_NAME);
  }
  await page.locator('button[type="submit"]').click();
  await Promise.race([
    page.waitForURL((url) => !String(url).includes("/login"), { timeout: 30000 }),
    page.locator("#login-error").waitFor({ state: "visible", timeout: 30000 }).then(async () => {
      throw new Error(`login failed: ${String(await page.locator("#login-error").textContent() || "unknown error").trim()}`);
    }),
  ]);
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
}

function normalizeLabel(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/[0-9]+$/g, "");
}

async function mainNavigationLabels(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll(".nav-shell .label"))
    .filter((el) => Boolean(el.offsetWidth || el.offsetHeight || el.getClientRects().length))
    .map((el) => String(el.textContent || "").trim().replace(/\s+/g, " ")));
}

async function openBusinessNavigation(page) {
  const navigationButton = page.locator('.workspace-activity-rail button[aria-label="业务导航"]');
  await navigationButton.waitFor({ state: "visible", timeout: 30000 });
  await navigationButton.click();
  try {
    await page.locator(".nav-shell button.label").first().waitFor({ state: "visible", timeout: 30000 });
  } catch {
    throw Object.assign(new Error("业务导航未形成可操作菜单"), {
      details: {
        url: page.url(),
        navigation_state: await page.locator(".nav-shell").getAttribute("data-navigation-state").catch(() => null),
        navigation_text: String(await page.locator(".nav-shell").textContent().catch(() => "") || "").trim(),
      },
    });
  }
}

async function visibleConfigurationEntries(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll(
    ".nav-shell .label, .workspace-activity-rail button[aria-label]",
  ))
    .filter((el) => Boolean(el.offsetWidth || el.offsetHeight || el.getClientRects().length))
    .map((el) => ({
      label: String(el.textContent || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " "),
      surface: el.closest(".workspace-activity-rail") ? "activity_rail" : "primary_navigation",
    }))
    .filter((entry) => entry.label === "产品配置" || entry.label === "配置中心"));
}

async function openMenuConfigurationFromProductEntry(page) {
  const productEntry = page.locator(".nav-shell button.label").filter({ hasText: /^\s*产品配置\s*$/ });
  assert(await productEntry.count() === 1, "产品配置运行态入口必须唯一", {
    product_entry_count: await productEntry.count(),
    visible_navigation_labels: await mainNavigationLabels(page),
  });
  assert(await productEntry.isEnabled(), "产品配置运行态入口不可操作");
  const productBranch = productEntry.locator("xpath=ancestor::li[1]");
  const menuConfigurationEntry = productBranch.locator("button.label").filter({ hasText: /^\s*菜单配置\s*$/ });
  const productToggle = productBranch.locator(":scope > .node > button.toggle");
  if (await productToggle.getAttribute("aria-expanded") !== "true") {
    await productToggle.click();
  }
  const lowCodeGroupEntry = productBranch.locator("button.label").filter({ hasText: /^\s*低代码系统配置\s*$/ });
  await lowCodeGroupEntry.waitFor({ state: "visible", timeout: 30000 });
  const lowCodeGroup = lowCodeGroupEntry.locator("xpath=ancestor::li[1]");
  const lowCodeToggle = lowCodeGroup.locator(":scope > .node > button.toggle");
  if (await lowCodeToggle.getAttribute("aria-expanded") !== "true") {
    await lowCodeToggle.click();
  }
  try {
    await menuConfigurationEntry.waitFor({ state: "visible", timeout: 30000 });
  } catch {
    throw Object.assign(new Error("产品配置分组无法展开菜单配置"), {
      details: {
        product_toggle_expanded: await productToggle.getAttribute("aria-expanded"),
        low_code_toggle_expanded: await lowCodeToggle.getAttribute("aria-expanded"),
        product_branch_text: String(await productBranch.textContent() || "").trim().replace(/\s+/g, " "),
      },
    });
  }
  const sourceUrl = page.url();
  await menuConfigurationEntry.click();
  await page.waitForURL((url) => String(url) !== sourceUrl, { timeout: 30000 });
  return page.url();
}

async function menuConfigSurface(page) {
  const resolvedMenuConfigurationUrl = await openMenuConfigurationFromProductEntry(page);
  const menuConfigurationHeading = page.getByRole("heading", { name: "菜单配置", exact: true });
  await menuConfigurationHeading.waitFor({ state: "visible", timeout: 30000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  return {
    resolvedMenuConfigurationUrl,
    heading: String(await menuConfigurationHeading.textContent() || "").trim(),
  };
}

async function main() {
  const browser = await launchChromium({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  try {
    await login(page);
    await openBusinessNavigation(page);
    const labels = await mainNavigationLabels(page);
    const configurationEntries = await visibleConfigurationEntries(page);
    const { heading: menuConfigHeading, resolvedMenuConfigurationUrl } = await menuConfigSurface(page);
    const normalizedMainLabels = labels.map(normalizeLabel);
    const result = {
      url: page.url(),
      resolved_menu_configuration_url: resolvedMenuConfigurationUrl,
      labels,
      menu_config_heading: menuConfigHeading,
      has_lowcode_fact_spread: ["客户", "供应商", "一般合同", "材料合同"].every((label) => normalizedMainLabels.includes(label)),
      has_legacy_base_settings_group: normalizedMainLabels.some((label) => label.includes("基础设置") || label.includes("系统设置")),
      configuration_entries: configurationEntries,
      product_configuration_entry_count: configurationEntries.filter((entry) => entry.label === "产品配置").length,
      legacy_configuration_entry_count: configurationEntries.filter((entry) => entry.label === "配置中心").length,
    };
    result.has_single_product_configuration_entry = result.product_configuration_entry_count === 1
      && result.legacy_configuration_entry_count === 0;
    result.ok = !result.has_lowcode_fact_spread
      && !result.has_legacy_base_settings_group
      && result.has_single_product_configuration_entry
      && result.menu_config_heading === "菜单配置";
    console.log(JSON.stringify(result, null, 2));
    assert(result.ok, "产品发布主导航与菜单配置默认树边界漂移", result);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error("[product_navigation_boundary_acceptance] FAIL", error.message);
  if (error.details) console.error(JSON.stringify(error.details, null, 2));
  process.exit(1);
});
