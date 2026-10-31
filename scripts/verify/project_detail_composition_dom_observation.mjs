// Read-only runtime observation for project.project Action 590/652.
// Captures the page root structure-source attributes and native vs legacy
// field-node counts without mutating any business data.
import { launchChromium } from './playwright_runtime.mjs';

const BASE = process.env.SC_FRONTEND_BASE_URL || 'http://127.0.0.1:5178';
const LOGIN = process.env.SC_OBSERVATION_LOGIN || 'fixture_role_config_admin';
const PASSWORD = process.env.SC_OBSERVATION_PASSWORD || 'scdevpass';
const ACTIONS = [590, 652];

const browser = await launchChromium({ headless: true });
const page = await browser.newPage();
const results = [];
try {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#login-username', { timeout: 30000 });
  await page.fill('#login-username', LOGIN);
  await page.fill('#login-password', PASSWORD);
  await Promise.all([
    page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {}),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForTimeout(4000);

  for (const actionId of ACTIONS) {
    try {
      await page.goto(`${BASE}/a/${actionId}`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('[data-semantic-component="ContractFormPage"]', { timeout: 30000 });
      await page.waitForTimeout(2500);
      const snapshot = await page.evaluate(() => {
        const root = document.querySelector('[data-semantic-component="ContractFormPage"]');
        if (!root) return { error: 'ContractFormPage root not found' };
        return {
          url: location.href,
          formComposition: root.getAttribute('data-form-composition'),
          formCompositionReason: root.getAttribute('data-form-composition-reason'),
          detailComposition: root.getAttribute('data-detail-composition'),
          detailAdopted: root.getAttribute('data-detail-composition-adopted'),
          shadowLayoutSource: root.getAttribute('data-v2-shadow-layout-source'),
          shadowGlobalSource: root.getAttribute('data-v2-shadow-global-source'),
          shadowFieldOverlap: root.getAttribute('data-v2-shadow-field-overlap'),
          shadowSourceContext: root.getAttribute('data-v2-shadow-source-context'),
          nativeLocatorCount: document.querySelectorAll('[data-native-locator]').length,
          legacyFormSectionCount: document.querySelectorAll('[data-semantic-component="FormSection"],.template-form-section').length,
          nativeTreeCount: document.querySelectorAll('[data-semantic-component="NativeFormTreeRenderer"]').length,
        };
      });
      results.push({ actionId, ...snapshot });
    } catch (err) {
      results.push({ actionId, error: String(err && err.message ? err.message : err).slice(0, 240) });
    }
  }
} catch (err) {
  results.push({ login: 'failed', error: String(err && err.message ? err.message : err).slice(0, 240) });
} finally {
  console.log(JSON.stringify({ base: BASE, login: LOGIN, results }, null, 2));
  await browser.close();
}
