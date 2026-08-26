<template>
  <TDesignUpload
    v-bind="semanticPrimitiveIdentity('ScUpload')"
    class="sc-file-field"
    theme="file-input"
    :accept="accept || undefined"
    :disabled="disabled"
    :auto-upload="false"
    :multiple="false"
    :max="1"
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
      <span class="sc-file-field__name" :title="selectedName || emptyLabel">{{ selectedName || emptyLabel }}</span>
    </template>
  </TDesignUpload>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ScButton from './ScButton.vue';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
import { TDesignUpload } from './tdesignPrimitiveBridge';

withDefaults(defineProps<{
  id?: string; accept?: string; disabled?: boolean; required?: boolean; invalid?: boolean;
  describedBy?: string; chooseLabel?: string; emptyLabel?: string;
}>(), {
  id: undefined, accept: '', disabled: false, required: false, invalid: false,
  describedBy: undefined, chooseLabel: '选择文件', emptyLabel: '未选择文件',
});

type UploadFileLike = { name?: string; raw?: File };
const emit = defineEmits<{ change: [file: File | null] }>();
const selected = ref<File | null>(null);
const selectedName = computed(() => selected.value?.name || '');
const files = computed<UploadFileLike[]>(() => selected.value ? [{ name: selected.value.name, raw: selected.value }] : []);

function handleSelectChange(nextFiles: File[]) {
  selected.value = nextFiles[0] || null;
  emit('change', selected.value);
}

function clearSelection() {
  selected.value = null;
  emit('change', null);
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
