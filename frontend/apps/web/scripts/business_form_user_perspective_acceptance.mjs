import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

function requiredEnv(name, aliases = []) {
  for (const key of [name, ...aliases]) {
    const value = String(process.env[key] || "").trim();
    if (value) return value;
  }
  throw new Error(`missing required environment variable: ${[name, ...aliases].join(" or ")}`);
}

const BASE_URL = requiredEnv("BASE_URL", ["WORKFLOW_CONTRACT_FRONTEND_URL"]);
const DB_NAME = requiredEnv("DB_NAME", ["DB"]);
const LOGIN = requiredEnv("E2E_LOGIN", ["LOGIN"]);
const PASSWORD = requiredEnv("E2E_PASSWORD", ["PASSWORD"]);

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(SCRIPT_DIR, "..", "..", "..", "..");
const ARTIFACT_ROOT = path.join(ROOT_DIR, "artifacts", "playwright", "business-form-user-perspective");
const REPORT_PATH = path.join(ARTIFACT_ROOT, "report.json");

// Governed delivered-entry declaration. Every case below is bound to a declared
// delivered entry identity (`menu_xmlid|action_xmlid|model`); the runtime must
// deliver that exact identity or the case fails closed. Retired standalone entry
// labels are no longer part of the resolution path.
//
// The delivered-entry declaration is `frontend_business_entry_acceptance_v1.csv`
// (the governed formal product-entry surface: 89 rows, verified identical in both
// directions to the published runtime navigation). `config/frontend/
// authoritative_navigation.json` is deliberately NOT unioned here: it declares the
// per-role surface *entitlement* (`ROLE_SURFACE_OVERRIDES`) and still carries
// handling menus that the locked user-confirmed formal menu policy has already
// merged into unified handling entries, so consuming it would re-introduce
// assertions against entries the product does not deliver.
const FORMAL_ENTRY_DECLARATION = path.join(ROOT_DIR, "docs", "product", "frontend_business_entry_acceptance_v1.csv");

// User-perspective create-form journeys, one per declared delivered handling entry.
// `entry` is the declared delivered identity. The expected business content is
// NOT hand written here: it is the create contract the frontend itself consumes
// (`ui.contract.v2 op=model render_profile=create`), read back from the runtime
// during the journey. `forbidden` is the migration/audit vocabulary a product
// surface must never leak.
const CASE_DEFINITIONS = [
  {
    code: "finance.loan.project_borrow_company",
    label: "项目借公司款登记",
    entry: "smart_construction_core.menu_sc_product_current_account_v1|smart_construction_core.action_sc_product_current_account_v1|sc.current.account.workspace",
    kind: "consolidated",
    retired: "smart_construction_core.menu_sc_project_borrow_company|smart_construction_core.action_sc_financing_loan_project_borrow_company|sc.financing.loan",
    forbidden: ["来源与系统追溯", "历史账户线索"],
  },
  {
    code: "settlement.income",
    label: "收入合同结算",
    entry: "smart_construction_core.menu_sc_p1_income_settlement|smart_construction_core.action_sc_settlement_order_income|sc.settlement.order",
    forbidden: ["来源与系统追溯", "历史来源表"],
  },
  {
    code: "finance.receipt.income.progress",
    label: "工程进度款收入登记",
    entry: "smart_construction_core.menu_sc_receipt_income|smart_construction_core.action_sc_receipt_income|sc.receipt.income",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.receipt.income.project",
    label: "到款确认",
    entry: "smart_construction_core.menu_sc_receipt_income|smart_construction_core.action_sc_receipt_income|sc.receipt.income",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.receipt.income.residual",
    label: "其他/残余收款",
    entry: "smart_construction_core.menu_sc_receipt_income|smart_construction_core.action_sc_receipt_income|sc.receipt.income",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.self_funding.income",
    label: "自筹垫付办理",
    entry: "smart_construction_core.menu_sc_product_company_project_refund_v1|smart_construction_core.action_sc_product_company_project_refund_v1|sc.company.project.refund.workspace",
    kind: "consolidated",
    retired: "smart_construction_core.menu_sc_self_funding_advance_income|smart_construction_core.action_sc_self_funding_registration_income|sc.self.funding.registration",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.fund.transfer",
    label: "账户间资金往来",
    entry: "smart_construction_core.menu_sc_product_current_account_v1|smart_construction_core.action_sc_product_current_account_v1|sc.current.account.workspace",
    kind: "consolidated",
    retired: "smart_construction_core.menu_sc_fund_account_between_user|smart_construction_core.action_sc_fund_account_between_user|sc.fund.account.operation",
    forbidden: ["来源与系统追溯", "历史账户线索"],
  },
  {
    code: "finance.payment.apply.pay",
    label: "付款申请",
    entry: "smart_construction_core.menu_sc_user_payment_apply|smart_construction_core.action_payment_request_user_payment_apply|payment.request",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.payment.apply.receive",
    label: "收款申请",
    entry: "smart_construction_core.menu_sc_user_payment_apply|smart_construction_core.action_payment_request_user_payment_apply|payment.request",
    kind: "create_form",
    retired: "smart_construction_core.menu_payment_request_receive|smart_construction_core.action_payment_request_receive|payment.request",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.expense.reimbursement",
    label: "报销申请",
    entry: "smart_construction_core.menu_sc_reimbursement_request|smart_construction_core.action_sc_expense_claim_reimbursement_request|sc.expense.claim",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.deposit.bid.pay",
    label: "投标保证金缴纳",
    entry: "smart_construction_core.menu_sc_product_current_account_v1|smart_construction_core.action_sc_product_current_account_v1|sc.current.account.workspace",
    kind: "consolidated",
    retired: "smart_construction_core.menu_sc_bid_deposit_pay|smart_construction_core.action_sc_bid_deposit_pay|sc.expense.claim",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.deduction.bill",
    label: "扣款单",
    entry: "smart_construction_core.menu_sc_deduction_bill|smart_construction_core.action_sc_expense_claim_deduction_bill|sc.expense.claim",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "finance.repayment.registration",
    label: "还款登记",
    entry: "smart_construction_core.menu_sc_product_current_account_v1|smart_construction_core.action_sc_product_current_account_v1|sc.current.account.workspace",
    kind: "consolidated",
    retired: "smart_construction_core.menu_sc_repayment_registration|smart_construction_core.action_sc_expense_claim_repayment_registration|sc.expense.claim",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "material.inbound",
    label: "入库单",
    entry: "smart_construction_core.menu_sc_material_inbound|smart_construction_core.action_sc_material_inbound_handling|sc.material.inbound",
    forbidden: ["来源与系统追溯"],
  },
  {
    code: "site.construction.diary",
    label: "施工日志",
    entry: "smart_construction_core.menu_sc_construction_diary|smart_construction_core.action_sc_construction_diary|sc.construction.diary",
    forbidden: ["来源与系统追溯"],
  },
  {
    code: "tax.deduction.registration",
    label: "抵扣登记",
    entry: "smart_construction_core.menu_sc_tax_deduction_registration_user|smart_construction_core.action_sc_tax_deduction_registration_user|sc.tax.deduction.registration",
    forbidden: ["来源与系统追溯"],
  },
  {
    code: "invoice.output.application",
    label: "销项开票申请",
    entry: "smart_construction_core.menu_sc_invoice_application_user|smart_construction_core.action_sc_invoice_application_user|sc.invoice.registration",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "invoice.output.registration",
    label: "销项开票登记",
    entry: "smart_construction_core.menu_sc_invoice_registration_user|smart_construction_core.action_sc_invoice_registration_user|sc.invoice.registration",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "invoice.input.report",
    label: "进项税额上报",
    entry: "smart_construction_core.menu_sc_invoice_input|smart_construction_core.action_sc_invoice_input|sc.invoice.registration",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
  {
    code: "invoice.prepaid_tax",
    label: "预缴税款",
    entry: "smart_construction_core.menu_sc_invoice_prepaid_tax_user|smart_construction_core.action_sc_invoice_prepaid_tax_user|sc.invoice.registration",
    forbidden: ["来源与系统追溯", "迁移来源"],
  },
];

// Declared-entry assertions that are not create-form journeys: the entry header
// must render exactly the declared action set for the declared state.
const DECLARED_ENTRY_ACTION_ASSERTIONS = [
  {
    id: "workspace-entry-actions",
    label: "往来款登记",
    entry: "smart_construction_core.menu_sc_product_current_account_v1|smart_construction_core.action_sc_product_current_account_v1|sc.current.account.workspace",
    note: "baseline header must equal the declared baseline-visible action set",
  },
];

const requestedCodes = new Set(
  String(process.env.CASE_CODES || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean),
);
const CASES = requestedCodes.size
  ? CASE_DEFINITIONS.filter((item) => requestedCodes.has(item.code))
  : CASE_DEFINITIONS;

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
      continue;
    }
    if (ch === '"') inQuotes = true;
    else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

async function loadDeclaredEntryKeys() {
  const keys = new Set();
  const csvRows = parseCsv(await fs.readFile(FORMAL_ENTRY_DECLARATION, "utf8"));
  const header = (csvRows.shift() || []).map((item) => String(item).trim());
  const menuIndex = header.indexOf("menu_xmlid");
  const actionIndex = header.indexOf("action_xmlid");
  const modelIndex = header.indexOf("model");
  if (menuIndex < 0 || actionIndex < 0 || modelIndex < 0) {
    throw new Error(`formal entry declaration is missing the identity columns: ${FORMAL_ENTRY_DECLARATION}`);
  }
  for (const row of csvRows) {
    if (row.length < header.length) continue;
    const key = `${String(row[menuIndex]).trim()}|${String(row[actionIndex]).trim()}|${String(row[modelIndex]).trim()}`;
    if (!key.includes("undefined")) keys.add(key);
  }
  return keys;
}

function routeAuthorityRows(routeAuthority) {
  return [
    ...(routeAuthority?.primary_actions || []),
    ...(routeAuthority?.role_home_actions || []),
    ...(routeAuthority?.contextual_actions || []),
    ...(routeAuthority?.admin_actions || []),
  ];
}

function collectNavigationLeaves(nav) {
  const leaves = [];
  const walk = (nodes) => {
    for (const node of nodes || []) {
      if (!node || typeof node !== "object") continue;
      const meta = node.meta && typeof node.meta === "object" ? node.meta : {};
      if (Number(meta.action_id || 0) > 0) {
        leaves.push({
          label: String(node.label || node.title || "").trim(),
          menuId: Number(node.menu_id || node.id || meta.menu_id || 0),
          actionId: Number(meta.action_id || 0),
          menuXmlid: String(meta.menu_xmlid || ""),
          model: String(meta.model || ""),
        });
      }
      walk(Array.isArray(node.children) ? node.children : []);
    }
  };
  walk(nav);
  return leaves;
}

function parseEntryKey(entryKey) {
  const [menuXmlid, actionXmlid, model] = String(entryKey).split("|");
  return { menuXmlid, actionXmlid, model };
}

function resolveDeclaredEntry(entryKey, declaredKeys, routeAuthority, navLeaves) {
  const { menuXmlid, actionXmlid, model } = parseEntryKey(entryKey);
  if (!menuXmlid || !actionXmlid || !model) {
    return { error: `declared entry identity is incomplete: ${entryKey}` };
  }
  if (!declaredKeys.has(entryKey)) {
    return { error: `declared entry is not present in the governed declaration: ${entryKey}` };
  }
  const row = routeAuthorityRows(routeAuthority).find(
    (item) => String(item?.menu_xmlid || "") === menuXmlid && String(item?.action_xmlid || "") === actionXmlid,
  );
  if (row) {
    const menuId = Number(row.menu_id || 0);
    const actionId = Number(row.action_id || 0);
    if (!menuId || !actionId) {
      return { error: `declared entry resolved without menu/action identity: ${entryKey}` };
    }
    const rowModel = String(row.model || "");
    if (rowModel && rowModel !== model) {
      return { error: `declared entry model drift: declared ${model}, delivered ${rowModel}` };
    }
    return { menuId, actionId, label: String(row.label || ""), via: "route_authority" };
  }
  const leaves = navLeaves.filter((leaf) => leaf.menuXmlid === menuXmlid);
  if (leaves.length !== 1) {
    return { error: `declared entry is not delivered by the runtime navigation (matches=${leaves.length}): ${entryKey}` };
  }
  const [leaf] = leaves;
  if (leaf.model && leaf.model !== model) {
    return { error: `declared entry model drift: declared ${model}, delivered ${leaf.model}` };
  }
  if (!leaf.menuId || !leaf.actionId) {
    return { error: `declared entry navigation node lacks route identity: ${entryKey}` };
  }
  return { menuId: leaf.menuId, actionId: leaf.actionId, label: leaf.label, via: "navigation_contract" };
}

function declaredActionRef(row) {
  const name = String(row?.button?.name || "").trim();
  if (name) return `action.${name}`;
  return String(row?.actionKey || "").trim();
}

// Evaluates the declared `invisible` expression carried by the contract. Unknown
// expression kinds fail closed so a drifted declaration can never silently pass.
function evaluateDeclaredInvisible(expression, values) {
  if (expression === null || expression === undefined) return false;
  if (typeof expression === "boolean") return expression;
  const kind = String(expression.kind || "");
  if (kind === "not") return !evaluateDeclaredInvisible(expression.expr, values);
  if (kind === "any") {
    return (expression.exprs || []).some((item) => evaluateDeclaredInvisible(item, values));
  }
  if (kind === "all") {
    return (expression.exprs || []).every((item) => evaluateDeclaredInvisible(item, values));
  }
  if (kind === "field_truthy") return Boolean(values[String(expression.field || "")]);
  if (kind === "static") return Boolean(expression.value);
  if (kind === "field_compare") {
    const actual = values[String(expression.field || "")];
    const expected = expression.value;
    const operator = String(expression.operator || "");
    if (operator === "==" || operator === "=") return actual === expected;
    if (operator === "!=" || operator === "<>") return actual !== expected;
    if (operator === "in") return Array.isArray(expected) ? expected.includes(actual) : false;
    if (operator === "not in") return Array.isArray(expected) ? !expected.includes(actual) : true;
    throw new Error(`unsupported declared visibility comparison: ${JSON.stringify(expression)}`);
  }
  if (kind === "true") return true;
  if (kind === "false") return false;
  throw new Error(`unsupported declared visibility expression: ${JSON.stringify(expression)}`);
}

function findCachedChromiumExecutable() {
  const explicit = process.env.CHROMIUM_EXECUTABLE_PATH || process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || "";
  if (explicit && fsSync.existsSync(explicit)) {
    return explicit;
  }
  const cacheRoot = path.join(process.env.HOME || "", ".cache", "ms-playwright");
  if (!cacheRoot || !fsSync.existsSync(cacheRoot)) {
    return "";
  }
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

async function login(page) {
  await page.goto(`${BASE_URL}/login?db=${encodeURIComponent(DB_NAME)}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator("input").nth(0).fill(LOGIN);
  await page.locator('input[type="password"]').fill(PASSWORD);
  if (await page.locator("input").count() >= 3) {
    const db = page.locator("input").nth(2);
    if (await db.isEnabled().catch(() => false)) {
      await db.fill(DB_NAME);
    }
  }
  await page.locator('button[type="submit"]').click();
  await page.waitForFunction(() => !window.location.pathname.includes("/login"), null, { timeout: 60000 });
}

async function readToken(page) {
  return page.evaluate(() => {
    const key = Object.keys(sessionStorage).find((item) => item.startsWith("sc_auth_token")) || "";
    return key ? sessionStorage.getItem(key) : "";
  });
}

async function intent(page, token, intentName, params = {}) {
  return page.evaluate(async ({ token, intentName, params, dbName }) => {
    const res = await fetch(`/api/v1/intent?db=${encodeURIComponent(dbName)}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Odoo-DB": dbName,
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ intent: intentName, params, meta: { startup_chain_bypass: true } }),
    });
    const body = await res.json();
    if (!res.ok || body.ok === false) {
      throw new Error(JSON.stringify(body.error || body).slice(0, 700));
    }
    return body.data || body;
  }, { token, intentName, params, dbName: DB_NAME });
}

async function openCreateFromMenu(page, menuId, actionId, code, optionLabel = "") {
  const route = actionId
    ? `/a/${actionId}?db=${encodeURIComponent(DB_NAME)}&menu_id=${menuId}`
    : `/m/${menuId}?db=${encodeURIComponent(DB_NAME)}`;
  await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForURL((url) => url.pathname.startsWith("/a/") || url.pathname.startsWith("/m/"), { timeout: 60000 });
  // The delivered entry must expose its declared create capability. The list
  // chrome class varies per declared action, so the create control itself is
  // the contract-driven anchor rather than a specific container selector.
  const createButton = page.locator("button").filter({ hasText: /^(新建|创建|新增|Create)/ }).first();
  await createButton.waitFor({ state: "attached", timeout: 60000 }).catch(() => {});
  if (!(await createButton.count())) {
    throw new Error("the declared entry exposes no create control");
  }
  await createButton.click();
  await page.waitForTimeout(800);
  if (!page.url().includes("/new")) {
    const pickerText = optionLabel || code;
    const optionButton = page.locator("button", { hasText: pickerText }).last();
    if (await optionButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await optionButton.click();
    } else {
      const codeOption = page.locator("button", { hasText: code }).last();
      if (await codeOption.isVisible({ timeout: 5000 }).catch(() => false)) {
        await codeOption.click();
      }
    }
  }
  await page.waitForURL((url) => url.pathname.includes("/new"), { timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForFunction(
    () => !((document.body?.innerText || "").includes("加载表单中")),
    null,
    { timeout: 60000 },
  ).catch(() => {});
  // The delivered create surface must mount its declared fields; sampling before
  // the contract-driven form is ready would read an empty page as a product gap.
  await page.waitForFunction(
    () => document.querySelectorAll("[data-field-name]").length > 0,
    null,
    { timeout: 60000 },
  ).catch(() => {});
  await page.waitForTimeout(600);
}

async function readRenderedFieldNames(page) {
  return page.evaluate(() => Array.from(new Set(
    Array.from(document.querySelectorAll("[data-field-name]"))
      .map((element) => element.getAttribute("data-field-name"))
      .filter(Boolean),
  ))).catch(() => []);
}

// Notebook pages only mount their active panel, so the declared field surface is
// the union across every tab state. Reading only the landing tab would report a
// required field on another tab as a false product gap.
async function collectRenderedFieldNames(page) {
  const names = new Set(await readRenderedFieldNames(page));
  for (let pass = 0; pass < 3; pass += 1) {
    const tabs = page.locator("[data-section-tab]");
    const count = await tabs.count().catch(() => 0);
    if (!count) break;
    const seenCount = names.size;
    for (let index = 0; index < count; index += 1) {
      await tabs.nth(index).click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(200);
      for (const name of await readRenderedFieldNames(page)) names.add(name);
    }
    if (names.size === seenCount) break;
  }
  return [...names];
}

async function assertDeclaredEntryActions(page, token, assertion, context) {
  const resolved = resolveDeclaredEntry(assertion.entry, context.declaredKeys, context.routeAuthority, context.navLeaves);
  if (resolved.error) {
    return { id: assertion.id, entry: assertion.entry, ok: false, reason: resolved.error };
  }
  const contract = await intent(page, token, "ui.contract.v2", {
    op: "action_open",
    action_id: resolved.actionId,
    menu_id: resolved.menuId,
    model: parseEntryKey(assertion.entry).model,
    view_type: "form",
    render_profile: "create",
    client_type: "web_pc",
    accepted_contract_versions: ["2.0.x", "2.1.x", "2.2.x"],
    client_contract_capabilities: [
      "container_tree.v2",
      "data_source.v2",
      "action_rule.v2",
      "relation_entry.v2",
      "status_contract.v2",
      "form_layout.children_owner.v1",
    ],
  });
  const rules = ((contract?.actionContract || {}).actionRuleList) || [];
  if (!rules.length) {
    return { id: assertion.id, entry: assertion.entry, ok: false, reason: "the declared contract exposes no action rules for this entry" };
  }
  const declared = [];
  for (const rule of rules) {
    const ref = declaredActionRef(rule);
    if (!ref) continue;
    const invisible = rule?.constraints?.visible?.attrs?.invisible || rule?.visible?.attrs?.invisible || null;
    declared.push({
      ref,
      invisible: invisible && invisible.raw ? invisible.raw : null,
      invisibleRaw: invisible,
    });
  }
  if (!declared.length) {
    return { id: assertion.id, entry: assertion.entry, ok: false, reason: "the declared contract exposes no declared action identity" };
  }
  const rawByRef = new Map();
  for (const item of declared) {
    const seen = rawByRef.get(item.ref);
    if (seen && JSON.stringify(seen) !== JSON.stringify(item.invisibleRaw)) {
      return { id: assertion.id, entry: assertion.entry, ok: false, reason: `conflicting declared visibility for ${item.ref}` };
    }
    rawByRef.set(item.ref, item.invisibleRaw);
  }
  const baselineValues = {};
  const declaredBaselineVisible = [];
  const declaredConditional = [];
  for (const item of declared) {
    const expression = item.invisibleRaw;
    if (expression) declaredConditional.push({ ref: item.ref, invisible: item.invisible });
    if (evaluateDeclaredInvisible(expression, baselineValues)) continue;
    declaredBaselineVisible.push(item.ref);
  }
  await page.goto(`${BASE_URL}/a/${resolved.actionId}?db=${encodeURIComponent(DB_NAME)}&menu_id=${resolved.menuId}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
  await page.waitForFunction(() => document.querySelectorAll('[data-action-ref]').length > 0, null, { timeout: 60000 });
  await page.waitForTimeout(500);
  const renderedRefs = await page.evaluate(() =>
    [...document.querySelectorAll("[data-action-ref]")].map((node) => node.getAttribute("data-action-ref")).filter(Boolean),
  );
  const declaredSet = new Set(declaredBaselineVisible);
  const renderedSet = new Set(renderedRefs);
  const undeclared = [...renderedSet].filter((ref) => !declaredSet.has(ref) && !declared.map((item) => item.ref).includes(ref));
  const missing = declaredBaselineVisible.filter((ref) => !renderedSet.has(ref));
  const unexpected = [...renderedSet].filter((ref) => !declaredSet.has(ref));
  const ok = undeclared.length === 0 && missing.length === 0 && unexpected.length === 0;
  const screenshotPath = path.join(ARTIFACT_ROOT, `${assertion.id}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  return {
    id: assertion.id,
    label: assertion.label,
    entry: assertion.entry,
    resolvedVia: resolved.via,
    url: page.url(),
    declaredRefs: declared.map((item) => item.ref),
    declaredConditional,
    declaredBaselineVisible,
    renderedRefs,
    undeclared,
    missing,
    unexpected,
    screenshotPath,
    ok,
    reason: ok ? "" : "rendered header action set does not match the declared baseline action set",
  };
}

// Odoo's ORM virtual record id for an unsaved record (`models.NewId`, serialized
// as `NewId_0x...`). A create-profile contract delivers it under
// `dataContract.mainData.id` — a recorded, frozen convention of this repository
// (docs/contract/snapshots/api_onchange_intent_admin.json) — so a declared
// `invisible` expression such as the native `not id` must resolve that sentinel as
// an unsaved record, exactly as the delivered form does. Reading it as a truthy
// persisted id would invert the declaration and report a correctly hidden create
// region as a rendering gap.
const UNSAVED_RECORD_ID = /^NewId_0x[0-9a-f]+$/i;

function declaredRecordValues(values) {
  const resolved = { ...(values && typeof values === "object" ? values : {}) };
  const id = resolved.id;
  if (typeof id === "string" && UNSAVED_RECORD_ID.test(id.trim())) resolved.id = false;
  return resolved;
}

function declaredUnsavedRecord(values) {
  const raw = values && typeof values === "object" ? values.id : undefined;
  return typeof raw === "string" && UNSAVED_RECORD_ID.test(raw.trim());
}

// Ground-truth native layout visibility: a field renders only when its own and
// every ancestor node's declared `invisible` expression evaluates false against
// the create defaults carried by the contract (`dataContract.mainData`). This is
// evaluated from the declaration, not from the delivered status, so a projection
// that wrongly hides an occurrence cannot excuse itself.
function collectNativeFieldVisibility(containerTree, defaults) {
  const baseline = declaredRecordValues(defaults);
  const visibility = new Map();
  const walk = (node, ancestorHidden) => {
    if (Array.isArray(node)) {
      for (const item of node) walk(item, ancestorHidden);
      return;
    }
    if (!node || typeof node !== "object") return;
    const expression = node.modifiers && typeof node.modifiers === "object" ? node.modifiers.invisible : null;
    let hidden = ancestorHidden;
    let unknown = false;
    if (!hidden) {
      try {
        hidden = evaluateDeclaredInvisible(expression, baseline);
      } catch {
        unknown = true;
      }
    }
    if (node.type === "field" && node.name) {
      const name = String(node.name);
      const occurrenceVisible = !hidden && !unknown;
      const prior = visibility.get(name);
      // The delivered status contract is per field, not per occurrence, so a
      // field is visible when any declared occurrence survives its ancestor
      // chain; one hidden duplicate must not overwrite a visible one.
      visibility.set(name, {
        nativeVisible: prior ? prior.nativeVisible || occurrenceVisible : occurrenceVisible,
        unknown: prior ? prior.unknown || unknown : unknown,
      });
    }
    for (const key of ["children", "nodes", "items"]) walk(node[key] || [], hidden);
  };
  walk(containerTree || [], false);
  return visibility;
}

function collectStatusbarFieldNames(containerTree) {
  const names = new Set();
  const walk = (node) => {
    if (Array.isArray(node)) {
      for (const item of node) walk(item);
      return;
    }
    if (!node || typeof node !== "object") return;
    if (node.type === "field" && node.name) {
      const widgets = [String(node.widget || "").trim(), String(node.attributes?.widget || "").trim()];
      if (widgets.includes("statusbar")) names.add(String(node.name));
    }
    for (const key of ["children", "nodes", "items"]) walk(node[key] || []);
  };
  walk(containerTree || []);
  return names;
}

function collectLayoutFieldNames(containerTree) {
  const names = new Set();
  const walk = (node) => {
    if (Array.isArray(node)) {
      for (const item of node) walk(item);
      return;
    }
    if (!node || typeof node !== "object") return;
    if (node.type === "field" && node.name) names.add(String(node.name));
    for (const key of ["children", "nodes", "items"]) walk(node[key] || []);
  };
  walk(containerTree || []);
  return names;
}

function fieldNameFromWidgetId(widgetId) {
  const match = /^field\.(.+?)\.occ\./.exec(String(widgetId || ""));
  return match ? match[1] : "";
}

// Aggregates the delivered status per field name. A field is "declared required,
// visible and editable" when at least one delivered occurrence is required,
// visible and not readonly; "declared visible and editable" when at least one
// occurrence is visible, not readonly and not denied by authorization.
function aggregateDeliveredFieldStatus(widgetStatus) {
  const aggregated = new Map();
  for (const entry of Array.isArray(widgetStatus) ? widgetStatus : []) {
    const name = fieldNameFromWidgetId(entry && entry.widgetId);
    if (!name) continue;
    const current = aggregated.get(name) || { visible: false, readonly: true, required: false, denied: true };
    const visible = entry.visible !== false;
    const readonly = entry.readonly === true;
    const auth = String(entry.auth || "");
    current.visible = current.visible || visible;
    current.readonly = current.readonly && readonly;
    current.required = current.required || entry.required === true;
    current.denied = current.denied && (auth === "none");
    aggregated.set(name, current);
  }
  return aggregated;
}

// A consolidated code's standalone entry must no longer be part of the governed
// delivered surface. The locked formal product menu policy, the published product
// policy, the daily acceptance navigation policy and the delivered-entry
// declaration all agree on the same 89 entries; these standalone handling menus are
// absent from all four. If one comes back the consolidation has drifted and must be
// re-declared by the owner, so this check fails closed instead of tolerating it.
function checkRetiredConsolidation(testCase, declaredKeys, navLeaves) {
  const retired = String(testCase.retired || "");
  if (!retired) return "";
  if (declaredKeys.has(retired)) {
    return `retired standalone entry is still present in the governed delivered-entry declaration: ${retired}`;
  }
  const { menuXmlid } = parseEntryKey(retired);
  const matches = navLeaves.filter((leaf) => leaf.menuXmlid === menuXmlid);
  if (matches.length) {
    return `retired standalone entry is still delivered by the runtime navigation (matches=${matches.length}): ${retired}`;
  }
  return "";
}

async function main() {
  await fs.rm(ARTIFACT_ROOT, { recursive: true, force: true });
  await fs.mkdir(ARTIFACT_ROOT, { recursive: true });
  const declaredKeys = await loadDeclaredEntryKeys();
  const executablePath = findCachedChromiumExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, locale: "zh-CN" });
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text().slice(0, 500));
    }
  });
  page.on("pageerror", (err) => consoleErrors.push(err.message.slice(0, 500)));

  // The assertion consumes the same create-profile contract the frontend fetches
  // (`ui.contract.v2 op=model render_profile=create`), captured per navigation so
  // the check can never be satisfied by a contract the page did not receive.
  let deliveredCreateContract = null;
  let deliveredCreateContractModel = "";
  page.on("response", async (response) => {
    if (!response.url().includes("/api/v1/intent")) return;
    let request;
    try {
      request = JSON.parse(response.request().postData() || "{}");
    } catch {
      return;
    }
    if (request.intent !== "ui.contract.v2") return;
    const params = request.params || {};
    if (params.op !== "model" || params.render_profile !== "create") return;
    let body;
    try {
      body = await response.json();
    } catch {
      return;
    }
    const contract = body && body.data ? body.data : body;
    if (!contract || !contract.statusContract) return;
    deliveredCreateContract = contract;
    deliveredCreateContractModel = String(params.model || contract?.pageInfo?.model || "");
  });

  await login(page);
  const token = await readToken(page);
  if (!token) {
    throw new Error("login token missing");
  }
  const init = await intent(page, token, "system.init", {
    with_preload: false,
    with: ["workspace_home"],
    root_xmlid: "smart_construction_core.menu_sc_root",
  });
  const nav = init?.navigation?.nav || [];
  const routeAuthority = init?.navigation?.route_authority || {};
  const navLeaves = collectNavigationLeaves(nav);
  const context = { declaredKeys, routeAuthority, navLeaves };
  const results = [];
  const errors = [];

  for (const testCase of CASES) {
    const retirementBreach = checkRetiredConsolidation(testCase, declaredKeys, navLeaves);
    if (retirementBreach) {
      errors.push(`${testCase.code}: ${retirementBreach}`);
      results.push({
        code: testCase.code,
        entry: testCase.entry,
        kind: testCase.kind || "create_form",
        retired: testCase.retired || "",
        retiredAbsentFromDeclaration: false,
        ok: false,
        reason: retirementBreach,
      });
      continue;
    }
    if (testCase.kind === "consolidated") {
      // The standalone create surface is gone; the delivered carrier entry is the
      // declared unified handling entry. Assert it the same way every other
      // declared entry is asserted: capture the delivered action contract, then
      // require the rendered header action set to equal the declared baseline
      // action set. This is real behavior bound to a declared contract, not a
      // selector or text coincidence.
      const outcome = await assertDeclaredEntryActions(page, token, {
        id: `consolidated-${testCase.code.replaceAll(".", "_")}`,
        label: testCase.label,
        entry: testCase.entry,
      }, context);
      results.push({
        ...outcome,
        code: testCase.code,
        kind: "consolidated",
        retired: testCase.retired,
        retiredAbsentFromDeclaration: !declaredKeys.has(testCase.retired),
      });
      if (!outcome.ok) errors.push(`${testCase.code}: ${outcome.reason}`);
      continue;
    }
    const node = resolveDeclaredEntry(testCase.entry, declaredKeys, routeAuthority, navLeaves);
    if (node.error) {
      errors.push(`${testCase.code}: ${node.error}`);
      results.push({ code: testCase.code, entry: testCase.entry, ok: false, reason: node.error });
      continue;
    }
    deliveredCreateContract = null;
    deliveredCreateContractModel = "";
    try {
      await openCreateFromMenu(page, node.menuId, node.actionId, testCase.code, testCase.label);
    } catch (err) {
      const reason = `cannot open the declared entry create form: ${err instanceof Error ? err.message.slice(0, 200) : String(err)}`;
      errors.push(`${testCase.code}: ${reason}`);
      results.push({ code: testCase.code, entry: testCase.entry, menuId: node.menuId, actionId: node.actionId, ok: false, reason });
      continue;
    }

    const contract = deliveredCreateContract;
    const contractCaptured = Boolean(contract && contract.statusContract);
    const widgetStatus = contractCaptured ? contract.statusContract.widgetStatus : [];
    const defaults = (contractCaptured && contract.dataContract && contract.dataContract.mainData) || {};
    // A create-profile contract must describe an unsaved record. Delivering a
    // persisted id here would bind the create surface to an existing record and
    // silently invalidate every declaration evaluated against these values, so
    // that state fails closed instead of being normalised away.
    const createIdValue = Object.prototype.hasOwnProperty.call(defaults, "id") ? defaults.id : undefined;
    const createRecordIdKind = createIdValue === undefined || createIdValue === null || createIdValue === false || createIdValue === 0
      ? "absent"
      : (declaredUnsavedRecord(defaults) ? "unsaved_sentinel" : "persisted");
    const containerTree = (contractCaptured && contract.layoutContract && contract.layoutContract.containerTree) || [];
    const nativeVisibility = collectNativeFieldVisibility(containerTree, defaults);
    const layoutFieldNames = collectLayoutFieldNames(containerTree);
    const deliveredFields = aggregateDeliveredFieldStatus(widgetStatus);
    const statusbarFields = collectStatusbarFieldNames(containerTree);
    const declaredFieldNames = new Set([...layoutFieldNames, ...deliveredFields.keys()]);

    const domFieldNames = await collectRenderedFieldNames(page);
    const domFieldSet = new Set(domFieldNames);

    const declaredRequired = [];
    const declaredVisibleEditable = [];
    const unknownVisibility = [];
    const policyHiddenDeclaredVisible = [];
    const nativeHiddenDeclaredVisible = [];
    for (const [name, status] of deliveredFields) {
      if (statusbarFields.has(name)) continue;
      const native = nativeVisibility.get(name);
      if (native && native.unknown) {
        unknownVisibility.push(name);
        if (status.required && status.visible && !status.readonly) declaredRequired.push(name);
        continue;
      }
      const nativeVisible = native ? native.nativeVisible : false;
      if (nativeVisible && status.visible && !status.denied) {
        if (status.required && !status.readonly) declaredRequired.push(name);
        if (!status.readonly) declaredVisibleEditable.push(name);
      }
      if (nativeVisible && !status.visible) policyHiddenDeclaredVisible.push(name);
      if (!nativeVisible && status.visible) nativeHiddenDeclaredVisible.push(name);
    }
    // Gate: a field the delivered contract declares required, visible and
    // editable must be rendered. Declaration-only drift in the other direction
    // (declared visible but not rendered) is recorded as evidence, not silently
    // treated as a pass and not used to weaken the required-field gate.
    const missing = declaredRequired
      .filter((name) => !domFieldSet.has(name))
      .filter((name, index, list) => list.indexOf(name) === index);
    const declaredVisibleNotRendered = declaredVisibleEditable
      .filter((name) => !domFieldSet.has(name));
    const undeclared = domFieldNames.filter((name) => !declaredFieldNames.has(name));

    const screenshotPath = path.join(ARTIFACT_ROOT, `${testCase.code.replaceAll(".", "_")}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const bodyText = await page.locator("body").innerText({ timeout: 30000 }).catch(() => "");
    const leakedFinal = testCase.forbidden.filter((text) => bodyText.includes(text));
    const contractModelOk = !deliveredCreateContractModel || deliveredCreateContractModel === parseEntryKey(testCase.entry).model;
    const ok = contractCaptured
      && contractModelOk
      && createRecordIdKind !== "persisted"
      && domFieldNames.length > 0
      && missing.length === 0
      && undeclared.length === 0
      && leakedFinal.length === 0;
    if (!ok) {
      errors.push(`${testCase.code}: captured=${contractCaptured} createId=${createRecordIdKind} domFields=${domFieldNames.length} missing=${missing.join(",")} undeclared=${undeclared.join(",")} leaked=${leakedFinal.join(",")}`);
    }
    results.push({
      code: testCase.code,
      entry: testCase.entry,
      kind: testCase.kind || "create_form",
      retired: testCase.retired || "",
      retiredAbsentFromDeclaration: testCase.retired
        ? !declaredKeys.has(testCase.retired)
        : null,
      resolvedVia: node.via,
      menuId: node.menuId,
      actionId: node.actionId,
      label: node.label,
      url: page.url(),
      contractCaptured,
      contractModel: deliveredCreateContractModel,
      contractModelOk,
      createRecordIdKind,
      domFieldCount: domFieldNames.length,
      declaredRequired,
      declaredVisibleEditable,
      declaredVisibleNotRendered,
      unknownVisibility,
      policyHiddenDeclaredVisible,
      nativeHiddenDeclaredVisible,
      undeclared,
      missing,
      leaked: leakedFinal,
      screenshotPath,
      ok,
    });
  }

  const declaredEntryAssertions = [];
  for (const assertion of DECLARED_ENTRY_ACTION_ASSERTIONS) {
    let outcome;
    try {
      outcome = await assertDeclaredEntryActions(page, token, assertion, context);
    } catch (err) {
      outcome = {
        id: assertion.id,
        entry: assertion.entry,
        ok: false,
        reason: err instanceof Error ? err.message.slice(0, 300) : String(err),
      };
    }
    declaredEntryAssertions.push(outcome);
    if (!outcome.ok) {
      errors.push(`${assertion.id}: ${outcome.reason}`);
    }
  }

  const report = {
    ok: errors.length === 0 && consoleErrors.length === 0,
    baseUrl: BASE_URL,
    dbName: DB_NAME,
    login: LOGIN,
    declaredEntryCount: declaredKeys.size,
    results,
    declaredEntryAssertions,
    errors,
    consoleErrors,
  };
  await fs.writeFile(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  await browser.close();

  if (!report.ok) {
    console.error(JSON.stringify(report, null, 2));
    process.exit(1);
  }
  console.log(JSON.stringify(report, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
