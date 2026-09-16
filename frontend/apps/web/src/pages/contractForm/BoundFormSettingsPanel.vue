<template>
  <section class="bound-form-settings" aria-label="当前页面字段配置" :data-ready="loaded" data-bound-form-designer>
    <h3>当前页面字段配置</h3>
    <p>设置当前入口、当前公司及当前角色的表单。保存配置不会保存业务单据。</p>
    <ScInlineState v-if="error" state="error" :label="error" />
    <ScInlineState v-if="feedback" :label="feedback" />
    <div class="bound-design-grid">
    <ScForm :disabled="busy || !loaded || published" label-align="top" class="bound-form-fields" @submit.prevent>
      <ScFormField v-slot="control" label="选择字段" field-key="selected">
        <ScSelect v-model="selected" :id="control.controlId" aria-label="选择字段" :options="fieldOptions" filterable />
      </ScFormField>
      <template v-if="selectedRow">
        <ScFormField v-slot="control" label="字段显示名称" field-key="label">
          <ScInput v-model="label" :id="control.controlId" aria-label="字段显示名称" />
        </ScFormField>
        <ScFormField v-slot="control" label="字段显示" field-key="visibility">
          <ScSelect v-model="visibility" :id="control.controlId" aria-label="字段显示" :options="visibilityOptions" />
        </ScFormField>
        <div class="bound-form-actions">
          <ScButton type="button" @click="applyField">应用字段设置</ScButton>
          <ScButton type="button" @click="reorder(-1)">上移字段</ScButton>
          <ScButton type="button" @click="reorder(1)">下移字段</ScButton>
        </div>
        <ScFormField v-slot="control" label="新分组名称" field-key="group" help="同一区域支持一个新分组；排序在原区域内调整。">
          <ScInput v-model="groupLabel" :id="control.controlId" aria-label="新分组名称" />
        </ScFormField>
        <ScButton type="button" @click="groupField">加入新分组</ScButton>
      </template>
    </ScForm>
    <section aria-label="待发布改动" data-bound-change-summary>
      <h4>待发布改动</h4>
      <ol v-if="changeSummary.length"><li v-for="(item, index) in changeSummary" :key="index">{{ item }}</li></ol>
      <ScInlineState v-else label="尚无配置改动" />
    </section>
    </div>
    <div class="bound-form-actions">
      <ScButton :disabled="busy || !loaded || !patches.length || published" @click="save">保存配置草稿</ScButton>
      <ScButton :disabled="busy || !draft || dirty || published" @click="preview">验证并预览</ScButton>
      <a v-if="previewUrl" :href="previewUrl" target="_blank" rel="opener" data-bound-preview-link>打开配置预览</a>
      <ScButton :disabled="busy || !previewUrl || dirty || published" @click="publish">发布配置</ScButton>
      <a :href="businessUrl" target="_blank" rel="opener">打开业务页面</a>
      <ScButton :disabled="busy || !published" @click="rollback">回滚本次发布</ScButton>
      <ScButton :disabled="busy || !draft || published" @click="discard">撤销配置草稿</ScButton>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ScInput from '../../components/design-system/ScInput.vue';
import ScSelect from '../../components/design-system/ScSelect.vue';
import ScForm from '../../components/design-system/ScForm.vue';
import ScFormField from '../../components/design-system/ScFormField.vue';
import ScInlineState from '../../components/design-system/ScInlineState.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import type { ContractV2Snapshot } from '../../app/contracts/v2/types';
import { ApiError } from '../../api/client';
import { intentRequest } from '../../api/intents';
import { BUSINESS_CONFIG_INTENTS, BUSINESS_CONFIG_MODES } from '../../app/businessConfigBoundaries';
import { openBusinessConfigChangeSet, loadBusinessConfigChangeSet, stageBusinessConfigChangeSetItem,
  previewBusinessConfigChangeSet, publishBusinessConfigChangeSet, rollbackBusinessConfigChangeSet,
  discardBusinessConfigChangeSet, type BusinessConfigChangeSet } from '../../api/businessConfig';
import { summarizeBoundPatches, boundNodes, editBoundField, groupBoundField, orderBoundField, type BoundPatch } from './boundFormConfiguration';
const props = defineProps<{ snapshot: ContractV2Snapshot; roleKey: string }>();
const route = useRoute();
const router = useRouter();
const authority = props.snapshot.formStructureContract!.sourceAuthority.governance_source;
const scope = { model: props.snapshot.pageInfo.model, view_type: 'form', action_id: Number(authority.resolvedActionId),
  view_id: Number(authority.resolvedViewId), role_key: props.roleKey };
const name = `view_orchestration:${scope.model}:form:action:${scope.action_id}:view:${scope.view_id}:role:${scope.role_key}`;
const fields = boundNodes(props.snapshot.layoutContract.containerTree).filter(({ node }) => node.type === 'field');
const fieldOptions = fields.map(({ node, parent }) => ({ value: node.nativeLocator!, label: `${node.label || node.name} · ${parent?.label || parent?.title || '表单'} · ${node.occurrenceIndex}` }));
const visibilityOptions = [{ value: 'inherit', label: '保持原规则' }, { value: 'hide', label: '隐藏' }, { value: 'show', label: '显示（不放宽业务约束）' }];
const selected = ref(fields[0]?.node.nativeLocator || '');
const selectedRow = computed(() => fields.find(({ node }) => node.nativeLocator === selected.value));
const patches = ref<BoundPatch[]>([]);
const changeSummary = computed(() => summarizeBoundPatches(props.snapshot.layoutContract.containerTree, patches.value));
const loaded = ref(false), busy = ref(false), dirty = ref(false), published = ref(false);
const error = ref(''), feedback = ref(''), label = ref(''), visibility = ref('inherit'), groupLabel = ref('');
const initialDefinition = ref('absent');
const draft = ref<BusinessConfigChangeSet | null>(null), previewUrl = ref('');
const businessUrl = `/f/${scope.model}/new?${new URLSearchParams({ action_id: String(scope.action_id), view_id: String(scope.view_id), menu_id: String(route.query.menu_id || '') })}`;
function syncSelection() {
  const node = selectedRow.value?.node;
  if (!node) return;
  const set = patches.value.find((patch) => patch.target === node.nativeLocator)?.set;
  label.value = set?.label || node.label || node.name || '';
  visibility.value = set?.visible === undefined ? 'inherit' : set.visible ? 'show' : 'hide';
}
watch(selected, syncSelection, { immediate: true });
function edit(operation: () => BoundPatch[]) {
  error.value = '';
  try { patches.value = operation(); dirty.value = true; previewUrl.value = ''; feedback.value = '配置已修改，尚未保存'; }
  catch (cause) { error.value = cause instanceof Error ? cause.message : String(cause); }
}
function applyField() {
  if (!selectedRow.value) return;
  edit(() => {
    const next = editBoundField(patches.value, selectedRow.value!.node, { label: label.value });
    const patch = next.find((item) => item.target === selectedRow.value!.node.nativeLocator)!;
    if (visibility.value === 'inherit') delete patch.set!.visible;
    else patch.set!.visible = visibility.value === 'show';
    return next;
  });
}
function reorder(delta: number) { const row = selectedRow.value; if (row?.parent) edit(() => orderBoundField(patches.value, row.parent!, row.node, delta)); }
function groupField() { const row = selectedRow.value; if (row?.parent) edit(() => groupBoundField(patches.value, row.parent!, row.node, groupLabel.value)); }
async function run(operation: () => Promise<void>) {
  busy.value = true; error.value = '';
  try { await operation(); } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
    if (cause instanceof ApiError && cause.details?.message) error.value += ` ${String(cause.details.message)}`;
  }
  finally { busy.value = false; }
}
const params = () => ({ change_set_token: draft.value!.token, role_key: scope.role_key });
async function readBaseline() {
  initialDefinition.value = 'absent';
  patches.value = [];
  try {
    const existing = await intentRequest<{ definition_sha256: string; active: boolean; contract_json: { view_orchestration?: { views?: { form?: { node_patches?: BoundPatch[] } } } } }>({
      intent: BUSINESS_CONFIG_INTENTS.contractGet, params: { ...scope, name, include_inactive: true },
    });
    initialDefinition.value = existing.definition_sha256;
    if (existing.active) {
      const spec = existing.contract_json.view_orchestration?.views?.form;
      if (!spec?.node_patches) throw new Error('当前配置尚未绑定稳定节点，不能覆盖保存');
      patches.value = JSON.parse(JSON.stringify(spec.node_patches));
    }
  } catch (cause) {
    if (!(cause instanceof ApiError && cause.reasonCode === 'NOT_FOUND')) throw cause;
  }
}
onMounted(() => run(async () => {
  if (!scope.action_id || !scope.view_id || !scope.role_key) throw new Error('正式入口身份尚未就绪，请刷新页面');
  await readBaseline();
  const token = String(route.query.change_set_token || '');
  if (token) {
    draft.value = await loadBusinessConfigChangeSet({ change_set_token: token, role_key: scope.role_key });
    if (draft.value.items.some((item) => item.target_key !== name)) throw new Error('此变更集包含其他配置，请从配置工作台处理');
    const item = draft.value.items[0];
    if (item) {
      const payload = item.draft_payload as { view_orchestration?: { views?: { form?: { node_patches?: BoundPatch[] } } } };
      patches.value = JSON.parse(JSON.stringify(payload.view_orchestration?.views?.form?.node_patches || []));
    }
    published.value = draft.value.state === 'published';
  }
  loaded.value = true; syncSelection();
}));
async function save() { await run(async () => {
  for (const patch of patches.value) if (!patch.expected) throw new Error('配置目标缺少稳定身份');
  if (!draft.value || ['published', 'discarded', 'superseded'].includes(draft.value.state)) {
    draft.value = await openBusinessConfigChangeSet({ role_key: scope.role_key, name: '表单设计配置', fresh: true });
  }
  draft.value = await stageBusinessConfigChangeSetItem({ ...params(), ...scope, config_type: 'form', target_key: name, current_definition_hash: initialDefinition.value,
    draft_payload: { view_orchestration: { views: { form: { node_patches: patches.value } } } },
    diff_summary: { summary: '正式表单设计器：标签、顺序、分组和显隐' } });
  await router.replace({ query: { ...route.query, config_mode: BUSINESS_CONFIG_MODES.formFieldConfiguration, change_set_token: draft.value.token } });
  dirty.value = false; previewUrl.value = ''; feedback.value = '配置已保存，尚未发布';
}); }
async function preview() { await run(async () => {
  draft.value = await previewBusinessConfigChangeSet(params());
  const preview = draft.value.preview;
  if (!preview) throw new Error('未取得有效预览');
  previewUrl.value = `${businessUrl}&${new URLSearchParams({ preview_token: preview.token, preview_role_key: scope.role_key, designer_token: draft.value.token })}`;
  feedback.value = '最终契约核验通过；请打开预览检查页面';
}); }
async function publish() { await run(async () => {
  draft.value = await publishBusinessConfigChangeSet({ ...params(), request_id: crypto.randomUUID() });
  if (draft.value.publish_result.published_content_verified !== true || draft.value.publish_result.runtime_verified !== true) throw new Error('发布或最终契约核验未通过');
  published.value = true; feedback.value = '配置已发布，最终契约核验通过；页面行为仍需复核';
}); }
async function rollback() { await run(async () => {
  await rollbackBusinessConfigChangeSet({ ...params(), request_id: crypto.randomUUID() });
  published.value = false; draft.value = null; previewUrl.value = '';
  await readBaseline(); syncSelection(); dirty.value = false;
  await router.replace({ query: { ...route.query, change_set_token: undefined } });
  feedback.value = '本次发布已回滚，请刷新业务页面核对';
}); }
async function discard() { await run(async () => {
  await discardBusinessConfigChangeSet(params()); draft.value = null; previewUrl.value = ''; feedback.value = '配置草稿已撤销';
}); }
</script>
<style scoped>
.bound-form-settings { grid-column: 1 / -1; padding: 20px; width: 100%; min-width: 0; box-sizing: border-box; }
.bound-form-fields { min-width: 0; margin-block: 16px; }
.bound-design-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; }
@media (max-width: 720px) { .bound-design-grid { grid-template-columns: minmax(0, 1fr); } .bound-form-settings { padding: 8px; } }
[data-bound-change-summary] { overflow-wrap: anywhere; }


.bound-form-actions { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin: 12px 0; }
[role=alert] { color: var(--td-error-color); }
</style>
