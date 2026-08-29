<template>
  <TDesignUpload
    v-bind="semanticPrimitiveIdentity('ScUpload')"
    class="sc-file-field"
    theme="file-input"
    :accept="accept || undefined"
    :disabled="disabled"
    :auto-upload="false"
    :multiple="multiple"
    :max="multiple ? 0 : 1"
    :files="files"
    :aria-required="required || undefined"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedBy"
    :data-field-id="id"
    @select-change="handleSelectChange"
    @remove="clearSelection"
  >
    <template #trigger>
      <ScButton variant="secondary" size="small" type="button" :disabled="disabled">{{ chooseLabel }}</ScButton>
    </template>
    <template #file-list-display>
      <span class="sc-file-field__name" :title="displayName || emptyLabel">{{ displayName || emptyLabel }}</span>
    </template>
  </TDesignUpload>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ScButton from './ScButton.vue';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
import { TDesignUpload } from './tdesignPrimitiveBridge';

const props = withDefaults(defineProps<{
  id?: string; accept?: string; disabled?: boolean; required?: boolean; invalid?: boolean;
  describedBy?: string; chooseLabel?: string; emptyLabel?: string; multiple?: boolean;
}>(), {
  id: undefined, accept: '', disabled: false, required: false, invalid: false,
  describedBy: undefined, chooseLabel: '选择文件', emptyLabel: '未选择文件', multiple: false,
});

type UploadFileLike = { name?: string; raw?: File };
const selected = ref<File[]>([]);
const displayName = computed(() => {
  if (selected.value.length === 0) return '';
  if (selected.value.length === 1) return selected.value[0].name;
  return `已选择 ${selected.value.length} 个文件`;
});
const files = computed<UploadFileLike[]>(() => selected.value.map(f => ({ name: f.name, raw: f })));

const emit = defineEmits<{ change: [files: File[]] }>();

function handleSelectChange(nextFiles: File[]) {
  selected.value = nextFiles || [];
  emit('change', selected.value);
}

function clearSelection() {
  selected.value = [];
  emit('change', []);
}
</script>

<style scoped>
.sc-file-field { width: 100%; }
.sc-file-field__name {
  min-width: 0;
  overflow: hidden;
  color: var(--sc-app-text-secondary);
  font-size: calc(var(--sc-component-input-font-size) * 1px);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
