import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const entryId = '\0collaboration-primitives-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0 },
  plugins: [{
    name: 'collaboration-primitives-browser-harness',
    configureServer(vite) {
      vite.middlewares.use('/__collaboration_primitives.html', (_request, response) => {
        response.setHeader('content-type', 'text/html');
        response.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="app"></div><script type="module" src="/__collaboration_primitives.js"></script></body></html>');
      });
    },
    resolveId(id) { return id === '/__collaboration_primitives.js' ? entryId : undefined; },
    load(id) {
      if (id !== entryId) return undefined;
      return `
        import { createApp, h, reactive } from 'vue';
        import Composer from '/src/pages/contractForm/ProfessionalCollaborationComposer.vue';
        import Attachments from '/src/pages/contractForm/ProfessionalAttachmentManager.vue';
        import '/src/styles/design-system.css';
        const state = reactive({ draft: '', note: '', posting: false, selected: '', updates: 0 });
        window.collaborationState = state;
        createApp({ render() { return h('main', [
          h(Composer, {
            activity: false, posting: state.posting, usersLoading: false, draft: state.draft,
            placeholder: '输入评论', submitLabel: '发送', postingLabel: '发送中', submitDisabled: false,
            collaborationUserQuery: '', selectedMentionUsers: [], collaborationUserChoices: [],
            activityAssigneeOptions: [], activityAssigneeId: 0, activityAssigneeLabel: '负责人',
            activitySummary: '', activityDeadline: '', activityNote: state.note,
            activitySummaryLabel: '摘要', activityDeadlineLabel: '期限', activityNoteLabel: '说明',
            activitySummaryPlaceholder: '摘要', activityNotePlaceholder: '说明',
            'onUpdate:draft': (value) => { state.draft = value; state.updates += 1; },
          }),
          h(Attachments, {
            editable: true, enabled: true, uploading: state.posting, uploadLabel: '上传附件',
            uploadingLabel: '上传中', error: '', pending: [],
            onSelected: (event) => { state.selected = event.target?.files?.[0]?.name || ''; },
          }),
        ]); } }).mount('#app');
      `;
    },
  }],
});

await server.listen();
const address = server.httpServer?.address();
if (!address || typeof address === 'string') throw new Error('collaboration harness did not expose a TCP port');
const browser = await launchChromium({ headless: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console:${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`page:${error.message}`));
  await page.goto(`http://127.0.0.1:${address.port}/__collaboration_primitives.html`);

  const textarea = page.locator('[data-professional-collaboration-component="composer"] [data-semantic-component="ScTextarea"]');
  await textarea.fill('协作内容');
  const updated = await page.evaluate(() => ({ draft: window.collaborationState.draft, updates: window.collaborationState.updates }));
  await page.evaluate(() => { window.collaborationState.posting = true; });
  const disabled = await textarea.isDisabled();
  const busy = await textarea.getAttribute('aria-busy');
  const beforeBlockedInput = await page.evaluate(() => window.collaborationState.updates);
  await textarea.dispatchEvent('input');
  const afterBlockedInput = await page.evaluate(() => window.collaborationState.updates);
  await page.evaluate(() => { window.collaborationState.posting = false; });

  const fileInput = page.locator('[data-professional-collaboration-component="attachments"] input[type="file"]');
  await fileInput.setInputFiles({ name: 'contract-note.txt', mimeType: 'text/plain', buffer: Buffer.from('fixture') });
  const selected = await page.evaluate(() => window.collaborationState.selected);
  const filePrimitivePresent = await page.locator('[data-professional-collaboration-component="attachments"] .sc-file-field').count() === 1;

  const pass = updated.draft === '协作内容' && updated.updates > 0
    && disabled && busy === 'true' && beforeBlockedInput === afterBlockedInput
    && selected === 'contract-note.txt' && filePrimitivePresent && errors.length === 0;
  console.log(JSON.stringify({ pass, updated, disabled, busy, blockedInput: beforeBlockedInput === afterBlockedInput, selected, filePrimitivePresent, errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}
