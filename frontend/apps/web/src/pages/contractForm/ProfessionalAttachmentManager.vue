<template>
  <section
    v-if="enabled || pending.length"
    data-professional-collaboration-component="attachments"
    data-semantic-component="ProfessionalAttachmentManager"
    :data-state="uploading ? 'loading' : enabled ? 'ready' : 'fail-closed'"
    :data-attachment-readiness="enabled ? 'ready' : 'fail_closed'"
  >
    <section
      v-if="editable && enabled"
      class="native-attachment-tools"
      data-collaboration-capability="attachments"
      :class="{ 'native-attachment-drag-over': isDragOver }"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
    >
      <div v-if="isDragOver" class="native-attachment-drag-hint">
        <span class="native-attachment-drag-icon">📁</span>
        <span>释放文件以上传</span>
      </div>
      <ScFileField
        v-else
        class="native-attachment-upload"
        :disabled="uploading"
        :choose-label="uploading ? uploadingLabel : uploadLabel"
        empty-label=""
        @change="onFilesSelected($event)"
      />
      <ScInlineState v-if="error" class="validation-error native-chatter-message" state="error" :label="error" />
    </section>
    <ul v-if="pending.length" class="native-pending-attachments">
      <li v-for="item in pending" :key="item.key" class="native-chatter-attachment-item native-pending-attachment-item">
        <span class="native-chatter-attachment-icon">📄</span>
        <div class="native-chatter-attachment-content">
          <span class="native-chatter-attachment-name">{{ item.name }}</span>
          <div class="native-chatter-attachment-meta">
            <span class="native-chatter-attachment-type">待上传</span>
            <span class="native-chatter-attachment-size">{{ formatFileSize(item.size) }}</span>
          </div>
        </div>
        <ScButton variant="ghost" size="small" class="native-attachment-download" :disabled="uploading" @click="emit('remove', item.key)">移除</ScButton>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import ScButton from '../../components/design-system/ScButton.vue';
import ScFileField from '../../components/design-system/ScFileField.vue';
import ScInlineState from '../../components/design-system/ScInlineState.vue';
export type PendingProfessionalAttachment = { key: string; name: string; size: number; file: File };
defineProps<{ editable: boolean; enabled: boolean; uploading: boolean; uploadLabel: string; uploadingLabel: string; error: string; pending: PendingProfessionalAttachment[] }>();
import { ref } from 'vue';

const emit = defineEmits<{ selected: [file: File | null]; remove: [key: string] }>();

const isDragOver = ref(false);

function onDragOver(event: DragEvent) {
  if (event.dataTransfer?.types.includes('Files')) {
    isDragOver.value = true;
  }
}

function onDragLeave(event: DragEvent) {
  // 只在离开容器时才隐藏提示
  const relatedTarget = event.relatedTarget as Node | null;
  if (!relatedTarget || !(event.currentTarget as Node).contains(relatedTarget)) {
    isDragOver.value = false;
  }
}

function onDrop(event: DragEvent) {
  isDragOver.value = false;
  const files = event.dataTransfer?.files;
  if (files && files.length > 0) {
    // 处理所有拖拽的文件
    for (let i = 0; i < files.length; i++) {
      emit('selected', files[i]);
    }
  }
}

function onFilesSelected(files: File[] | FileList | null) {
  if (!files) return;
  const fileArray = Array.from(files);
  for (const file of fileArray) {
    emit('selected', file);
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
