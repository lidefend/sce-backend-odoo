<template>
  <article
    class="block block-rich-text-overview"
    data-semantic-component="BlockRichTextOverview"
    :data-state="phase"
    :data-editable="view.canEdit ? 'true' : 'false'"
  >
    <header class="block-rich-text-overview__header">
      <h4>{{ block.title || titleFallback }}</h4>
      <ScButton
        v-if="view.canEdit && phase === 'idle'"
        size="small"
        variant="outline"
        data-action="begin-edit"
        @click="beginEdit"
      >
        {{ copy.edit }}
      </ScButton>
    </header>

    <!-- 只读态：内容为服务端净化后的受限 HTML（读取直渲染，净化权威在后端） -->
    <div
      v-if="phase === 'idle' || phase === 'saved'"
      class="block-rich-text-overview__content"
      data-state="readonly"
      v-html="renderedContent"
    ></div>
    <p
      v-if="(phase === 'idle' || phase === 'saved') && !renderedContent"
      class="block-rich-text-overview__hint"
      data-empty
    >
      {{ emptyMessage }}
    </p>

    <p
      v-if="phase === 'saved' && savedMessage"
      class="block-rich-text-overview__notice"
      data-state="saved"
      role="status"
    >
      {{ savedMessage }}
      <button type="button" class="block-rich-text-overview__link" data-action="dismiss-saved" @click="dismissSaved">
        {{ copy.dismiss }}
      </button>
    </p>

    <!-- 编辑态：受限输入 + 会话状态机（保存中/错误/冲突） -->
    <div v-if="phase === 'editing'" class="block-rich-text-overview__editor" data-state="editing">
      <RestrictedHtmlEditor
        v-model="draft"
        :max-length="view.maxLength"
        :disabled="session.state === 'saving'"
      />
      <p v-if="session.state === 'error' || session.state === 'conflict'" class="block-rich-text-overview__notice" data-state="error" role="alert">
        {{ session.errorMessage }}
        <button
          v-if="session.state === 'conflict'"
          type="button"
          class="block-rich-text-overview__link"
          data-action="reload-baseline"
          @click="reloadBaseline"
        >
          {{ copy.reload }}
        </button>
      </p>
      <div class="block-rich-text-overview__actions">
        <ScButton
          size="small"
          data-action="save"
          :disabled="session.state === 'saving' || !canSubmit"
          @click="submitDraft"
        >
          {{ session.state === 'saving' ? copy.saving : copy.save }}
        </ScButton>
        <ScButton
          size="small"
          variant="outline"
          :disabled="session.state === 'saving'"
          data-action="cancel"
          @click="cancelEdit"
        >
          {{ copy.cancel }}
        </ScButton>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
/**
 * 受限富文本内容块包装（页面编排 block）。
 *
 * 职责（共享层，无业务语义）：
 * - 从块契约 dataset（后端块投影）解析数据上下文视图：
 *   内容 / 摘要基线 / 长度上限 / 可编辑能力投影；
 * - 只读态直渲染服务端净化后的受限 HTML（净化权威在后端）；
 * - 可编辑时进入受限编辑会话：脏值判定 + 幂等键提交 +
 *   错误/冲突降级（BASELINE_MISMATCH 时经块读 intent 重载基线）。
 * 业务标题与空态文案由后端块契约（dataset 文案字段）提供，
 * 本组件只保留通用 fallback。
 */
import { computed, ref } from 'vue';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import ScButton from '../../design-system/ScButton.vue';
import RestrictedHtmlEditor from '../../editor/RestrictedHtmlEditor.vue';
import { sanitizeRestrictedHtml } from '../../../utils/sanitizeRestrictedHtml';
import {
  buildOverviewRichTextPatchIdempotencyKey,
  fetchOverviewRichTextBlock,
  patchOverviewRichText,
} from '../../../api/overviewRichTextPatch';
import {
  applyOverviewRichTextResult,
  beginOverviewRichTextSession,
  describeOverviewRichTextSuccess,
  markOverviewRichTextError,
  markOverviewRichTextSaving,
  OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK,
  OVERVIEW_RICH_TEXT_SESSION_SAVING,
  projectOverviewRichTextBlockData,
  updateOverviewRichTextDraft,
  validateOverviewRichTextDraft,
  type OverviewRichTextBlockView,
  type OverviewRichTextSession,
} from '../../../app/presentation/overviewRichTextPatch';

const GENERIC_TITLE_FALLBACK = '内容说明';
const GENERIC_EMPTY = '暂无可展示的内容。';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const copy = {
  edit: '编辑',
  save: '保存',
  saving: '保存中…',
  cancel: '取消',
  reload: '重新加载',
  dismiss: '知道了',
};

const phase = ref<'idle' | 'editing' | 'saved'>('idle');
const draft = ref('');
const session = ref<OverviewRichTextSession | null>(null);
const savedMessage = ref('');
const reloading = ref(false);

/** 块数据视图（后端投影为权威；刷新后同源更新） */
const view = ref<OverviewRichTextBlockView>(
  projectOverviewRichTextBlockData(props.dataset),
);

/** 只读渲染内容：服务端净化权威 + 渲染前纵深收敛（ADR-006 决策 3） */
const renderedContent = computed(() => sanitizeRestrictedHtml(view.value.content));
const titleFallback = GENERIC_TITLE_FALLBACK;
const emptyMessage = computed(() => {
  const source = (props.dataset && typeof props.dataset === 'object' ? props.dataset : {}) as Record<string, unknown>;
  const data = (source.data && typeof source.data === 'object' ? source.data : {}) as Record<string, unknown>;
  return typeof data.empty_message === 'string' && data.empty_message.trim()
    ? data.empty_message
    : GENERIC_EMPTY;
});

/** 可提交：草稿非空转（脏，对照实时 draft 与基线内容）且长度预校验通过 */
const canSubmit = computed(() => {
  const current = session.value;
  if (!current) return false;
  // dirty 必须以实时 draft ref 判定（v-model 逐键更新）；session.draft 是
  // beginEdit 时的快照，不随输入变化，直接比较它会把脏值误判为干净。
  const dirty = String(draft.value ?? '') !== String(current.baselineContent ?? '');
  if (!dirty) return false;
  return validateOverviewRichTextDraft(draft.value, view.value.maxLength).ok;
});

function beginEdit() {
  session.value = beginOverviewRichTextSession({
    projectId: view.value.projectId,
    content: view.value.content,
    digest: view.value.digest,
  });
  draft.value = view.value.content;
  savedMessage.value = '';
  phase.value = 'editing';
}

function cancelEdit() {
  session.value = null;
  draft.value = '';
  phase.value = 'idle';
}

function dismissSaved() {
  savedMessage.value = '';
  phase.value = 'idle';
}

async function submitDraft() {
  const current = session.value;
  if (!current || current.state === OVERVIEW_RICH_TEXT_SESSION_SAVING) return;
  const validation = validateOverviewRichTextDraft(draft.value, view.value.maxLength);
  if (!validation.ok) return;
  const idempotencyKey = current.idempotencyKey || buildOverviewRichTextPatchIdempotencyKey(current.projectId);
  session.value = markOverviewRichTextSaving(updateOverviewRichTextDraft(current, draft.value), idempotencyKey);
  try {
    const result = await patchOverviewRichText({
      projectId: current.projectId,
      expectedOverviewDigest: current.expectedDigest,
      newOverviewHtml: draft.value,
      idempotencyKey,
    });
    const saved = applyOverviewRichTextResult(result);
    view.value = {
      ...view.value,
      content: saved.content,
      digest: saved.digest,
      maxLength: view.value.maxLength || OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK,
    };
    savedMessage.value = describeOverviewRichTextSuccess(result);
    session.value = null;
    draft.value = '';
    phase.value = 'saved';
  } catch (err) {
    const reasonCode = extractReasonCode(err);
    session.value = markOverviewRichTextError(session.value, reasonCode);
  }
}

/** 冲突重载：经块读 intent 拉取最新内容与摘要基线，重置编辑会话 */
async function reloadBaseline() {
  const current = session.value;
  if (!current || reloading.value) return;
  reloading.value = true;
  try {
    const envelope = await fetchOverviewRichTextBlock(current.projectId);
    const fresh = projectOverviewRichTextBlockData(envelope);
    view.value = { ...view.value, ...fresh };
    session.value = beginOverviewRichTextSession({
      projectId: fresh.projectId || current.projectId,
      content: fresh.content,
      digest: fresh.digest,
    });
    draft.value = fresh.content;
  } catch {
    session.value = markOverviewRichTextError(current, 'NETWORK_ERROR');
  } finally {
    reloading.value = false;
  }
}

function extractReasonCode(err: unknown): string {
  const candidate = (err && typeof err === 'object' ? err : {}) as Record<string, unknown>;
  const reason = candidate.reasonCode ?? candidate.reason_code ?? candidate.code;
  return typeof reason === 'string' && reason.trim() ? reason.trim() : 'NETWORK_ERROR';
}
</script>

<style scoped>
.block-rich-text-overview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.block-rich-text-overview__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.block-rich-text-overview__header h4 {
  margin: 0;
}

.block-rich-text-overview__content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--sc-text, #333);
  overflow-wrap: break-word;
}

.block-rich-text-overview__content :deep(h1),
.block-rich-text-overview__content :deep(h2),
.block-rich-text-overview__content :deep(h3) {
  margin: 0.6em 0 0.3em;
}

.block-rich-text-overview__content :deep(ul),
.block-rich-text-overview__content :deep(ol) {
  padding-left: 1.4em;
  margin: 0.3em 0;
}

.block-rich-text-overview__content :deep(table) {
  border-collapse: collapse;
}

.block-rich-text-overview__content :deep(td),
.block-rich-text-overview__content :deep(th) {
  border: 1px solid var(--sc-border, #dcdcdc);
  padding: 4px 8px;
}

.block-rich-text-overview__hint {
  margin: 0;
  color: var(--sc-text-secondary, #666);
  font-size: 13px;
}

.block-rich-text-overview__notice {
  margin: 0;
  font-size: 13px;
  color: var(--sc-text-secondary, #666);
}

.block-rich-text-overview__notice[data-state='error'] {
  color: var(--sc-danger, #d54941);
}

.block-rich-text-overview__link {
  margin-left: 6px;
  padding: 0;
  border: none;
  background: none;
  color: var(--sc-primary, #0052d9);
  font-size: 13px;
  cursor: pointer;
  text-decoration: underline;
}

.block-rich-text-overview__editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.block-rich-text-overview__actions {
  display: flex;
  gap: 8px;
}
</style>
