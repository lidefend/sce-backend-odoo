#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { launchChromium } from './playwright_runtime.mjs';

const require = createRequire(import.meta.url);
const axeModule = require(require.resolve('@axe-core/playwright', { paths: [path.resolve('frontend/apps/web/node_modules')] }));
const AxeBuilder = axeModule.default || axeModule;
const baseUrl = process.env.FRONTEND_URL || 'http://127.0.0.1:5198';
const output = path.resolve(process.env.ARTIFACT_DIR || '/tmp/frontend-tdesign-foundation');
const viewports = [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
];
const results = [];
const sourceSha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const sourceDirty = Boolean(execFileSync('git', ['status', '--short'], { encoding: 'utf8' }).trim());
const packageManifest = JSON.parse(await fs.readFile('frontend/apps/web/package.json', 'utf8'));
const engineVersions = {
  tdesign_vue_next: packageManifest.dependencies?.['tdesign-vue-next'],
  tdesign_icons_vue_next: packageManifest.dependencies?.['tdesign-icons-vue-next'],
};

await fs.mkdir(output, { recursive: true });
const browser = await launchChromium();
try {
  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const runtime = { console: [], pageerror: [], http: [] };
    page.on('console', (message) => {
      if (message.type() === 'error' && !/Failed to load resource/i.test(message.text())) runtime.console.push(message.text());
    });
    page.on('pageerror', (error) => runtime.pageerror.push(error.message));
    page.on('response', (response) => {
      if (response.status() >= 400 && !/favicon/i.test(response.url())) runtime.http.push({ status: response.status(), url: response.url() });
    });
    await page.goto(`${baseUrl}/acceptance/tdesign-foundation.html`, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(500);
    if (await page.getByRole('heading', { name: '企业 UI 引擎验收夹具' }).count() === 0) {
      throw new Error(`${viewport.width}x${viewport.height}: fixture failed to mount ${JSON.stringify(runtime)}`);
    }

    const engineMarkers = await page.locator('[data-ui-engine]').count();
    if (engineMarkers < 11) throw new Error(`${viewport.width}x${viewport.height}: missing UI engine markers (${engineMarkers})`);
    const firstRow = page.locator('.sc-hierarchy-table tbody tr').first();
    await firstRow.focus();
    await firstRow.press('Enter');
    await page.getByRole('button', { name: '折叠层级' }).click();
    await page.getByRole('button', { name: '展开层级' }).click();
    await page.getByText('子节点 A', { exact: true }).click();
    await page.getByText('子节点 B', { exact: true }).dblclick();
    await page.getByRole('textbox', { name: '选项' }).click();
    await page.getByRole('listitem', { name: '选项 B' }).click();
    await page.getByRole('textbox', { name: '文本' }).fill('统一文本控件');
    await page.getByRole('textbox', { name: '说明' }).fill('统一多行控件');
    await page.locator('.sc-design-checkbox[aria-label="确认统一控件"]').click();
    if (!(await page.getByRole('checkbox', { name: '确认统一控件' }).isChecked())) {
      throw new Error(`${viewport.width}x${viewport.height}: checkbox state was not committed`);
    }
    await page.getByRole('button', { name: '打开对话框' }).click();
    await page.getByRole('dialog', { name: '通用对话框' }).waitFor();
    await page.getByRole('button', { name: '关闭对话框' }).click();
    await page.getByRole('button', { name: '打开抽屉' }).click();
    await page.getByRole('dialog', { name: '通用抽屉' }).waitFor();
    await page.getByRole('button', { name: '关闭抽屉' }).click();
    await page.evaluate(() => {
      window.getSelection()?.removeAllRanges();
      document.querySelector('.sc-hierarchy-table')?.scrollTo({ left: 0 });
      document.querySelector('.t-table__content')?.scrollTo({ left: 0 });
    });

    const geometry = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      selected: document.body.textContent?.includes('已选择：child-b') || false,
      opened: document.body.textContent?.includes('已打开：child-b') || false,
      selectedOption: document.body.textContent?.includes('当前选项：b') || false,
      textField: document.body.textContent?.includes('文本：统一文本控件') || false,
      textArea: document.body.textContent?.includes('说明：统一多行控件') || false,
      checkbox: document.body.textContent?.includes('确认：是') || false,
      hierarchy: (() => {
        const root = document.querySelector('.sc-hierarchy-table');
        const content = document.querySelector('.t-table__content');
        const firstHeader = document.querySelector('.t-table th');
        return {
          root_scroll_left: root?.scrollLeft || 0,
          root_scroll_width: root?.scrollWidth || 0,
          root_client_width: root?.clientWidth || 0,
          content_scroll_left: content?.scrollLeft || 0,
          content_scroll_width: content?.scrollWidth || 0,
          content_client_width: content?.clientWidth || 0,
          root_left: root?.getBoundingClientRect().left || 0,
          first_header_left: firstHeader?.getBoundingClientRect().left || 0,
        };
      })(),
    }));
    if (geometry.documentWidth > geometry.viewportWidth + 1) throw new Error(`${viewport.width}x${viewport.height}: page horizontal overflow`);
    if (!geometry.selected || !geometry.opened || !geometry.selectedOption || !geometry.textField || !geometry.textArea || !geometry.checkbox) {
      throw new Error(`${viewport.width}x${viewport.height}: interaction state missing`);
    }
    if (geometry.hierarchy.content_scroll_left !== 0 || geometry.hierarchy.first_header_left < geometry.hierarchy.root_left - 1) {
      throw new Error(`${viewport.width}x${viewport.height}: hierarchy left edge is clipped`);
    }
    if (runtime.console.length || runtime.pageerror.length || runtime.http.length) throw new Error(`${viewport.width}x${viewport.height}: runtime errors ${JSON.stringify(runtime)}`);

    const accessibility = await new AxeBuilder({ page }).analyze();
    const severe = accessibility.violations.filter((item) => ['serious', 'critical'].includes(item.impact || ''));
    if (severe.length) throw new Error(`${viewport.width}x${viewport.height}: serious accessibility violations ${severe.map((item) => item.id).join(',')}`);
    const screenshot = path.join(output, `tdesign-foundation-${viewport.width}x${viewport.height}.png`);
    await page.screenshot({ path: screenshot, fullPage: true });
    const screenshotSha256 = createHash('sha256').update(await fs.readFile(screenshot)).digest('hex');
    results.push({ viewport: `${viewport.width}x${viewport.height}`, engine_markers: engineMarkers, overflow: 0, hierarchy_geometry: geometry.hierarchy, serious_accessibility_violations: 0, screenshot, screenshot_sha256: screenshotSha256 });
    await context.close();
  }
} finally {
  await browser.close();
}

await fs.writeFile(path.join(output, 'report.json'), `${JSON.stringify({ status: 'PASS', source_sha: sourceSha, source_dirty: sourceDirty, base_url: baseUrl, engine_versions: engineVersions, results }, null, 2)}\n`, 'utf8');
console.log(`[frontend-tdesign-foundation-browser] PASS viewports=${results.length} output=${output}`);
