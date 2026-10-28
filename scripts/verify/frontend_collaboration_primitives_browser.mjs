import { createServer } from '../../frontend/apps/web/node_modules/vite/dist/node/index.js';
import { launchChromium } from './playwright_runtime.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs';

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
        import Followers from '/src/pages/contractForm/ProfessionalFollowerManager.vue';
        import ScList from '/src/components/design-system/ScList.vue';
        import '/src/styles/design-system.css';
        const state = reactive({ draft: '', note: '', posting: false, selected: '', updates: 0 });
        window.collaborationState = state;
        const followerItems = Array.from({length:19}, (_, index) => ({partner_id:index+1, name:'合成人员' + (index+1), is_current_user:index===0}));
        const followerState = reactive({items:followerItems, loading:false, error:'', enabled:true, canFollow:true, canUnfollow:false, actions:[]});
        window.followerState = followerState;
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
          h('div', {'data-follower-harness':'compact'}, [h(Followers, {
            ...followerState, label:'关注者', count:followerState.items.length, followLabel:'关注', unfollowLabel:'取消关注',
            onUpdate:action=>followerState.actions.push(action),
          }), h('p', {'data-following-content':''}, '后续协作内容')]),
          h('div', {'data-follower-harness':'ordinary'}, [h(ScList, {items:followerItems.map(item=>({...item,key:item.partner_id}))}, {item:({item})=>h('span',{'data-ordinary-follower':''},item.name)})]),
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

  const followerEvidence = {kind:'actual_component_browser', synthetic:true, measurements:[], assertions:0};
  const verify = (condition, message) => { assert.ok(condition, message); followerEvidence.assertions++; };
  const compact = page.locator('[data-follower-harness="compact"]');
  const followers = compact.locator('.native-follower-manager');
  const measure = () => page.evaluate(() => {
    const host=document.querySelector('[data-follower-harness="compact"]');
    const names=[...host.querySelectorAll('.native-follower-name')];
    const ordinary=document.querySelector('[data-follower-harness="ordinary"]');
    return {width:innerWidth,
      names:names.map(e=>e.textContent), rows:new Set(names.map(e=>Math.round(e.getBoundingClientRect().top))).size,
      allVisible:names.every(e=>e.getClientRects().length>0),
      overflow:document.documentElement.scrollWidth>innerWidth,
      ordinaryRows:new Set([...ordinary.querySelectorAll('[data-ordinary-follower]')].map(e=>Math.round(e.getBoundingClientRect().top))).size,
      ordinaryCount:ordinary.querySelectorAll('[data-ordinary-follower]').length,
      contentTop:host.querySelector('[data-following-content]').getBoundingClientRect().top};
  });
  fs.mkdirSync('.runtime/fepc12', {recursive:true});
  try {
    for (const width of [1440,768,320]) {
      await page.setViewportSize({width,height:1000});
      await followers.locator('.native-follower-name').last().waitFor();
      const measured=await measure();
      // Compare with the same-page control, never a fixed pixel target.
      measured.height=(await followers.locator('.native-follower-list').boundingBox())?.height;
      measured.ordinaryHeight=(await page.locator('[data-follower-harness="ordinary"]').boundingBox())?.height;
      followerEvidence.measurements.push(measured);
      await compact.screenshot({path:`.runtime/fepc12/followers-${width}.png`});
      verify(measured.names.join('|')===Array.from({length:19},(_,i)=>'合成人员'+(i+1)).join('|'),'all followers keep order and names');
      verify(measured.allVisible && !measured.overflow,'all followers visible without horizontal overflow');
      verify(measured.rows<19 && measured.ordinaryRows===19,'followers wrap compactly; ordinary list stays vertical');
      verify(measured.height<measured.ordinaryHeight,'complete follower list uses less height than the same-page vertical list');
      verify(measured.ordinaryCount===19,'ordinary list remains complete');
      verify(await followers.locator('.native-follower-current').count()===1,'current user marker retained');
      verify(await followers.locator('.native-follower-title').innerText()==='关注者（19）','declared label and total count retained');
    }
    await page.evaluate(()=>{window.followerState.items=[{partner_id:1,name:'合成长姓名'.repeat(30),is_current_user:true}];});
    const long=await measure(); followerEvidence.longName=long;
    verify(!long.overflow && long.names[0]==='合成长姓名'.repeat(30),'long name retained on narrow screen');
    verify(await followers.locator('.native-follower-name').evaluate(e=>e.scrollWidth<=e.clientWidth),'long name is readable without clipping');
    await followers.getByRole('button',{name:'关注',exact:true}).focus();
    await page.keyboard.press('Enter');
    verify(await page.evaluate(()=>window.followerState.actions.join())==='follow','keyboard follow emits existing action');
    await page.evaluate(()=>{window.followerState.canFollow=false;window.followerState.canUnfollow=true;});
    await followers.getByRole('button',{name:'取消关注',exact:true}).click();
    verify(await page.evaluate(()=>window.followerState.actions.join())==='follow,unfollow','unfollow action retained');
    await page.evaluate(()=>{window.followerState.canUnfollow=false;});
    verify(await followers.getByRole('button').count()===0,'denied actions stay absent');
    await page.evaluate(()=>{window.followerState.loading=true;window.followerState.canFollow=true;});
    verify(await followers.getByRole('button').isDisabled(),'loading disables action');
    await page.evaluate(()=>{window.followerState.items=[];});
    verify(await followers.getByText('暂无关注者',{exact:true}).count()===0,'loading does not claim an empty result');
    await page.evaluate(()=>{window.followerState.items=[];window.followerState.loading=false;});
    verify(await followers.getByText('暂无关注者',{exact:true}).isVisible(),'empty state retained');
    await page.evaluate(()=>{window.followerState.error='合成加载错误';});
    verify(await followers.getByText('合成加载错误',{exact:true}).isVisible(),'error state retained');
    await page.evaluate(()=>{window.followerState.enabled=false;});
    verify(await followers.count()===0,'disabled capability remains absent');
  } finally {
    fs.writeFileSync('.runtime/fepc12/component-browser.json',JSON.stringify(followerEvidence,null,2)+'\n');
  }

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
