import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';

const entryId = '\0collaboration-primitives-browser-entry';
const server = await createServer({
  root: new URL('../../frontend/apps/web', import.meta.url).pathname,
  logLevel: 'error',
  server: { host: '127.0.0.1', port: 0, hmr: false },
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
        import NativeContractSurface from '/src/pages/contractForm/CanonicalNativeFormSurface.vue';
        import '/src/styles/design-system.css';
        const state = reactive({ draft: '', note: '', posting: false, selected: '', updates: 0 });
        window.collaborationState = state;
        // The panel mode is a contract declaration, never a form render mode.
        // panelReadonly stands in for the value the contract resolver computes.
        const declaredSurfaceProps = (panelReadonly) => ({
          nativeBridge: null, sectionLinks: [], renderMode: 'readonly',
          visibleActions: [], directActions: [], overflowActions: [], effectivePrimaryKey: '',
          showCollaborationPanel: true, auditVisible: false, auditDeclared: false,
          collaborationPanelProps: {
            readonly: panelReadonly, title: '协作记录', unavailableMessage: '', busy: false, posting: false,
            usersLoading: false, userSearchEnabled: false, activeMode: '', activeIsActivity: false,
            activePlaceholder: '', activeSubmitLabel: '', activePostingLabel: '', chatterDraft: '', replyTarget: null,
            collaborationUserQuery: '', selectedMentionUsers: [], collaborationUserChoices: [],
            activityAssigneeOptions: [], activityAssigneeId: 0, activityAssigneeLabel: '',
            activitySummary: '', activityDeadline: '', activityNote: '', activitySummaryLabel: '',
            activityDeadlineLabel: '', activityNoteLabel: '', activitySummaryPlaceholder: '',
            activityNotePlaceholder: '', submitDisabled: false, chatterError: '',
            actions: [
              { key: 'message', label: '发送消息', intent: 'message', mode: 'message', payload: {}, enabled: true, hint: 'message' },
              { key: 'activity', label: '安排活动', intent: 'activity', mode: 'activity', payload: {}, enabled: true, hint: 'activity' },
            ],
            hasAttachments: true, attachmentUploading: false, attachmentDeletingIds: [], messageDeletingIds: [],
            attachmentUploadEnabled: true, attachmentUploadLabel: '上传附件', attachmentUploadingLabel: '上传中',
            attachmentViewLabel: '查看', attachmentError: '', pendingAttachments: [],
            followerEnabled: true, followerLabel: '关注者', followers: [], followerCount: 0, followersLoading: false,
            followerError: '', canFollow: true, canUnfollow: false, followLabel: '关注', unfollowLabel: '取消关注',
            timeline: [], timelineHasMore: false, timelineLoading: false, activityUpdatingIds: [],
          },
          collaborationPanelListeners: {},
        });
        createApp({ render() { return h('main', [
          h('div', { 'data-surface-harness': 'primitives' }, [
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
            onSelected: (file) => { state.selected = file?.name || ''; },
          }),
          ]),
          h('div', { 'data-surface-harness': 'declared-live' }, [h(NativeContractSurface, declaredSurfaceProps(false))]),
          h('div', { 'data-surface-harness': 'declared-readonly' }, [h(NativeContractSurface, declaredSurfaceProps(true))]),
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

  const primitives = page.locator('[data-surface-harness="primitives"]');
  const textareaHost = primitives.locator('[data-professional-collaboration-component="composer"] [data-semantic-component="ScTextarea"]');
  const textarea = textareaHost.locator('textarea');
  await textarea.fill('协作内容');
  const updated = await page.evaluate(() => ({ draft: window.collaborationState.draft, updates: window.collaborationState.updates }));
  await page.evaluate(() => { window.collaborationState.posting = true; });
  const disabled = await textarea.isDisabled();
  const busy = await textareaHost.getAttribute('aria-busy');
  const beforeBlockedInput = await page.evaluate(() => window.collaborationState.updates);
  await textarea.dispatchEvent('input');
  const afterBlockedInput = await page.evaluate(() => window.collaborationState.updates);
  await page.evaluate(() => { window.collaborationState.posting = false; });

  const fileInput = primitives.locator('[data-professional-collaboration-component="attachments"] input[type="file"]');
  await fileInput.setInputFiles({ name: 'contract-note.txt', mimeType: 'text/plain', buffer: Buffer.from('fixture') });
  const selected = await page.evaluate(() => window.collaborationState.selected);
  const filePrimitivePresent = await primitives.locator('[data-professional-collaboration-component="attachments"] .sc-file-field').count() === 1;

  // A form in readonly mode must still render the collaboration the contract
  // declares; a contract that declares the panel readonly must not.
  const declaredLive = page.locator('[data-surface-harness="declared-live"] [data-section-content-kind="collaboration-panel"]');
  const declaredReadonly = page.locator('[data-surface-harness="declared-readonly"] [data-section-content-kind="collaboration-panel"]');
  const declaredLiveControls = await declaredLive.locator('.chips button').count();
  const declaredLiveUpload = await declaredLive.locator('input[type="file"]').count();
  const declaredReadonlyControls = await declaredReadonly.locator('.chips button').count();
  const declaredReadonlyUpload = await declaredReadonly.locator('input[type="file"]').count();
  const declarationConsumed = declaredLiveControls === 2 && declaredLiveUpload === 1
    && declaredReadonlyControls === 0 && declaredReadonlyUpload === 0;

  const pass = updated.draft === '协作内容' && updated.updates > 0
    && disabled && busy === 'true' && beforeBlockedInput === afterBlockedInput
    && selected === 'contract-note.txt' && filePrimitivePresent && declarationConsumed && errors.length === 0;
  console.log(JSON.stringify({ pass, updated, disabled, busy, blockedInput: beforeBlockedInput === afterBlockedInput, selected, filePrimitivePresent, declarationConsumed, declaredLiveControls, declaredLiveUpload, declaredReadonlyControls, declaredReadonlyUpload, errors }, null, 2));
  if (!pass) process.exitCode = 1;
} finally {
  await browser.close();
  await server.close();
}
