import { launchChromium } from './playwright_runtime.mjs';

const expectedTypes = ['char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'html'];
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  await page.setContent(`
    <!doctype html><html><body>
      <div role="dialog" aria-labelledby="title">
        <h2 id="title">新增字段</h2>
        <form id="field-create" data-semantic-component="LowCodeFieldCreateForm">
          <label for="field-label">字段标题</label>
          <input id="field-label" name="label" required autofocus>
          <label for="field-type">字段类型</label>
          <select id="field-type" name="ttype" required>
            <option value="char">单行文本</option><option value="text">多行文本</option>
            <option value="integer">整数</option><option value="float">小数</option>
            <option value="boolean">是/否</option><option value="date">日期</option>
            <option value="datetime">日期时间</option><option value="html">富文本</option>
          </select>
          <footer data-semantic-component="LowCodeFieldCreateActions">
            <button type="button">取消</button><button type="submit">创建字段</button>
          </footer>
        </form>
      </div>
      <script>
        window.fieldCreateEvidence = { submits: 0 };
        document.querySelector('#field-create').addEventListener('submit', (event) => {
          event.preventDefault(); window.fieldCreateEvidence.submits += 1;
        });
      </script>
    </body></html>
  `);
  const form = page.locator('#field-create');
  const label = form.locator('#field-label');
  const type = form.locator('#field-type');
  const submit = form.getByRole('button', { name: '创建字段' });
  await submit.click();
  const emptySubmits = await page.evaluate(() => window.fieldCreateEvidence.submits);
  await label.fill('专业字段');
  await type.selectOption('datetime');
  await submit.click();
  const evidence = await page.evaluate(() => window.fieldCreateEvidence);
  const options = await type.locator('option').evaluateAll((nodes) => nodes.map((node) => node.value));
  const labels = await form.locator('label').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('for')));
  const primaryCount = await form.getByRole('button', { name: '创建字段' }).count();
  const cancelCount = await form.getByRole('button', { name: '取消' }).count();
  const pass = emptySubmits === 0
    && evidence.submits === 1
    && JSON.stringify(options) === JSON.stringify(expectedTypes)
    && JSON.stringify(labels) === JSON.stringify(['field-label', 'field-type'])
    && await label.getAttribute('autofocus') === ''
    && await label.getAttribute('required') === ''
    && await type.getAttribute('required') === ''
    && primaryCount === 1
    && cancelCount === 1;
  console.log(JSON.stringify({ pass, emptySubmits, evidence, options, labels, primaryCount, cancelCount }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
}
