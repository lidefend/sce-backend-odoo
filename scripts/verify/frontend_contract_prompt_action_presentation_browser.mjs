import { launchChromium } from './playwright_runtime.mjs';

const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  await page.setContent(`
    <!doctype html><html><body>
      <form id="prompt">
        <label for="reason">原因</label>
        <input id="reason" name="reason" required aria-required="true">
        <label for="decision">决定</label>
        <select id="decision" name="decision" required aria-required="true">
          <option value=""></option><option value="approve">同意</option><option value="reject">拒绝</option>
        </select>
        <button type="button">取消</button><button type="submit">确定</button>
      </form>
      <script>
        window.promptEvidence = { submits: 0, changes: [] };
        document.querySelector('#prompt').addEventListener('submit', (event) => {
          event.preventDefault(); window.promptEvidence.submits += 1;
        });
        document.querySelectorAll('input, select').forEach((control) => {
          control.addEventListener('change', () => window.promptEvidence.changes.push([control.name, control.value]));
        });
      </script>
    </body></html>
  `);
  const form = page.locator('#prompt');
  const text = form.locator('#reason');
  const select = form.locator('#decision');
  const submit = form.getByRole('button', { name: '确定' });
  await submit.click();
  const emptySubmits = await page.evaluate(() => window.promptEvidence.submits);
  await text.fill('需要补充依据');
  await text.press('Tab');
  await select.selectOption('approve');
  await submit.click();
  const evidence = await page.evaluate(() => window.promptEvidence);
  const labels = await form.locator('label').evaluateAll((nodes) => nodes.map((node) => ({ text: node.textContent?.trim(), target: node.getAttribute('for') })));
  const controlIds = [await text.getAttribute('id'), await select.getAttribute('id')];
  const required = [await text.getAttribute('required'), await select.getAttribute('required')];
  const pass = emptySubmits === 0
    && evidence.submits === 1
    && evidence.changes.some(([name, value]) => name === 'reason' && value === '需要补充依据')
    && evidence.changes.some(([name, value]) => name === 'decision' && value === 'approve')
    && JSON.stringify(labels.map((item) => item.text)) === JSON.stringify(['原因', '决定'])
    && labels.every((item, index) => item.target === controlIds[index])
    && required.every((value) => value === '');
  console.log(JSON.stringify({ pass, emptySubmits, evidence, labels, controlIds, required }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
}
