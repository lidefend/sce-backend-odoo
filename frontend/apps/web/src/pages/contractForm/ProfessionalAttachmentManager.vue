<template>
  <section
    v-if="enabled || pending.length"
    data-professional-collaboration-component="attachments"
    :data-attachment-readiness="enabled ? 'ready' : 'fail_closed'"
  >
    <section v-if="editable && enabled" class="native-attachment-tools" data-collaboration-capability="attachments">
      <label class="chip-btn native-attachment-upload">
        {{ uploading ? uploadingLabel : uploadLabel }}
        <input type="file" :disabled="uploading" @change="emit('selected', $event)" />
      </label>
      <p v-if="error" class="validation-error native-chatter-message">{{ error }}</p>
    </section>
    <ul v-if="pending.length" class="native-pending-attachments">
      <li v-for="item in pending" :key="item.key">
        <span>{{ item.name }}</span>
        <ScButton variant="ghost" size="small" class="native-attachment-download" :disabled="uploading" @click="emit('remove', item.key)">移除</ScButton>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import ScButton from '../../components/design-system/ScButton.vue';
export type PendingProfessionalAttachment = { key: string; name: string; size: number; file: File };
defineProps<{ editable: boolean; enabled: boolean; uploading: boolean; uploadLabel: string; uploadingLabel: string; error: string; pending: PendingProfessionalAttachment[] }>();
const emit = defineEmits<{ selected: [event: Event]; remove: [key: string] }>();
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
