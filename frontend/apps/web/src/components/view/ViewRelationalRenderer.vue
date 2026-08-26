<template>
  <div class="relational" data-semantic-component="ViewRelationalRenderer" :data-state="loading ? 'loading' : error ? 'error' : rows.length ? 'ready' : 'empty'" :aria-busy="loading || undefined">
    <div class="relational-header">
      <span class="relational-title">{{ headerLabel }}</span>
      <div class="relational-actions">
        <span class="relational-count">{{ countLabel }}</span>
        <ScButton v-if="canEdit" class="relational-add" type="button" variant="primary" size="small" @click="startCreate">Add line</ScButton>
      </div>
    </div>
    <ScInlineState v-if="loading" state="loading" label="Loading related records…" />
    <ScInlineState v-else-if="error" state="error" :label="error" />
    <ScInlineState v-else-if="!rows.length" state="empty" label="No related records." />
    <ul v-else class="relational-list">
      <li v-for="row in rows" :key="String(row.id)" class="relational-item">
        <ScButton class="relational-link" type="button" variant="ghost" size="small" @click="openRecord(row.id)">
          {{ row.name || `#${row.id}` }}
        </ScButton>
        <div v-if="canEdit" class="relational-row-actions">
          <ScButton class="relational-edit" type="button" variant="secondary" size="small" @click="startEdit(row)">Edit</ScButton>
          <ScButton class="relational-delete" type="button" variant="danger" size="small" @click="removeRow(row)">Delete</ScButton>
        </div>
      </li>
    </ul>
    <ScInlineState v-if="truncated" state="info" :label="`Showing first ${rows.length} records.`" />

    <div v-if="editorVisible" class="relational-editor">
      <div class="editor-card">
        <div class="editor-title">{{ editorTitle }}</div>
        <div v-if="editTxState === 'saved'" class="editor-banner">Saved.</div>
        <div v-else-if="editTxState === 'saving'" class="editor-banner">Saving…</div>
        <label class="editor-label">Name</label>
        <ScInput v-model="draftName" type="text" />
        <div class="editor-actions">
          <ScButton class="relational-save" type="button" variant="primary" :loading="saving" :disabled="!draftName.trim()" @click="saveRow">
            {{ saving ? 'Saving…' : 'Save' }}
          </ScButton>
          <ScButton class="relational-cancel" type="button" variant="ghost" @click="cancelEdit">Cancel</ScButton>
        </div>
        <ScInlineState v-if="editorError" state="error" :label="editorError" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ScButton from '../design-system/ScButton.vue';
import ScInput from '../design-system/ScInput.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import { useEditTx } from '../../composables/useEditTx';
import { pickContractNavQuery } from '../../app/navigationContext';
import {
  createRelationRendererRecord,
  listRelationRendererRecords,
  unlinkRelationRendererRecord,
  writeRelationRendererRecord,
} from '../../app/runtime/relationRendererDataRuntime';

const props = defineProps<{
  ids: number[];
  model?: string;
  relationField?: string;
  parentId?: number;
  editable?: boolean;
}>();

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const error = ref('');
const rows = ref<Array<{ id: number; name?: string }>>([]);
const truncated = ref(false);
const editorVisible = ref(false);
const editorMode = ref<'create' | 'edit'>('create');
const editorTargetId = ref<number | null>(null);
const draftName = ref('');
const saving = ref(false);
const editorError = ref('');
const editTx = useEditTx();
const editTxState = computed(() => editTx.state.value);

const headerLabel = computed(() => (props.model ? props.model : 'Related'));
const countLabel = computed(() => `${props.ids.length} items`);
const canEdit = computed(() => Boolean(props.editable && props.parentId && props.relationField && props.model));
const editorTitle = computed(() => (editorMode.value === 'create' ? 'Add related record' : 'Edit related record'));
type RelationRecordRaw = { id?: number | string; name?: unknown };

async function load() {
  rows.value = [];
  error.value = '';
  truncated.value = false;
  if (!props.model) {
    error.value = 'Missing relation model';
    return;
  }
  if (!Array.isArray(props.ids) || props.ids.length === 0) {
    return;
  }
  loading.value = true;
  try {
    const ids = props.ids.slice(0, 50);
    truncated.value = props.ids.length > ids.length;
    const response = await listRelationRendererRecords({
      model: props.model,
      fields: ['id', 'name'],
      domain: [['id', 'in', ids]],
      limit: ids.length,
      order: 'id asc',
      silentErrors: true,
    });
    rows.value = (response.records || []).map((record) => {
      const raw = record as RelationRecordRaw;
      return {
      id: Number(raw.id),
      name: raw.name ? String(raw.name) : undefined,
      };
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load relation records';
  } finally {
    loading.value = false;
  }
}

function openRecord(id: number) {
  if (!props.model) return;
  const carry = pickContractNavQuery(route.query as Record<string, unknown>);
  router.push({ name: 'record', params: { model: props.model, id }, query: carry });
}

function startCreate() {
  editorError.value = '';
  editorVisible.value = true;
  editorMode.value = 'create';
  editorTargetId.value = null;
  draftName.value = '';
  editTx.beginEdit();
}

function startEdit(row: { id: number; name?: string }) {
  editorError.value = '';
  editorVisible.value = true;
  editorMode.value = 'edit';
  editorTargetId.value = row.id;
  draftName.value = row.name || '';
  editTx.beginEdit();
}

function cancelEdit() {
  editorVisible.value = false;
  editorTargetId.value = null;
  draftName.value = '';
  editTx.cancelEdit();
}

async function saveRow() {
  if (!props.model || !props.relationField || !props.parentId) {
    editorError.value = 'Missing relation configuration';
    return;
  }
  if (!draftName.value.trim()) return;
  saving.value = true;
  editorError.value = '';
  try {
    await editTx.save(async () => {
      if (editorMode.value === 'create') {
        return createRelationRendererRecord({
          model: props.model,
          vals: {
            name: draftName.value.trim(),
            [props.relationField]: props.parentId,
          },
        });
      }
      if (editorTargetId.value) {
        return writeRelationRendererRecord({
          model: props.model,
          ids: [editorTargetId.value],
          vals: { name: draftName.value.trim() },
        });
      }
      return null;
    });
    editTx.markSaved();
    editorVisible.value = false;
    editorTargetId.value = null;
    draftName.value = '';
    await load();
  } catch (err) {
    editorError.value = err instanceof Error ? err.message : 'Failed to save related record';
    editTx.markError();
  } finally {
    saving.value = false;
  }
}

async function removeRow(row: { id: number }) {
  if (!props.model) return;
  if (!confirm('Delete this related record?')) return;
  try {
    await editTx.save(async () => {
      return unlinkRelationRendererRecord({ model: props.model, ids: [row.id] });
    });
    editTx.markSaved();
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to delete related record';
    editTx.markError();
  }
}

watch(
  () => [props.model, props.ids.join(',')],
  () => {
    load();
  },
  { immediate: true },
);

onMounted(load);
</script>

<style scoped>
.relational {
  display: grid;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  border: 1px dashed var(--sc-app-border-strong);
  background: var(--sc-app-muted-bg);
}

.relational-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.relational-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.relational-title {
  font-weight: 600;
  color: var(--sc-app-text-primary);
}

.relational-count {
  color: var(--sc-app-text-secondary);
}

.relational-meta {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}

.relational-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 6px;
}

.relational-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.relational-link {
  width: 100%;
  text-align: left;
}

.relational-row-actions {
  display: flex;
  gap: 6px;
}

.relational-editor {
  margin-top: 12px;
}

.editor-card {
  border: 1px dashed var(--sc-app-border-strong);
  border-radius: 10px;
  padding: 12px;
  background: var(--sc-app-panel);
  display: grid;
  gap: 8px;
}

.editor-title {
  font-weight: 600;
}

.editor-label {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}

.editor-banner {
  font-size: 12px;
  color: var(--sc-app-info-text);
  background: var(--sc-app-info-bg);
  border: 1px solid var(--sc-app-info-border);
  padding: 4px 8px;
  border-radius: 8px;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

</style>
